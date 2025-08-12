from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

region = "us-east-1"  # same as your domain region
service = "es"        # for OpenSearch/Elasticsearch

host = "search-my-es-domain-defza2zny3somruv5ofxoqn2zm.us-east-1.es.amazonaws.com"
index_name = "ai_search_chunks"

# Get AWS credentials from your environment / profile
session = boto3.Session()
credentials = session.get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    region,
    service,
    session_token=credentials.token
)

# Create OpenSearch client
client = OpenSearch(
    hosts=[{"host": host, "port": 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

# Delete only the target index
client.indices.delete(index=index_name, ignore=[400, 404])
print(f"Deleted index: {index_name}")
