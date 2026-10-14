#!/usr/bin/env python3
"""Validate action.yml without third-party tooling.

Checks the structural rules GitHub enforces at runtime, plus a bash syntax pass
over every embedded `run:` block using the shell's own parser.
"""

import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ACTION = ROOT / "action.yml"

REQUIRED_INPUT_KEYS = ("description",)
errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def main() -> int:
    if not ACTION.exists():
        print(f"missing {ACTION}", file=sys.stderr)
        return 1

    try:
        doc = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"::error::action.yml is not valid YAML: {exc}")
        return 1

    if not isinstance(doc, dict):
        print("::error::action.yml must contain a YAML mapping at the top level")
        return 1

    for key in ("name", "description", "runs"):
        if key not in doc:
            fail(f"action.yml: missing top-level '{key}'")

    runs = doc.get("runs", {})
    if runs.get("using") != "composite":
        fail("action.yml: runs.using must be 'composite'")

    inputs = doc.get("inputs", {}) or {}
    for name, spec in inputs.items():
        if not isinstance(spec, dict):
            fail(f"input '{name}': must be a mapping")
            continue
        for key in REQUIRED_INPUT_KEYS:
            if key not in spec:
                fail(f"input '{name}': missing '{key}'")
        if "default" in spec and spec["default"] is None:
            fail(f"input '{name}': default must not be null")

    steps = runs.get("steps", []) or []
    if not steps:
        fail("action.yml: runs.steps is empty")

    step_ids = {s["id"] for s in steps if isinstance(s, dict) and "id" in s}

    for index, step in enumerate(steps):
        label = step.get("name") or step.get("id") or f"#{index}"
        if "uses" in step:
            if "run" in step:
                fail(f"step '{label}': cannot have both 'uses' and 'run'")
            continue
        if "run" not in step:
            fail(f"step '{label}': needs either 'uses' or 'run'")
            continue
        # Composite actions must declare a shell or GitHub rejects the run.
        if not step.get("shell"):
            fail(f"step '{label}': composite 'run' step requires 'shell'")
        else:
            check_bash(label, step)

    for name, spec in (doc.get("outputs", {}) or {}).items():
        value = (spec or {}).get("value", "") if isinstance(spec, dict) else str(spec)
        for referenced in re.findall(r"steps\.([A-Za-z0-9_-]+)\.", value):
            if referenced not in step_ids:
                fail(f"output '{name}': references unknown step id '{referenced}'")

    if errors:
        for e in errors:
            print(f"::error::{e}")
        return 1

    print(f"action.yml OK - {len(inputs)} inputs, {len(steps)} steps, {len(step_ids)} step ids")
    return 0


def check_bash(label: str, step: dict) -> None:
    shell = step.get("shell")
    if shell not in ("bash", "sh"):
        return
    script = step["run"]
    # GitHub expands ${{ }} before the shell sees it; substitute a harmless token.
    script = re.sub(r"\$\{\{[^}]*\}\}", "TOKEN", script)
    proc = subprocess.run(
        ["bash", "-n"],
        input=script,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        fail(f"step '{label}': bash syntax error -> {proc.stderr.strip()}")


if __name__ == "__main__":
    sys.exit(main())
