#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit Prospero Manager transfers. Launch is a separate operator action."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import runpy
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

accept = runpy.run_path(str(Path(__file__).with_name("m0-accept.py")))
ID = accept["ID"]
PARENT = "/data/homebrew"


class Manager:
    def __init__(self, host):
        ip = ipaddress.IPv4Address(host)
        self.base = f"http://{ip}:7070/api/"
        self.opener = build_opener(ProxyHandler({}))

    def request(self, route, query=None, data=None, binary=False):
        url = self.base + route
        if query:
            url += "?" + urlencode(query)
        headers = {}
        if isinstance(data, dict):
            data = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        elif data is not None:
            headers["Content-Type"] = "application/octet-stream"
        with self.opener.open(Request(url, data=data, headers=headers), timeout=90) as response:
            if binary:
                return response.read()
            value = json.load(response)
            if value.get("error") or value.get("ok") is False:
                raise ValueError(value.get("error") or "Manager operation failed")
            return value

    def entries(self, path):
        listing = self.request("ftp/list", {"path": path})
        if listing["path"].rstrip("/") != path:
            raise ValueError("unexpected listing path")
        return listing["entries"]

    def download(self, path):
        return self.request("ftp/download", {"path": path}, binary=True)


def compare(manager, app, dest):
    for file in sorted(app.rglob("*")):
        if file.is_file():
            remote = manager.download(f"{dest}/{file.relative_to(app)}")
            if hashlib.sha256(remote).hexdigest() != accept["digest"](file):
                raise ValueError(f"readback mismatch: {file.name}")


def check_free(manager, title_id):
    if title_id.casefold() in json.dumps(manager.request("titles")["titles"]).casefold() or any(
            e["name"].casefold() == title_id.casefold() for e in manager.entries(PARENT)):
        raise ValueError("title ID or destination already in use")


def deploy(manager, app):
    accept["package"](app)
    check_free(manager, app.name)
    stage = f"{PARENT}/.prosperovk-{uuid4().hex}"
    manager.request("ftp/mkdir", data={"path": stage})
    print("Staging directory", stage, flush=True)
    for file in sorted(app.rglob("*")):
        remote = f"{stage}/{file.relative_to(app)}"
        if file.is_dir():
            manager.request("ftp/mkdir", data={"path": remote})
        else:
            manager.request("ftp/upload", {"path": remote}, file.read_bytes())
    compare(manager, app, stage)
    check_free(manager, app.name)
    dest = f"{PARENT}/{app.name}"
    manager.request("ftp/rename", data={"from": stage, "to": dest})
    compare(manager, app, dest)
    print("DEPLOY PASS", dest)


def retrieve(manager, name, out, app=None):
    if not re.fullmatch(r"run-[0-9]{6}", name):
        raise ValueError("expected run-NNNNNN")
    title_id = ID
    workload = "compute"
    if app is not None:
        package = accept["package"](app)
        title_id = app.name
        workload = package["workload"]
        if workload == "m1":
            compare(manager, app, f"{PARENT}/{title_id}")
    remote = f"{PARENT}/{title_id}/{name}"
    entries = {e["name"] for e in manager.entries(remote) if not e["is_dir"]}
    out.mkdir(parents=True, exist_ok=False)
    artifacts = {
        "compute": ("result.json", "timing.json", "timing-exit-code.txt"),
        "cts": ("TestResults.qpa", "title.log"),
        "m1": ("report.json", "report.json.start.json"),
    }[workload]
    for file in ("start.log", "exit-code.txt", *artifacts):
        if file in entries:
            (out / file).write_bytes(manager.download(f"{remote}/{file}"))
    capture = {"title_id": title_id, "run": name}
    if workload == "m1":
        capture["build_id"] = package["build_id"]
    title_name = {"compute": "ProsperoVK Lab", "cts": "ProsperoVK Lab CTS", "m1": "ProsperoVK Lab M1"}[workload]
    for route, filename in (("klogs", "title-klog.log"), ("logs", "manager-title.log")):
        try:
            log = manager.request(route)
            lines = [str(line) for line in log["lines"] if title_id in str(line)
                     or (title_name in str(line) and (workload != "compute" or not
                         any(other in str(line) for other in ("ProsperoVK Lab CTS", "ProsperoVK Lab M1"))))]
            (out / filename).write_text("".join(s + "\n" for s in lines))
            capture[route] = dict(connected=log.get("connected"), matched_lines=len(lines))
        except (URLError, TimeoutError, ValueError, KeyError) as error:
            capture[route] = dict(error=type(error).__name__)
    (out / "retrieval.json").write_text(json.dumps(capture, indent=2) + "\n")
    print(f"Retrieved {remote} to {out}. Log status in retrieval.json.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("deploy", "readback"):
        command = commands.add_parser(cmd)
        command.add_argument("app", type=Path)
        command.add_argument("host")
    command = commands.add_parser("retrieve")
    command.add_argument("host")
    command.add_argument("run")
    command.add_argument("out", type=Path)
    command.add_argument("--app", type=Path, help="verified local title folder (required for CTS and M1)")
    args = parser.parse_args()
    manager = Manager(args.host)
    if args.cmd == "deploy":
        deploy(manager, args.app)
    elif args.cmd == "readback":
        accept["package"](args.app)
        dest = f"{PARENT}/{args.app.name}"
        compare(manager, args.app, dest)
        print("DEPLOY PASS", dest)
    else:
        retrieve(manager, args.run, args.out, args.app)
