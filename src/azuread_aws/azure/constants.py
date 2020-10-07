import os

# Always read secrets from environment. App expects bootstraping code
# to take care of reading secrets storage and populating the envrionment.
# This can be tests setup or Docker image entrypoint or any other way.

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_APP_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_APP_CLIENT_SECRET")
APP_ID = os.getenv("AZURE_APP_ID")
SERVICE_ID = os.getenv("AZURE_SERVICE_ID")
DOMAIN = os.getenv("AZURE_DOMAIN")
