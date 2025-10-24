#!/usr/bin/env python3
"""
Cisco CPU-Only MCP (Solution Version)

Usage:
  python server_cpu_solution.py --inventory devices.yaml
"""
from __future__ import annotations
import argparse, os, re, yaml
from typing import Dict, Any, Optional
from fastmcp import FastMCP
from netmiko import ConnectHandler

mcp = FastMCP("Cisco CPU-Only MCP (Solution Version)")
DEVICES: Dict[str, Dict[str, Any]] = {}
INVENTORY_PATH = "devices.yaml"

def load_inventory(path: str) -> Dict[str, Dict[str, Any]]:
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    devices = data.get("devices", {})
    for _, d in devices.items():
        d.setdefault("port", 22)
        d.setdefault("device_type", "cisco_ios")
    return devices

def default_device_name() -> str:
    return next(iter(DEVICES))

def get_connection(device_name: Optional[str] = None):
    dev = DEVICES[device_name or default_device_name()]
    conn = ConnectHandler(**dev)
    if dev.get("secret"):
        conn.enable()
    return conn

# -----------------------------------------
# WORKING SOLUTION REGEX
# -----------------------------------------
CPU_LINE_HINT = "one minute:"
CPU_RE = re.compile(
    r"five seconds: (?P<s5>\\d+)%.*one minute: (?P<m1>\\d+)%.*five minutes: (?P<m5>\\d+)%",
    re.IGNORECASE,
)

def parse_cpu_utilization(raw: str) -> Dict[str, Optional[float]]:
    five_seconds = one_minute = five_minutes = None
    for line in raw.splitlines():
        if CPU_LINE_HINT in line:
            m = CPU_RE.search(line)
            if m:
                try:
                    five_seconds = float(m.group("s5"))
                    one_minute = float(m.group("m1"))
                    five_minutes = float(m.group("m5"))
                except Exception:
                    pass
            break
    return {"five_seconds": five_seconds, "one_minute": one_minute, "five_minutes": five_minutes}

@mcp.tool(name="get_cpu_utilization", description="Run 'show processes cpu | include one minute' and parse output.")
def get_cpu_utilization(device: Optional[str] = None) -> dict:
    conn = get_connection(device)
    raw = conn.send_command("show processes cpu | include one minute") or conn.send_command("show processes cpu")
    conn.disconnect()
    return {"device": device or default_device_name(), "raw": raw, "parsed": parse_cpu_utilization(raw)}

def _parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", "-i", default="devices.yaml")
    return p.parse_args()

if __name__ == "__main__":
    args = _parse_args()
    DEVICES.update(load_inventory(args.inventory))
    mcp.run()

