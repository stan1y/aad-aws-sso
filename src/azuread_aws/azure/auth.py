import logging
from azuread_aws import http
from azuread_aws.azure.constants import TENANT_ID, CLIENT_ID, CLIENT_SECRET
from azuread_aws.azure import AzureError

# Resource
# https://graph.windows.net for Azure API
# https://graph.microsoft.com for Graph API

log = logging.getLogger('azure.auth')


def get_bearer_token(resource):
    if not TENANT_ID or not CLIENT_ID or not CLIENT_SECRET:
        raise AzureError('Missing authentication.')

    url = "https://login.microsoftonline.com/{0}/oauth2/token".format(TENANT_ID)
    payload = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'resource': resource
    }
    response = http.post(url, data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if response.ok:
        log.debug('Authentication response: %s', response.text)
        if 'access_token' not in response.json:
            raise AzureError(f'Unexpected response in get_bearer_token - {response}')
        # return actual token
        return response.json['access_token']
    raise AzureError(f'get_bearer_token failed with {response.code} - {response.text}')
