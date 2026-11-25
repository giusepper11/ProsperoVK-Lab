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
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

accept = runpy.run_path(str(Path(__file__).with_name("m0-accept.py")))
ID = accept["ID"]
PARENT = "/data/homebrew"
DEST = PARENT + "/" + ID


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


def check_free(manager):
    if ID in json.dumps(manager.request("titles")["titles"]) or any(
            e["name"].casefold() == ID.casefold() for e in manager.entries(PARENT)):
        raise ValueError("title ID or destination already in use")


def deploy(manager, app):
    accept["package"](app)
    check_free(manager)
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
    check_free(manager)
    manager.request("ftp/rename", data={"from": stage, "to": DEST})
    compare(manager, app, DEST)
    print("DEPLOY PASS", DEST)


def retrieve(manager, name, out):
    if not re.fullmatch(r"run-[0-9]{6}", name):
        raise ValueError("expected run-NNNNNN")
    remote = f"{DEST}/{name}"
    entries = {e["name"] for e in manager.entries(remote) if not e["is_dir"]}
    out.mkdir(parents=True, exist_ok=False)
    for file in ("start.log", "result.json", "exit-code.txt", "timing.json", "timing-exit-code.txt"):
        if file in entries:
            (out / file).write_bytes(manager.download(f"{remote}/{file}"))
    log = manager.request("klogs")
    lines = [str(line) for line in log["lines"] if ID in str(line) or "ProsperoVK Lab" in str(line)]
    (out / "title-klog.log").write_text("".join(s + "\n" for s in lines))
    print(f"Retrieved {name} to {out}. Kernel log connected={log.get('connected')}, title lines={len(lines)}")


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
    args = parser.parse_args()
    manager = Manager(args.host)
    if args.cmd == "deploy":
        deploy(manager, args.app)
    elif args.cmd == "readback":
        accept["package"](args.app)
        compare(manager, args.app, DEST)
        print("DEPLOY PASS", DEST)
    else:
        retrieve(manager, args.run, args.out)
