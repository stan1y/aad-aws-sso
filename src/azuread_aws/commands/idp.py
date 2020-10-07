''' Lookup and configure AWS SAML IDP for accounts of the AWS Organization.
    Requires valid AWS credentials in the master account of the organization.
'''
import os
import pathlib
import logging
import threading
import time
import boto3
import http.client
import urllib.parse

from azuread_aws import amazon
from azuread_aws import http
from azuread_aws.azure import constants

log = logging.getLogger('idp')


def validate_master_account():
    current_id = amazon.get_current_account()
    master_id = amazon.get_master_account()
    if current_id != master_id:
        raise Exception('This command must be executed with authority and credentials'
                        f' in the organization master account {master_id},'
                        f'you are logged into {current_id}.')
    return master_id


def setup_saml_provider(resource, client, options, name='AAD'):
    '''Setup AzureAD SAML Provider with federation metadata'''
    for saml_provider in resource.saml_providers.all():
        if name in saml_provider.arn:
            if not options.recreate_saml_idp:
                log.info(f'Found existing SAML IdP with ARN: {saml_provider.arn}')
                return
            # we found existing IdP and want to re-create it
            saml_provider.delete()
            break

    metadata_url = f'https://login.microsoftonline.com/{constants.TENANT_ID}/federationmetadata/2007-06/federationmetadata.xml?appid={constants.CLIENT_ID}'
    log.info(f'Reading SAML metadata from {metadata_url}')
    metadata = http.get(metadata_url).text
    if not len(metadata):
        raise Exception(f'Failed to get metadata from {metadata_url}')

    created_arn = client.create_saml_provider(
        Name=name,
        SAMLMetadataDocument=metadata)['SAMLProviderArn']
    log.info(f'Created SAML IdP with ARN: {created_arn}')
    return created_arn


def ls(options):
    '''List identity providers across organizational accounts.'''
    master_id = validate_master_account()
    orgs = boto3.client('organizations')
    accounts = amazon.list_accounts(orgs)
    log.info(f'Listing identity providers in {len(accounts)} accounts of the organization.')
    for account_name, account_id in accounts.items():
        if account_id == master_id:
            continue
        account_resources = amazon.resource('iam', account_id)
        found = False
        for saml_provider in account_resources.saml_providers.all():
            if 'AAD' in saml_provider.arn:
                log.info(f'Found SAML provider [{saml_provider.arn}] in {account_name} ({account_id})')
                found = True
                break
        if not found:
            log.info(f'No SAML rovider found in account {account_name} ({account_id})')


def configure(options):
    '''Create or Update identity provider of specific account.'''
    validate_master_account()

    iam_client = amazon.client('iam', options.account_id)
    iam_resource = amazon.resource('iam', options.account_id)
    setup_saml_provider(iam_resource, iam_client, options)


def arguments(parser):
    subparsers = parser.add_subparsers(help=f'Subcommands for {__doc__}.')
    subparsers.required = True
    subparsers.dest = 'IDP subcommand missing'

    list_cmd = subparsers.add_parser('ls', help=ls.__doc__)
    list_cmd.set_defaults(cmd=ls)

    cfg_cmd = subparsers.add_parser('configure', help=configure.__doc__)
    cfg_cmd.add_argument('account_id', help='Account ID within organization to setup SAML IdP')
    cfg_cmd.add_argument('--recreate-saml-idp',
                         action='store_true',
                         help='Re-create SAML IdP if already exists in the account')
    cfg_cmd.set_defaults(cmd=configure)
