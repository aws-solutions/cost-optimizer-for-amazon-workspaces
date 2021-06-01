###############################################################################
#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.    #
#                                                                             #
#  Licensed under the Apache License, Version 2.0 (the "License").            #
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at                                        #
#                                                                             #
#      http://www.apache.org/licenses/LICENSE-2.0                             #
#                                                                             #
#  or in the "license" file accompanying this file. This file is distributed  #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express #
#  or implied. See the License for the specific language governing permissions#
#  and limitations under the License.                                         #
###############################################################################

from json import dumps
from datetime import datetime
import requests
import logging
from os import getenv
from ecs.utils.decimal_encoder import DecimalEncoder
import boto3
from botocore.config import Config

# setup logger
logger = logging.getLogger()
LOG_LEVEL = str(getenv('LogLevel', 'INFO'))
logger.setLevel(LOG_LEVEL)

# Setup SSM client
config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'standard'
    },
    user_agent_extra=getenv('UserAgentString')
)
ssm_client = boto3.client('ssm', config=config)

SOLUTION_UUID_NAME = getenv('SOLUTION_UUID_NAME')


def send_metrics(data: dict,
                 solution_id=getenv('SolutionID'),
                 url=getenv('MetricsEndpoint'),
                 uuid=getenv('UUID')):
    """
    Sends anonymous metrics.

    :param uuid: unique id for solution deployment
    :param url: metrics endpoint
    :param solution_id: unique id of the solution
    :param data: anonymous customer metrics to be sent
    :return status code returned by https post request
    """
    logger.debug("Sending metrics with data {}, solution_is {} and url {}".format(data, solution_id, url))
    try:
        uuid = uuid
        time_stamp = {'TimeStamp': str(datetime.utcnow().isoformat())}
        data.update({"SolutionVersion": getenv('SOLUTION_VERSION')})
        params = {'Solution': solution_id,
                  'UUID': uuid,
                  'Data': data}
        metrics = dict(time_stamp, **params)
        json_data = dumps(metrics, cls=DecimalEncoder)
        headers = {'content-type': 'application/json'}
        r = requests.post(url, data=json_data, headers=headers)
        code = r.status_code
        logger.debug("The return code for the metrics request is {}".format(code))
        return code
    except Exception:
        pass
