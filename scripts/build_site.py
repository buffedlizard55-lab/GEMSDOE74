#!/usr/bin/env python3
"""Build the evidence pages and conservative no-submit status panel (idempotent, no network).

The status comes from the current run card. Historical TIFs are never promoted based on
legacy sidecars, and this builder cannot declare a submission READY.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REVIEW = DOCS / "review"
DATA = REVIEW / "data"

NAV = [
    ("session-review-2026-10-21.html", "Current review"),
    ("submit-checklist.html", "Submit checklist"),
    ("analysis-0-2778.html", "The 0.2778 question"),
    ("hypotheses.html", "Hypotheses"),
    ("leaderboard.html", "Leaderboard"),
    ("irregularities.html", "Irregularities"),
    ("sources.html", "Sources"),
    ("run-card.html", "Run card"),
]

STATUS_STYLE = """<style>
.gstat{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;border-radius:12px;padding:16px 18px;margin:16px 0;border:2px solid;color:#111;background:#fff}
.gstat h2{font-size:18px;margin:0 0 6px}
.gstat.hold{border-color:#b00020;background:#fff3f3}
.gstat.ready{border-color:#0a7a0a;background:#f1fbf1}
.gstat.notready{border-color:#b35c00;background:#fff8ef}
.gstat ul{margin:6px 0 6px 18px;padding:0}
.gstat code{font-size:13px}
.gstat table{border-collapse:collapse;font-size:13px;margin:6px 0}
.gstat td,.gstat th{border:1px solid #ddd;padding:4px 7px;text-align:left;vertical-align:top}
.gstat .lab{display:inline-block;font-size:11px;font-weight:700;border-radius:999px;padding:2px 8px;margin-right:4px;background:#e8eefc;color:#123}
.gstat .no{color:#b00020;font-weight:700}
.gstat .yes{color:#0a7a0a;font-weight:700}
.gstat .btn{display:inline-block;margin-top:6px;padding:9px 14px;border-radius:9px;font-weight:700;text-decoration:none;border:1px solid #888;color:#111;background:#fff}
.gstat .btn.go{background:#0a7a0a;border-color:#0a7a0a;color:#fff}
.gstat .btn.review{background:#fff;border-color:#b35c00;color:#7a3e00}
.gstat .nav{font-size:13px;margin-top:8px}
</style>"""


def _load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _esc(x) -> str:
    return html.escape(str(x))


def page(title: str, body: str, active: str) -> str:
    links = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == active else ""
        links.append(f'<a href="{href}"{cur}>{_esc(label)}</a>')
    nav = "".join(links)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} · GEMSDOE74 review</title>
<link rel="stylesheet" href="../assets/site.css">
</head><body>
<header class="top"><span class="brand">GEMSDOE74</span><a href="../index.html">Site home</a>{nav}</header>
<main>
{body}
</main>
<footer>Not affiliated with DrivenData, NLR, DOE or USGS. Every number carries an evidence label.</footer>
</body></html>
"""


def build_leaderboard() -> None:
    d = _load(DATA / "leaderboard_2026-10-21.json")
    rows = []
    for r in d["rows"]:
        hl = ' class="hl"' if r["participant"] == "extradr19" else ""
        rows.append(
            f"<tr{hl}><td>{r['rank']}</td><td>{_esc(r['participant'])}</td>"
            f"<td><b>{r['public_dw_tversky']:.4f}</b></td><td>{r['submissions']}</td></tr>"
        )
    body = f"""
<h1>Public leaderboard snapshot</h1>
<p class="sub">Source: <a href="{_esc(d['source'])}">DrivenData leaderboard</a> · retrieved {d['retrieved']} · top {d['rows_listed']} rows</p>
<div class="card">
<span class="pill p-pl">PUBLIC-LEADERBOARD</span> <b>What this is:</b> the public-test DW-Tversky shown on the board. It is <b>not</b> the private-test score that decides Phase 1, and not the Phase 2 score.
<br><br><span class="mut">Highlighted row: rank 47, <code>extradr19</code>, 0.2778. That is the only 0.2778 on the board. Nothing on the board links it to the GEMSDOE32 file <code>h33-h33-2-b2</code>. See <a href="analysis-0-2778.html">the 0.2778 analysis</a> and <a href="irregularities.html">IR-74-03</a>.</span>
</div>
<table><tr><th>rank</th><th>participant</th><th>public DW-Tversky</th><th>submissions</th></tr>
{''.join(rows)}
</table>
<p class="mut">Labels: <span class="pill p-pl">PUBLIC-LEADERBOARD</span> rows are copied from the platform. None is an <span class="pill p-ol">ORGANIZER-CONFIRMED</span> receipt for a file in this repo.</p>
"""
    (REVIEW / "leaderboard.html").write_text(page("Leaderboard", body, "leaderboard.html"))


def build_run_card() -> None:
    card = _load(DATA / "run-card.json")
    body = f"""
<h1>Run card</h1>
<p class="sub">Machine-readable copy: <a href="data/run-card.json">data/run-card.json</a> · schema {_esc(card['schema'])} · {card['date_utc']}</p>
<div class="status hold"><p class="big">{_esc(card['status'])}</p>
<p>{_esc(card['blocker'])}</p></div>
<pre>{_esc(json.dumps(card, indent=2, ensure_ascii=False))}</pre>
"""
    (REVIEW / "run-card.html").write_text(page("Run card", body, "run-card.html"))


# ---------------------------------------------------------------- status panel

def submission_status_html(prefix: str) -> str:
    """Render a conservative status from the current run card; historical TIFs are not releases."""
    card = _load(DATA / "run-card.json") or {}
    session = f"{prefix}review/session-review-2026-10-21.html"
    return f"""<div class="gstat hold">
<h2>HOLD — DO NOT SUBMIT ANY FILE FROM THIS SITE</h2>
<p><b>No current candidate is cleared.</b> The official feature stack and sample template are absent; the current C1 method and protocol-compliant holdout have not been run. No new TIF was generated.</p>
<p>Historical files under <code>downloads/</code> are inherited review artifacts, not approved predictions. Format validity does not establish model validity, provenance, or organizer acceptance.</p>
<p>Current lane: <b>{_esc(card.get('hypothesis', 'C1 magnetic edge artifact suppression'))}</b></p>
<p><a class="btn review" href="{session}">Open current session review and ranked tests</a> · <a href="{prefix}review/run-card.html">run card</a> · <a href="{prefix}executive-summary.html">how submission works once cleared</a></p>
</div>"""

def inject_status(path: Path, prefix: str) -> None:
    if not path.exists():
        raise SystemExit(f"missing {path}")
    text = path.read_text()
    block = ("<!-- BEGIN:SUBMISSION_STATUS -->\n" + STATUS_STYLE + "\n"
             + submission_status_html(prefix) + "\n<!-- END:SUBMISSION_STATUS -->")
    new, n = re.subn(r"<!-- BEGIN:SUBMISSION_STATUS -->.*?<!-- END:SUBMISSION_STATUS -->",
                     lambda _m: block, text, flags=re.S)
    if n == 0:
        raise SystemExit(f"no SUBMISSION_STATUS markers in {path}")
    if new != text:
        path.write_text(new)


def main() -> None:
    build_leaderboard()
    build_run_card()
    inject_status(DOCS / "index.html", "")
    inject_status(REVIEW / "submit-checklist.html", "../")
    print("built:", ", ".join(sorted(p.name for p in REVIEW.glob("*.html"))))


if __name__ == "__main__":
    main()
