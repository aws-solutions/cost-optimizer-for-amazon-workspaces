# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import re
import logging
from enum import Enum

REGEX_ACCOUNT_ID = r"^(\d{12})$"
REGEX_ROLE_ARN = r"^arn:[A-Za-z-]*:iam::\d{12}:role\/[a-zA-Z0-9_+=,.@-]*$"

# Initialize log level
log = logging.getLogger(__name__)


class RequestEvent:
    """
    Class to represent the request event and support the validations on the request event.
    """

    def __init__(self, account_id, request_type, role_arn):
        self.account_id = account_id
        self.request_type = request_type
        self.role_arn = role_arn
        self._validate_event_values()

    class RequestType(Enum):
        """
        Class to store valid request types.
        """

        REGISTER = 'Register'
        UNREGISTER = 'Unregister'

    def __str__(self):
        return f"account_id: {self.account_id[-4:]}, request_type: {self.request_type}, role_arn: {self.role_arn.split('/')[1]}"

    @classmethod
    def from_json(cls, json_obj):
        json_string = json.dumps(json_obj)
        json_dict = json.loads(json_string)
        return cls(**json_dict)

    def _validate_event_values(self):
        """
        This method validates if the values for the request keys.

        :raises: ValueError: if validation for any values in the request event fails
        """
        log.debug(f"Validating the values for {self}")
        self._validate_account_id()
        self._validate_role_arn()
        self._validate_request_type()

    def _validate_account_id(self):
        """
        This method validates the account id in the request against a regex.

        :raises: ValueError: if the account id does not match the regular expression REGEX_ACCOUNT_ID
        """
        log.debug(f"Validating the account_id: {self.account_id[-4:]}")
        if not re.fullmatch(REGEX_ACCOUNT_ID, self.account_id):
            log.error(f'Error validating the value for the {self.account_id[-4:]} in the request {self}')
            raise ValueError("Invalid value provided for Account ID.")

    def _validate_role_arn(self):
        """
        This method validates the role arn in the request against a regex.

        :raises: ValueError: if the roles arn does not match teh regular expression REGEX_ROLE_ARN
        """
        log.debug(f"Validating the role_arn: {self.role_arn.split('/')[1]}")
        if not re.fullmatch(REGEX_ROLE_ARN, self.role_arn):
            log.error(f"Error validating the value for the {self.role_arn.split('/')[1]} in the request {self}")
            raise ValueError("Invalid value provided for Role Arn.")

    def _validate_request_type(self):
        """
        This method validates the request type in the request.

        :raises: ValueError: if the request type does is not part of the list VALID_REQUEST_TYPES
        """
        log.debug(f"Validating the request_type: {self.request_type}")
        if self.request_type not in [self.RequestType.REGISTER.value, self.RequestType.UNREGISTER.value]:
            log.error(f'Error validating the value for the {self.request_type} in the request {self}')
            raise ValueError("Invalid value provided for RequestType. Valid values are Register and Unregister.")
