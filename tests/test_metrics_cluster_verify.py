"""Tests for cluster-verify metrics collection logic"""

#
# Copyright (c) 2026, Ganeti Project
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from unittest.mock import patch, Mock
from prometheus_ganeti_exporter.__main__ import GanetiCollector


def make_response(data):
    m = Mock(status_code=200)
    m.json.return_value = data
    return m


class TestCollectClusterVerifyMetrics:

    @patch('prometheus_ganeti_exporter.__main__.requests.get')
    def test_no_verify_jobs_returns_empty_metrics(self, mock_get, sample_config, mock_cluster_info):
        mock_get.return_value = make_response(mock_cluster_info)
        collector = GanetiCollector(sample_config)

        jobs = [{'id': 1, 'status': 'success', 'summary': ['INSTANCE_CREATE']}]
        metrics = collector.collect_cluster_verify_metrics(jobs)

        assert len(metrics) == 3
        for m in metrics:
            assert list(m.samples) == []

    @patch('prometheus_ganeti_exporter.__main__.requests.get')
    def test_all_children_pass_reports_healthy(self, mock_get, sample_config, mock_cluster_info):
        parent_full = {
            'id': 100,
            'status': 'success',
            'summary': ['CLUSTER_VERIFY'],
            'opresult': [{'jobs': [['job', 101], ['job', 102]]}],
            'start_ts': [1640000100, 0],
            'end_ts': [1640000200, 0],
        }
        child_101 = {'id': 101, 'status': 'success', 'opresult': [True],
                     'start_ts': [1640000100, 0], 'end_ts': [1640000150, 0]}
        child_102 = {'id': 102, 'status': 'success', 'opresult': [True],
                     'start_ts': [1640000110, 0], 'end_ts': [1640000160, 0]}

        mock_get.side_effect = [
            make_response(mock_cluster_info),  # __init__ /2/info
            make_response(parent_full),         # /2/jobs/100
            make_response(child_101),           # /2/jobs/101
            make_response(child_102),           # /2/jobs/102
        ]

        collector = GanetiCollector(sample_config)
        jobs_list = [{'id': 100, 'status': 'success', 'summary': ['CLUSTER_VERIFY']}]
        metrics = collector.collect_cluster_verify_metrics(jobs_list)

        job_status = next(m for m in metrics if 'time' not in m.name)
        samples = list(job_status.samples)
        assert len(samples) == 1
        assert samples[0].value == 1

    @patch('prometheus_ganeti_exporter.__main__.requests.get')
    def test_failing_child_reports_unhealthy(self, mock_get, sample_config, mock_cluster_info):
        parent_full = {
            'id': 200,
            'status': 'success',
            'summary': ['CLUSTER_VERIFY'],
            'opresult': [{'jobs': [['job', 201], ['job', 202]]}],
            'start_ts': [1640001000, 0],
            'end_ts': [1640001100, 0],
        }
        child_201 = {'id': 201, 'status': 'success', 'opresult': [True],
                     'start_ts': [1640001000, 0], 'end_ts': [1640001050, 0]}
        child_202 = {'id': 202, 'status': 'error', 'opresult': [False],
                     'start_ts': [1640001010, 0], 'end_ts': [1640001060, 0]}

        mock_get.side_effect = [
            make_response(mock_cluster_info),
            make_response(parent_full),
            make_response(child_201),
            make_response(child_202),
        ]

        collector = GanetiCollector(sample_config)
        jobs_list = [{'id': 200, 'status': 'success', 'summary': ['CLUSTER_VERIFY']}]
        metrics = collector.collect_cluster_verify_metrics(jobs_list)

        job_status = next(m for m in metrics if 'time' not in m.name)
        samples = list(job_status.samples)
        assert len(samples) == 1
        assert samples[0].value == 0
