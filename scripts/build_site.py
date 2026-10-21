#!/usr/bin/env python3
"""Build the generated parts of the GitHub Pages site in docs/.

What it does (idempotent, no network):
  1. docs/leaderboard.html  <- docs/data/leaderboard_2026-10-21.json
  2. docs/run-card.html     <- docs/data/run-card.json
  3. Replaces the block between
         <!-- BEGIN:SUBMISSION_STATUS --> and <!-- END:SUBMISSION_STATUS -->
     in docs/index.html and docs/submit-checklist.html
     with a self-contained status panel. The panel is decided from what is on disk:
       * READY only when a docs/downloads/*.receipt.json has release_status exactly "READY";
       * HOLD when downloadable files exist but none is cleared (shows why);
       * NOT READY when there are no downloadable files at all.
     Holdout numbers shown in the panel are read from evidence/*.json and labelled HOLDOUT-DTI.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = DOCS / "data"
DOWNLOADS = DOCS / "downloads"
EVIDENCE = ROOT / "evidence"

NAV = [
    ("index.html", "Home"),
    ("submit-checklist.html", "Submit checklist"),
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
    "MEASURED-LOCAL": "p-hd",
    "CLAIM": "p-cl",
    "PROJECTION": "p-pr",
    "NOT COMPUTED": "p-no",
    "NOT RUN": "p-no",
}

STATUS_STYLE = """<style>
.gstat{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;border-radius:12px;padding:16px 18px;margin:16px 0;border:2px solid;color:#111;background:#fff}
.gstat h2{font-size:18px;margin:0 0 6px}
.gstat.hold{border-color:#b00020;background:#fff3f3}
.gstat.ready{border-color:#0a7a0a;background:#f1fbf1}
.gstat.notready{border-color:#b35c00;background:#fff8ef}
.gstat ul{margin:6px 0 6px 18px;padding:0}
.gstat code{font-size:13px}
.gstat .lab{display:inline-block;font-size:11px;font-weight:700;border-radius:999px;padding:2px 8px;margin-right:4px;background:#e8eefc;color:#123}
.gstat .btn{display:inline-block;margin-top:6px;padding:9px 14px;border-radius:9px;font-weight:700;text-decoration:none;border:1px solid #888;color:#111;background:#fff}
.gstat .btn.go{background:#0a7a0a;border-color:#0a7a0a;color:#fff}
.gstat .btn.review{background:#fff;border-color:#b35c00;color:#7a3e00}
.gstat .nav{font-size:13px;margin-top:8px}
</style>"""


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
<footer>Not affiliated with DrivenData, NLR, DOE or USGS. Every number carries an evidence label.</footer>
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


def _load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _holdout_lines() -> list:
    """Summarise the holdout evidence on disk, labelled HOLDOUT-DTI."""
    out = []
    for name, label in (("holdout_h74a.json", "v0.1 4-quadrant"), ("holdout_h74a_segments.json", "v0.2 segment")):
        d = _load(EVIDENCE / name)
        if not d:
            continue
        cand = d.get("candidate", {})
        rnd = d.get("random_control", {})
        cat_key = "pooled_DTI_cat_hidden" if "pooled_DTI_cat_hidden" in cand else "pooled_DTI_cat"
        passes = d.get("passes_random", d.get("passes_random_cat"))
        out.append(
            f"<li><span class=\"lab\">HOLDOUT-DTI</span> {html.escape(label)}: candidate {cand.get(cat_key, float('nan')):.5f} "
            f"vs random control {rnd.get(cat_key, float('nan')):.5f} "
            f"(passes random control: <b>{'yes' if passes else 'NO'}</b>). "
            f"Source: <code>evidence/{html.escape(name)}</code>.</li>"
        )
    return out


def submission_status_html() -> str:
    ready = []
    for rp in sorted(DOWNLOADS.glob("*.receipt.json")):
        r = _load(rp)
        if r and r.get("release_status") == "READY":
            ready.append(r)

    files = sorted(p for p in DOWNLOADS.iterdir() if p.is_file() and p.suffix.lower() in (".tif", ".zip"))
    cleared = bool(ready)

    if cleared:
        parts = []
        for r in ready:
            parts.append(
                f"<h2>READY TO SUBMIT: {html.escape(str(r.get('submission_name', '')))}</h2>"
                f"<ul><li>File: <a href=\"downloads/{html.escape(r['file'])}\">{html.escape(r['file'])}</a></li>"
                f"<li>Note ({r.get('note_chars', '?')}/200): {html.escape(str(r.get('submission_note', '')))}</li>"
                f"<li>sha256: <code>{html.escape(str(r.get('sha256', '')))}</code></li></ul>"
                f"<a class=\"btn go\" href=\"downloads/{html.escape(r['file'])}\">Download submission .tif</a>"
            )
        return f'<div class="gstat ready">{"".join(parts)}</div>' + STATUS_NAV

    if files:
        listing = "".join(
            f"<li><a href=\"downloads/{html.escape(p.name)}\">{html.escape(p.name)}</a> "
            f"<span class=\"lab\">FOR REVIEW ONLY</span></li>"
            for p in files
        )
        hold_lines = "".join(_holdout_lines()) or "<li>No holdout evidence file found.</li>"
        primary = next((p for p in files if p.name.endswith("zeros.tif")), files[0])
        return f"""<div class="gstat hold">
<h2>HOLD: DO NOT SUBMIT. Downloadable files exist but none is cleared.</h2>
<p><b>Submit: NO.</b> <b>Download:</b> for review only, not cleared for submission.</p>
<p><b>Files in <code>docs/downloads/</code>:</b></p><ul>{listing}</ul>
<p><b>Why it is on hold:</b></p>
<ul>
<li>No <code>*.receipt.json</code> in <code>docs/downloads/</code> has <code>release_status</code> set to READY. Promotion is a separate step and has not been done.</li>
{hold_lines}
<li>The inputs are not verified. <code>scripts/fetch_data.sh</code> pulls the labels and the sample submission from a sibling repo's mirror of login-gated competition data, and the rights are unconfirmed (<a href="irregularities.html">IR-74-04</a>).</li>
<li>The holdout truth is catalogue-only, so it cannot reward genuinely new faults (the candidate's own evidence note).</li>
</ul>
<a class="btn review" href="downloads/{html.escape(primary.name)}">Download for review only (not cleared)</a>
{STATUS_NAV}
</div>"""

    return f"""<div class="gstat notready">
<h2>NO SUBMISSION FILE IS READY. DO NOT SUBMIT ANYTHING FROM THIS SITE YET.</h2>
<p>No GeoTIFF is in <code>docs/downloads/</code>, so there is nothing to submit.</p>
<p><b>Blocker:</b> the competition feature stack and labels are login-gated on DrivenData and cannot be downloaded here (<a href="irregularities.html">IR-74-04</a>).</p>
{STATUS_NAV}
</div>"""


STATUS_NAV = (
    '<div class="nav">Also: <a href="submit-checklist.html">submit checklist</a> · '
    '<a href="analysis-0-2778.html">0.2778 analysis</a> · <a href="hypotheses.html">hypotheses</a> · '
    '<a href="irregularities.html">irregularities</a> · <a href="sources.html">sources</a> · '
    '<a href="leaderboard.html">leaderboard</a> · <a href="run-card.html">run card</a></div>'
)


def inject_status(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text()
    block = "<!-- BEGIN:SUBMISSION_STATUS -->\n" + STATUS_STYLE + "\n" + submission_status_html() + "\n<!-- END:SUBMISSION_STATUS -->"
    new, n = re.subn(r"<!-- BEGIN:SUBMISSION_STATUS -->.*?<!-- END:SUBMISSION_STATUS -->", lambda _m: block, text, flags=re.S)
    if n == 0:
        raise SystemExit(f"no SUBMISSION_STATUS markers in {path.name}")
    if new != text:
        path.write_text(new)
    return True


def main() -> None:
    build_leaderboard()
    build_run_card()
    for name in ("index.html", "submit-checklist.html"):
        inject_status(DOCS / name)
    print("site built:", ", ".join(sorted(p.name for p in DOCS.glob("*.html"))))


if __name__ == "__main__":
    main()
