"""Tests for instance exclusion tag violation metrics"""

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


class TestCollectInstanceTagMetrics:

    @patch('prometheus_ganeti_exporter.__main__.requests.get')
    def test_no_exclusion_tags_configured_returns_no_metrics(self, mock_get, sample_config,
                                                               mock_cluster_info):
        mock_get.return_value = make_response(mock_cluster_info)
        collector = GanetiCollector(sample_config)

        assert collector.collect_instance_tag_metrics([]) == []

    @patch('prometheus_ganeti_exporter.__main__.requests.get')
    def test_no_violations_reports_healthy(self, mock_get, sample_config,
                                           mock_cluster_info_with_exclusion_tags):
        mock_get.return_value = make_response(mock_cluster_info_with_exclusion_tags)
        collector = GanetiCollector(sample_config)

        # Two instances with same exclusion tag but on DIFFERENT nodes — no violation
        instances = [
            {'name': 'vm1', 'oper_state': True, 'pnode': 'node1', 'tags': ['gpu:nvidia-a100']},
            {'name': 'vm2', 'oper_state': True, 'pnode': 'node2', 'tags': ['gpu:nvidia-a100']},
        ]
        metrics = collector.collect_instance_tag_metrics(instances)

        samples = list(metrics[0].samples)
        assert samples[0].value == 1  # healthy

    @patch('prometheus_ganeti_exporter.__main__.requests.get')
    def test_two_instances_same_tag_same_node_is_violation(self, mock_get, sample_config,
                                                            mock_cluster_info_with_exclusion_tags):
        mock_get.return_value = make_response(mock_cluster_info_with_exclusion_tags)
        collector = GanetiCollector(sample_config)

        instances = [
            {'name': 'vm1', 'oper_state': True, 'pnode': 'node1', 'tags': ['gpu:nvidia-a100']},
            {'name': 'vm2', 'oper_state': True, 'pnode': 'node1', 'tags': ['gpu:nvidia-a100']},
        ]
        metrics = collector.collect_instance_tag_metrics(instances)

        samples = list(metrics[0].samples)
        assert samples[0].value == 0  # unhealthy

    @patch('prometheus_ganeti_exporter.__main__.requests.get')
    def test_stopped_instances_do_not_count_as_violation(self, mock_get, sample_config,
                                                          mock_cluster_info_with_exclusion_tags):
        mock_get.return_value = make_response(mock_cluster_info_with_exclusion_tags)
        collector = GanetiCollector(sample_config)

        # One running + one stopped on same node — stopped is ignored
        instances = [
            {'name': 'vm1', 'oper_state': True, 'pnode': 'node1', 'tags': ['gpu:nvidia-a100']},
            {'name': 'vm2', 'oper_state': False, 'pnode': 'node1', 'tags': ['gpu:nvidia-a100']},
        ]
        metrics = collector.collect_instance_tag_metrics(instances)

        samples = list(metrics[0].samples)
        assert samples[0].value == 1  # healthy
