#!/usr/bin/env python3
"""gcp_logs.py — Cloud Logging helpers for GPU instances."""
from __future__ import annotations

import json
import subprocess
from typing import Optional


LOG_FILTERS = {
    "xid":  'jsonPayload.XID != "" OR textPayload =~ "XID"',
    "host": 'logName =~ "hostError|system_event"',
    "syslog": 'logName =~ "syslog" AND severity >= WARNING',
}


def build_gcloud_commands(project_id: str, instance_name: str) -> dict[str, str]:
    """Return copy-pasteable gcloud logging commands for an instance."""
    base = (f'gcloud logging read --project={project_id} '
            f'--freshness=7d --format=json')
    return {
        "XID errors": (f'{base} \'resource.labels.instance_id="{instance_name}" '
                       f'AND (jsonPayload.XID!="" OR textPayload=~"XID")\''),
        "Host errors": (f'{base} \'resource.labels.instance_id="{instance_name}" '
                        f'AND logName=~"hostError"\''),
        "Syslog warnings": (f'{base} \'resource.labels.instance_id="{instance_name}" '
                            f'AND logName=~"syslog" AND severity>=WARNING\''),
    }


def fetch_logs(project_id: str, instance_name: str,
               filter_key: str = "xid", limit: int = 50) -> list[dict]:
    log_filter = (f'resource.labels.instance_id="{instance_name}" '
                  f'AND ({LOG_FILTERS.get(filter_key, "")})')
    out = subprocess.run(
        ["gcloud", "logging", "read", f"--project={project_id}",
         "--freshness=7d", "--format=json", f"--limit={limit}", log_filter],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0 or not out.stdout.strip():
        return []
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return []
