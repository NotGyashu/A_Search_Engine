# core/opensearch_service.py
import os
import logging
import boto3
from typing import List, Dict, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv

load_dotenv()

class OpenSearchService:
    """
    Clean, modular OpenSearch service for document and chunk retrieval.
    Each method has a single, clear responsibility.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.documents_index = "documents"
        self.chunks_index = "chunks"
        self.os_client = self._initialize_connection()

    def _initialize_connection(self) -> OpenSearch:
        """Initialize OpenSearch connection with proper error handling."""
        try:
            host = os.environ.get("OPENSEARCH_HOST")
            if not host:
                raise ValueError("OPENSEARCH_HOST environment variable is not set.")

            region = os.environ.get("AWS_REGION", "us-east-1")
            service = "es"

            session = boto3.Session()
            credentials = session.get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token
            )

            client = OpenSearch(
                hosts=[{"host": host.replace("https://", ""), "port": 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection
            )

            if not client.ping():
                raise ConnectionError("Could not connect to OpenSearch.")
            
            self.logger.info("OpenSearch client initialized successfully.")
            return client
            
        except Exception as e:
            self.logger.critical(f"Failed to initialize OpenSearch client: {e}", exc_info=True)
            raise ConnectionError(f"OpenSearch connection failed: {e}")

    def search_chunks(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Primary search method - searches chunks with enhanced matching.
        Returns raw chunk results without document metadata.
        """
        if not self.os_client:
            self.logger.error("Search failed: OpenSearch client is not available.")
            return []

        search_body = self._build_chunk_search_query(query, limit)
        
        try:
            response = self.os_client.search(index=self.chunks_index, body=search_body)
            return response['hits']['hits']
        except Exception as e:
            self.logger.error(f"Chunk search failed for '{query}': {e}", exc_info=True)
            return []

    def search_chunks_fallback(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Fallback search with relaxed matching when primary search fails.
        """
        if not self.os_client:
            return []

        search_body = self._build_fallback_search_query(query, limit)
        
        try:
            response = self.os_client.search(index=self.chunks_index, body=search_body)
            return response['hits']['hits']
        except Exception as e:
            self.logger.error(f"Fallback search failed for '{query}': {e}")
            return []

    def get_documents_by_ids(self, document_ids: List[str]) -> Dict[str, Dict]:
        """
        Retrieve document metadata for given document IDs.
        Returns a dictionary mapping document_id -> document_data.
        """
        if not document_ids or not self.os_client:
            return {}

        try:
            response = self.os_client.mget(index=self.documents_index, body={"ids": document_ids})
            return {
                doc['_id']: doc['_source'] 
                for doc in response.get('docs', []) 
                if doc.get('found')
            }
        except Exception as e:
            self.logger.error(f"Document retrieval failed for IDs {document_ids}: {e}")
            return {}

    def apply_domain_diversity(self, chunk_hits: List[Dict], limit: int) -> List[Dict]:
        """
        Apply domain diversity filtering to ensure varied sources.
        Pure function - no side effects.
        """
        if not chunk_hits:
            return []

        domain_counts = {}
        diverse_results = []
        max_per_domain = max(1, limit // 3)  # Allow max 1/3 results per domain
        
        # First pass: respect domain limits
        for hit in chunk_hits:
            if len(diverse_results) >= limit:
                break
                
            domain = hit['_source'].get('domain', 'unknown')
            domain_count = domain_counts.get(domain, 0)
            
            if domain_count < max_per_domain:
                diverse_results.append(hit)
                domain_counts[domain] = domain_count + 1
        
        # Second pass: fill remaining slots if needed
        if len(diverse_results) < limit:
            for hit in chunk_hits:
                if len(diverse_results) >= limit:
                    break
                if hit not in diverse_results:
                    diverse_results.append(hit)
        
        return diverse_results

    def merge_chunk_and_document_data(self, chunk_hits: List[Dict], documents: Dict[str, Dict]) -> List[Dict]:
        """
        Merge chunk results with document metadata.
        Pure function - creates new objects without modifying inputs.
        """
        merged_results = []
        
        for chunk_hit in chunk_hits:
            document_id = chunk_hit['_source']['document_id']
            document_data = documents.get(document_id, {})
            
            if document_data:
                # Create merged result preserving both chunk and document data
                merged_source = {
                    **document_data,  # Document metadata first
                    **chunk_hit['_source'],  # Chunk data second (can override)
                    'chunk_score': chunk_hit['_score']  # Preserve original chunk relevance
                }
                
                merged_result = {
                    '_id': document_id,
                    '_score': chunk_hit['_score'],
                    '_source': merged_source
                }
                merged_results.append(merged_result)
        
        return merged_results

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Main search interface - orchestrates the complete search flow.
        Clean, linear flow without nested function calls.
        """
        # Step 1: Search chunks
        chunk_hits = self.search_chunks(query, limit * 3)  # Get more for diversity
        
        # Step 2: Try fallback if no results
        if not chunk_hits:
            chunk_hits = self.search_chunks_fallback(query, limit)
        
        if not chunk_hits:
            return []
        
        # Step 3: Apply domain diversity
        diverse_chunks = self.apply_domain_diversity(chunk_hits, limit)
        
        # Step 4: Get document metadata
        document_ids = [hit['_source']['document_id'] for hit in diverse_chunks]
        documents = self.get_documents_by_ids(document_ids)
        
        # Step 5: Merge and return results
        return self.merge_chunk_and_document_data(diverse_chunks, documents)

    def _build_chunk_search_query(self, query: str, limit: int) -> Dict:
        """Build the primary chunk search query."""
        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "text_chunk^1.5",
                                    "headings^3.0",
                                    "keywords^2.0",
                                    "title^2.5"
                                ],
                                "fuzziness": "AUTO",
                                "operator": "or"
                            }
                        },
                        {
                            "match_phrase": {
                                "text_chunk": {
                                    "query": query,
                                    "boost": 2.0
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"quality_score": {"order": "desc"}},
                {"domain_score": {"order": "desc"}}
            ],
            "size": limit * 3,
            "_source": [
                "document_id", "text_chunk", "headings", "keywords",
                "title", "url", "domain", "quality_score", "domain_score",
                "content_categories", "chunk_index", "word_count"
            ]
        }

    def _build_fallback_search_query(self, query: str, limit: int) -> Dict:
        """Build the fallback search query with relaxed matching."""
        return {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"title": {"query": query, "boost": 2.0}}},
                        {"match": {"text_chunk": query}},
                        {"wildcard": {"url": f"*{query.lower()}*"}}
                    ],
                    "minimum_should_match": 1
                }
            },
            "sort": [{"_score": {"order": "desc"}}],
            "size": limit,
            "_source": [
                "document_id", "text_chunk", "headings", "keywords",
                "title", "url", "domain", "quality_score", "domain_score",
                "content_categories", "chunk_index", "word_count"
            ]
        }

    def health_check(self) -> Dict:
        """Check OpenSearch cluster health."""
        if not self.os_client:
            return {"status": "unhealthy", "reason": "Client not initialized."}
        
        try:
            info = self.os_client.info()
            return {"status": "healthy", "cluster_info": info}
        except Exception as e:
            self.logger.error(f"OpenSearch health check failed: {e}")
            return {"status": "unhealthy", "reason": str(e)}