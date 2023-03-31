#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

def append_entry(old_csv: str, result: dict) -> str:
    s = ','
    csv = old_csv + s.join((
        result['workspaceID'],
        str(result['billableTime']),
        str(result['hourlyThreshold']),
        result['optimizationResult'],
        result['bundleType'],
        result['initialMode'],
        result['newMode'],
        result['userName'],
        result['computerName'],
        result['directoryId'],
        result['workspaceTerminated'],
        ''.join(('"', str(result['tags']), '"')),
        str(result['reportDate']) + '\n'  # Adding quotes to the string to help with csv format
    ))

    return csv


def expand_csv(raw_csv: str) -> str:
    csv = raw_csv.replace(',-M-', ',ToMonthly').replace(',-H-', ',ToHourly'). \
        replace(',-E-', ',Failed to change the mode').replace(',-N-', ',No Change').replace(',-S-', ',Skipped')
    return csv
