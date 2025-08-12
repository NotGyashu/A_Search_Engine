# core/opensearch_service.py
import os
import logging
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv

load_dotenv()

class OpenSearchService:
    """Manages all interactions with AWS OpenSearch."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Define both indices
        self.documents_index = "documents"
        self.chunks_index = "chunks"
        self.os_client = self._connect()

    def _connect(self) -> OpenSearch:
        """Establishes and verifies the OpenSearch connection."""
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

    def search(self, query: str, limit: int = 10):
        """
        Enhanced search with domain diversity and quality scoring.
        1. Search the chunks index to get the most relevant content.
        2. Apply domain diversity filtering.
        3. Return formatted results with enhanced metadata.
        """
        if not self.os_client:
            self.logger.error("Search failed: OpenSearch client is not available.")
            return []

        try:
            # Step 1: Search the chunks index with enhanced matching
            search_body = {
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
                "size": limit * 3,  # Get more results for diversity filtering
                "_source": [
                    "document_id", "text_chunk", "headings", "keywords",
                    "title", "url", "domain", "quality_score", "domain_score",
                    "content_categories", "chunk_index"
                ]
            }
            
            response = self.os_client.search(index=self.chunks_index, body=search_body)
            hits = response['hits']['hits']
            
            if not hits:
                return []

            # Step 2: Apply domain diversity and get unique documents
            diverse_results = self._apply_domain_diversity(hits, limit)
            
            # Step 3: Enhance results with document metadata
            return self._enhance_with_document_metadata(diverse_results)

        except Exception as e:
            self.logger.error(f"Error during OpenSearch search for query '{query}': {e}", exc_info=True)
            return []

    def _apply_domain_diversity(self, hits, limit):
        """Apply domain diversity to ensure varied sources in results."""
        domain_counts = {}
        diverse_results = []
        max_per_domain = max(1, limit // 3)  # Allow max 1/3 results per domain
        
        for hit in hits:
            if len(diverse_results) >= limit:
                break
                
            domain = hit['_source'].get('domain', 'unknown')
            domain_count = domain_counts.get(domain, 0)
            
            # Add result if we haven't exceeded domain limit
            if domain_count < max_per_domain:
                diverse_results.append(hit)
                domain_counts[domain] = domain_count + 1
        
        # If we still need more results and have remaining hits
        if len(diverse_results) < limit:
            for hit in hits:
                if len(diverse_results) >= limit:
                    break
                if hit not in diverse_results:
                    diverse_results.append(hit)
        
        return diverse_results

    def _enhance_with_document_metadata(self, chunk_hits):
        """Enhance chunk results with full document metadata."""
        doc_ids = [hit['_source']['document_id'] for hit in chunk_hits]
        
        if not doc_ids:
            return []

        try:
            # Get document metadata
            docs_response = self.os_client.mget(index=self.documents_index, body={"ids": doc_ids})
            docs_by_id = {doc['_id']: doc for doc in docs_response.get('docs', []) if doc.get('found')}
            
            # Combine chunk and document data
            enhanced_results = []
            for chunk_hit in chunk_hits:
                doc_id = chunk_hit['_source']['document_id']
                doc_data = docs_by_id.get(doc_id, {})
                
                if doc_data.get('found'):
                    # Merge chunk and document data
                    combined_source = {
                        **doc_data['_source'],
                        **chunk_hit['_source'],
                        'chunk_score': chunk_hit['_score']
                    }
                    
                    enhanced_result = {
                        '_id': doc_id,
                        '_score': chunk_hit['_score'],
                        '_source': combined_source
                    }
                    enhanced_results.append(enhanced_result)
            
            return enhanced_results
            
        except Exception as e:
            self.logger.error(f"Error enhancing results with document metadata: {e}")
            return chunk_hits  # Fallback to chunk data only

    def fallback_search(self, query: str, limit: int = 10):
        """Fallback search method when primary search returns no results."""
        try:
            # Simple match_all with query filtering
            search_body = {
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
                "size": limit
            }
            
            response = self.os_client.search(index=self.chunks_index, body=search_body)
            hits = response['hits']['hits']
            
            return self._enhance_with_document_metadata(hits)
            
        except Exception as e:
            self.logger.error(f"Fallback search failed for query '{query}': {e}")
            return []

    def health_check(self):
        """Checks cluster health."""
        if not self.os_client:
            return {"status": "unhealthy", "reason": "Client not initialized."}
        try:
            return self.os_client.info()
        except Exception as e:
            self.logger.error(f"OpenSearch health check failed: {e}")
            return {"status": "unhealthy", "reason": str(e)}