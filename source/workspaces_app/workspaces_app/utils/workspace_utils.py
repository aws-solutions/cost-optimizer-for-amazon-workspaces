#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import os

# AWS Libraries
from aws_lambda_powertools import Logger

# Initialize logger
logger = Logger(service="workspace_utils")
log_level = os.getenv("LogLevel", "INFO")
logger.setLevel(log_level)

TERMINATE_UNUSED_WORKSPACES = os.getenv("TerminateUnusedWorkspaces")
RESOURCE_UNAVAILABLE = "ResourceUnavailable"


def is_terminate_workspace_enabled():
    """
    This function returns true if terminate workspace feature enabled else returns false
    """
    logger.debug(f"Terminate workspaces option set to {TERMINATE_UNUSED_WORKSPACES}")
    return (
        TERMINATE_UNUSED_WORKSPACES == "Yes" or TERMINATE_UNUSED_WORKSPACES == "Dry Run"
    )


def check_if_workspace_used_for_selected_period(
    last_known_user_connection_timestamp, first_day_selected_month
):
    """
    This method returns a boolean value to indicate if the workspace was used in selected period
    :param: last_known_user_connection_timestamp: Last known connection timestamp
    :return: returns a boolean value to indicate if the workspace was used in current month
    """
    logger.debug("Checking the workspace usage in the selected period")
    if (
        last_known_user_connection_timestamp is None
    ):  # This indicates that user never logged into the workspace
        return False
    elif last_known_user_connection_timestamp == RESOURCE_UNAVAILABLE:
        # This indicates that the API failed to get the value for last user login timestamp
        # in which case avoid workspace termination by returning True
        return True
    else:
        logger.debug("Last know timestamp value is not None. Processing further.")
        logger.debug(f"First day for selected period is {first_day_selected_month}")
        last_known_user_connection_day = last_known_user_connection_timestamp.date()
        return last_known_user_connection_day >= first_day_selected_month


def check_for_skip_tag(tags):
    """
    Return a boolean value to indicate if the workspace needs to be skipped from the solution workflow
    :param tags:
    :return: True or False to indicate if the workspace can be skipped
    """
    # Added for case-insensitive matching.  Works with standard alphanumeric tags
    if tags is None:
        return True
    else:
        for tag_pair in tags:
            if tag_pair.get("Key").lower() == "Skip_Convert".lower():
                return True

    return False
