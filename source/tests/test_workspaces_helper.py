import sys
sys.path.append('engine')
from ecs.workspaces_helper import WorkspacesHelper
from botocore.stub import Stubber



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
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)

    mocker.patch.object(workspace_helper.metricsHelper, 'get_billable_hours')
    workspace_helper.metricsHelper.get_billable_hours.return_value = 444

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
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)

    mocker.patch.object(workspace_helper.metricsHelper, 'get_billable_hours')
    workspace_helper.metricsHelper.get_billable_hours.return_value = 100

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


def test_modify_workspace_properties_Always_On(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.client)
    response = {}
    expected_params = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {'RunningMode': 'ALWAYS_ON'}
    }
    client_stubber.add_response('modify_workspace_properties', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    new_running_mode = 'ALWAYS_ON'
    result = workspace_helper.modify_workspace_properties(workspace_id, new_running_mode)
    assert result == '-M-'


def test_modify_workspace_properties_Auto_stop(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.client)
    response = {}
    expected_params = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {'RunningMode': 'AUTO_STOP'}
    }
    client_stubber.add_response('modify_workspace_properties', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    new_running_mode = 'AUTO_STOP'
    result = workspace_helper.modify_workspace_properties(workspace_id, new_running_mode)
    assert result == '-H-'
    client_stubber.deactivate()


def test_modify_workspace_properties_Exception(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.client)
    response = {}
    expected_params = {
        'WorkspaceProperties': {'RunningMode': 'AUTO_STOP'}
    }

    client_stubber.add_response('modify_workspace_properties', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    new_running_mode = 'AUTO_STOP'
    result = workspace_helper.modify_workspace_properties(workspace_id, new_running_mode)
    assert result == '-E-'


def test_modify_workspace_properties_Auto_stop_Dry_Run_True(mocker):
    # validate that the stubber call is not made when Dry Run is set to True
    # send an invalid request using stubber and validate that the does not method throws exception

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.client)
    response = {}
    expected_params = {
        'WorkspaceProperties': {'RunningMode': 'AUTO_STOP'}
    }
    client_stubber.add_response('modify_workspace_properties', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    new_running_mode = 'AUTO_STOP'
    # check if the method throws exception and validate that the stubber was not called
    result = workspace_helper.modify_workspace_properties(workspace_id, new_running_mode)
    assert result == '-H-'
    client_stubber.deactivate()


def test_modify_workspace_properties_Always_On_Dry_Run_True(mocker):
    # validate that the stubber call is not maded when Dry Run is set to True
    # send an invalid request using stubber and validate that the does not method throws exception

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.client)
    response = {}
    expected_params = {
        'WorkspaceProperties': {'RunningMode': 'ALWAYS_ON'}
    }
    client_stubber.add_response('modify_workspace_properties', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    new_running_mode = 'ALWAYS_ON'
    # check if the method throws exception and validate that the stubber was not called
    result = workspace_helper.modify_workspace_properties(workspace_id, new_running_mode)
    assert result == '-M-'
    client_stubber.deactivate()


def test_check_for_skip_tag_true(mocker):
    tags = [{'Key': 'skip_convert', 'Value': 'True'}]
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': 'yes',
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)
    result = workspace_helper.check_for_skip_tag(tags)
    assert result is True


def test_check_for_skip_tag_false(mocker):
    tags = [{'Key': 'nothing', 'Value': 'True'}]
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': 'yes',
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)
    result = workspace_helper.check_for_skip_tag(tags)
    assert result is False
