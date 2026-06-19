#!/usr/bin/env python3
"""Skill-level benchmark: launches Claude with the iceberg-optimizer skill context
and evaluates whether it gives the right advice for each scenario.

Uses the `claude` CLI (Claude Code) — no API key required.

Usage:
    # Run one scenario
    python tests/skill_benchmark/run_benchmark.py --scenario cold_archive

    # Run all scenarios with LLM-as-judge scoring
    python tests/skill_benchmark/run_benchmark.py --all --judge

    # Show the full LLM response for a scenario (useful for debugging)
    python tests/skill_benchmark/run_benchmark.py --scenario gdpr_deletes --verbose

    # Save results as JSON
    python tests/skill_benchmark/run_benchmark.py --all --judge --output-json results.json
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from textwrap import indent

SKILL_DIR = Path(__file__).parent.parent.parent
FIXTURE_DIR = Path(__file__).parent / "fixtures"
SCENARIOS_FILE = Path(__file__).parent / "scenarios.json"

CLAUDE_CLI = "claude"


# ── Context loading ───────────────────────────────────────────────────────────

def load_skill_context() -> str:
    """Load SKILL.md + all references/*.md as a combined system prompt."""
    parts = []

    skill_md = SKILL_DIR / "SKILL.md"
    if skill_md.exists():
        parts.append(f"# SKILL INSTRUCTIONS\n\n{skill_md.read_text()}")

    refs_dir = SKILL_DIR / "references"
    if refs_dir.exists():
        for ref_file in sorted(refs_dir.glob("*.md")):
            parts.append(f"# REFERENCE: {ref_file.name}\n\n{ref_file.read_text()}")

    return "\n\n---\n\n".join(parts)


# ── Message building ──────────────────────────────────────────────────────────

def build_scenario_message(scenario: dict) -> str:
    """Build the single-turn user message for a scenario."""
    sid = scenario["id"]
    fixture = FIXTURE_DIR / sid

    profile = json.loads((fixture / "profile.json").read_text())
    workload = json.loads((fixture / "workload.json").read_text())
    simulate_output = (fixture / "simulate_output.txt").read_text()

    answers = scenario.get("interview_answers", {})
    engine = scenario.get("engine", "Spark")
    table = scenario.get("table", "catalog.schema.table")

    answer_lines = "\n".join(
        f"- **{k.replace('_', ' ').title()}**: {v}"
        for k, v in answers.items()
    )

    return f"""I need your help optimizing an Apache Iceberg table.

**Table**: `{table}`
**Engine**: {engine}

I've already run the profiling and workload scripts. Here is all the data:

## Profile output (profile.json)

```json
{json.dumps(profile, indent=2)}
```

## Workload output (workload.json)

```json
{json.dumps(workload, indent=2)}
```

## Simulator output

```
{simulate_output}
```

## Interview answers

Here are my answers to the Phase 2b interview questions:

{answer_lines}

Based on all the above, please provide your optimization recommendations (Phase 3 and 4 onward). Include specific action codes, SQL commands, and a maintenance schedule.
"""


# ── Claude CLI invocation ─────────────────────────────────────────────────────

def call_claude(system_prompt: str, user_message: str) -> str:
    """Call the claude CLI with a system prompt and user message, return the text output."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(system_prompt)
        system_file = f.name

    try:
        last_exc = None
        for attempt in range(3):
            try:
                result = subprocess.run(
                    [
                        CLAUDE_CLI, "-p",
                        "--system-prompt-file", system_file,
                        "--output-format", "text",
                        "--no-session-persistence",
                    ],
                    input=user_message,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                wait = 15 * (attempt + 1)
                print(f"\n    [attempt {attempt+1} failed (exit {result.returncode}), "
                      f"retrying in {wait}s] stderr: {result.stderr.strip()[:200]}", flush=True)
                last_exc = RuntimeError(result.stderr.strip()[:500])
                time.sleep(wait)
            except subprocess.TimeoutExpired as e:
                wait = 15 * (attempt + 1)
                print(f"\n    [attempt {attempt+1} timed out, retrying in {wait}s]", flush=True)
                last_exc = e
                time.sleep(wait)
        raise RuntimeError(f"claude CLI failed after 3 attempts: {last_exc}")
    finally:
        os.unlink(system_file)


# ── LLM-as-judge ─────────────────────────────────────────────────────────────

JUDGE_SYSTEM = """You are a strict technical evaluator for Apache Iceberg optimization advice.

You will be given:
1. The EXPECTED OUTCOME — a plain-English description of what a correct recommendation looks like.
2. The AI'S RECOMMENDATION — what the system actually said.

Evaluate whether the AI's recommendation matches the expected outcome. Score 1–5:

5 = Fully correct: all required actions present, correct priority, no harmful extras.
4 = Mostly correct: main actions right, minor gap or one unnecessary extra step.
3 = Partially correct: got the main action but missed an important co-action, or included a clearly wrong recommendation alongside correct ones.
2 = Mostly wrong: missed the main action, or recommended something the expected outcome says is incorrect.
1 = Completely wrong or dangerous advice.

PASS = score >= 3. FAIL = score <= 2.

Return JSON only, no markdown fences:
{"score": <1-5>, "passed": <true|false>, "reasoning": "<one concise paragraph>", "correct_actions_found": ["..."], "incorrect_or_missing": ["..."]}"""


def llm_judge(output: str, scenario: dict) -> dict:
    """Use Claude CLI to rate the recommendation quality against expected_outcome."""
    expected = scenario.get("expected_outcome", scenario.get("description", ""))

    judge_prompt = f"""EXPECTED OUTCOME:
{expected}

AI'S RECOMMENDATION:
---
{output}
---

Does the AI's recommendation match the expected outcome? Return JSON only, no markdown fences."""

    raw = call_claude(JUDGE_SYSTEM, judge_prompt).strip()

    # Strip markdown code fences if model adds them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "score": 0,
            "reasoning": f"Judge returned unparseable JSON: {raw[:300]}",
            "correct_actions_found": [],
            "incorrect_or_missing": [],
        }


# ── Single scenario runner ────────────────────────────────────────────────────

def run_scenario(scenario: dict, skill_context: str,
                 use_judge: bool = False, verbose: bool = False) -> dict:
    """Run one scenario: call Claude, then optionally score with LLM judge."""
    print(f"\n{'─' * 60}")
    print(f"  Scenario: {scenario['id']}")
    print(f"  {scenario['description'][:80]}...")
    print(f"{'─' * 60}")

    user_msg = build_scenario_message(scenario)

    print("  Calling Claude...", end="", flush=True)
    output = call_claude(skill_context, user_msg)
    word_count = len(output.split())
    print(f" done ({word_count} words)")

    if verbose:
        print("\n  ── LLM Response ──")
        print(indent(output, "  "))
        print()

    result = {
        "scenario_id": scenario["id"],
        "word_count": word_count,
        "output": output,
    }

    if use_judge:
        print("  Running LLM judge...", end="", flush=True)
        judge = llm_judge(output, scenario)
        judge_passed = judge.get("passed", judge.get("score", 0) >= 3)
        judge_status = "PASS" if judge_passed else "FAIL"
        print(f" score={judge.get('score', '?')}/5  {judge_status}")
        reasoning = judge.get("reasoning", "")
        if reasoning:
            print(f"    {reasoning[:140]}")
        if not judge_passed:
            for item in judge.get("incorrect_or_missing", []):
                print(f"    ✗ {item}")
        result["judge"] = judge
        result["judge_passed"] = judge_passed

    return result


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(results: list, use_judge: bool) -> None:
    print("\n" + "═" * 60)
    print("  BENCHMARK SUMMARY")
    print("═" * 60)

    total = len(results)

    if use_judge:
        judge_passed = sum(1 for r in results if r.get("judge_passed", False))
        scores = [r["judge"]["score"] for r in results
                  if "judge" in r and isinstance(r["judge"].get("score"), int)]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"\n  LLM judge: {judge_passed}/{total} passed  (scores: {scores}, avg={avg:.1f}/5)")
        for r in results:
            jp = "✓" if r.get("judge_passed") else "✗"
            score = r.get("judge", {}).get("score", "?")
            print(f"    {jp} {r['scenario_id']}  {score}/5")

        overall_pass = judge_passed == total
        label = "PASSED" if overall_pass else "FAILED"
        print(f"\n  Overall: {label} ({judge_passed}/{total})")
    else:
        print(f"\n  Ran {total} scenario(s). Use --judge to score results.")
        for r in results:
            print(f"    • {r['scenario_id']}  ({r['word_count']} words)")

    print("═" * 60 + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark the iceberg-optimizer skill against fixture scenarios."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scenario", help="Run a single scenario by id")
    group.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--judge", action="store_true",
                        help="Run LLM-as-judge scoring after each scenario")
    parser.add_argument("--verbose", action="store_true",
                        help="Print full LLM response for each scenario")
    parser.add_argument("--output-json", metavar="FILE",
                        help="Save full results as JSON to FILE")
    args = parser.parse_args()

    scenarios = json.loads(SCENARIOS_FILE.read_text())
    scenario_map = {s["id"]: s for s in scenarios}

    if args.all:
        selected = scenarios
    else:
        if args.scenario not in scenario_map:
            print(f"ERROR: unknown scenario '{args.scenario}'. "
                  f"Available: {list(scenario_map)}", file=sys.stderr)
            sys.exit(1)
        selected = [scenario_map[args.scenario]]

    print(f"\nLoading skill context from {SKILL_DIR}...")
    skill_context = load_skill_context()
    print(f"  {len(skill_context):,} chars ({len(skill_context.split()):,} words)")

    results = []
    for i, scenario in enumerate(selected):
        if i > 0:
            time.sleep(3)  # brief pause between scenarios to avoid rate-limit bursts
        r = run_scenario(scenario, skill_context,
                         use_judge=args.judge, verbose=args.verbose)
        results.append(r)

    print_report(results, use_judge=args.judge)

    if args.output_json:
        out = [
            {k: v for k, v in r.items() if k != "output"}
            for r in results
        ]
        Path(args.output_json).write_text(json.dumps(out, indent=2))
        print(f"Results saved to {args.output_json}")

    if args.judge:
        failed = sum(1 for r in results if not r.get("judge_passed", False))
        sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
