#!/usr/bin/env python3
"""
app.py — GPU Fleet Monitor  (port 8484 by default).

Tracks GCP GPU instance state (GB200 / B200 / H100 etc.) and surfaces
Cloud Logging events (XID errors, host-level faults, interruptions,
syslog entries) per node — with copyable gcloud commands.

Requires: gcloud CLI authenticated, projects listed in projects.yaml.
"""
from __future__ import annotations

import datetime
import subprocess
import threading
from pathlib import Path

import yaml
from flask import Flask, jsonify, redirect, render_template, request, url_for

import db
import gcp_logs

ROOT = Path(__file__).parent
GCLOUD = "gcloud"
PORT = int(__import__("os").environ.get("PORT", 8484))

app = Flask(__name__, template_folder=str(ROOT / "templates"),
            static_folder=str(ROOT / "static"))
app.config["TEMPLATES_AUTO_RELOAD"] = True

db.init()


def load_projects() -> list[dict]:
    with open(ROOT / "projects.yaml") as f:
        return yaml.safe_load(f)["projects"]


def project_index() -> dict[str, dict]:
    return {p["key"]: p for p in load_projects()}


# ── background refresh ────────────────────────────────────────────────────────

_refresh = {"running": False, "done": 0, "total": 0, "started": "", "finished": ""}
_lock = threading.Lock()


def _run_refresh(keys: list[str]) -> None:
    import collect
    with _lock:
        _refresh.update(running=True, done=0, total=len(keys),
                        started=datetime.datetime.now().strftime("%H:%M:%S"),
                        finished="")
    idx = project_index()
    for k in keys:
        try:
            collect.collect_one(idx[k])
        except Exception:
            pass
        with _lock:
            _refresh["done"] += 1
    with _lock:
        _refresh.update(running=False,
                        finished=datetime.datetime.now().strftime("%H:%M:%S"))


# ── template helpers ──────────────────────────────────────────────────────────

@app.template_filter("ago")
def ago(ts: str | None) -> str:
    if not ts:
        return "—"
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
        s = (datetime.datetime.utcnow() - dt).total_seconds()
        if s < 60:
            return f"{int(s)}s ago"
        if s < 3600:
            return f"{int(s/60)}m ago"
        return f"{int(s/3600)}h ago"
    except Exception:
        return ts


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    projects = load_projects()
    instances = {p["key"]: db.get_instances(p["key"]) for p in projects}
    summary = {p["key"]: {
        "total": len(instances[p["key"]]),
        "running": sum(1 for i in instances[p["key"]] if i["status"] == "RUNNING"),
        "stopped": sum(1 for i in instances[p["key"]] if i["status"] != "RUNNING"),
    } for p in projects}
    with _lock:
        refresh_state = dict(_refresh)
    return render_template("index.html", projects=projects, instances=instances,
                           summary=summary, refresh=refresh_state)


@app.route("/instance/<project_key>/<name>")
def instance_detail(project_key: str, name: str):
    instance = db.get_instance(project_key, name)
    if not instance:
        return redirect(url_for("index"))
    logs = db.get_logs(project_key, name, limit=200)
    proj = project_index().get(project_key, {})
    gcloud_cmds = gcp_logs.build_gcloud_commands(proj.get("project_id", ""), name)
    return render_template("instance.html", instance=instance, logs=logs,
                           gcloud_cmds=gcloud_cmds, project_key=project_key)


@app.route("/refresh", methods=["POST"])
def refresh():
    keys = request.form.getlist("keys") or [p["key"] for p in load_projects()]
    threading.Thread(target=_run_refresh, args=(keys,), daemon=True).start()
    return redirect(url_for("index"))


@app.route("/api/refresh-status")
def refresh_status():
    with _lock:
        return jsonify(dict(_refresh))


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print(f"GPU Fleet Monitor → http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
