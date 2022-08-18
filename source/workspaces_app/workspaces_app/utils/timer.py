#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import time
import typing


class TimerNotStartedException(Exception):
    pass


class Timer:
    """Timer based on `perf_counter`. Call `start`, then `get_elapsed_time` to get the time elapsed since start in seconds."""

    def __init__(self) -> None:
        self._start_time: typing.Union[float, None] = None

    def start(self) -> None:
        """Start the timer. """
        self._start_time = time.perf_counter()

    def get_elapsed_time(self) -> float:
        """Get the time elapsed from the last call of `start` in seconds."""
        if not self._start_time:
            raise TimerNotStartedException('Timer stopped without starting.')
        return time.perf_counter() - self._start_time
