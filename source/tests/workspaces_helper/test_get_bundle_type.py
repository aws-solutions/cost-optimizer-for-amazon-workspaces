#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#  Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
#                                                                            #
#  Licensed under the Amazon Software License (the "License"). You may not   #
#  use this file except in compliance with the License. A copy of the        #
#  License is located at                                                     #
#                                                                            #
#      http://aws.amazon.com/asl/                                            #
#                                                                            #
#  or in the "license" file accompanying this file. This file is distributed #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,        #
#  express or implied. See the License for the specific language governing   #
#  permissions and limitations under the License.                            #
##############################################################################

from lib.workspaces_helper import WorkspacesHelper

helper = WorkspacesHelper({
    'region': 'us-west-2',
    'hourlyLimits': {
        'VALUE': 5,
        'STANDARD': 5,
        'PERFORMANCE': 5,
        'GRAPHICS': 5
    },
    'testEndOfMonth': False,
    'isDryRun': True,
    'startTime': '2018-02-01T00:00:00Z',
    'endTime': '2018-02-01T12:00:00Z'
})

# get_bundle_type
def test_get_bundle_type(monkeypatch):
    def mock_describe_workspace_bundles(BundleIds=['wsb-123']):
        return {
            u'Bundles': [
                {
                    u'ComputeType': {u'Name': u'STANDARD'},
                    u'Description': u'xxxxxxxxx',
                    u'RootStorage': {u'Capacity': u'80'},
                    u'BundleId': u'wsb-xxxxxxxxx',
                    u'Owner': u'Amazon',
                    u'UserStorage': {u'Capacity': u'50'},
                    u'Name': u'xxxxxxxxx'
                }
            ],
            'ResponseMetadata': {
                'RetryAttempts': 0,
                'HTTPStatusCode': 200,
                'RequestId': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                'HTTPHeaders': {
                    'x-amzn-requestid': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                    'date': 'Thu, 07 Feb 1988 11:00:00',
                    'content-length': '296',
                    'content-type': 'application/x-amz-json-1.1'
                }
            }
        }

    monkeypatch.setattr(helper.client, 'describe_workspace_bundles', mock_describe_workspace_bundles)

    result = helper.get_bundle_type({
        "BundleId": "wsb-xxxxxxxxx"
    })
    assert result == 'STANDARD'