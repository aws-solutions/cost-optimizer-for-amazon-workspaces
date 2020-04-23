import sys
sys.path.append('engine')
from pytest_mock import mocker
from lib.workspaces_helper import WorkspacesHelper


def test_process_workspace_standard(mocker):
    workspace = {
        'WorkspaceId': 'ws-68h123hty',
        'DirectoryId': 'd-901230bb84',
        'UserName': 'test_user',
        'IpAddress': '111.16.1.233',
        'State': 'AVAILABLE',
        'BundleId': 'wsb-cl123qzj1',
        'SubnetId': 'subnet-05d421387eaa7cf86',
        'ComputerName': 'A-APPW123KP4NP',
        'WorkspaceProperties': {
            'RunningMode': 'ALWAYS_ON',
            'RootVolumeSizeGib': 80,
            'UserVolumeSizeGib': 50,
            'ComputeTypeName': 'STANDARD'
        },
        'ModificationStates': []
    }

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': 'yes',
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)

    mocker.patch.object(workspace_helper.metricsHelper, 'get_billable_time')
    workspace_helper.metricsHelper.get_billable_time.return_value = 444

    mocker.patch.object(workspace_helper, 'check_for_skip_tag')
    workspace_helper.check_for_skip_tag.return_value = True

    result = workspace_helper.process_workspace(workspace)
    assert result['bundleType'] == 'STANDARD'


def test_process_workspace_performance(mocker):
    workspace = {
        'WorkspaceId': 'ws-68h123hty',
        'DirectoryId': 'd-901230bb84',
        'UserName': 'test_user',
        'IpAddress': '111.16.1.233',
        'State': 'AVAILABLE',
        'BundleId': 'wsb-cl123qzj1',
        'SubnetId': 'subnet-05d421387eaa7cf86',
        'ComputerName': 'A-APPW123KP4NP',
        'WorkspaceProperties': {
            'RunningMode': 'ALWAYS_ON',
            'RootVolumeSizeGib': 80,
            'UserVolumeSizeGib': 50,
            'ComputeTypeName': 'PERFORMANCE'
        },
        'ModificationStates': []
    }

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': 'yes',
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)

    mocker.patch.object(workspace_helper.metricsHelper, 'get_billable_time')
    workspace_helper.metricsHelper.get_billable_time.return_value = 100

    mocker.patch.object(workspace_helper, 'check_for_skip_tag')
    workspace_helper.check_for_skip_tag.return_value = False

    mocker.patch.object(workspace_helper, 'get_hourly_threshold')
    workspace_helper.get_hourly_threshold.return_value = 5

    mocker.patch.object(workspace_helper, 'compare_usage_metrics')
    workspace_helper.compare_usage_metrics.return_value = {
            'resultCode': '-N-',
            'newMode': 'ALWAYS_ON'
        }

    result = workspace_helper.process_workspace(workspace)
    assert result['bundleType'] == 'PERFORMANCE'
    assert result['billableTime'] == 100
