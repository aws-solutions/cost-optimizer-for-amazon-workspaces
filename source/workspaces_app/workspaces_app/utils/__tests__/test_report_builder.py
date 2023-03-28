#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from .. import report_builder


def test_append_entry_adds_record_to_csv():
    test_params = {
        'workspaceID': 'workspaceID',
        'billableTime': 'billableTime',
        'hourlyThreshold': 'hourlyThreshold',
        'optimizationResult': 'optimizationResult',
        'bundleType': 'bundleType',
        'initialMode': 'initialMode',
        'newMode': 'newMode',
        'userName': 'userName',
        'computerName': 'computerName',
        'directoryId': 'directoryId',
        'workspaceTerminated': 'workspaceTerminated',
        'tags': 'tags',
        'reportDate': 'test'
    }
    old_csv = ""
    expected = 'workspaceID,billableTime,hourlyThreshold,optimizationResult,bundleType,initialMode,newMode,userName,computerName,directoryId,workspaceTerminated,"tags",test\n'
    assert report_builder.append_entry(old_csv, test_params) == expected


def test_expand_csv_adds_correct_description_to_status_codes():
    raw_csv = ",-M-,-H-,-E-,-N-,-S-"
    expanded_csv = ",ToMonthly,ToHourly,Failed to change the mode,No Change,Skipped"
    assert report_builder.expand_csv(raw_csv) == expanded_csv


