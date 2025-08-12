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

from opensearchpy import OpenSearch, helpers
from opensearchpy.exceptions import ConnectionError, RequestError
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class OpenSearchIndexer:
    """Advanced OpenSearch client with optimization and monitoring."""
    
    def __init__(self, host: Optional[str] = None, timeout: int = 60):
        self.host = host or os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
        self.timeout = timeout
        self.client = None
        
        # Index names
        self.documents_index = "documents"
        self.chunks_index = "chunks"
        
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
                
                # Test connection
                if self.client.ping():
                    logger.info(f"Successfully connected to OpenSearch at {self.host}")
                    return True
                else:
                    raise ConnectionError("Ping failed")
                    
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect to OpenSearch after {max_retries} attempts")
                    raise ConnectionError(f"OpenSearch connection failed: {e}")
        
        return False
    
    def create_indices(self, force_recreate: bool = False) -> bool:
        """Create optimized indices for documents and chunks."""
        if not self.client:
            logger.error("OpenSearch client not connected")
            return False
        
        try:
            # Create documents index
            success = self._create_documents_index(force_recreate)
            success &= self._create_chunks_index(force_recreate)
            
            if success:
                logger.info("All indices created successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating indices: {e}")
            return False
    
    def _create_documents_index(self, force_recreate: bool = False) -> bool:
        """Create optimized documents index."""
        if force_recreate and self.client.indices.exists(index=self.documents_index):
            logger.info(f"Deleting existing index: {self.documents_index}")
            self.client.indices.delete(index=self.documents_index)
        
        if self.client.indices.exists(index=self.documents_index):
            logger.info(f"Index '{self.documents_index}' already exists")
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
                    "text_snippet": {
                        "type": "text",
                        "analyzer": "content_analyzer"
                    },
                    "timestamp": {
                        "type": "date",
                        "format": "epoch_second||strict_date_optional_time"
                    }
                }
            }
        }
        
        try:
            self.client.indices.create(index=self.documents_index, body=documents_mapping)
            logger.info(f"Created documents index: {self.documents_index}")
            return True
        except RequestError as e:
            logger.error(f"Error creating documents index: {e}")
            return False
    
    def _create_chunks_index(self, force_recreate: bool = False) -> bool:
        """Create optimized chunks index for search."""
        if force_recreate and self.client.indices.exists(index=self.chunks_index):
            logger.info(f"Deleting existing index: {self.chunks_index}")
            self.client.indices.delete(index=self.chunks_index)
        
        if self.client.indices.exists(index=self.chunks_index):
            logger.info(f"Index '{self.chunks_index}' already exists")
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
                        "type": "text",
                        "analyzer": "search_analyzer",
                        "fields": {
                            "exact": {"type": "keyword"},
                            "ngram": {
                                "type": "text",
                                "analyzer": "standard"
                            }
                        }
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
            self.client.indices.create(index=self.chunks_index, body=chunks_mapping)
            logger.info(f"Created chunks index: {self.chunks_index}")
            return True
        except RequestError as e:
            logger.error(f"Error creating chunks index: {e}")
            return False
    
    def optimize_for_bulk_indexing(self) -> Dict[str, Any]:
        """Optimize index settings for bulk operations."""
        if not self.client:
            return {}
        
        original_settings = {}
        
        for index_name in [self.documents_index, self.chunks_index]:
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
                
                # Force refresh after restoring settings
                self.client.indices.refresh(index=index_name)
                
                 # Add this after restoring settings:
                for index_name in [self.documents_index, self.chunks_index]:
                    self.client.indices.refresh(index=index_name)
                logger.info("Forced index refresh after bulk operations")
                
                logger.info(f"Restored settings for index '{index_name}'")
                
            except Exception as e:
                logger.warning(f"Could not restore settings for {index_name}: {e}")
    
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
            # Generate actions for bulk indexing
            def generate_actions():
                # Index documents
                for doc in documents:
                    yield {
                        "_index": self.documents_index,
                        "_id": doc["document_id"],
                        "_source": doc
                    }
                
                # Index chunks
                for chunk in chunks:
                    yield {
                        "_index": self.chunks_index,
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
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of OpenSearch cluster."""
        if not self.client:
            return {"status": "unhealthy", "reason": "Client not initialized"}
        
        try:
            # Cluster health
            cluster_health = self.client.cluster.health()
            
            # Index stats
            indices_stats = {}
            for index_name in [self.documents_index, self.chunks_index]:
                if self.client.indices.exists(index=index_name):
                    stats = self.client.indices.stats(index=index_name)
                    indices_stats[index_name] = {
                        "doc_count": stats["indices"][index_name]["total"]["docs"]["count"],
                        "size_mb": stats["indices"][index_name]["total"]["store"]["size_in_bytes"] / (1024 * 1024)
                    }
            
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
            
            response = self.client.search(index=self.chunks_index, body=search_body)
            
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
