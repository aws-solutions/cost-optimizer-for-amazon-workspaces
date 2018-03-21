#!/usr/bin/env python
from __future__ import unicode_literals
from setuptools import setup, find_packages

tests_require = [
    "pytest-mock>=1.6.2",
    "pytest-runner>=2.11.1",
    "pytest==3.2.1",
    "boto3>=1.4.5"
]

setup(
    name="workspaces_cost_optimizer",
    version="1.0.0",
    description="WorkSpaces Cost Optimizer Custom Resource",
    author="AWS Solutions Builder",
    license="ASL",
    zip_safe=False,
    packages=["workspaces_cost_optimizer", "lib"],
    package_dir={"workspaces_cost_optimizer": "."},
    setup_requires=["pytest-runner"],
    test_suite="tests",
    tests_require=tests_require
)
