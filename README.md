# AzureAD SAML-based Single Sign-On Configuration

aad-aws-sso is administrative utility for AzureAD and AWS APIs. Allows to configure various aspects of SAML-based
Single Sign-On setup with AzureAD as Identity Provider and AWS as Service Provider.
This tool does not create or manage AWS IAM Roles, and expects them to be created before. It does
however support automatic synchronization of discovered AWS IAM Roles with AzureAD App Roles.

## Installation

Utility CLI and module are available from PyPI.

`python -m pip install aad-aws-sso`

