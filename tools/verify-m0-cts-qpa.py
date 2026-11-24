#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Check the single QPA case selected for M0 without assigning a hardware result."""

import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


CASE_ID = "dEQP-VK.compute.pipeline.basic.copy_ssbo_single_invocation"
CASE_BEGIN = b"#beginTestCaseResult " + CASE_ID.encode("ascii")
CASE_END = b"#endTestCaseResult"
CASE_TERMINATE = b"#terminateTestCaseResult"
BOUNDARIES = (b"#beginSession", CASE_BEGIN, CASE_END, b"#endSession")
MARKERS = {boundary.split()[0] for boundary in BOUNDARIES} | {CASE_TERMINATE}


def check_boundaries(lines):
    next_boundary = 0
    xml_start = 0
    case_xml = None

    for index, line in enumerate(lines):
        line_number = index + 1
        words = line.split(maxsplit=1)
        if not words:
            continue
        if next_boundary == len(BOUNDARIES):
            raise ValueError(f"line {line_number}: data after #endSession")
        if words[0] not in MARKERS:
            continue

        expected = BOUNDARIES[next_boundary]
        marker = line.rstrip(b"\r\n")
        if not line.endswith(b"\n"):
            raise ValueError(f"line {line_number}: unterminated QPA marker")
        is_termination = (expected == CASE_END and marker.startswith(CASE_TERMINATE + b" ")
                          and len(words) == 2)
        if marker != expected and not is_termination:
            raise ValueError(f"line {line_number}: expected {expected.decode('ascii')}")
        if expected == CASE_BEGIN:
            xml_start = index + 1
        if marker == CASE_END:
            case_xml = b"".join(lines[xml_start:index])
        next_boundary += 1

    if next_boundary != len(BOUNDARIES):
        raise ValueError(f"incomplete QPA: missing {BOUNDARIES[next_boundary].decode('ascii')}")
    return case_xml


def parse_cts_result(cts_source, qpa_path, lines):
    parser_path = cts_source / "scripts" / "log" / "log_parser.py"
    spec = importlib.util.spec_from_file_location("cts_log_parser", parser_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load the upstream CTS parser at {parser_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    parser = module.BatchResultParser()
    parser.init(str(qpa_path))
    try:
        for line_number, line in enumerate(lines, 1):
            parser.curLine = line_number
            parser.parseLine(line)
    except module.ParseError as error:
        raise ValueError(str(error)) from error

    if len(parser.testCaseResults) != 1 or parser.testCaseResults[0].name != CASE_ID:
        raise ValueError("upstream parser did not return exactly the selected CTS case")
    return parser.testCaseResults[0]


def verify(cts_source, qpa_path):
    payload = qpa_path.read_bytes()
    lines = io.BytesIO(payload).readlines()
    case_xml = check_boundaries(lines)
    result = parse_cts_result(cts_source, qpa_path, lines)

    if case_xml is not None:
        root = ET.fromstring(case_xml)
        if root.tag != "TestCaseResult" or root.get("CasePath") != CASE_ID:
            raise ValueError("XML TestCaseResult CasePath does not match the selected CTS case")
        results = root.findall(".//Result")
        if len(results) != 1 or root.find("Result") is not results[0]:
            raise ValueError("expected exactly one direct XML Result")
        if results[0].get("StatusCode") != result.statusCode:
            raise ValueError("XML Result StatusCode does not match the upstream parser status")

    return {
        "case_id": result.name,
        "qpa_status": result.statusCode,
        "detail": result.statusDetails,
        "case_completed": case_xml is not None,
        "qpa_sha256": hashlib.sha256(payload).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cts_source", type=Path, help="pinned Khronos VK-GL-CTS checkout")
    parser.add_argument("qpa", type=Path, help="raw TestResults.qpa")
    args = parser.parse_args()

    try:
        result = verify(args.cts_source, args.qpa)
    except (OSError, ValueError, ET.ParseError) as error:
        print(f"QPA verification failed: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result))
    return 0 if result["case_completed"] and result["qpa_status"] == "Pass" else 1


if __name__ == "__main__":
    sys.exit(main())
