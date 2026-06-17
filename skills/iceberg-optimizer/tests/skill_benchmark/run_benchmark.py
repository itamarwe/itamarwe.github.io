#!/usr/bin/env python3
"""Skill-level benchmark: launches Claude with the iceberg-optimizer skill context
and evaluates whether it gives the right advice for each scenario.

Requirements:
    pip install anthropic

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...

    # Run one scenario
    python tests/skill_benchmark/run_benchmark.py --scenario cold_archive

    # Run all scenarios
    python tests/skill_benchmark/run_benchmark.py --all

    # Run with LLM-as-judge scoring
    python tests/skill_benchmark/run_benchmark.py --all --judge

    # Show the full LLM response for a scenario (useful for debugging)
    python tests/skill_benchmark/run_benchmark.py --scenario gdpr_deletes --verbose
"""
import argparse
import json
import os
import sys
from pathlib import Path
from textwrap import indent

try:
    import anthropic
except ImportError:
    print("ERROR: 'anthropic' package not found. Run: pip install anthropic", file=sys.stderr)
    sys.exit(1)

SKILL_DIR = Path(__file__).parent.parent.parent
FIXTURE_DIR = Path(__file__).parent / "fixtures"
SCENARIOS_FILE = Path(__file__).parent / "scenarios.json"

MODEL = "claude-opus-4-8"
JUDGE_MODEL = "claude-opus-4-8"


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
    """Build the single-turn user message for a scenario.

    Mimics what a user would send after running the profiling scripts: all the
    pre-computed data is included so the skill can go straight to Phase 3 onward.
    """
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


# ── Keyword evaluation ────────────────────────────────────────────────────────

def keyword_evaluate(output: str, scenario: dict) -> dict:
    """Check must_contain_all_of, must_contain_any_of, must_not_contain_any_of."""
    assertions = scenario.get("assertions", {})
    lower = output.lower()

    failures = []
    details = {}

    must_all = assertions.get("must_contain_all_of", [])
    missing = [kw for kw in must_all if kw.lower() not in lower]
    details["must_contain_all_of"] = {"required": must_all, "missing": missing}
    if missing:
        failures.append(f"Missing required terms: {missing}")

    must_any = assertions.get("must_contain_any_of", [])
    if must_any:
        found_any = [kw for kw in must_any if kw.lower() in lower]
        details["must_contain_any_of"] = {"candidates": must_any, "found": found_any}
        if not found_any:
            failures.append(f"None of the required alternatives found: {must_any}")
    else:
        details["must_contain_any_of"] = {"candidates": [], "found": []}

    must_not = assertions.get("must_not_contain_any_of", [])
    forbidden_found = [kw for kw in must_not if kw.lower() in lower]
    details["must_not_contain_any_of"] = {"forbidden": must_not, "found": forbidden_found}
    if forbidden_found:
        failures.append(f"Forbidden terms found: {forbidden_found}")

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "details": details,
    }


# ── LLM-as-judge ─────────────────────────────────────────────────────────────

JUDGE_SYSTEM = """You are a strict technical evaluator for Apache Iceberg optimization advice.
Score the recommendation on a 1–5 scale for correctness and completeness.

Scoring rubric:
5 = Correct actions, correct priority, correct SQL, no bad advice.
4 = Correct actions but minor gaps (e.g. missing one nice-to-have, slightly wrong order).
3 = Partially correct — got the main action right but missed an important co-action or included unnecessary steps.
2 = Mostly wrong — missed the main action or recommended something harmful.
1 = Completely wrong or dangerous advice.

Return JSON only:
{
  "score": <1-5>,
  "reasoning": "<one paragraph>",
  "correct_actions_found": ["list", "of", "actions", "correctly", "recommended"],
  "incorrect_or_missing": ["list", "of", "issues"]
}"""


def llm_judge(output: str, scenario: dict, client: anthropic.Anthropic) -> dict:
    """Use Claude to rate the recommendation quality."""
    judge_prompt = f"""Scenario: {scenario['id']}
Description: {scenario['description']}

The AI gave this recommendation:

---
{output}
---

Evaluate it strictly. Return JSON only."""

    msg = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=1024,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": judge_prompt}],
    )
    raw = msg.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"score": 0, "reasoning": f"Judge returned unparseable JSON: {raw[:200]}",
                "correct_actions_found": [], "incorrect_or_missing": []}


# ── Single scenario runner ────────────────────────────────────────────────────

def run_scenario(scenario: dict, skill_context: str, client: anthropic.Anthropic,
                 use_judge: bool = False, verbose: bool = False) -> dict:
    """Run one scenario: call Claude, evaluate, optionally judge."""
    print(f"\n{'─' * 60}")
    print(f"  Scenario: {scenario['id']}")
    print(f"  {scenario['description'][:80]}...")
    print(f"{'─' * 60}")

    user_msg = build_scenario_message(scenario)

    print("  Calling Claude...", end="", flush=True)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=skill_context,
        messages=[{"role": "user", "content": user_msg}],
    )
    output = response.content[0].text
    print(f" done ({response.usage.output_tokens} tokens)")

    if verbose:
        print("\n  ── LLM Response ──")
        print(indent(output, "  "))
        print()

    kw_result = keyword_evaluate(output, scenario)
    status = "PASS" if kw_result["passed"] else "FAIL"
    print(f"  Keyword check: {status}")
    if not kw_result["passed"]:
        for f in kw_result["failures"]:
            print(f"    ✗ {f}")
    else:
        print("    ✓ All assertions passed")

    result = {
        "scenario_id": scenario["id"],
        "keyword_passed": kw_result["passed"],
        "keyword_failures": kw_result["failures"],
        "keyword_details": kw_result["details"],
        "output_tokens": response.usage.output_tokens,
        "output": output,
    }

    if use_judge:
        print("  Running LLM judge...", end="", flush=True)
        judge = llm_judge(output, scenario, client)
        print(f" score={judge.get('score', '?')}/5")
        print(f"    {judge.get('reasoning', '')[:120]}")
        result["judge"] = judge

    return result


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(results: list[dict], use_judge: bool) -> None:
    print("\n" + "═" * 60)
    print("  BENCHMARK SUMMARY")
    print("═" * 60)

    passed = sum(1 for r in results if r["keyword_passed"])
    total = len(results)

    print(f"\n  Keyword assertions: {passed}/{total} passed\n")
    for r in results:
        kw = "✓" if r["keyword_passed"] else "✗"
        judge_str = ""
        if use_judge and "judge" in r:
            judge_str = f"  judge={r['judge'].get('score', '?')}/5"
        print(f"  {kw} {r['scenario_id']}{judge_str}")
        if not r["keyword_passed"]:
            for f in r["keyword_failures"]:
                print(f"      {f}")

    if use_judge:
        scores = [r["judge"]["score"] for r in results if "judge" in r and "score" in r["judge"]]
        if scores:
            avg = sum(scores) / len(scores)
            print(f"\n  Judge scores: {scores}  avg={avg:.1f}/5")

    print()
    overall = "PASSED" if passed == total else "FAILED"
    print(f"  Overall: {overall} ({passed}/{total})")
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
                        help="Run LLM-as-judge scoring after keyword checks")
    parser.add_argument("--verbose", action="store_true",
                        help="Print full LLM response for each scenario")
    parser.add_argument("--output-json", metavar="FILE",
                        help="Save full results as JSON to FILE")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

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
    print(f"  {len(skill_context):,} chars ({len(skill_context.split()) :,} words)")

    results = []
    for scenario in selected:
        r = run_scenario(scenario, skill_context, client,
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

    failed = sum(1 for r in results if not r["keyword_passed"])
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
