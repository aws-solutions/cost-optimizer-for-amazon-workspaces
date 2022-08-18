#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import cfnresponse
import uuid
import logging
import os
import sys

logger = logging.getLogger(__name__)
log_level = getattr(logging, str(os.getenv('LOG_LEVEL', 'INFO')))
logging.basicConfig(stream=sys.stdout, format='%(levelname)s: %(message)s', level=log_level)


def lambda_handler(event, context):
    try:
        request = event.get('RequestType')
        response_data = {}

        if request == 'Create':
            response_data = {'UUID': str(uuid.uuid4())}
            logger.debug(" UUID: {}".format(response_data))

        cfnresponse.send(event, context, 'SUCCESS', response_data)

    except Exception as e:
        logger.error('Exception: {}'.format(e))
        cfnresponse.send(event, context, 'FAILED', {}, context.log_stream_name)
