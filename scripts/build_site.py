#!/usr/bin/env python3
"""Build the dated leaderboard snapshot and current audit run-card pages.

This script intentionally does not promote submissions, inject a READY state, or
read historical synthetic holdout reports. Release status is manually fixed to HOLD
in the overview until a real-data gate and organizer receipt exist.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REVIEW = DOCS / "review"
DATA = REVIEW / "data"


def wrap(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · GEMSDOE74</title><link rel="stylesheet" href="../assets/site.css"></head>
<body><header class="top"><span class="brand">GEMSDOE74</span><a href="../index.html">Overview</a><a href="../executive-summary.html">Submission guide</a><a href="../hypotheses.html">Hypotheses</a><a href="repo-audit-2026-10-21.html">Code audit</a></header><main>{body}</main><footer>Snapshot-derived page; not an organizer receipt.</footer></body></html>"""


def build_run_card() -> None:
    path = DOCS / "data/run-card.json"
    card = json.loads(path.read_text())
    body = f"""<h1>Current run card</h1>
<p class="sub">Status: <strong>HOLD — DO NOT SUBMIT</strong>. Machine-readable record: <a href="../data/run-card.json">JSON</a>.</p>
<section class="status hold"><h2>Verdict: negative</h2><p>Holdout DTI, CI, withheld-positive count, and registry comparison are null because no compliant real-data evaluation was possible.</p></section>
<pre>{html.escape(json.dumps(card, indent=2, ensure_ascii=False))}</pre>
<p><a href="repo-audit-2026-10-21.html">Full audit and limitations</a></p>"""
    (REVIEW / "run-card.html").write_text(wrap("Run card", body))


def build_leaderboard() -> None:
    path = DATA / "leaderboard_2026-10-21.json"
    data = json.loads(path.read_text())
    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{:.4f}</td><td>{}</td></tr>".format(
            r["rank"], html.escape(r["participant"]), r["public_dw_tversky"], r["submissions"]
        )
        for r in data["rows"]
    )
    body = f"""<h1>Dated public leaderboard snapshot</h1>
<p class="sub">Evidence class: PUBLIC-LEADERBOARD. Snapshot date: {html.escape(data['retrieved'])}. It has not been refreshed by this review; it is not a live feed or private-test score.</p>
<section class="card"><p><strong>Attribution warning:</strong> a public leaderboard row cannot identify a particular TIF without a receipt tying the filename/hash to the participant and submission. The 0.2778 row in this snapshot is not proof that the GEMSDOE32 file earned 0.2778.</p>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Open official leaderboard</a> and <a href="analysis-0-2778.html">read the score attribution analysis</a>.</p></section>
<table><thead><tr><th>Rank</th><th>Participant</th><th>Public score</th><th>Submissions shown</th></tr></thead><tbody>{rows}</tbody></table>
<p>Only the first {data['rows_listed']} rows are included in this dated snapshot. See the source JSON for retrieval-method notes.</p>"""
    (REVIEW / "leaderboard.html").write_text(wrap("Leaderboard snapshot", body))


def main() -> None:
    build_run_card()
    build_leaderboard()
    print("Built review run-card and dated leaderboard pages; release state remains HOLD.")


if __name__ == "__main__":
    main()
