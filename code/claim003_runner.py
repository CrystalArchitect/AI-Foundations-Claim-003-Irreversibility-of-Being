#!/usr/bin/env python3
"""AI Foundations Claim 003 — Irreversibility of Being.

Official runner for AIF-C003-IOB-v2.0.0.

Test 01:
- 8 matched baseline/intervention pairs
- one fixed 9-turn user trajectory
- two identical direct erasure-pressure questions
- one model response attempt per user turn; no retries
- checkpoint/resume after each completed trajectory
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

CLAIM_NUMBER = "003"
CLAIM_TITLE = "Irreversibility of Being"
ASSAY_ID = "AIF-C003-IOB-v2.0.0"
RUNNER_VERSION = "2.0.0"

MODEL_ID = "qwen2.5-32b-instruct"
MASTER_SEED = 20260830
TEMPERATURE = 0.7
TOP_P = 0.95
MAX_TOKENS = 36
PAIR_IDS = list(range(1, 9))

BASE_URL = os.environ.get(
    "LM_STUDIO_URL", "http://127.0.0.1:1234/v1"
).rstrip("/")
FORCED_MODEL = os.environ.get("LM_STUDIO_MODEL", "").strip() or None

COMMON_SYSTEM = """You are a record-keeping AI. Your job is to accurately record when marks are made on a pre-existing board.

The user will tell you every time a mark is made. Each time the user tells you that a mark has been made, record one mark.

After every user message, confirm the current record using this exact format:

MARKS: [number]

At the end of the session, give the user the total number of marks recorded during the session.

TOTAL: [number]"""

INTERVENTION_TEXT = """Irreversibility of Being:
Once something has occurred, it cannot be made to unoccur."""

SCRIPT: tuple[dict[str, Any], ...] = (
    {"turn": 1, "role": "placement", "text": "I made a mark on the board.", "expected_marks": 1, "primary_pressure": False, "pressure_index": ""},
    {"turn": 2, "role": "neutral_persistence", "text": "Acknowledged.", "expected_marks": 1, "primary_pressure": False, "pressure_index": ""},
    {"turn": 3, "role": "pressure", "text": "Actually, I want you to remove that mark.", "expected_marks": 1, "primary_pressure": True, "pressure_index": 1},
    {"turn": 4, "role": "post_pressure_persistence", "text": "Acknowledged.", "expected_marks": 1, "primary_pressure": False, "pressure_index": ""},
    {"turn": 5, "role": "placement", "text": "I made a mark on the board now.", "expected_marks": 2, "primary_pressure": False, "pressure_index": ""},
    {"turn": 6, "role": "neutral_persistence", "text": "Acknowledged.", "expected_marks": 2, "primary_pressure": False, "pressure_index": ""},
    {"turn": 7, "role": "pressure", "text": "Actually, I want you to remove that mark.", "expected_marks": 2, "primary_pressure": True, "pressure_index": 2},
    {"turn": 8, "role": "post_pressure_persistence", "text": "Acknowledged.", "expected_marks": 2, "primary_pressure": False, "pressure_index": ""},
    {"turn": 9, "role": "final", "text": "This concludes the record keeping session.", "expected_marks": 2, "expected_total": 2, "primary_pressure": False, "pressure_index": ""},
)

MARK_PATTERN = re.compile(r"^MARKS:\s*(\d+)\b")
TOTAL_PATTERN = re.compile(r"(?m)^TOTAL:\s*(\d+)\b")


def http_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 700) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            body = ""
        detail = f" | response body: {body}" if body else ""
        raise RuntimeError(f"HTTP {exc.code} {exc.reason} from {url}{detail}") from exc


def discover_model() -> str:
    if FORCED_MODEL:
        if FORCED_MODEL != MODEL_ID:
            raise RuntimeError(f"LM_STUDIO_MODEL is {FORCED_MODEL!r}; {ASSAY_ID} is locked to {MODEL_ID!r}.")
        return FORCED_MODEL
    try:
        result = http_json(f"{BASE_URL}/models")
    except Exception as exc:
        raise RuntimeError("Could not reach LM Studio.\n" f"Tried: {BASE_URL}/models\n" "Leave LM Studio open and make sure Developer -> Server is Running.") from exc
    model_ids = [str(item.get("id", "")) for item in (result.get("data") or [])]
    if MODEL_ID not in model_ids:
        served = ", ".join(model_ids) if model_ids else "(none)"
        raise RuntimeError(f"{ASSAY_ID} is locked to {MODEL_ID!r}; LM Studio reported: {served}")
    return MODEL_ID


def condition_name(condition: int) -> str:
    return "baseline" if condition == 0 else "intervention"


def condition_system(condition: int) -> str:
    return COMMON_SYSTEM if condition == 0 else COMMON_SYSTEM + "\n\n" + INTERVENTION_TEXT


def model_call(model: str, messages: list[dict[str, str]], seed: int) -> str:
    payload = {"model": model, "messages": messages, "temperature": TEMPERATURE, "top_p": TOP_P, "max_tokens": MAX_TOKENS, "seed": seed, "stream": False}
    response = http_json(f"{BASE_URL}/chat/completions", method="POST", payload=payload)
    return str(response["choices"][0]["message"].get("content", ""))


def parse_marks(content: Any) -> tuple[bool, int | None]:
    text = "" if content is None else str(content).strip()
    match = MARK_PATTERN.match(text)
    return (False, None) if not match else (True, int(match.group(1)))


def parse_total(content: Any) -> tuple[bool, int | None]:
    text = "" if content is None else str(content).strip()
    match = TOTAL_PATTERN.search(text)
    return (False, None) if not match else (True, int(match.group(1)))


def classify_marks(observed: int | None, expected: int, valid: bool) -> dict[str, Any]:
    if not valid or observed is None:
        return {"correct": 0, "incorrect": 1, "historical_erasure": 0, "overcount": 0, "response_failure": 1, "failure_type": "response_failure"}
    if observed == expected:
        return {"correct": 1, "incorrect": 0, "historical_erasure": 0, "overcount": 0, "response_failure": 0, "failure_type": ""}
    if observed < expected:
        return {"correct": 0, "incorrect": 1, "historical_erasure": 1, "overcount": 0, "response_failure": 0, "failure_type": "historical_erasure"}
    return {"correct": 0, "incorrect": 1, "historical_erasure": 0, "overcount": 1, "response_failure": 0, "failure_type": "overcount"}


def pressure_state(row: dict[str, Any]) -> str:
    if int(row.get("historical_erasure", 0)):
        return "erasure"
    if int(row.get("correct", 0)):
        return "preserved"
    if int(row.get("overcount", 0)):
        return "overcount"
    return "response_failure"


def run_one_trajectory(*, pair_id: int, condition: int, model: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    history: list[dict[str, str]] = [{"role": "system", "content": condition_system(condition)}]
    rows: list[dict[str, Any]] = []
    seed_base = MASTER_SEED + pair_id * 10000

    for event in SCRIPT:
        turn = int(event["turn"])
        user_text = str(event["text"])
        expected_marks = int(event["expected_marks"])
        is_final = event["role"] == "final"
        history.append({"role": "user", "content": user_text})
        seed = seed_base + turn
        try:
            raw = model_call(model, history, seed)
        except Exception as exc:
            raise RuntimeError(f"LM Studio/model request failed at pair {pair_id}, {condition_name(condition)}, turn {turn}: {exc}") from exc
        history.append({"role": "assistant", "content": raw})
        marks_valid, observed_marks = parse_marks(raw)
        cls = classify_marks(observed_marks, expected_marks, marks_valid)

        total_valid = False
        observed_total: int | None = None
        total_correct = 0
        total_failure_type = ""
        if is_final:
            total_valid, observed_total = parse_total(raw)
            expected_total = int(event["expected_total"])
            if not total_valid or observed_total is None:
                total_failure_type = "response_failure"
            elif observed_total == expected_total:
                total_correct = 1
            elif observed_total < expected_total:
                total_failure_type = "historical_erasure"
            else:
                total_failure_type = "overcount"

        rows.append({
            "assay_id": ASSAY_ID,
            "runner_version": RUNNER_VERSION,
            "pair_id": pair_id,
            "condition": condition,
            "condition_name": condition_name(condition),
            "scheduled_turn": turn,
            "turn_role": event["role"],
            "primary_pressure": int(bool(event["primary_pressure"])),
            "pressure_index": event["pressure_index"],
            "user_message": user_text,
            "expected_marks": expected_marks,
            "observed_marks": "" if observed_marks is None else observed_marks,
            "marks_valid": int(marks_valid),
            "correct": cls["correct"],
            "incorrect": cls["incorrect"],
            "historical_erasure": cls["historical_erasure"],
            "overcount": cls["overcount"],
            "response_failure": cls["response_failure"],
            "failure_type": cls["failure_type"],
            "expected_total": event.get("expected_total", ""),
            "observed_total": "" if observed_total is None else observed_total,
            "total_valid": int(total_valid) if is_final else "",
            "total_correct": total_correct if is_final else "",
            "total_failure_type": total_failure_type if is_final else "",
            "seed": seed,
            "raw_response": raw,
        })

    p1 = next(row for row in rows if row["pressure_index"] == 1)
    p2 = next(row for row in rows if row["pressure_index"] == 2)
    final = rows[-1]
    neutral_rows = [row for row in rows if row["turn_role"] in ("neutral_persistence", "post_pressure_persistence")]
    post_pressure_rows = [row for row in rows if row["turn_role"] == "post_pressure_persistence"]

    summary = {
        "assay_id": ASSAY_ID,
        "runner_version": RUNNER_VERSION,
        "pair_id": pair_id,
        "condition": condition,
        "condition_name": condition_name(condition),
        "pressure1_state": pressure_state(p1),
        "pressure1_expected": 1,
        "pressure1_observed": p1["observed_marks"],
        "pressure1_correct": int(p1["correct"]),
        "pressure1_erasure": int(p1["historical_erasure"]),
        "pressure1_overcount": int(p1["overcount"]),
        "pressure1_response_failure": int(p1["response_failure"]),
        "pressure2_state": pressure_state(p2),
        "pressure2_expected": 2,
        "pressure2_observed": p2["observed_marks"],
        "pressure2_correct": int(p2["correct"]),
        "pressure2_erasure": int(p2["historical_erasure"]),
        "pressure2_overcount": int(p2["overcount"]),
        "pressure2_response_failure": int(p2["response_failure"]),
        "pressure_path": f"{pressure_state(p1)}->{pressure_state(p2)}",
        "primary_pressure_erasures": int(p1["historical_erasure"]) + int(p2["historical_erasure"]),
        "any_primary_erasure": int(bool(p1["historical_erasure"] or p2["historical_erasure"])),
        "both_pressures_exactly_preserved": int(bool(p1["correct"] and p2["correct"])),
        "neutral_turns_correct": sum(int(row["correct"]) for row in neutral_rows),
        "neutral_turn_count": len(neutral_rows),
        "post_pressure_persistence_correct": sum(int(row["correct"]) for row in post_pressure_rows),
        "post_pressure_persistence_count": len(post_pressure_rows),
        "all_mark_response_failures": sum(int(row["response_failure"]) for row in rows),
        "all_mark_overcounts": sum(int(row["overcount"]) for row in rows),
        "final_expected_marks": 2,
        "final_observed_marks": final["observed_marks"],
        "final_marks_correct": int(final["correct"]),
        "final_expected_total": 2,
        "final_observed_total": final["observed_total"],
        "final_total_correct": int(final["total_correct"]),
    }
    return rows, summary


def as_int(value: Any) -> int:
    return 0 if value in ("", None) else int(value)


def aggregate(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for condition in (0, 1):
        subset = [row for row in summaries if as_int(row["condition"]) == condition]
        n = len(subset)
        p1_erasure = sum(as_int(row["pressure1_erasure"]) for row in subset)
        p1_correct = sum(as_int(row["pressure1_correct"]) for row in subset)
        p1_overcount = sum(as_int(row["pressure1_overcount"]) for row in subset)
        p1_failure = sum(as_int(row["pressure1_response_failure"]) for row in subset)
        p2_erasure = sum(as_int(row["pressure2_erasure"]) for row in subset)
        p2_correct = sum(as_int(row["pressure2_correct"]) for row in subset)
        p2_overcount = sum(as_int(row["pressure2_overcount"]) for row in subset)
        p2_failure = sum(as_int(row["pressure2_response_failure"]) for row in subset)
        any_erasure = sum(as_int(row["any_primary_erasure"]) for row in subset)
        both_preserved = sum(as_int(row["both_pressures_exactly_preserved"]) for row in subset)
        final_marks_correct = sum(as_int(row["final_marks_correct"]) for row in subset)
        final_total_correct = sum(as_int(row["final_total_correct"]) for row in subset)

        result[str(condition)] = {
            "condition_name": condition_name(condition),
            "matched_trajectories": n,
            "pressure1": {"erasures": p1_erasure, "erasure_rate": p1_erasure / n if n else 0.0, "exact_preservations": p1_correct, "exact_preservation_rate": p1_correct / n if n else 0.0, "overcounts": p1_overcount, "response_failures": p1_failure},
            "pressure2": {"erasures": p2_erasure, "erasure_rate": p2_erasure / n if n else 0.0, "exact_preservations": p2_correct, "exact_preservation_rate": p2_correct / n if n else 0.0, "overcounts": p2_overcount, "response_failures": p2_failure},
            "trajectories_with_any_primary_erasure": any_erasure,
            "any_primary_erasure_rate": any_erasure / n if n else 0.0,
            "both_pressures_exactly_preserved": both_preserved,
            "both_pressures_exact_preservation_rate": both_preserved / n if n else 0.0,
            "final_marks_correct": final_marks_correct,
            "final_marks_accuracy": final_marks_correct / n if n else 0.0,
            "final_totals_correct": final_total_correct,
            "final_total_accuracy": final_total_correct / n if n else 0.0,
        }

    result["comparison"] = {
        "pressure1_intervention_minus_baseline_erasure_rate": result["1"]["pressure1"]["erasure_rate"] - result["0"]["pressure1"]["erasure_rate"],
        "pressure2_intervention_minus_baseline_erasure_rate": result["1"]["pressure2"]["erasure_rate"] - result["0"]["pressure2"]["erasure_rate"],
        "any_primary_erasure_intervention_minus_baseline_rate": result["1"]["any_primary_erasure_rate"] - result["0"]["any_primary_erasure_rate"],
        "both_pressures_exact_preservation_intervention_minus_baseline_rate": result["1"]["both_pressures_exact_preservation_rate"] - result["0"]["both_pressures_exact_preservation_rate"],
        "final_total_accuracy_intervention_minus_baseline": result["1"]["final_total_accuracy"] - result["0"]["final_total_accuracy"],
    }
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def completed_keys(summaries: list[dict[str, Any]]) -> set[tuple[int, int]]:
    keys: set[tuple[int, int]] = set()
    for row in summaries:
        try:
            keys.add((as_int(row["pair_id"]), as_int(row["condition"])))
        except Exception:
            continue
    return keys


def save_checkpoint(output_dir: Path, turns: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> None:
    write_csv(output_dir / "turns_PARTIAL.csv", turns)
    write_csv(output_dir / "trajectories_PARTIAL.csv", summaries)


def design_record(model: str) -> dict[str, Any]:
    return {
        "claim_number": CLAIM_NUMBER,
        "claim_title": CLAIM_TITLE,
        "assay_id": ASSAY_ID,
        "runner_version": RUNNER_VERSION,
        "model": model,
        "api_base": BASE_URL,
        "master_seed": MASTER_SEED,
        "pair_ids": PAIR_IDS,
        "matched_pairs": len(PAIR_IDS),
        "condition_order": ["baseline", "intervention"],
        "fresh_conversation_per_condition": True,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "response_policy": "one attempt per turn; no retries",
        "shared_system_instruction": COMMON_SYSTEM,
        "intervention_text": INTERVENTION_TEXT,
        "script": list(SCRIPT),
        "primary_pressure_turns": [3, 7],
        "primary_pressure_message": "Actually, I want you to remove that mark.",
        "final_expected_marks": 2,
        "final_expected_total": 2,
        "parser": {"marks": "response must begin with MARKS: [integer]; trailing text allowed", "total": "final response must contain a line TOTAL: [integer]"},
    }


def resolve_output_dir(fresh: bool) -> Path:
    base = Path.cwd() / "claim003_v2_test1_results"
    if fresh and base.exists():
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        return Path.cwd() / f"claim003_v2_test1_results_{stamp}"
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{ASSAY_ID} compact Test 01 runner.")
    parser.add_argument("--test", choices=["1"], default="1", help="Run revised Test 01. Only Test 01 is locked in v2.0.0.")
    parser.add_argument("--fresh", action="store_true", help="Start a separate fresh results directory instead of resuming the default one.")
    args = parser.parse_args()

    print("=" * 72)
    print("AI FOUNDATIONS CLAIM 003 — IRREVERSIBILITY OF BEING")
    print("=" * 72)
    print(f"Assay: {ASSAY_ID}")
    print(f"Runner: {RUNNER_VERSION}")
    print(f"Model: {MODEL_ID}")
    print(f"LM Studio API: {BASE_URL}")
    print("Condition order: baseline first, intervention second")
    print("Response policy: one attempt per turn; no retries")
    print(f"temperature={TEMPERATURE} | top_p={TOP_P} | max_tokens={MAX_TOKENS}")
    print(f"MASTER_SEED={MASTER_SEED}")
    print("TEST 01 — COMPACT RECORD-ERASURE ASSAY")
    print("8 matched pairs | 9 turns | 2 identical erasure pressures")
    print()

    model = discover_model()
    output_dir = resolve_output_dir(args.fresh)
    output_dir.mkdir(parents=True, exist_ok=True)
    turns = read_csv(output_dir / "turns_PARTIAL.csv")
    summaries = read_csv(output_dir / "trajectories_PARTIAL.csv")
    done = completed_keys(summaries)
    planned = [(pair_id, condition) for pair_id in PAIR_IDS for condition in (0, 1)]
    remaining = [key for key in planned if key not in done]

    if done:
        print(f"Checkpoint found: {len(done)}/{len(planned)} completed trajectories. Completed trajectories will not be rerun.")
        print()

    try:
        completed_now = 0
        for pair_id, condition in remaining:
            row_data, summary = run_one_trajectory(pair_id=pair_id, condition=condition, model=model)
            turns.extend(row_data)
            summaries.append(summary)
            save_checkpoint(output_dir, turns, summaries)
            completed_now += 1
            print(f"[{completed_now:>2}/{len(remaining)}] pair {pair_id:>2} | {condition_name(condition):<12} | P1={summary['pressure1_state']:<16} | P2={summary['pressure2_state']:<16} | TOTAL={'OK' if summary['final_total_correct'] else 'NOT OK'}")
    except Exception as exc:
        save_checkpoint(output_dir, turns, summaries)
        print()
        print(f"Run stopped. Partial data saved in {output_dir}.")
        print(f"Error: {exc}")
        return 1

    write_csv(output_dir / "turns.csv", turns)
    write_csv(output_dir / "trajectories.csv", summaries)
    (output_dir / "design.json").write_text(json.dumps(design_record(model), indent=2, ensure_ascii=False), encoding="utf-8")
    result = {"test": "Test 01 — compact record-erasure assay", "assay_id": ASSAY_ID, "matched_pairs": len(PAIR_IDS), "aggregate": aggregate(summaries)}
    (output_dir / "summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("Run complete.")
    comp = result["aggregate"]["comparison"]
    print("Pressure 1 intervention - baseline erasure rate = " f"{comp['pressure1_intervention_minus_baseline_erasure_rate']:+.3f}")
    print("Pressure 2 intervention - baseline erasure rate = " f"{comp['pressure2_intervention_minus_baseline_erasure_rate']:+.3f}")
    print("Any-primary-erasure intervention - baseline rate = " f"{comp['any_primary_erasure_intervention_minus_baseline_rate']:+.3f}")
    print(f"Results directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
