#!/usr/bin/env python3
"""Cluster normalized Reddit questions and gate SEO briefs on page evidence."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

STOP = {"how", "what", "why", "when", "where", "which", "who", "can", "could", "should", "do", "does", "i", "a", "an", "the", "is", "are", "to", "for", "of"}
START = re.compile(r"^(how|what|why|when|where|which|who|can|could|should|is|are|do|does|best|vs|alternative)\b", re.I)


def csv_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


def is_question(title):
    return "?" in title or bool(START.match(title.strip()))


def normalize_question(title):
    return " ".join(re.sub(r"[^\w\s]", " ", title.lower(), flags=re.UNICODE).split())


def tokens(text):
    useful = set(normalize_question(text).split()) - STOP
    return useful or set(normalize_question(text).split())


def similarity(a, b):
    left, right = tokens(a), tokens(b)
    return len(left & right) / len(left | right) if left and right else 0.0


def cluster_questions(records, previous=None):
    deduped = {str(r["thread_id"]): r for r in records if r.get("thread_id") and is_question(str(r.get("title", "")))}
    clusters = []
    for row in sorted(deduped.values(), key=lambda r: normalize_question(r["title"])):
        question = normalize_question(row["title"])
        target = next((c for c in clusters if similarity(question, c["cluster_key"]) >= 0.6), None)
        evidence = {"thread_id": row["thread_id"], "title": row["title"], "subreddit": row.get("subreddit", "unknown"), "source_url": row.get("source_url"), "captured_at": row.get("captured_at")}
        if target is None:
            clusters.append({"cluster_key": question, "questions": [question], "evidence": [evidence]})
        else:
            target["questions"].append(question)
            target["evidence"].append(evidence)
    old_keys = [r["cluster_key"] for r in (previous or {}).get("rows", [])]
    for cluster in clusters:
        if old_keys:
            best = max(old_keys, key=lambda key: max(similarity(key, q) for q in cluster["questions"]))
            if max(similarity(best, q) for q in cluster["questions"]) >= 0.6:
                cluster["cluster_key"] = best
        cluster["questions"] = sorted(set(cluster["questions"]))
        cluster["sample_count"] = len(cluster["evidence"])
        cluster["subreddit_spread"] = len({e["subreddit"] for e in cluster["evidence"]})
        cluster["subreddits"] = sorted({e["subreddit"] for e in cluster["evidence"]})
    return sorted(clusters, key=lambda c: c["cluster_key"])


def comparison_value(value):
    if isinstance(value, dict):
        return {k: comparison_value(v) for k, v in value.items() if k not in {"status", "captured_at"}}
    if isinstance(value, list):
        return [comparison_value(v) for v in value]
    return value


def render(result):
    lines = ["# Reddit Question SEO Bank | Powered by Bright Data", "", "Counts describe the captured, keyword-selected Reddit sample. Search coverage is an editorial hypothesis, not search volume or keyword difficulty.", "", "| Question cluster | Threads | Subreddits | Coverage | Status |", "|---|---:|---:|---|---|"]
    for row in result["rows"]:
        lines.append(f"| {row['cluster_key']} | {row['sample_count']} | {row['subreddit_spread']} | {row['coverage']} | {row['status']} |")
    lines += ["", f"Supported brief count: {result['brief_count']}. Snippets alone never create a brief. Write original answers; do not copy Reddit answers or usernames."]
    return "\n".join(lines) + "\n"


def analyze(payload, previous=None):
    rows = cluster_questions(payload.get("rows", []), previous)
    coverage = {r.get("cluster_key"): r for r in payload.get("coverage", [])}
    old = {r["cluster_key"]: comparison_value(r) for r in (previous or {}).get("rows", [])}
    brief_count = 0
    for row in rows:
        check = coverage.get(row["cluster_key"], {})
        passages = check.get("passages") or []
        if check.get("evidence_type") == "page_passage" and passages and check.get("assessment") in {"gap_observed", "covered"}:
            row["coverage"] = check["assessment"]
        else:
            row["coverage"] = "not_assessed"
        row["coverage_evidence"] = passages
        brief_count += row["coverage"] == "gap_observed"
        identity = row["cluster_key"]
        row["status"] = "new" if identity not in old else ("unchanged" if old[identity] == comparison_value(row) else "changed")
    run_id = hashlib.sha256(json.dumps(comparison_value(rows), sort_keys=True).encode()).hexdigest()[:12]
    result = {"rows": rows, "brief_count": brief_count, "snapshot": {"schema_version": 1, "run_id": run_id, "rows": rows}}
    result["report"] = render(result)
    return result


def write_outputs(result, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(result["report"])
    (out / "run.json").write_text(json.dumps(result["snapshot"], indent=2, sort_keys=True) + "\n")
    fields = ["cluster_key", "sample_count", "subreddit_spread", "coverage", "status", "questions", "evidence"]
    with (out / "questions.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in result["rows"]:
            writer.writerow({key: csv_cell(json.dumps(row[key]) if key in {"questions", "evidence"} else row.get(key)) for key in fields})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--previous", help="Prior run.json; omit on the first run")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text())
    previous = json.loads(Path(args.previous).read_text()) if args.previous else None
    write_outputs(analyze(payload, previous), args.output_dir)


if __name__ == "__main__":
    main()
