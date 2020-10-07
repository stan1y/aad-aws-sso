import os
import boto3
import logging
import time
import datetime
import random

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr


log = logging.getLogger('amazon')


def list_accounts(client):
    ''' Returns map of account names to account ids.'''
    accounts = {}
    for page in client.get_paginator('list_accounts').paginate():
        for info in page['Accounts']:
            name = info['Name']
            no = info['Id']
            accounts[name] = no
    return accounts


def list_accounts_by_name(client):
    ''' Returns map of account ids to account names.'''
    accounts = {}
    for page in client.get_paginator('list_accounts').paginate():
        for info in page['Accounts']:
            name = info['Name']
            no = info['Id']
            accounts[no] = name
    return accounts


def get_master_account():
    ''' Returns master account id'''
    return boto3.client('organizations').describe_organization()['Organization']['MasterAccountId']


def get_current_account():
    ''' Returns currently logged into account id'''
    return boto3.client('sts').get_caller_identity()['Account']


def get_organization_id():
    ''' Returns current organization id.'''
    return boto3.client('organizations').describe_organization()['Organization']['Id']


def cloudformation_template(filename):
    ''' Returns body of the embedded resource cloudformation template.'''
    template_path = os.path.join(
        os.path.dirname(accounts.__file__),
        'cloudformation',
        filename)
    if not os.path.exists(template_path):
        raise Exception(f'Template file {template_path} does not exist')

    with open(template_path, 'r') as f:
        return f.read()


def read_ssm(client, key, default=None):
    try:
        response = client.get_parameter(Name=key, WithDecryption=True)
        return response['Parameter']['Value']

    except client.exceptions.ParameterNotFound as pe:
        log.warning(f'SSM parameter {key} does not exist.')
        return default


def write_ssm(client, key, value, ptype='String', key_id=None, desc=None):
    args = {
        'Name': key, 'Value': value, 'Type': ptype, 'Overwrite': True
    }
    if ptype == 'SecureString' and key_id:
        args['KeyId'] = key_id
    if desc:
        args['Description'] = desc
    client.put_parameter(**args)


def get_stack_id(client, stack_name):
    ''' Returns Cloudformation stack id if found or None.'''
    stack_id = None
    for page in client.get_paginator('list_stacks').paginate():
        if stack_id is not None:
            break
        for stack in page['StackSummaries']:
            if stack['StackName'] == stack_name:
                stack_id = stack['StackId']
                break
    return stack_id


def wait_stack_set_operation(client, stack_set_name, op_id):
    '''Waits for operation completition'''
    log.info(f'Waiting stack set operation {op_id} to complete...')
    status = 'RUNNING'
    while status in ['RUNNING', 'STOPPING']:
        op = client.describe_stack_set_operation(
            StackSetName=stack_set_name,
            OperationId=op_id
        )['StackSetOperation']
        started = op.get('CreationTimestamp')
        finished = op.get('EndTimestamp')
        action = op['Action']
        status = op['Status']
        time.sleep(random.randint(15, 30))

    if status in ['FAILED']:
        raise Exception(f'{stack_set_name} stackset is in FAILED state. Please investigate')

    elapsed = finished - started
    log.info(f'Operation "{op_id}" started on {started} and {status} in {elapsed}')


def deploy_stack_set(client, stackset_name, template, description, parameters, capabilities):
    ''' Create or update stackset with given name and template.
    '''
    try:
        stack_set = client.describe_stack_set(StackSetName=stackset_name)['StackSet']
        if stack_set['Status'] != 'ACTIVE':
            raise Exception(f'Stack set {stackset_name} is in unexpected status')

        should_update = False
        if stack_set['TemplateBody'] != template:
            log.info(f'Stackset {stackset_name} template changes detected.')
            should_update = True

        if stack_set['Capabilities'] != capabilities:
            log.info(f'Stackset {stackset_name} capabilities changes detected.')
            should_update = True

        for p in parameters:
            match = False
            for existing in stack_set['Parameters']:
                if p['ParameterKey'] == existing['ParameterKey'] and p['ParameterValue'] == p['ParameterValue']:
                    match = True
                    break
            if not match:
                log.info(f'Parameter {p["ParameterKey"]} value of stack set {stackset_name} was changed or new.')
                should_update = True
                break

        if not should_update:
            log.info(f'No changes to deploy for a stack set {stackset_name}.')
            return

        log.info(f'Updating stack set {stackset_name}.')
        op_id = client.update_stack_set(
            StackSetName=stackset_name,
            Description=description,
            TemplateBody=template,
            UsePreviousTemplate=False,
            Parameters=parameters,
            Capabilities=capabilities,
            OperationPreferences={
                'FailureToleranceCount': 9,
                'MaxConcurrentPercentage': 100
            }
        )['OperationId']
        wait_stack_set_operation(client, stackset_name, op_id)

    except client.exceptions.StackSetNotFoundException:
        log.info(f'Creating stack set {stackset_name}.')
        client.create_stack_set(
            StackSetName=stackset_name,
            Description=description,
            TemplateBody=template,
            Parameters=parameters
        )


def deploy_stack_set_instance(client, stack_set_name, account_id, regions):
    ''' Checks if there is a stackset instance in the given account.
        If not found, creates a new stack set instance.
        If found & status = OUTDATED, updates the stack set instance
        If found & status = INOPERABLE, throws exception
        If found & status = CURRENT, does nothing
    '''

    found = None
    for page in client.get_paginator('list_stack_instances').paginate(StackSetName=stack_set_name):
        for summary in page['Summaries']:
            if summary['Account'] == account_id:
                found = summary
                break

    if not found:
        log.info(f'Creating new instance of {stack_set_name} for account {account_id}')
        op_id = client.create_stack_instances(
            StackSetName=stack_set_name,
            Accounts=[account_id],
            Regions=regions,
            OperationPreferences={
                'FailureToleranceCount': 10,
                'MaxConcurrentPercentage': 100
            }
        )['OperationId']
        wait_stack_set_operation(client, stack_set_name, op_id)

    elif found['Status'] == 'OUTDATED':
        log.info(f'Updating {stack_set_name} instance for account {account_id}')
        op_id = client.update_stack_instances(
            StackSetName=stack_set_name,
            Accounts=[account_id],
            Regions=regions,
            OperationPreferences={
                'FailureToleranceCount': 10,
                'MaxConcurrentPercentage': 100
            }
        )['OperationId']
        wait_stack_set_operation(client, stack_set_name, op_id)

    elif found['Status'] == 'CURRENT':
        log.info(f'Instance of {stack_set_name} for account {account_id} is up to date.')

    else:
        status = found['Status']
        raise Exception(f'Stack set {stack_set_name} instance for {account_id} is in {status} status')


def deploy_stack(client, stack_name, template, parameters, capabilities):
    ''' Create or update stack with given name, template & parameters.
        Waits for the operation to be complete.
    '''
    stack_id = get_stack_id(client, stack_name)
    if stack_id:
        log.info(f'Updating stack {stack_name} ({stack_id})')
        try:
            client.update_stack(
                StackName=stack_name,
                TemplateBody=template,
                Parameters=parameters,
                Capabilities=capabilities
            )

            log.info('Waiting for stack update to complete.')
            client.get_waiter('stack_update_complete').wait(StackName=stack_name)

        except ClientError as ce:
            if ce.response['Error']['Code'] != 'ValidationError':
                raise
            if 'No updates are to be performed' not in ce.response['Error']['Message']:
                raise
            log.info('No changes to deploy')
    else:
        log.info(f'Creating new stack {stack_name}')
        client.create_stack(
            StackName=stack_name,
            TemplateBody=template,
            Parameters=parameters,
            Capabilities=capabilities
        )

        log.info('Waiting for stack creation to complete...')
        client.get_waiter('stack_create_complete').wait(StackName=stack_name)

    # check stack status after operations are complete
    stack_status = client.describe_stacks(StackName=stack_name)['Stacks'][0]
    if stack_status['StackStatus'] not in ('UPDATE_COMPLETE', 'CREATE_COMPLETE'):
        status = stack_status['StackStatus']
        reason = stack_status['StackStatusReason']
        log.error(f'Stack operation failed with status: {status} - {reason}')
        raise Exception(f'Stack {stack_name} is in unexpected status {status}: {reason}')

    log.info(f'Stack {stack_name} was created or updated successfully')


def assume_account_role(account, role_name):
    '''Assume role in the target account'''
    return boto3.client('sts').assume_role(
        RoleArn=f'arn:aws:iam::{account}:role/{role_name}',
        RoleSessionName=f'aad-aws-{random.randint(1, 10000)}'
    )


def client(client_name,
           account_id=None,
           role_name='OrganizationAccountAccessRole'):
    '''Returns a boto3.client for given account id'''
    if account_id is None:
        return boto3.client(client_name)
    # assume role in the target account
    assumed_role = assume_account_role(account_id, role_name)
    return boto3.client(client_name,
                        aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
                        aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
                        aws_session_token=assumed_role['Credentials']['SessionToken'])


def resource(client_name,
             account_id=None,
             role_name='OrganizationAccountAccessRole'):
    '''Returns a boto3.resource for given account id'''
    if account_id is None:
        return boto3.resource(client_name)
    # assume role in the target account
    assumed_role = assume_account_role(account_id, role_name)
    return boto3.resource(client_name,
                          aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
                          aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
                          aws_session_token=assumed_role['Credentials']['SessionToken'])
