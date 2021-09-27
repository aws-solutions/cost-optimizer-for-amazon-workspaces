import sys

sys.path.append('engine')
import ecs.workspaces_helper
from ecs.workspaces_helper import WorkspacesHelper
from botocore.stub import Stubber
import time
import datetime
from dateutil.tz import tzutc


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
    mocker.patch.object(workspace_helper.metrics_helper, 'get_billable_hours')
    workspace_helper.metrics_helper.get_billable_hours.return_value = 444
    mocker.patch.object(workspace_helper, 'get_tags')
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

    mocker.patch.object(workspace_helper.metrics_helper, 'get_billable_hours')
    workspace_helper.metrics_helper.get_billable_hours.return_value = 100
    mocker.patch.object(workspace_helper, 'get_tags')
    mocker.patch.object(workspace_helper, 'check_for_skip_tag')
    workspace_helper.check_for_skip_tag.return_value = False
    mocker.patch.object(workspace_helper, 'get_hourly_threshold')
    workspace_helper.get_hourly_threshold.return_value = 5
    mocker.patch.object(workspace_helper, 'compare_usage_metrics')
    workspace_helper.compare_usage_metrics.return_value = {
        'resultCode': '-N-',
        'newMode': 'ALWAYS_ON'
    }
    mocker.patch.object(workspace_helper, 'get_termination_status')
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
    client_stubber = Stubber(workspace_helper.workspaces_client)
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
    client_stubber = Stubber(workspace_helper.workspaces_client)
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
    client_stubber = Stubber(workspace_helper.workspaces_client)
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
    client_stubber = Stubber(workspace_helper.workspaces_client)
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
    client_stubber = Stubber(workspace_helper.workspaces_client)
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


def test_terminate_workspaces_yes(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {'TerminateWorkspaceRequests': [{'WorkspaceId': '123qwer'}]}
    client_stubber.add_response('terminate_workspaces', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    result = workspace_helper.terminate_unused_workspace(workspace_id)
    assert result == 'Yes'
    client_stubber.deactivate()


def test_terminate_workspaces_no(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error('TerminateWorkspaceRequests', "Invalid_request")
    client_stubber.activate()
    workspace_id = '123qwer'
    result = workspace_helper.terminate_unused_workspace(workspace_id)
    assert result == ''
    client_stubber.deactivate()


def test_check_workspace_available_yes(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    start_time = time.strftime("%Y-%m") + '-01T00:00:00Z'
    end_time = time.strftime("%Y-%m") + '-02T00:00:00Z'
    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.cloudwatch_client)
    workspace_id = '123qwer'
    response = {
        'Datapoints': [
            {'Timestamp': datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'}
        ]
    }
    expected_params = {
        'Dimensions': [
            {
                'Name': 'WorkspaceId',
                'Value': workspace_id
            }
        ],
        'Namespace': 'AWS/WorkSpaces',
        'MetricName': 'Available',
        'StartTime': start_time,
        'EndTime': end_time,
        'Period': 300,
        'Statistics': ['Maximum']
    }
    client_stubber.add_response('get_metric_statistics', response, expected_params)
    client_stubber.activate()
    result = workspace_helper.check_if_workspace_available_on_first_day(workspace_id)
    assert result is True
    client_stubber.deactivate()


def test_check_workspace_available_no(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    start_time = time.strftime("%Y-%m") + '-01T00:00:00Z'
    end_time = time.strftime("%Y-%m") + '-02T00:00:00Z'
    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.cloudwatch_client)
    workspace_id = '123qwer'
    response = {
        'Datapoints': []
    }
    expected_params = {
        'Dimensions': [
            {
                'Name': 'WorkspaceId',
                'Value': workspace_id
            }
        ],
        'Namespace': 'AWS/WorkSpaces',
        'MetricName': 'Available',
        'StartTime': start_time,
        'EndTime': end_time,
        'Period': 300,
        'Statistics': ['Maximum']
    }
    client_stubber.add_response('get_metric_statistics', response, expected_params)
    client_stubber.activate()
    result = workspace_helper.check_if_workspace_available_on_first_day(workspace_id)
    assert result is False
    client_stubber.deactivate()


def test_check_workspace_available_exception(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.cloudwatch_client)
    workspace_id = '123qwer'
    client_stubber.add_client_error('get_metric_statistics', 'Invalid request')
    client_stubber.activate()
    result = workspace_helper.check_if_workspace_available_on_first_day(workspace_id)
    assert result is False
    client_stubber.deactivate()


def test_get_workspaces(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    directory_id = "123qwe123qwe"
    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {
        'Workspaces': [
            {'WorkspaceId': '1234'},
            {'WorkspaceId': '1234'},
            {'WorkspaceId': '1234'}
        ]
    }
    expected_params = {
        'DirectoryId': directory_id
    }
    client_stubber.add_response('describe_workspaces', response, expected_params)
    client_stubber.activate()
    result = workspace_helper.get_workspaces_for_directory(directory_id)
    assert result == [
        {'WorkspaceId': '1234'},
        {'WorkspaceId': '1234'},
        {'WorkspaceId': '1234'}
    ]
    client_stubber.deactivate()


def test_get_workspaces_exception(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    directory_id = "123qwe123qwe"
    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error('describe_workspaces', 'Invalid Directory')
    client_stubber.activate()
    result = workspace_helper.get_workspaces_for_directory(directory_id)
    assert result == []
    client_stubber.deactivate()


def test_check_if_workspace_needs_to_be_terminated_1(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = WorkspacesHelper(settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(workspace_id)
    assert result == 'Yes - Dry Run'


def test_check_if_workspace_needs_to_be_terminated_2(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = WorkspacesHelper(settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(workspace_id)
    assert result == 'Yes - Dry Run'


def test_check_if_workspace_needs_to_be_terminated_3(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Yes'
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = WorkspacesHelper(settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(workspace_id)
    assert result == ''


def test_check_if_workspace_needs_to_be_terminated_4(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Yes'
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = WorkspacesHelper(settings)
    mocker.patch.object(workspace_helper, 'terminate_unused_workspace')
    workspace_helper.terminate_unused_workspace.return_value = 'Yes'
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(workspace_id)
    assert result == 'Yes'


def test_check_if_workspace_needs_to_be_terminated_5(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Yes'
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = WorkspacesHelper(settings)
    mocker.patch.object(workspace_helper, 'terminate_unused_workspace')
    workspace_helper.terminate_unused_workspace.return_value = ''
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(workspace_id)
    assert result == ''


def test_terminate_unused_workspace_exception(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error('terminate_workspaces', 'Invalid Directory')
    client_stubber.activate()
    result = workspace_helper.terminate_unused_workspace(workspace_id)
    assert result == ''
    client_stubber.deactivate()


def test_terminate_unused_workspace_failed_request(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    workspace_id = "123qwe123qwe"
    response = {
        'FailedRequests': [
            {
                'WorkspaceId': 'string',
                'ErrorCode': 'string',
                'ErrorMessage': 'string'
            },
        ]
    }
    expected_params = {
        'TerminateWorkspaceRequests': [{
            'WorkspaceId': workspace_id
        }]
    }
    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_response('terminate_workspaces', response, expected_params)
    client_stubber.activate()
    result = workspace_helper.terminate_unused_workspace(workspace_id)
    assert result == ''
    client_stubber.deactivate()


def test_terminate_unused_workspace_yes(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    workspace_id = "123qwe123qwe"
    response = {
        'FailedRequests': []
    }
    expected_params = {
        'TerminateWorkspaceRequests': [{
            'WorkspaceId': workspace_id
        }]
    }
    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_response('terminate_workspaces', response, expected_params)
    client_stubber.activate()
    result = workspace_helper.terminate_unused_workspace(workspace_id)
    assert result == 'Yes'
    client_stubber.deactivate()


def test_check_workspace_usage_for_current_month_None(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    last_known_user_connection_timestamp = None
    workspace_helper = WorkspacesHelper(settings)
    result = workspace_helper.check_workspace_usage_for_current_month(last_known_user_connection_timestamp)
    assert result is True


def test_check_workspace_usage_for_current_month_false(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    last_known_user_connection_timestamp = datetime.datetime.strptime('2021-01-10 19:35:15.524000+00:00',
                                                                      '%Y-%m-%d %H:%M:%S.%f+00:00')
    workspace_helper = WorkspacesHelper(settings)
    result = workspace_helper.check_workspace_usage_for_current_month(last_known_user_connection_timestamp)
    assert result is False


def test_check_workspace_usage_for_current_month_true(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    last_known_user_connection_timestamp = datetime.datetime.utcnow().today().replace(day=1, hour=0, minute=0, second=0,
                                                                                      microsecond=0)
    workspace_helper = WorkspacesHelper(settings)
    result = workspace_helper.check_workspace_usage_for_current_month(last_known_user_connection_timestamp)
    assert result is True


def test_get_last_known_user_connection_timestamp(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    last_known_user_connection_timestamp = datetime.datetime.strptime('2021-08-10 19:35:15.524000+00:00',
                                                                      '%Y-%m-%d %H:%M:%S.%f+00:00')
    workspace_id = "123qwe123qwe"
    response = {
        'WorkspacesConnectionStatus': [{
            'LastKnownUserConnectionTimestamp': last_known_user_connection_timestamp
        }]
    }
    expected_params = {
        'WorkspaceIds': [workspace_id]
    }
    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_response('describe_workspaces_connection_status', response, expected_params)
    client_stubber.activate()
    result = workspace_helper.get_last_known_user_connection_timestamp(workspace_id)
    assert result == last_known_user_connection_timestamp
    client_stubber.deactivate()


def test_get_last_known_user_connection_timestamp_exception(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = WorkspacesHelper(settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error('get_last_known_user_connection_timestamp', 'Invalid workspace')
    client_stubber.activate()
    result = workspace_helper.get_last_known_user_connection_timestamp(workspace_id)
    assert result is None
    client_stubber.deactivate()


def test_get_termination_status_1():
    ecs.workspaces_helper.TERMINATE_UNUSED_WORKSPACES = 'No'
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Yes'
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = WorkspacesHelper(settings)
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ''


def test_get_termination_status_2(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Yes'
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = WorkspacesHelper(settings)
    ecs.workspaces_helper.TERMINATE_UNUSED_WORKSPACES = 'Yes'
    ecs.workspaces_helper.today = "2021-09-30"
    ecs.workspaces_helper.last_day = "2021-09-30"
    mocker.patch.object(workspace_helper, 'get_last_known_user_connection_timestamp')

    mocker.patch.object(workspace_helper, 'check_workspace_usage_for_current_month')
    workspace_helper.check_workspace_usage_for_current_month.return_value = False

    mocker.patch.object(workspace_helper, 'check_if_workspace_available_on_first_day')
    workspace_helper.check_if_workspace_available_on_first_day.return_value = True

    mocker.patch.object(workspace_helper, 'check_if_workspace_needs_to_be_terminated')
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = 'Yes'
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == 'Yes'


def test_get_termination_status_3(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = WorkspacesHelper(settings)
    ecs.workspaces_helper.TERMINATE_UNUSED_WORKSPACES = 'Yes'
    mocker.patch.object(workspace_helper, 'get_last_known_user_connection_timestamp')

    mocker.patch.object(workspace_helper, 'check_workspace_usage_for_current_month')
    workspace_helper.check_workspace_usage_for_current_month.return_value = False

    mocker.patch.object(workspace_helper, 'check_if_workspace_available_on_first_day')
    workspace_helper.check_if_workspace_available_on_first_day.return_value = True

    mocker.patch.object(workspace_helper, 'check_if_workspace_needs_to_be_terminated')
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = 'Yes - Dry Run'
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == 'Yes - Dry Run'


def test_get_termination_status_4(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = WorkspacesHelper(settings)
    ecs.workspaces_helper.TERMINATE_UNUSED_WORKSPACES = 'Yes'
    mocker.patch.object(workspace_helper, 'get_last_known_user_connection_timestamp')

    mocker.patch.object(workspace_helper, 'check_workspace_usage_for_current_month')
    workspace_helper.check_workspace_usage_for_current_month.return_value = True

    mocker.patch.object(workspace_helper, 'check_if_workspace_available_on_first_day')
    workspace_helper.check_if_workspace_available_on_first_day.return_value = True

    mocker.patch.object(workspace_helper, 'check_if_workspace_needs_to_be_terminated')
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = 'Yes - Dry Run'
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ''


def test_get_termination_status_5(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = WorkspacesHelper(settings)
    ecs.workspaces_helper.TERMINATE_UNUSED_WORKSPACES = 'Yes'
    mocker.patch.object(workspace_helper, 'get_last_known_user_connection_timestamp')

    mocker.patch.object(workspace_helper, 'check_workspace_usage_for_current_month')
    workspace_helper.check_workspace_usage_for_current_month.return_value = False

    mocker.patch.object(workspace_helper, 'check_if_workspace_available_on_first_day')
    workspace_helper.check_if_workspace_available_on_first_day.return_value = False

    mocker.patch.object(workspace_helper, 'check_if_workspace_needs_to_be_terminated')
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = 'Yes - Dry Run'
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ''


def test_get_termination_status_5(mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = "123qwe123qwe"
    billable_time = 1
    tags = []
    workspace_helper = WorkspacesHelper(settings)
    ecs.workspaces_helper.TERMINATE_UNUSED_WORKSPACES = 'Yes'
    mocker.patch.object(workspace_helper, 'get_last_known_user_connection_timestamp')

    mocker.patch.object(workspace_helper, 'check_workspace_usage_for_current_month')
    workspace_helper.check_workspace_usage_for_current_month.return_value = False

    mocker.patch.object(workspace_helper, 'check_if_workspace_available_on_first_day')
    workspace_helper.check_if_workspace_available_on_first_day.return_value = True

    mocker.patch.object(workspace_helper, 'check_if_workspace_needs_to_be_terminated')
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = 'Yes - Dry Run'
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ''
