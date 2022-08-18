# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from register_spoke_lambda.request_event import RequestEvent


def test_even_key_role_arn():
    with pytest.raises(ValueError, match=r"Invalid value provided for Role Arn."):
        event = {
            'account_id': '123456789123',
            'request_type': 'Register',
            'role_arn': 'arn:aws:12345::role/test_arn'
        }
        RequestEvent.from_json(event)


def test_even_key_account_id():
    with pytest.raises(ValueError, match=r"Invalid value provided for Account ID."):
        event = {
            'account_id': '123456789',
            'request_type': 'Register',
            'role_arn': 'arn:aws:iam::123456789123:role/Admin'
        }
        RequestEvent.from_json(event)


def test_even_key_request_type():
    with pytest.raises(ValueError,
                       match=r"Invalid value provided for RequestType. Valid values are Register and Unregister."):
        event = {
            'account_id': '123456789123',
            'request_type': 'test',
            'role_arn': 'arn:aws:iam::123456789123:role/Admin'
        }
        RequestEvent.from_json(event)
