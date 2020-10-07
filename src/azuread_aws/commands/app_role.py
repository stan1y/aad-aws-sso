''' List, Create and Delete Azure AD Application Roles for corresponding AWS IAM Roles in 
    organization accounts. Uses Graph API to modify Azure AD Application Manifest.
'''
import os
import uuid
import logging

from azuread_aws import amazon
from azuread_aws import http
from azuread_aws.azure import auth
from azuread_aws.azure import graph_api

log = logging.getLogger('app_role')


def list_app_roles(options):
    '''List Registered App Roles for AWS Application.'''
    token = auth.get_bearer_token('https://graph.microsoft.com')
    application = graph_api.get_application(token)
    log.info('Get application details with %d roles', len(application['appRoles']))
    for app_role in application['appRoles']:
        if not app_role['displayName'].startswith('AWS/'):
            continue
        if '@' not in app_role['description']:
            log.warning('Found app role %s without expected description format', app_role['displayName'])
            continue
        aws_role_name, aws_account_id = app_role['description'].split('@')
        log.info('Found id: %s, name: %s, aws role: %s, aws account: %s', app_role['id'], app_role['displayName'].replace('AWS/', ''),
                 aws_role_name, aws_account_id)


def new_app_role(options):
    '''Create new app role for corresponding iam role in some aws account.'''
    token = auth.get_bearer_token('https://graph.microsoft.com')
    application = graph_api.get_application(token)
    iam_role_arn = f'arn:aws:iam::{options.account_id}:role/aad/{options.aws_role_name}'
    if not options.app_role_name:    
        options.app_role_name = f'{options.aws_role_name}/{options.account_id}'
    saml_provider_arn = f'arn:aws:iam::{options.account_id}:saml-provider/AAD'
    app_role = {
        'allowedMemberTypes': ['User'],
        'description': f'{options.aws_role_name}@{options.account_id}',
        'displayName': f'AWS/{options.app_role_name}',
        'id': str(uuid.uuid4()),
        'isEnabled': True,
        'origin': 'Application',
        'value': f'{iam_role_arn},{saml_provider_arn}'
    }
    application['appRoles'].append(app_role)
    graph_api.patch_application(token, application)
    log.info('Created new app role [%s] for aws role "%s" in account %s',
             app_role['id'], options.aws_role_name, options.account_id)


def find_app_role_by_name(app_role_name, app_roles):
    log.debug('Looking for application role in %d roles', len(app_roles))
    for app_role in app_roles:
        if not app_role['displayName'].startswith('AWS/'):
            continue
        if '@' not in app_role['description']:
            log.warning('Found app role "%s" without expected description format', app_role['displayName'])
            continue
        aws_role_name, _ = app_role['description'].split('@')
        if app_role['displayName'] == f'AWS/{app_role_name}':
            return app_role
    return None


def find_app_roles_by_aws_name(aws_name, app_roles):
    log.debug('Looking for application role in %d roles', len(app_roles))
    found = []
    for app_role in app_roles:
        if '@' not in app_role['description']:
            log.warning('Found app role "%s" without expected description format', app_role['displayName'])
            continue
        aws_role_name, _ = app_role['description'].split('@')
        if aws_role_name == aws_name:
            found.append(app_role)
    return found


def show_app_role_info(options):
    '''Information about app role.'''
    token = auth.get_bearer_token('https://graph.microsoft.com')
    application = graph_api.get_application(token)

    app_role = find_app_role_by_name(options.role_name, application['appRoles'])
    if not app_role:
        raise Exception(f'AWS App role with name {options.role_name} was not found')

    aws_role_name, aws_account_id = app_role['description'].split('@')
    iam_resource = amazon.resource('iam', aws_account_id)
    role_arn = 'Not Found'
    for iam_role in iam_resource.roles.filter(PathPrefix='/aad'):
        if iam_role.name == aws_role_name:
            role_arn = iam_role.arn
            break
    log.info('ID: %s, Name: %s', app_role['id'], options.role_name)
    log.info('AWS Account: %s, Role Name: %s, Role ARN: %s', aws_account_id, aws_role_name, role_arn)


def arguments(parser):
    subparsers = parser.add_subparsers(help=f'Subcommands for {__doc__}.')
    subparsers.required = True
    subparsers.dest = 'AAD App Roles subcommand missing'

    list_cmd = subparsers.add_parser('ls', help=list_app_roles.__doc__)
    list_cmd.set_defaults(cmd=list_app_roles)

    info_cmd = subparsers.add_parser('info', help=show_app_role_info.__doc__)
    info_cmd.add_argument('role_name')
    info_cmd.set_defaults(cmd=show_app_role_info)

    new_cmd = subparsers.add_parser('new', help=new_app_role.__doc__)
    new_cmd.add_argument('-n', '--aws-role-name', required=True, help='Name of the AWS role to use.')
    new_cmd.add_argument('-a', '--account-id', required=True, help='AWS Account ID the role exists in.')
    new_cmd.add_argument('-d', '--app-role-name', help='Name of the new app role name.')
    new_cmd.set_defaults(cmd=new_app_role)
