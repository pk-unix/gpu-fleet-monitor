#!/usr/bin/env python3
"""
collect.py — Poll GCE GPU instances and discover Cloud Logging streams.

Run by cron every 5 minutes (or via the app's Refresh button).

Usage:
    python collect.py                        # all projects in projects.yaml
    python collect.py --project my-project   # one project by key
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml
import db

GCLOUD = "gcloud"
ROOT = Path(__file__).parent
RACK_RE = re.compile(r"(rack\d+)", re.IGNORECASE)


def load_projects() -> list[dict]:
    with open(ROOT / "projects.yaml") as f:
        return yaml.safe_load(f)["projects"]


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fetch_instances(project_id: str) -> list[dict]:
    fmt = "csv[no-heading](name,id,zone,machineType.basename(),status,lastStartTimestamp,statusMessage)"
    out = subprocess.run(
        [GCLOUD, "compute", "instances", "list",
         f"--project={project_id}", f"--format={fmt}"],
        capture_output=True, text=True, timeout=300,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:500])
    rows = []
    for line in out.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split(",", 6)
        parts += [""] * (7 - len(parts))
        name, iid, zone, mtype, status, last_start, msg = parts[:7]
        m = RACK_RE.search(name)
        rows.append({
            "name": name, "instance_id": iid, "zone": zone,
            "machine_type": mtype, "status": status,
            "last_start": last_start, "status_message": msg,
            "rack": m.group(1).lower() if m else "",
        })
    return rows


def collect_one(proj: dict) -> None:
    key = proj["key"]
    project_id = proj["project_id"]
    print(f"  [{key}] collecting…", end=" ", flush=True)
    try:
        instances = fetch_instances(project_id)
        db.save_instances(key, instances, _now())
        print(f"{len(instances)} instances")
    except Exception as e:
        print(f"ERROR: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", help="Collect a single project by key")
    args = ap.parse_args()

    db.init()
    projects = load_projects()
    if args.project:
        projects = [p for p in projects if p["key"] == args.project]
        if not projects:
            print(f"No project with key: {args.project}")
            sys.exit(1)

    for proj in projects:
        collect_one(proj)
    print("Done.")


if __name__ == "__main__":
    main()
