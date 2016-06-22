# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup

VERSION = "0.1.3"

requirements = [
    # Boto3 is the Amazon Web Services (AWS) Software Development Kit (SDK)
    # for Python.
    # License: Apache2
    # Upstream url: https://github.com/boto/boto3
    # Use: For KMS
    'boto3>=1.2.0,<1.4.0'
]

setup(
    name="kmsauth",
    version=VERSION,
    install_requires=requirements,
    author="Ryan Lane",
    author_email="rlane@lyft.com",
    description=("A library for generating and validating KMS authentication"
                 "tokens"),
    license="apache2",
    url="https://github.com/lyft/python-kmsauth"
)
