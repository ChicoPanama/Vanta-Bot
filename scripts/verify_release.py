#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from typing import Optional

PHASE_STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "PHASE_STATE.md"
)


def read_file_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_phase_state(text: str) -> tuple[int, str]:
    current_phase = None
    status = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("current_phase:"):
            try:
                current_phase = int(line.split(":", 1)[1].strip())
            except Exception:
                pass
        elif line.startswith("status:"):
            status = line.split(":", 1)[1].strip()
    if current_phase is None or not status:
        raise ValueError("Invalid PHASE_STATE.md: current_phase or status missing")
    return current_phase, status


def load_github_event() -> Optional[dict]:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        return None
    try:
        with open(event_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def extract_pr_metadata(
    event: Optional[dict],
) -> tuple[Optional[int], list, Optional[str]]:
    if not event or "pull_request" not in event:
        return None, [], None
    pr = event["pull_request"]
    labels = [lbl.get("name", "") for lbl in pr.get("labels", [])]
    body = pr.get("body") or ""
    phase_label = None
    for label in labels:
        m = re.match(r"^phase:(\d+)$", label.strip())
        if m:
            phase_label = int(m.group(1))
            break
    return phase_label, labels, body


def fail(message: str) -> None:
    print(f"❌ {message}")
    sys.exit(1)


def warn(message: str) -> None:
    print(f"⚠️  {message}")


def check_phase_gate() -> None:
    if not os.path.exists(PHASE_STATE_PATH):
        fail("PHASE_STATE.md not found at repository root")
    current_phase, status = parse_phase_state(read_file_text(PHASE_STATE_PATH))
    event = load_github_event()
    pr_phase, labels, _body = extract_pr_metadata(event)

    # If not a PR (e.g., push), do not enforce phase labelling
    if pr_phase is None:
        print("ℹ️  No PR phase label detected; phase gate not enforced for this event.")
        return

    if pr_phase <= current_phase:
        print(
            f"✅ Phase gate passed: PR phase {pr_phase} <= current phase {current_phase}"
        )
        return

    # pr_phase > current_phase → only allowed if exactly +1 and current PASSED
    if pr_phase == current_phase + 1 and status == "PASSED":
        print(
            f"✅ Phase gate passed: promoting to phase {pr_phase} with current phase PASSED"
        )
        return

    fail(
        "Phase gate blocked: attempting to start next phase before current PASSED. "
        f"current_phase={current_phase}, status={status}, pr_phase={pr_phase}"
    )


def check_pr_policy(strict: bool = False) -> None:
    # Basic repository hygiene checks
    required_files = [
        PHASE_STATE_PATH,
        os.path.join(os.path.dirname(PHASE_STATE_PATH), "PHASES_BREAKDOWN.md"),
        os.path.join(os.path.dirname(PHASE_STATE_PATH), "DEPENDENCIES.md"),
        os.path.join(os.path.dirname(PHASE_STATE_PATH), "DELIVERY_PLAN.md"),
        os.path.join(
            os.path.dirname(PHASE_STATE_PATH), ".github", "PULL_REQUEST_TEMPLATE.md"
        ),
    ]
    missing = [p for p in required_files if not os.path.exists(p)]
    if missing:
        fail(f"Missing required planning artifacts: {missing}")

    # PR metadata checks
    event = load_github_event()
    pr_phase, labels, body = extract_pr_metadata(event)
    if pr_phase is None:
        fail("PR must include label 'phase:N'")
    has_type_label = any(lbl.startswith("type:") for lbl in labels)
    if not has_type_label:
        fail("PR must include a 'type:<category>' label")

    # Template section checks (lightweight)
    required_sections = [
        "What & Why",
        "Risks",
        "Rollback Plan",
        "Test Plan",
        "Manual Validation",
    ]
    missing_sections = [s for s in required_sections if s.lower() not in body.lower()]
    if missing_sections:
        if strict:
            fail(f"PR description missing required sections: {missing_sections}")
        else:
            warn(f"PR description missing recommended sections: {missing_sections}")

    print("✅ verify_release checks passed")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify release readiness and phase gates"
    )
    parser.add_argument(
        "--phase-gate", action="store_true", help="Only run phase gate checks"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Fail missing PR sections"
    )
    args = parser.parse_args()

    if args.phase_gate:
        check_phase_gate()
    else:
        # Run both policy and gate checks during verify_release job
        check_pr_policy(strict=args.strict)
        check_phase_gate()


if __name__ == "__main__":
    main()
