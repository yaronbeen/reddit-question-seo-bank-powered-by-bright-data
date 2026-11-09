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
    old_keys = list(dict.fromkeys(r["cluster_key"] for r in (previous or {}).get("rows", [])))
    candidates = []
    for index, cluster in enumerate(clusters):
        for old_key in old_keys:
            score = max(similarity(old_key, q) for q in cluster["questions"])
            if score >= 0.6:
                candidates.append((-score, cluster["cluster_key"], old_key, index))
    used_clusters, used_old_keys = set(), set()
    for _, _, old_key, index in sorted(candidates):
        if index in used_clusters or old_key in used_old_keys:
            continue
        clusters[index]["cluster_key"] = old_key
        used_clusters.add(index)
        used_old_keys.add(old_key)
    for cluster in clusters:
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


def resolve_coverage(rows, checks):
    matches = {row["cluster_key"]: [] for row in rows}
    warnings = []
    for check in checks:
        label = check.get("cluster_key") or check.get("question") or check.get("thread_id") or "unlabeled coverage"
        normalized_label = normalize_question(str(label))
        targets = []
        for row in rows:
            question_match = normalized_label in {row["cluster_key"], *row["questions"]}
            thread_match = check.get("thread_id") and check["thread_id"] in {e["thread_id"] for e in row["evidence"]}
            if question_match or thread_match:
                targets.append(row["cluster_key"])
        if len(targets) != 1:
            warnings.append(f"Coverage '{label}' matched {len(targets)} clusters; left not_assessed.")
        else:
            matches[targets[0]].append(check)
    for key, entries in matches.items():
        if len(entries) > 1:
            warnings.append(f"Coverage for '{key}' has multiple entries; left not_assessed.")
    return matches, warnings


def md(value):
    return " ".join(str(value if value is not None else "").split()).replace("|", "\\|")


def render_briefs(rows, audience=None):
    lines = [
        "# Evidence-gated SEO briefs | Powered by Bright Data", "",
        "These are original-research scaffolds, not finished articles. The captured sample does not establish search volume or ranking difficulty.", "",
        f"**Audience:** {md(audience or 'Unspecified — confirm the intended reader before drafting.')}", "",
    ]
    if not rows:
        lines.append("No supported briefs. A question cluster needs page-passage evidence and a gap_observed assessment.")
        return "\n".join(lines) + "\n"
    for row in rows:
        lines += [f"## {md(row['cluster_key'])}", "", f"Evidence scope: {row['sample_count']} captured threads across {row['subreddit_spread']} subreddits. Treat this as sample evidence, not demand.", "", "### Questions the draft must answer", ""]
        lines += [f"- {md(question)}" for question in row["questions"]]
        lines += ["", "### Observed passage and editorial gap to validate", ""]
        for passage in row["coverage_evidence"]:
            lines.append(f"- {md(passage.get('text'))} — {md(passage.get('source_url') or 'source not captured')}")
        lines += ["", "### Thread evidence for audience language", ""]
        for evidence in row["evidence"]:
            lines.append(f"- {md(evidence.get('title'))} — {md(evidence.get('source_url') or 'source not captured')}")
        lines += ["", "### Original outline", "", "1. Give a direct answer to the primary question.", "2. Resolve the decision or missing sub-answer shown by the collected passage.", "3. Add an original example, checklist, or experiment with primary-source support.", "4. Cover the remaining captured question variants where they help the reader.", "", "### Acceptance checks", "", "- [ ] Answer every relevant question variant without copying Reddit answers.", "- [ ] Independently verify factual claims and cite primary sources.", "- [ ] Preserve the evidence caveat; add no volume, difficulty, or ranking claims.", "- [ ] Have a human review the brief and final draft before publication.", ""]
    return "\n".join(lines) + "\n"


def render(result):
    lines = ["# Reddit Question SEO Bank | Powered by Bright Data", "", "Counts describe the captured, keyword-selected Reddit sample. Search coverage is an editorial hypothesis, not search volume or keyword difficulty.", "", "| Question cluster | Threads | Subreddits | Coverage | Status |", "|---|---:|---:|---|---|"]
    for row in result["rows"]:
        lines.append(f"| {row['cluster_key']} | {row['sample_count']} | {row['subreddit_spread']} | {row['coverage']} | {row['status']} |")
    lines += ["", f"Supported brief count: {result['brief_count']}. Snippets alone never create a brief. Write original answers; do not copy Reddit answers or usernames."]
    if result["warnings"]:
        lines += ["", "## Coverage warnings", ""] + [f"- {warning}" for warning in result["warnings"]]
    return "\n".join(lines) + "\n"


def analyze(payload, previous=None):
    rows = cluster_questions(payload.get("rows", []), previous)
    coverage, warnings = resolve_coverage(rows, payload.get("coverage", []))
    old = {r["cluster_key"]: comparison_value(r) for r in (previous or {}).get("rows", [])}
    for row in rows:
        entries = coverage.get(row["cluster_key"], [])
        check = entries[0] if len(entries) == 1 else {}
        passages = check.get("passages") or []
        if check.get("evidence_type") == "page_passage" and passages and check.get("assessment") in {"gap_observed", "covered"}:
            row["coverage"] = check["assessment"]
        else:
            row["coverage"] = "not_assessed"
        row["coverage_evidence"] = passages
        identity = row["cluster_key"]
        row["status"] = "new" if identity not in old else ("unchanged" if old[identity] == comparison_value(row) else "changed")
    brief_rows = sorted((r for r in rows if r["coverage"] == "gap_observed"), key=lambda r: (-r["sample_count"], -r["subreddit_spread"], r["cluster_key"]))[:4]
    brief_count = len(brief_rows)
    run_id = hashlib.sha256(json.dumps(comparison_value(rows), sort_keys=True).encode()).hexdigest()[:12]
    result = {"rows": rows, "brief_count": brief_count, "warnings": warnings, "snapshot": {"schema_version": 1, "run_id": run_id, "rows": rows, "warnings": warnings}}
    result["report"] = render(result)
    result["briefs"] = render_briefs(brief_rows, payload.get("audience"))
    return result


def write_outputs(result, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(result["report"])
    (out / "run.json").write_text(json.dumps(result["snapshot"], indent=2, sort_keys=True) + "\n")
    (out / "briefs.md").write_text(result["briefs"])
    fields = ["cluster_key", "sample_count", "subreddit_spread", "coverage", "status", "questions", "evidence"]
    with (out / "questions.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
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
