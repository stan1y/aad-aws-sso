''' List assigned and assign new Azure AD Application Roles, representing AWS IAM Roles
    in the organization accounts. AWS IAM Roles must be created and SAML IDP configured before.
'''
import os
import json
import uuid
import logging

from azuread_aws import amazon
from azuread_aws import http

from azuread_aws.commands.app_role import find_app_role_by_name

from azuread_aws.azure import auth
from azuread_aws.azure import graph_api

log = logging.getLogger('app_role')


def assign_user(options):
    '''Assign specified AWS App Role to a user.'''
    graph_token = auth.get_bearer_token('https://graph.microsoft.com')
    user = graph_api.find_user_by_email(graph_token, options.user_email)
    if not user:
        raise Exception(f'User with email [{options.user_email}] was not found.')
    user = user[0]
    log.info('Assigning user id: %s, name: %s', user['id'], user['displayName'])

    application = graph_api.get_application(graph_token)
    app_role = find_app_role_by_name(options.role_name, application['appRoles'])
    if not app_role:
        raise Exception(f'AWS App role with name {options.role_name} was not found')
    log.info('To app role id: %s, name: %s', app_role['id'], app_role['displayName'])
    aws_role_name, aws_account = app_role['description'].split('@')
    log.info('To AWS role name: %s, account id: %s', aws_role_name, aws_account)

    assignments = graph_api.get_user_app_roles(graph_token, user['id'])
    existing_role_ids = [a['appRoleId'] for a in assignments]
    if app_role['id'] in existing_role_ids:
        raise Exception(f'AWS App role {options.role_name} is already assigned to {options.user_email}')

    graph_api.assign_user_to_app_role(graph_token, user['id'], app_role['id'])


def unassign_user(options):
    '''Remove assignment of AWS App Role from a user.'''
    graph_token = auth.get_bearer_token('https://graph.microsoft.com')
    user = graph_api.find_user_by_email(graph_token, options.user_email)
    if not user:
        raise Exception(f'User with email [{options.user_email}] was not found.')
    user = user[0]
    log.info('Unassigning user id: %s, name: %s', user['id'], user['displayName'])

    application = graph_api.get_application(graph_token)
    app_role = find_app_role_by_name(options.role_name, application['appRoles'])
    if not app_role:
        raise Exception(f'AWS App role with name {options.role_name} was not found')
    log.info('From app role id: %s, name: %s', app_role['id'], app_role['displayName'])
    aws_role_name, aws_account = app_role['description'].split('@')
    log.info('From AWS role name: %s, account id: %s', aws_role_name, aws_account)

    assignments = graph_api.get_user_app_roles(graph_token, user['id'])
    assignment = [a for a in assignments if a['appRoleId'] == app_role['id']]
    if not assignment:
        raise Exception(f'AWS App role {options.role_name} is not assigned to {options.user_email}')

    assignment = assignment[0]
    log.info('Removing assignment id: %s', assignment['id'])
    graph_api.remove_user_from_app_role(graph_token, user['id'], assignment['id'])


def show_user_info(options):
    '''Lookup user by email and show app role assignments.'''
    graph_token = auth.get_bearer_token('https://graph.microsoft.com')
    user = graph_api.find_user_by_email(graph_token, options.user_email)
    if not user:
        raise Exception(f'User with email [{options.user_email}] was not found.')
    user = user[0]
    application = graph_api.get_application(graph_token)
    assignments = graph_api.get_user_app_roles(graph_token, user['id'])
    app_role_ids = [a['appRoleId'] for a in assignments]
    app_roles = []
    app_roles = [app_role for app_role in application['appRoles'] if app_role['id'] in app_role_ids]
    if not app_roles:
        log.info(f'No AWS App Roles assigned to {options.user_email}')
        return 0
    log.info('User id: %s, name: %s', user['id'], user['displayName'])
    log.info('Assignments:')
    for app_role in app_roles:
        app_role_name = app_role['displayName'].replace('AWS/', '')
        if app_role['value']:
            role_arn, idp_arn = app_role['value'].split(',')
            log.info('Role id: %s, name: %s, AWS Role Arn: %s', app_role['id'], app_role_name, role_arn)
        else:
            log.info('Role id: %s, name: %s, ---', app_role['id'], app_role_name)


def arguments(parser):
    subparsers = parser.add_subparsers(help=f'Subcommands for {__doc__}.')
    subparsers.required = True
    subparsers.dest = 'AAD App Roles subcommand missing'

    info_cmd = subparsers.add_parser('info', help=show_user_info.__doc__)
    info_cmd.add_argument('user_email')
    info_cmd.set_defaults(cmd=show_user_info)

    assign_cmd = subparsers.add_parser('assign', help=assign_user.__doc__)
    assign_cmd.add_argument('user_email', help='Email name of the user')
    assign_cmd.add_argument('role_name', help='AWS Application Role name to assign.')
    assign_cmd.set_defaults(cmd=assign_user)

    remove_cmd = subparsers.add_parser('unassign', help=unassign_user.__doc__)
    remove_cmd.add_argument('user_email', help='Email name of the user')
    remove_cmd.add_argument('role_name', help='AWS Application Role name to remove.')
    remove_cmd.set_defaults(cmd=unassign_user)
