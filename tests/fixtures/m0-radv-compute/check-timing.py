# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile


def run(executable, *options, env=None):
    return subprocess.run((executable, *options), capture_output=True, text=True, env=env, timeout=10)


def check_pass(executable, verbose):
    options = ('--verbose',) if verbose else ()
    completed = run(executable, *options)
    assert completed.returncode == 0, completed
    report = json.loads(completed.stdout)
    assert report['case_id'] == 'm0.radv.compute', report
    assert report['schema_version'] == 1 and report['execution_target'] == 'linux', report
    assert report['status'] == 'PASS' and report['gpu_execution_ns'] is None, report
    assert (report['initial_checks'], report['warmups'], report['sample_count']) == (1, 5, 30), report
    assert report['checked_words_per_dispatch'] == 4096 and report['verbose'] is verbose, report

    metric_names = ('cpu_queue_submit_ns', 'cpu_fence_wait_ns', 'cpu_submit_to_completion_ns')
    for name in metric_names:
        metric = report[name]
        samples = metric['samples']
        assert len(samples) == 30 and all(type(value) is int and value >= 0 for value in samples), metric
        assert metric['median'] == statistics.median(samples), metric
        assert metric['p95'] == sorted(samples)[28], metric
        assert metric['min'] == min(samples) and metric['max'] == max(samples), metric
        assert metric['range'] == max(samples) - min(samples), metric

    submit, wait, completion = (report[name]['samples'] for name in metric_names)
    assert all(total >= queue + fence for queue, fence, total in zip(submit, wait, completion)), report

    markers = [json.loads(line) for line in completed.stderr.splitlines() if line.startswith('{')]
    assert markers[0] == {'case_id': 'm0.radv.compute', 'event': 'start', 'mode': 'host_timing'}, markers
    expected = [('correctness', 1), *(('warmup', i) for i in range(1, 6)), *(('sample', i) for i in range(1, 31))]
    events = [{'event': 'dispatch', 'phase': phase, 'index': index, 'status': 'PASS'} for phase, index in expected]
    assert markers[1:] == (events if verbose else []), markers


if __name__ == '__main__':
    executable, injected_executable = sys.argv[1:]
    check_pass(executable, verbose=False)
    check_pass(executable, verbose=True)

    invalid = run(executable, '--unknown')
    assert invalid.returncode == 2 and not invalid.stdout and invalid.stderr.startswith('Usage:'), invalid

    with tempfile.TemporaryDirectory() as temp:
        missing_icd = str(Path(temp) / 'missing-icd.json')
        missing = run(executable, env={**os.environ, 'VK_DRIVER_FILES': missing_icd, 'VK_ICD_FILENAMES': missing_icd})
    failure = json.loads(missing.stdout)
    assert missing.returncode == 1 and failure['status'] == 'ERROR', missing
    assert failure['stage'] == 'vkCreateInstance' and 'cpu_submit_to_completion_ns' not in failure, failure

    for fault, expected_status in (('no-op', 'FAIL'), ('timeout', 'TIMEOUT')):
        injected = run(injected_executable, fault)
        report = json.loads(injected.stdout)
        assert injected.returncode == 1 and report['status'] == expected_status, injected
        assert 'cpu_submit_to_completion_ns' not in report, report
        marker = json.loads(injected.stderr.splitlines()[-1])
        assert marker == {'event': 'dispatch', 'phase': 'sample', 'index': 2, 'status': 'FAILED'}, marker
        if fault == 'no-op':
            assert report['mismatch_count'] == 4096 and report['first_mismatch_actual'] == 0, report
        else:
            assert report['stage'] == 'vkWaitForFences', report
