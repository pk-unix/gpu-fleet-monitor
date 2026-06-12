# GPU Fleet Monitor

A Flask dashboard for monitoring GCP GPU instance fleets (GB200, B200, H100, etc.) — tracks instance health, surfaces Cloud Logging events (XID errors, host faults, syslog warnings) per node, and provides copy-pasteable `gcloud` commands for deep investigation.

![Python](https://img.shields.io/badge/python-3.10+-blue) ![GCP](https://img.shields.io/badge/cloud-GCP-4285F4) ![Flask](https://img.shields.io/badge/flask-3.0-green)

---

## What it does

- **Fleet overview** — all GCP projects in one view, instance counts, running/stopped status
- **Per-instance detail** — zone, machine type, status, last start time, rack grouping
- **Cloud Logging integration** — XID GPU errors, host-level faults, syslog warnings surfaced in the UI
- **Copyable gcloud commands** — one-click copy for `gcloud logging read` queries scoped to each instance
- **Background refresh** — cron/launchd driven; manual refresh button in the UI
- **Multi-project** — configure any number of GCP projects in `projects.yaml`

## Architecture

```
projects.yaml         ← GCP project IDs + display config
      │
      ▼
collect.py  (cron every 5 min)
      │  gcloud compute instances list
      ▼
fleet.db    (SQLite)
      │
      ▼
app.py  (Flask — port 8484)
      │  on-demand: gcloud logging read (per instance)
      ▼
Browser dashboard
```

## Quick start

```bash
git clone https://github.com/pk-unix/gpu-fleet-monitor
cd gpu-fleet-monitor

# 1. Authenticate with GCP
gcloud auth application-default login

# 2. Configure your projects
cp projects.example.yaml projects.yaml
$EDITOR projects.yaml

# 3. Install dependencies
python3 -m venv venv && venv/bin/pip install -r requirements.txt

# 4. Initial collection
venv/bin/python collect.py

# 5. Start the dashboard
venv/bin/python app.py
# → http://localhost:8484
```

## Cron example

```bash
# Collect every 5 minutes
*/5 * * * * /opt/gpu-monitor/venv/bin/python /opt/gpu-monitor/collect.py
```

## projects.yaml format

```yaml
projects:
  - key: gb200-fleet
    display_name: "GB200 Production Fleet"
    project_id: "my-gcp-project-12345"
    machine_type_prefix: "a4-"
```

## Requirements

- Python 3.10+
- `gcloud` CLI authenticated (`gcloud auth application-default login`)
- GCP roles: `compute.viewer` + `logging.viewer` on each project

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3, Flask 3 |
| Storage | SQLite |
| Cloud | GCP Compute Engine API + Cloud Logging |
| CLI | `gcloud` subprocess |
| Frontend | Vanilla HTML/CSS |
