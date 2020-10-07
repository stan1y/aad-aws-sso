
import uuid
import logging

from azuread_aws import http
from azuread_aws.azure.constants import APP_ID, SERVICE_ID
from azuread_aws.azure import AzureError

log = logging.getLogger('azure.api')


def get_next_link(auth_token, next_url):
    url = next_url
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers)
    if response.ok:
        return response.json
    raise AzureError(f'get_next_link failed with {response.code} - {response.text}')


def get_application(auth_token):
    url = "https://graph.microsoft.com/v1.0/applications/{0}/".format(APP_ID)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers)
    if response.ok:
        return response.json
    raise AzureError(f'get_application failed with {response.code} - {response.text}')


def patch_application(auth_token, data):
    url = "https://graph.microsoft.com/v1.0/applications/{0}".format(APP_ID)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }

    data.pop('spa', None)
    response = http.patch(url, headers=headers, data=data)
    if response.status_code == 204:
        return True
    raise AzureError(f'patch_application failed with {response.code} - {response.text} for request data {data}')


def get_app_roles_assigned_to(auth_token, url=None):
    url = url or "https://graph.microsoft.com/v1.0/servicePrincipals/{0}/appRoleAssignments".format(SERVICE_ID)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers)
    if response.ok:
        return response.json
    raise AzureError(f'get_app_roles_assigned_to failed with {response.code} - {response.text}')


def aggregate_assigned_app_roles(auth_token, url=None, values=[]):
    r = get_app_roles_assigned_to(auth_token, url)
    values = values + r['value']
    if '@odata.nextLink' in r:
        return aggregate_assigned_app_roles(auth_token, r['@odata.nextLink'], values)
    else:
        return values


def get_user(auth_token, user_id):
    url = "https://graph.microsoft.com/v1.0/users/" + user_id
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers)
    if response.ok:
        return response.json
    raise AzureError(f'get_user failed with {response.code} - {response.text}')


def get_user_groups(auth_token, user_id):
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/getMemberGroups"
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.post(url, headers=headers, data={'securityEnabledOnly': False})
    if response.ok:
        return response.json['value']
    raise AzureError(f'get_user_groups failed with {response.code} - {response.text}')


def find_user_by_email(auth_token, user_email):
    url = "https://graph.microsoft.com/v1.0/users"
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    # special graphql way of escaping single quotes
    user_email = user_email.replace("'", "''")
    params = {"$filter": f"mail eq '{user_email}'"}
    response = http.get(url, headers=headers, params=params)
    log.debug(f'Looking up used by email with filter parameters: {params}')
    if response.ok:
        return response.json['value']
    raise AzureError(f'find_user_by_email failed with {response.code} - {response.text}')


def find_user_by_sso(auth_token, user_sso):
    url = "https://graph.microsoft.com/v1.0/users"
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers, params={'$filter': 'userPrincipalName eq \'' + user_sso + '\''})
    if response.ok:
        return response.json['value']
    raise AzureError(f'find_user_by_sso failed with {response.code} - {response.text}')


def delete_group(auth_token, group_id):
    url = f"https://graph.microsoft.com/v1.0/groups/{group_id}"
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }

    response = http.delete(url, headers=headers)
    if response.status_code == 204:
        return response.json

    raise AzureError(f'delete_group failed with {response.code} - {response.text}')


def create_group(auth_token, name, desc):
    url = "https://graph.microsoft.com/v1.0/groups"
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    data = {
        'description': desc,
        'displayName': name,
        'mailEnabled': False,
        'mailNickname': str(uuid.uuid4()),
        'securityEnabled': True
    }
    response = http.post(url, headers=headers, data=data)
    if response.status_code == 201:
        return response.json
    raise AzureError(f'create_group failed with {response.code} - {response.text}')


def get_group(auth_token, group_id):
    url = f"https://graph.microsoft.com/v1.0/groups/{group_id}"
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers)
    if response.ok:
        return response.json
    raise AzureError(f'get_group failed with {response.code} - {response.text}')


def find_group_by_name(auth_token, name):
    url = "https://graph.microsoft.com/v1.0/groups"
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers, params={'$filter': 'displayName eq \'' + name + '\''})
    if response.ok:
        return response.json['value']
    raise AzureError(f'find_group_by_name failed with {response.code} - {response.text}')


def find_group_starts_with_name(auth_token, name):
    all_data = []
    data = find_group_starts_with_name_initial(auth_token, name)
    all_data += data["value"]
    while '@odata.nextLink' in data:
        data = get_next_link(auth_token, data['@odata.nextLink'])
        all_data += data["value"]
    return all_data


def find_group_starts_with_name_initial(auth_token, name):
    url = "https://graph.microsoft.com/v1.0/groups"
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers, params={'$filter': 'startsWith(displayName,\'' + name + '\')'})
    if response.ok:
        return response.json
    raise AzureError(f'find_group_starts_with_name_initial failed with {response.code} - {response.text}')


def group_members(auth_token, group_id):
    all_data = []
    data = group_members_initial(auth_token, group_id)
    all_data += data["value"]
    while '@odata.nextLink' in data:
        data = get_next_link(auth_token, data['@odata.nextLink'])
        all_data += data["value"]
    return all_data


def group_members_initial(auth_token, group_id):
    url = "https://graph.microsoft.com/v1.0/groups/{}/members".format(group_id)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers)
    if response.ok:
        return response.json
    raise AzureError(f'group_members_initial failed with {response.code} - {response.text}')


def group_add_member(auth_token, group_id, user_id):
    url = "https://graph.microsoft.com/v1.0/groups/{}/members/$ref".format(group_id)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    data = {
        '@odata.id': f'https://graph.microsoft.com/v1.0/users/{user_id}'
    }
    response = http.post(url, headers=headers, data=data)
    if response.status_code == 204:
        return True
    raise AzureError(f'group_add_member failed with {response.code} - {response.text}')


def group_remove_member(auth_token, group_id, user_id):
    url = "https://graph.microsoft.com/v1.0/groups/{}/members/{}/$ref".format(group_id, user_id)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.delete(url, headers=headers)
    if response.status_code == 204:
        return True
    raise AzureError(f'group_remove_member failed with {response.code} - {response.text}')


def assign_user_to_app_role(auth_token, user_id, app_role_id):
    url = "https://graph.microsoft.com/v1.0/users/{0}/appRoleAssignments".format(user_id)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    data = {
        'principalId': user_id,
        'resourceId': SERVICE_ID,
        'appRoleId': app_role_id
    }
    response = http.post(url, headers=headers, data=data)
    if response.ok:
        return response.json
    raise AzureError(f'assign_user_to_app_role failed with {response.code} - {response.text}')


def get_group_app_roles(auth_token, group_id):
    url = "https://graph.microsoft.com/v1.0/groups/{0}/appRoleAssignments/?$top=999".format(group_id)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers)
    if response.ok:
        value = response.json['value']
        while '@odata.nextLink' in response.json:
            next_page = get_next_link(auth_token, response.json['@odata.nextLink'])
            value.extend(next_page['value'])
        return value
    raise AzureError(f'get group app roles failed with {response.code} - {response.text}')


def get_user_app_roles(auth_token, user_id):
    url = "https://graph.microsoft.com/v1.0/users/{0}/appRoleAssignments/?$top=999".format(user_id)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers)
    if response.ok:
        value = response.json['value']
        while '@odata.nextLink' in response.json:
            next_page = get_next_link(auth_token, response.json['@odata.nextLink'])
            value.extend(next_page['value'])
        return value
    raise AzureError(f'get_user_app_roles failed with {response.code} - {response.text}')


def assign_group_to_app_role(auth_token, group_id, app_role_id):
    url = "https://graph.microsoft.com/v1.0/groups/{0}/appRoleAssignments".format(group_id)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    data = {
        'principalId': group_id,
        'resourceId': SERVICE_ID,
        'appRoleId': app_role_id
    }
    response = http.post(url, headers=headers, data=data)
    if response.ok:
        return response.json
    raise AzureError(f'assign_group_to_app_role failed with {response.code} - {response.text}')


def lookup_assignment_object_id(auth_token, user_id, role_id):
    url = "https://graph.microsoft.com/v1.0/users/{0}/appRoleAssignments".format(user_id)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.get(url, headers=headers)
    if response.ok:
        matched_assignments = [assignment['objectId'] for assignment in response.json['value'] if assignment['id'] == role_id]
        if len(matched_assignments) != 1:
            raise AzureError('lookup_assignment_object_id - Invalid number of matched assignments found')

        return matched_assignments[0]
    raise AzureError(f'lookup_assignment_object_id failed with {response.code} - {response.text}')


def remove_user_from_app_role(auth_token, user_id, assignment_id):
    url = "https://graph.microsoft.com/v1.0/users/{0}/appRoleAssignments/{1}".format(user_id, assignment_id)
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = http.delete(url, headers=headers)
    if response.ok:
        return response
    raise AzureError(f'remove_user_from_app_role failed with {response.code} - {response.text}')
