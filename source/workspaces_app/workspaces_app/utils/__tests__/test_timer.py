#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import math
import unittest

# Cost Optimizer for Amazon Workspaces
from ..timer import Timer


@unittest.mock.patch("time.perf_counter")
def test_timer(mock_perf_counter):
    mock_perf_counter.side_effect = [50.0, 120.0]
    timer = Timer()
    timer.start()
    assert math.isclose(timer.get_elapsed_time(), 70.0)
