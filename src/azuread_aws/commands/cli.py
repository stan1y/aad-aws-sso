#!/usr/bin/env python
''' Administrative utility for AzureAD and AWS APIs. Allows to configure various aspects of SAML-based
    Single Sign-On setup with AzureAD as Identity Provider and AWS as Service Provider.
    This tool does not create or manage AWS IAM Roles, and expects them to be created before. It does
    however support automatic synchronization of discovered AWS IAM Roles with AzureAD App Roles.
'''
import os
import sys
import argparse
import logging
import pkg_resources

from azuread_aws.commands import idp
from azuread_aws.commands import app_role
from azuread_aws.commands import user

log = logging.getLogger(__name__)


def init_subcommand(subparsers, cmd, name):
    log.debug(f'Setting up subcommand {cmd.__name__}')
    subp = subparsers.add_parser(name, help=cmd.__doc__)
    cmd.arguments(subp)


def main():
    parser = argparse.ArgumentParser(
        description='AzureAD and AWS command line toolkit. Version: {ver}. {doc}'.format(
            doc=__doc__,
            ver=pkg_resources.get_distribution("aad-aws-sso").version
        ))
    parser.add_argument(
        '-s', '--silent', action='store_true',
        help='Enable no output (WARNING level logging)')
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help='Enable debug output (DEBUG level logging)')

    subparsers = parser.add_subparsers(help='Supported commands. '
                                            'Each subcommand has own arguments.')
    subparsers.required = True
    subparsers.dest = 'subcommand missing'
    init_subcommand(subparsers, idp, 'idp')
    init_subcommand(subparsers, app_role, 'role')
    init_subcommand(subparsers, user, 'user')
    options = parser.parse_args()

    lvl = getattr(logging, os.getenv('SILENT_LOG_LEVEL', 'WARNING'))
    if not options.silent:
        lvl = getattr(logging, os.getenv('LOG_LEVEL', 'INFO'))
    if options.debug:
        lvl = logging.DEBUG
    logging.basicConfig(
        level=lvl,
        format='%(asctime)s %(levelname)s\t%(message)s',
        datefmt='%Y-%m-%d %I:%M:%S')

    try:
        rc = options.cmd(options)
        log.debug(f'Subcommand {options.cmd.__name__} returned {rc}')
        return rc if rc is not None else 0

    except Exception as ex:
        log.error(f'{ex.__class__.__name__} - {ex}')
        if lvl == logging.DEBUG:
            raise
        return 1


if __name__ == '__main__':
    sys.exit(main())
