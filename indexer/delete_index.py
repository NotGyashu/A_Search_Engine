from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

region = "us-east-1"  # your OpenSearch domain region
service = "es"        # service name for OpenSearch

host = "search-my-es-domain-defza2zny3somruv5ofxoqn2zm.us-east-1.es.amazonaws.com"

# Get AWS credentials from your environment/profile
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

# 🚨 Delete ALL indices — this is irreversible
response = client.indices.delete(index="_all", ignore=[400, 404])
print("Deleted all indices:", response)
