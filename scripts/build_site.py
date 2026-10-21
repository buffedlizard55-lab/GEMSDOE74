#!/usr/bin/env python3
"""Build the generated parts of the GitHub Pages site in docs/.

What it does (idempotent):
  1. docs/leaderboard.html  <- docs/data/leaderboard_2026-10-21.json
  2. docs/run-card.html     <- docs/data/run-card.json
  3. Replaces the block between
         <!-- BEGIN:SUBMISSION_STATUS --> and <!-- END:SUBMISSION_STATUS -->
     in docs/index.html and docs/executive-summary.html with the current state of
     docs/downloads/*.receipt.json. With no receipt, it shows a red NOT READY panel.
     A receipt is only shown as READY when its `release_status` is exactly "READY".

Nothing here fetches from the network. Source data is recorded in docs/data/.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = DOCS / "data"
DOWNLOADS = DOCS / "downloads"

NAV = [
    ("index.html", "Home"),
    ("executive-summary.html", "How to submit"),
    ("analysis-0-2778.html", "The 0.2778 question"),
    ("hypotheses.html", "Hypotheses"),
    ("leaderboard.html", "Leaderboard"),
    ("irregularities.html", "Irregularities"),
    ("sources.html", "Sources"),
    ("run-card.html", "Run card"),
]

PILL = {
    "ORGANIZER-CONFIRMED": "p-ol",
    "PUBLIC-LEADERBOARD": "p-pl",
    "HOLDOUT-DTI": "p-hd",
    "CLAIM": "p-cl",
    "PROJECTION": "p-pr",
    "NOT COMPUTED": "p-no",
    "NOT RUN": "p-no",
}


def page(title: str, body: str, active: str) -> str:
    links = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == active else ""
        links.append(f'<a href="{href}"{cur}>{html.escape(label)}</a>')
    nav = "".join(links)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · GEMSDOE74</title>
<link rel="stylesheet" href="assets/site.css">
</head><body>
<header class="top"><span class="brand">GEMSDOE74</span>{nav}</header>
<main>
{body}
</main>
<footer>Generated or edited in repo <code>buffedlizard55-lab/GEMSDOE74</code>. Every number carries an evidence label. Not affiliated with DrivenData, NLR, DOE or USGS.</footer>
</body></html>
"""


def pill(label: str) -> str:
    cls = PILL.get(label, "p-pr")
    return f'<span class="pill {cls}">{html.escape(label)}</span>'


def build_leaderboard() -> None:
    d = json.loads((DATA / "leaderboard_2026-10-21.json").read_text())
    rows = []
    for r in d["rows"]:
        hl = ' class="hl"' if r["participant"] == "extradr19" else ""
        rows.append(
            f"<tr{hl}><td>{r['rank']}</td><td>{html.escape(r['participant'])}</td>"
            f"<td><b>{r['public_dw_tversky']:.4f}</b></td><td>{r['submissions']}</td></tr>"
        )
    body = f"""
<h1>Public leaderboard snapshot</h1>
<p class="sub">Source: <a href="{html.escape(d['source'])}">DrivenData leaderboard</a> · retrieved {d['retrieved']} · top {d['rows_listed']} rows</p>
<div class="card">
{pill('PUBLIC-LEADERBOARD')} <b>What this is:</b> the public-test DW-Tversky shown on the board. It is <b>not</b> the private-test score that decides Phase 1, and not the Phase 2 score.
<br><br><span class="mut">Highlighted row: rank 47, <code>extradr19</code>, 0.2778. That is the only 0.2778 on the board. Nothing on the board links it to the GEMSDOE32 file <code>h33-h33-2-b2</code>. See <a href="analysis-0-2778.html">the 0.2778 analysis</a> and <a href="irregularities.html">IR-74-03</a>.</span>
</div>
<table><tr><th>rank</th><th>participant</th><th>public DW-Tversky</th><th>submissions</th></tr>
{''.join(rows)}
</table>
<p class="mut">Labels: {pill('PUBLIC-LEADERBOARD')} rows are copied from the platform. None is an {pill('ORGANIZER-CONFIRMED')} receipt for a file in this repo. Rank 1 is shown as 0.4413; the value is the platform's, not a GEMSDOE group score.</p>
"""
    (DOCS / "leaderboard.html").write_text(page("Leaderboard", body, "leaderboard.html"))


def build_run_card() -> None:
    card = json.loads((DATA / "run-card.json").read_text())
    body = f"""
<h1>Run card</h1>
<p class="sub">Machine-readable copy: <a href="data/run-card.json">data/run-card.json</a> · schema {html.escape(card['schema'])} · {card['date_utc']}</p>
<div class="status hold"><p class="big">{html.escape(card['status'])}</p>
<p>{html.escape(card['blocker'])}</p></div>
<pre>{html.escape(json.dumps(card, indent=2, ensure_ascii=False))}</pre>
"""
    (DOCS / "run-card.html").write_text(page("Run card", body, "run-card.html"))


def submission_status_html() -> str:
    receipts = sorted(DOWNLOADS.glob("*.receipt.json"))
    ready = []
    for rp in receipts:
        r = json.loads(rp.read_text())
        if r.get("release_status") == "READY":
            ready.append(r)
    if not ready:
        return """<div class="status hold">
<p class="big">NO SUBMISSION FILE IS READY. DO NOT SUBMIT ANYTHING FROM THIS SITE YET.</p>
<p>No GeoTIFF has been generated from the competition data, so there is no prediction to submit. A file without a real prediction would use one of the three weekly slots for nothing.</p>
<p><b>Blocker:</b> the training features and labels are login-gated on DrivenData, and this build environment cannot download them. See <a href="irregularities.html">IR-74-04</a> for the data-source question that has to be cleared before any mirror is used.</p>
<p><a class="btn dis" aria-disabled="true">Download submission .tif (not available)</a></p>
</div>"""
    parts = []
    for r in ready:
        parts.append(
            f"""<div class="status ready"><p class="big">READY TO SUBMIT: {html.escape(r['submission_name'])}</p>
<div class="kv"><div>File</div><div><a href="downloads/{html.escape(r['file'])}">{html.escape(r['file'])}</a></div>
<div>Note field</div><div>{html.escape(r['submission_note'])} <span class="mut">({r['note_chars']}/200)</span></div>
<div>sha256</div><div><code>{html.escape(r['sha256'])}</code></div>
<div>Validator</div><div>{'PASSED' if r['validator']['passed'] else 'FAILED'}</div></div>
<p><a class="btn" href="downloads/{html.escape(r['file'])}">Download submission .tif</a></p></div>"""
        )
    return "\n".join(parts)


def inject_status(path: Path) -> None:
    text = path.read_text()
    new = re.sub(
        r"<!-- BEGIN:SUBMISSION_STATUS -->.*?<!-- END:SUBMISSION_STATUS -->",
        "<!-- BEGIN:SUBMISSION_STATUS -->\n" + submission_status_html() + "\n<!-- END:SUBMISSION_STATUS -->",
        text,
        flags=re.S,
    )
    if new != text:
        path.write_text(new)


def main() -> None:
    build_leaderboard()
    build_run_card()
    for name in ("index.html", "executive-summary.html"):
        inject_status(DOCS / name)
    print("site built:", ", ".join(sorted(p.name for p in DOCS.glob("*.html"))))


if __name__ == "__main__":
    main()
