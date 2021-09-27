import sys
import os
from unittest import mock
mock.patch.dict(os.environ, {'AutoStopTimeoutHours': '1'}).start()
sys.path.append('engine')
import ecs.workspaces_app


def test_process_input_regions_1():
    ecs.workspaces_app.REGIONS = []
    valid_workspaces_regions = ['us-east-1']
    result = ecs.workspaces_app.process_input_regions(valid_workspaces_regions)
    assert result == {'us-east-1'}


def test_process_input_regions_2():
    ecs.workspaces_app.REGIONS = 'us-west-2, us-east-1, us-east-2'
    valid_workspaces_regions = ['us-east-1', 'us-west-2']
    result = ecs.workspaces_app.process_input_regions(valid_workspaces_regions)
    assert result == {'us-east-1', 'us-west-2'}


def test_process_input_regions_3():
    ecs.workspaces_app.REGIONS = '"us-west-2", "us-east-1", us-east-2'
    valid_workspaces_regions = ['us-east-1', 'us-west-2']
    result = ecs.workspaces_app.process_input_regions(valid_workspaces_regions)
    assert result == {'us-east-1', 'us-west-2'}


def test_process_input_regions_4():
    ecs.workspaces_app.REGIONS = '"us-west-2", "us-east-1", us-east-2'
    valid_workspaces_regions = ['us-east-1', 'us-west-2']
    result = ecs.workspaces_app.process_input_regions(valid_workspaces_regions)
    assert result == {'us-east-1', 'us-west-2'}


def test_process_input_regions_5():
    ecs.workspaces_app.REGIONS = '"us-west-2", us-east-2, 1234,ajdfbkjfb'
    valid_workspaces_regions = ['us-east-1', 'us-west-2']
    result = ecs.workspaces_app.process_input_regions(valid_workspaces_regions)
    assert result == {'us-west-2'}
