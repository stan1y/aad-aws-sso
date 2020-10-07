# Build saml-aws package
#

import os
import subprocess
import datetime

from setuptools import setup

with open('README.md', 'r') as f:
    long_description = f.read().strip()

with open('VERSION', 'r') as f:
    version = f.read().strip()
    build_num = os.getenv('BUILD_NUMBER')
    if not build_num:
        p = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'],
                             stdout=subprocess.PIPE)
        p.wait()
        if p.returncode == 0:
            rev = p.stdout.read().decode('utf-8').strip()
            build_num = f'dev.{rev}'
    version = f'{version}.{build_num}'

# Install package
setup(
    name='aad-aws-sso',
    packages=[
        'azuread_aws',
        'azuread_aws.azure',
        'azuread_aws.commands',
    ],
    version=version,
    author='Stanislav Yudin',
    author_email='stan@endlessinsomnia.com',
    description='Configure and manage AzureAD Idp and AWS Sp SAML setup for your AWS organization.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='',
    zip_safe=True,
    install_requires=[
        'boto3',
    ],
    entry_points={
        'console_scripts': ['aad-aws=azuread_aws.commands.cli:main'],
    },
    python_requires='>=3.6'
)
