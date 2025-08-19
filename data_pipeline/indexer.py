"""
OpenSearch Client and Indexing Manager

Handles all OpenSearch operations including index creation, bulk indexing,
and connection management with advanced optimization features.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Generator
from urllib.parse import urlparse
import time
from datetime import datetime

from opensearchpy import OpenSearch, helpers, RequestsHttpConnection
from opensearchpy.exceptions import ConnectionError, RequestError
from dotenv import load_dotenv
import boto3
from requests_aws4auth import AWS4Auth

load_dotenv()
logger = logging.getLogger(__name__)


class OpenSearchIndexer:
    """Advanced OpenSearch client with optimization and monitoring."""
    
    def __init__(self, host: Optional[str] = None, timeout: int = 60):
        self.host = host or os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
        self.timeout = timeout
        self.client = None
        
        # Index base names (will be date-stamped for daily indices)
        self.documents_index_base = "documents"
        self.chunks_index_base = "chunks"
        
        # Performance tracking
        self.stats = {
            'documents_indexed': 0,
            'chunks_indexed': 0,
            'failed_operations': 0,
            'total_indexing_time': 0,
            'last_operation_time': None
        }
        
        # Connect to OpenSearch
        self._connect()
    
    def _connect(self) -> bool:
        """Establish connection to OpenSearch with retry logic."""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                parsed_url = urlparse(self.host)
                
                # Check if this is an AWS OpenSearch domain
                is_aws_domain = 'amazonaws.com' in self.host or 'es.amazonaws.com' in self.host
                
                if is_aws_domain:
                    # Use AWS authentication
                    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
                    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
                    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
                    
                    if not aws_access_key or not aws_secret_key:
                        # Try to get credentials from boto3/AWS CLI
                        try:
                            session = boto3.Session()
                            credentials = session.get_credentials()
                            if credentials:
                                aws_access_key = credentials.access_key
                                aws_secret_key = credentials.secret_key
                                aws_session_token = credentials.token
                                logger.info("Using AWS credentials from boto3 session")
                            else:
                                raise Exception("No AWS credentials found")
                        except Exception as e:
                            logger.error(f"Failed to get AWS credentials: {e}")
                            logger.error("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env file")
                            raise ConnectionError("AWS credentials not configured")
                    
                    # Create AWS4Auth instance
                    aws_auth = AWS4Auth(
                        aws_access_key, 
                        aws_secret_key, 
                        aws_region, 
                        'es',
                        session_token=getattr(credentials, 'token', None) if 'credentials' in locals() else None
                    )
                    
                    self.client = OpenSearch(
                        hosts=[{
                            "host": parsed_url.hostname,
                            "port": parsed_url.port or 443
                        }],
                        http_auth=aws_auth,
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection,
                        timeout=self.timeout,
                        max_retries=3,
                        retry_on_timeout=True
                    )
                    
                    logger.info(f"Connecting to AWS OpenSearch with authentication at {self.host}")
                    
                else:
                    # Use regular connection for local/non-AWS OpenSearch
                    self.client = OpenSearch(
                        hosts=[{
                            "host": parsed_url.hostname,
                            "port": parsed_url.port or (443 if parsed_url.scheme == "https" else 9200)
                        }],
                        use_ssl=(parsed_url.scheme == "https"),
                        verify_certs=True,
                        timeout=self.timeout,
                        max_retries=3,
                        retry_on_timeout=True
                    )
                    
                    logger.info(f"Connecting to OpenSearch (non-AWS) at {self.host}")
                
                # Test connection
                cluster_info = self.client.info()
                logger.info(f"Successfully connected to OpenSearch: {cluster_info.get('version', {}).get('number', 'unknown')}")
                return True
                    
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect to OpenSearch after {max_retries} attempts")
                    raise ConnectionError(f"OpenSearch connection failed: {e}")
        
        return False
    
    def _get_daily_index_name(self, base_name: str) -> str:
        """Generates an index name with the current date, e.g., 'chunks-2025-08-14'."""
        return f"{base_name}-{datetime.utcnow().strftime('%Y-%m-%d')}"
    
    def create_index_templates_if_needed(self) -> bool:
        """Creates index templates for daily indices with ISM policy support."""
        if not self.client:
            logger.error("OpenSearch client not connected")
            return False
        
        try:
            # Create template for documents indices
            docs_success = self._create_documents_template()
            # Create template for chunks indices  
            chunks_success = self._create_chunks_template()
            
            if docs_success and chunks_success:
                logger.info("All index templates created/verified successfully")
            
            return docs_success and chunks_success
            
        except Exception as e:
            logger.error(f"Error creating index templates: {e}")
            return False
    
    def _create_documents_template(self) -> bool:
        """Create index template for documents indices."""
        template_name = f"{self.documents_index_base}_template"
        
        # Check if template already exists
        try:
            if self.client.indices.exists_index_template(name=template_name):
                logger.info(f"Documents template '{template_name}' already exists")
                return True
        except Exception:
            # Fallback for older OpenSearch versions that don't support exists_index_template
            try:
                self.client.indices.get_index_template(name=template_name)
                logger.info(f"Documents template '{template_name}' already exists")
                return True
            except:
                pass  # Template doesn't exist, continue to create it
        
        template_body = {
            "index_patterns": [f"{self.documents_index_base}-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "title_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "stop", "snowball"]
                            },
                            "content_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "stop", "snowball", "word_delimiter"]
                            }
                        }
                    },
                    "index": {
                        "refresh_interval": "30s",
                        "number_of_routing_shards": 1
                    },
                    # ISM policy configuration
                    "plugins.index_state_management.policy_id": "daily_crawl_data_management",
                    "plugins.index_state_management.rollover_alias": self.documents_index_base
                },
                "mappings": {
                    "properties": {
                        "url": {
                            "type": "keyword",
                            "index": True
                        },
                        "title": {
                            "type": "text",
                            "analyzer": "title_analyzer",
                            "fields": {
                                "raw": {"type": "keyword"},
                                "suggest": {
                                    "type": "completion",
                                    "analyzer": "simple"
                                }
                            }
                        },
                        "domain": {
                            "type": "keyword",
                            "index": True
                        },
                        "description": {
                            "type": "text",
                            "analyzer": "content_analyzer"
                        },
                        "content_type": {
                            "type": "keyword",
                            "index": True
                        },
                        "categories": {
                            "type": "keyword",
                            "index": True
                        },
                        "keywords": {
                            "type": "keyword",
                            "index": True
                        },
                        "canonical_url": {
                            "type": "keyword",
                            "index": False
                        },
                        "published_date": {
                            "type": "date",
                            "format": "strict_date_optional_time||yyyy-MM-dd||epoch_millis"
                        },
                        "modified_date": {
                            "type": "date",
                            "format": "strict_date_optional_time||yyyy-MM-dd||epoch_millis"
                        },
                        "author_info": {
                            "type": "object",
                            "enabled": False
                        },
                        "structured_data": {
                            "type": "object",
                            "enabled": False
                        },
                        "images": {
                            "type": "object",
                            "enabled": False
                        },
                        "table_of_contents": {
                            "type": "object",
                            "enabled": False
                        },
                        "semantic_info": {
                            "type": "object",
                            "enabled": False
                        },
                        "icons": {
                            "type": "object",
                            "enabled": False
                        }
                    }
                }
            },
            "priority": 200,
            "composed_of": [],
            "_meta": {
                "description": "Template for daily documents indices with automated lifecycle management",
                "created_by": "search_engine_pipeline"
            }
        }
        
        try:
            self.client.indices.put_index_template(name=template_name, body=template_body)
            logger.info(f"Created documents index template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating documents template: {e}")
            return False
    
    def _create_chunks_template(self) -> bool:
        """Create index template for chunks indices."""
        template_name = f"{self.chunks_index_base}_template"
        
        # Check if template already exists
        try:
            if self.client.indices.exists_index_template(name=template_name):
                logger.info(f"Chunks template '{template_name}' already exists")
                return True
        except Exception:
            # Fallback for older OpenSearch versions that don't support exists_index_template
            try:
                self.client.indices.get_index_template(name=template_name)
                logger.info(f"Chunks template '{template_name}' already exists")
                return True
            except:
                pass  # Template doesn't exist, continue to create it
        
        template_body = {
            "index_patterns": [f"{self.chunks_index_base}-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "search_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "stop",
                                    "snowball",
                                    "word_delimiter",
                                    "unique"
                                ]
                            }
                        }
                    },
                    "index": {
                        "refresh_interval": "30s",
                        "number_of_routing_shards": 1
                    },
                    # ISM policy configuration
                    "plugins.index_state_management.policy_id": "daily_crawl_data_management",
                    "plugins.index_state_management.rollover_alias": self.chunks_index_base
                },
                "mappings": {
                    "properties": {
                        "document_id": {
                            "type": "keyword",
                            "index": True
                        },
                        "text_chunk": {
                            "type": "match_only_text",
                            "analyzer": "search_analyzer"
                        },
                        "headings": {
                            "type": "text",
                            "analyzer": "search_analyzer"
                        },
                        "domain_score": {
                            "type": "half_float",
                            "index": True
                        },
                        "quality_score": {
                            "type": "half_float",
                            "index": True
                        },
                        "word_count": {
                            "type": "integer",
                            "index": True
                        },
                        "content_categories": {
                            "type": "keyword",
                            "index": True
                        },
                        "keywords": {
                            "type": "keyword",
                            "index": True
                        }
                    }
                }
            },
            "priority": 200,
            "composed_of": [],
            "_meta": {
                "description": "Template for daily chunks indices with automated lifecycle management",
                "created_by": "search_engine_pipeline"
            }
        }
        
        try:
            self.client.indices.put_index_template(name=template_name, body=template_body)
            logger.info(f"Created chunks index template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating chunks template: {e}")
            return False
    
    def create_ism_policy_if_needed(self, retention_days: int = 90) -> bool:
        """Create ISM policy for automated data lifecycle management."""
        if not self.client:
            logger.error("OpenSearch client not connected")
            return False
        
        policy_id = "daily_crawl_data_management"
        
        try:
            # Check if policy already exists
            try:
                existing_policy = self.client.transport.perform_request(
                    "GET", f"/_plugins/_ism/policies/{policy_id}"
                )
                logger.info(f"ISM policy '{policy_id}' already exists")
                return True
            except:
                pass  # Policy doesn't exist, continue to create it
            
            # Define the ISM policy
            policy_body = {
                "policy": {
                    "policy_id": policy_id,
                    "description": f"Manages daily web crawl data. Deletes after {retention_days} days.",
                    "default_state": "hot",
                    "states": [
                        {
                            "name": "hot",
                            "actions": [],
                            "transitions": [
                                {
                                    "state_name": "delete",
                                    "conditions": {
                                        "min_index_age": f"{retention_days}d"
                                    }
                                }
                            ]
                        },
                        {
                            "name": "delete",
                            "actions": [
                                {
                                    "delete": {}
                                }
                            ],
                            "transitions": []
                        }
                    ],
                    "ism_template": [
                        {
                            "index_patterns": [f"{self.documents_index_base}-*", f"{self.chunks_index_base}-*"],
                            "priority": 100
                        }
                    ]
                }
            }
            
            # Create the policy
            response = self.client.transport.perform_request(
                "PUT", f"/_plugins/_ism/policies/{policy_id}",
                body=policy_body
            )
            
            logger.info(f"Created ISM policy '{policy_id}' with {retention_days} day retention")
            return True
            
        except Exception as e:
            logger.warning(f"Could not create ISM policy (may not be supported): {e}")
            # ISM may not be available in all OpenSearch distributions
            return True  # Don't fail the pipeline if ISM isn't available
    
    def create_indices_if_needed(self) -> bool:
        """Create daily indices, templates, and ISM policies if they don't exist."""
        if not self.client:
            logger.error("OpenSearch client not connected")
            return False
        
        try:
            # Step 1: Create ISM policy first (if supported)
            self.create_ism_policy_if_needed()
            
            # Step 2: Create index templates
            templates_success = self.create_index_templates_if_needed()
            
            # Step 3: Create today's daily indices with alias management
            docs_success = self._create_daily_documents_index()
            chunks_success = self._create_daily_chunks_index()
            
            if docs_success and chunks_success:
                logger.info("All daily indices, templates, and policies created/verified successfully")
            
            return docs_success and chunks_success and templates_success
            
        except Exception as e:
            logger.error(f"Error creating indices: {e}")
            return False
    
    def _create_daily_documents_index(self) -> bool:
        """Create today's documents index and manage alias."""
        docs_index_name = self._get_daily_index_name(self.documents_index_base)
        docs_alias_name = self.documents_index_base  # e.g., 'documents'
        
        # Check if today's index already exists
        if self.client.indices.exists(index=docs_index_name):
            logger.info(f"Daily documents index '{docs_index_name}' already exists")
            return True
        else:
            # Create the index if it doesn't exist
            if not self._create_documents_index_with_name(docs_index_name):
                return False  # Stop if index creation fails

        try:
            # This command is idempotent and will create the alias or do nothing if it's correct.
            self.client.indices.put_alias(index=docs_index_name, name=docs_alias_name)
            logger.info(f"Ensured index '{docs_index_name}' has alias '{docs_alias_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to add alias '{docs_alias_name}' to index '{docs_index_name}': {e}")
            return False
    
    def _create_daily_chunks_index(self) -> bool:
        """Create today's chunks index and manage alias."""
        chunks_index_name = self._get_daily_index_name(self.chunks_index_base)
        chunks_alias_name = self.chunks_index_base  # e.g., 'chunks'
        
        # Check if today's index already exists
        if self.client.indices.exists(index=chunks_index_name):
            logger.info(f"Daily chunks index '{chunks_index_name}' already exists")
        else:
            # Create the index if it doesn't exist
            if not self._create_chunks_index_with_name(chunks_index_name):
                return False  # Stop if index creation fails
        
        try:
            self.client.indices.put_alias(index=chunks_index_name, name=chunks_alias_name)
            logger.info(f"Ensured index '{chunks_index_name}' has alias '{chunks_alias_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to add alias '{chunks_alias_name}' to index '{chunks_index_name}': {e}")
            return False
    
    def _create_documents_index_with_name(self, index_name: str) -> bool:
        """Create optimized documents index with custom name."""
        if self.client.indices.exists(index=index_name):
            logger.info(f"Index '{index_name}' already exists")
            return True
        
        documents_mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,  # Start with 0 replicas for performance
                "analysis": {
                    "analyzer": {
                        "title_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop", "snowball"]
                        },
                        "content_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop", "snowball", "word_delimiter"]
                        }
                    }
                },
                "index": {
                    "refresh_interval": "30s",  # Optimize for bulk indexing
                    "number_of_routing_shards": 1
                }
            },
            "mappings": {
                "properties": {
                    "url": {
                        "type": "keyword",
                        "index": True
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "title_analyzer",
                        "fields": {
                            "raw": {"type": "keyword"},
                            "suggest": {
                                "type": "completion",
                                "analyzer": "simple"
                            }
                        }
                    },
                    "domain": {
                        "type": "keyword",
                        "index": True
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "content_analyzer"
                    },
                    "content_type": {
                        "type": "keyword",
                        "index": True
                    },
                    "categories": {
                        "type": "keyword",
                        "index": True
                    },
                    "keywords": {
                        "type": "keyword",
                        "index": True
                    },
                    "canonical_url": {
                        "type": "keyword",
                        "index": False
                    },
                    "published_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||yyyy-MM-dd||epoch_millis"
                    },
                    "modified_date": {
                        "type": "date",
                        "format": "strict_date_optional_time||yyyy-MM-dd||epoch_millis"
                    },
                    "author_info": {
                        "type": "object",
                        "enabled": False
                    },
                    "structured_data": {
                        "type": "object",
                        "enabled": False
                    },
                    "images": {
                        "type": "object",
                        "enabled": False
                    },
                    "table_of_contents": {
                        "type": "object",
                        "enabled": False
                    },
                    "semantic_info": {
                        "type": "object",
                        "enabled": False
                    }
                }
            }
        }
        
        try:
            self.client.indices.create(index=index_name, body=documents_mapping)
            logger.info(f"Created documents index: {index_name}")
            return True
        except RequestError as e:
            logger.error(f"Error creating documents index: {e}")
            return False
    
    def _create_chunks_index_with_name(self, index_name: str) -> bool:
        """Create optimized chunks index with custom name."""
        if self.client.indices.exists(index=index_name):
            logger.info(f"Index '{index_name}' already exists")
            return True
        
        chunks_mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "search_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "stop",
                                "snowball",
                                "word_delimiter",
                                "unique"
                            ]
                        }
                    }
                },
                "index": {
                    "refresh_interval": "30s",
                    "number_of_routing_shards": 1
                }
            },
            "mappings": {
                "properties": {
                    "document_id": {
                        "type": "keyword",
                        "index": True
                    },
                    "text_chunk": {
                        "type": "match_only_text",
                        "analyzer": "search_analyzer"
                    },
                    "headings": {
                        "type": "text",
                        "analyzer": "search_analyzer"
                    },
                    "domain_score": {
                        "type": "half_float",
                        "index": True
                    },
                    "quality_score": {
                        "type": "half_float",
                        "index": True
                    },
                    "word_count": {
                        "type": "integer",
                        "index": True
                    },
                    "content_categories": {
                        "type": "keyword",
                        "index": True
                    },
                    "keywords": {
                        "type": "keyword",
                        "index": True
                    }
                }
            }
        }
        
        try:
            self.client.indices.create(index=index_name, body=chunks_mapping)
            logger.info(f"Created chunks index: {index_name}")
            return True
        except RequestError as e:
            logger.error(f"Error creating chunks index: {e}")
            return False
    
    def optimize_for_bulk_indexing(self) -> Dict[str, Any]:
        """Optimize index settings for bulk operations."""
        if not self.client:
            return {}
        
        original_settings = {}
        
        # Get today's index names
        docs_index_name = self._get_daily_index_name(self.documents_index_base)
        chunks_index_name = self._get_daily_index_name(self.chunks_index_base)
        
        for index_name in [docs_index_name, chunks_index_name]:
            if not self.client.indices.exists(index=index_name):
                continue
            
            try:
                # Store original settings
                current_settings = self.client.indices.get_settings(index=index_name)
                original_settings[index_name] = current_settings[index_name]["settings"]["index"]
                
                # Apply bulk indexing optimizations
                bulk_settings = {
                    "refresh_interval": "-1",  # Disable refresh during bulk load
                    "number_of_replicas": "0",  # Remove replicas during bulk load
                    "translog": {
                        "durability": "async",
                        "flush_threshold_size": "1gb"
                    }
                }
                
                self.client.indices.put_settings(
                    index=index_name,
                    body={"index": bulk_settings}
                )
                
                logger.info(f"Optimized index '{index_name}' for bulk indexing")
                
            except Exception as e:
                logger.warning(f"Could not optimize index {index_name}: {e}")
        
        return original_settings
    
    def restore_settings(self, original_settings: Dict[str, Any]):
        """Restore original index settings after bulk operations."""
        if not self.client or not original_settings:
            return

        indices_to_refresh = []
        
        for index_name, settings in original_settings.items():
            try:
                restore_settings = {
                    "refresh_interval": settings.get("refresh_interval", "1s"),
                    "number_of_replicas": settings.get("number_of_replicas", "1"),
                    "translog": {
                        "durability": "request"
                    }
                }
                
                self.client.indices.put_settings(
                    index=index_name,
                    body={"index": restore_settings}
                )
                
                indices_to_refresh.append(index_name)
                logger.info(f"Restored settings for index '{index_name}'")
                
            except Exception as e:
                logger.warning(f"Could not restore settings for {index_name}: {e}")
        
        # Refresh all indices once after restoring all settings
        if indices_to_refresh:
            try:
                for index_name in indices_to_refresh:
                    self.client.indices.refresh(index=index_name)
                logger.info("Forced index refresh after bulk operations")
            except Exception as e:
                logger.warning(f"Could not refresh indices: {e}")
    
    def bulk_index_documents(self, documents: List[Dict[str, Any]], 
                           chunks: List[Dict[str, Any]], 
                           thread_count: int = 4, 
                           chunk_size: int = 500) -> Dict[str, int]:
        """Perform bulk indexing with monitoring and error handling."""
        if not self.client:
            logger.error("OpenSearch client not connected")
            return {"success": 0, "failed": 0}
        
        start_time = time.time()
        results = {"success": 0, "failed": 0}
        
        try:
            # Get today's index names
            docs_index_name = self._get_daily_index_name(self.documents_index_base)
            chunks_index_name = self._get_daily_index_name(self.chunks_index_base)
            
            # Generate actions for bulk indexing
            def generate_actions():
                # Index documents
                for doc in documents:
                    yield {
                        "_index": docs_index_name,
                        "_id": doc["document_id"],
                        "_source": doc
                    }
                
                # Index chunks
                for chunk in chunks:
                    yield {
                        "_index": chunks_index_name,
                        "_id": chunk["chunk_id"],
                        "_source": chunk
                    }
            
            # Perform bulk indexing with parallel threads
            for success, info in helpers.parallel_bulk(
                client=self.client,
                actions=generate_actions(),
                thread_count=min(thread_count, 4),
                chunk_size=chunk_size,
                request_timeout=60,
                raise_on_error=False,
                raise_on_exception=False
            ):
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    logger.warning(f"Document indexing failed: {info}")
            
            # Update stats
            indexing_time = time.time() - start_time
            self.stats['documents_indexed'] += len(documents)
            self.stats['chunks_indexed'] += len(chunks)
            self.stats['failed_operations'] += results["failed"]
            self.stats['total_indexing_time'] += indexing_time
            self.stats['last_operation_time'] = time.time()
            
            logger.info(
                f"Bulk indexing completed in {indexing_time:.2f}s. "
                f"Success: {results['success']}, Failed: {results['failed']}"
            )
            
        except Exception as e:
            logger.error(f"Critical error during bulk indexing: {e}")
            results["failed"] += len(documents) + len(chunks)
        
        return results
    
    def cleanup_old_indices(self, days_to_keep: int = 7) -> Dict[str, int]:
        """Remove indices older than specified days to manage storage."""
        if not self.client:
            logger.error("OpenSearch client not connected")
            return {"deleted": 0, "failed": 0}
        
        results = {"deleted": 0, "failed": 0}
        
        try:
            # Get current date
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
            
            # Get all indices
            all_indices = self.client.indices.get_alias(index="*")
            
            for index_name in all_indices.keys():
                # Check if it's a daily index (contains date pattern)
                if ('-202' in index_name and 
                    (index_name.startswith(self.documents_index_base) or 
                     index_name.startswith(self.chunks_index_base))):
                    
                    # Extract date from index name
                    parts = index_name.split('-')
                    if len(parts) >= 4:  # e.g., documents-2025-08-14
                        try:
                            index_date_str = '-'.join(parts[-3:])  # 2025-08-14
                            if index_date_str < cutoff_str:
                                # Delete old index
                                self.client.indices.delete(index=index_name)
                                logger.info(f"Deleted old index: {index_name}")
                                results["deleted"] += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete index {index_name}: {e}")
                            results["failed"] += 1
            
            if results["deleted"] > 0:
                logger.info(f"Cleanup completed: deleted {results['deleted']} old indices")
            
        except Exception as e:
            logger.error(f"Error during index cleanup: {e}")
            results["failed"] += 1
        
        return results
    
    def get_ism_policy_status(self) -> Dict[str, Any]:
        """Get the status of ISM policies and affected indices."""
        if not self.client:
            return {"error": "OpenSearch client not connected"}
        
        policy_id = "daily_crawl_data_management"
        status = {
            "policy_exists": False,
            "policy_details": None,
            "managed_indices": [],
            "unmanaged_indices": []
        }
        
        try:
            # Check if policy exists
            try:
                policy_response = self.client.transport.perform_request(
                    "GET", f"/_plugins/_ism/policies/{policy_id}"
                )
                status["policy_exists"] = True
                status["policy_details"] = policy_response
            except:
                pass
            
            # Get all daily indices and their ISM status
            all_indices = self.client.indices.get_alias(index="*")
            
            for index_name in all_indices.keys():
                if (index_name.startswith(self.documents_index_base) or 
                    index_name.startswith(self.chunks_index_base)):
                    
                    try:
                        settings = self.client.indices.get_settings(index=index_name)
                        index_policy = settings[index_name]["settings"]["index"].get(
                            "plugins.index_state_management.policy_id"
                        )
                        
                        index_info = {
                            "name": index_name,
                            "policy_id": index_policy,
                            "managed": index_policy == policy_id
                        }
                        
                        if index_policy == policy_id:
                            status["managed_indices"].append(index_info)
                        else:
                            status["unmanaged_indices"].append(index_info)
                            
                    except Exception as e:
                        status["unmanaged_indices"].append({
                            "name": index_name,
                            "error": str(e),
                            "managed": False
                        })
            
        except Exception as e:
            status["error"] = str(e)
        
        return status
    
    def apply_ism_policy_to_existing_indices(self) -> Dict[str, int]:
        """Apply ISM policy to existing indices that don't have it."""
        if not self.client:
            logger.error("OpenSearch client not connected")
            return {"applied": 0, "failed": 0}
        
        results = {"applied": 0, "failed": 0}
        policy_id = "daily_crawl_data_management"
        
        try:
            # Get all daily indices
            all_indices = self.client.indices.get_alias(index="*")
            
            for index_name in all_indices.keys():
                if (index_name.startswith(self.documents_index_base) or 
                    index_name.startswith(self.chunks_index_base)):
                    
                    try:
                        # Check if index already has the policy
                        settings = self.client.indices.get_settings(index=index_name)
                        current_policy = settings[index_name]["settings"]["index"].get(
                            "plugins.index_state_management.policy_id"
                        )
                        
                        if current_policy != policy_id:
                            # Apply the policy to this index
                            self.client.transport.perform_request(
                                "POST", f"/_plugins/_ism/add/{index_name}",
                                body={"policy_id": policy_id}
                            )
                            logger.info(f"Applied ISM policy to index: {index_name}")
                            results["applied"] += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to apply ISM policy to {index_name}: {e}")
                        results["failed"] += 1
            
            if results["applied"] > 0:
                logger.info(f"Applied ISM policy to {results['applied']} indices")
            
        except Exception as e:
            logger.error(f"Error applying ISM policy to existing indices: {e}")
            results["failed"] += 1
        
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of OpenSearch cluster."""
        if not self.client:
            return {"status": "unhealthy", "reason": "Client not initialized"}
        
        try:
            # Cluster health
            cluster_health = self.client.cluster.health()
            
            # More robust index stats collection that properly handles aliases.
            indices_stats = {}
            for alias_name in [self.documents_index_base, self.chunks_index_base]:
                if self.client.indices.exists_alias(name=alias_name):
                    # Get stats for the alias. The response will contain data for all backing indices.
                    stats = self.client.indices.stats(index=alias_name)
                    
                    # Initialize counters for the alias
                    total_docs = 0
                    total_size_bytes = 0
                    
                    # Iterate through all indices in the response and aggregate their stats.
                    # This correctly handles cases where an alias might point to multiple indices.
                    if "indices" in stats:
                        for index_data in stats["indices"].values():
                            total_docs += index_data.get("total", {}).get("docs", {}).get("count", 0)
                            total_size_bytes += index_data.get("total", {}).get("store", {}).get("size_in_bytes", 0)

                    indices_stats[alias_name] = {
                        "doc_count": total_docs,
                        "size_mb": total_size_bytes / (1024 * 1024)
                    }
            # --- FIX ENDS HERE ---
            
            return {
                "status": "healthy",
                "cluster_status": cluster_health["status"],
                "cluster_name": cluster_health["cluster_name"],
                "indices": indices_stats,
                "indexing_stats": self.stats
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "reason": str(e)}
    
    def search_test(self, query: str = "test", limit: int = 5) -> Dict[str, Any]:
        """Test search functionality."""
        if not self.client:
            return {"error": "Client not connected"}
        
        try:
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["text_chunk", "headings"],
                        "fuzziness": "AUTO"
                    }
                },
                "size": limit
            }
            
            response = self.client.search(index=self.chunks_index_base, body=search_body)
            
            return {
                "total_hits": response["hits"]["total"]["value"],
                "search_time_ms": response["took"],
                "results": len(response["hits"]["hits"])
            }
            
        except Exception as e:
            logger.error(f"Search test failed: {e}")
            return {"error": str(e)}
    
    def get_indexing_stats(self) -> Dict[str, Any]:
        """Get detailed indexing statistics."""
        return {
            **self.stats,
            "avg_indexing_rate": (
                (self.stats['documents_indexed'] + self.stats['chunks_indexed']) / 
                max(self.stats['total_indexing_time'], 1)
            ) if self.stats['total_indexing_time'] > 0 else 0,
            "success_rate": (
                (self.stats['documents_indexed'] + self.stats['chunks_indexed']) / 
                max(self.stats['documents_indexed'] + self.stats['chunks_indexed'] + self.stats['failed_operations'], 1) * 100
            )
        }
    
    def close(self):
        """Close the OpenSearch client connection."""
        if self.client:
            try:
                # No explicit close method in opensearch-py, but we can clear the reference
                self.client = None
                logger.info("OpenSearch client connection closed")
            except Exception as e:
                logger.warning(f"Error closing OpenSearch client: {e}")
