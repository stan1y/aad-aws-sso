# AzureAD SAML-based Single Sign-On Configuration

aad-aws-sso is administrative utility for AzureAD and AWS APIs. Allows to configure various aspects of SAML-based
Single Sign-On setup with AzureAD as Identity Provider and AWS as Service Provider.
This tool does not create or manage AWS IAM Roles, and expects them to be created before. It does
however support automatic synchronization of discovered AWS IAM Roles with AzureAD App Roles.

## Installation

Utility CLI and module are available from PyPI.

`python -m pip install aad-aws-sso`

And support Python 3.6+.

## Supported Features

* CLI interface for interactive and scripted configuration
* Configuration of SAML IDP in AWS Organization Accounts
* AzureAD App Roles creation and assignments on AzureAD users.

## Planned Features
* Synchronization of AWS IAM Roles with AzureAD App Roles with rules.
* Group assignments support.
* Add/Remove AzureAD users from AzureAD groups CLI interface.

## Usage

### AWS IAM Roles

This utility assumes that organization in AWS has already been configured with appropriate
IAM Roles which are available to be assumed with SAML. The [cloudformation](./cloudformation)
folder contains examples of roles as a CloudFormation template.
This templates can be deployed as Stack Sets across organizational units or specific accounts.

Configuration of Azure AD Application Roles with this utility requires names of such roles
to be known before using it.

### Using the utility

* Define a new AzureAD App Role corresponding to an AWS IAM Role in an account.
  ```
  aad-aws role new -a <account_id> -n <iam role name>
  ```
  This will modify application manifest in Azure AD to add a new App Role with name `<iam role name>/<account id>`.
* List available AzureAD App Roles for AWS Application
  ```
  aad-aws role ls
  ```
  This command lists app roles in the manifest.
* List assignments of a user
  ```
  aad-aws user info <user email> 
  ```
* Assign app role by name to a user
  ```
  aad-aws user assign <user email> <iam role name>/<account id>
  ```