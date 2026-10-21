#!/usr/bin/env python3
"""Build the review layer of the GitHub Pages site and its status panel.

Layout
  docs/index.html                 <- landing page of the other lanes; this script only injects a status panel
  docs/review/*.html              <- review pages written in this session (generated pages are rebuilt here)
  docs/review/data/*.json         <- leaderboard snapshot and run card for the review pages
  docs/downloads/                 <- candidate rasters (never cleared here; see the panel)

What this script does (idempotent, no network):
  1. docs/review/leaderboard.html <- docs/review/data/leaderboard_2026-10-21.json
  2. docs/review/run-card.html    <- docs/review/data/run-card.json
  3. Replaces the block between
         <!-- BEGIN:SUBMISSION_STATUS --> and <!-- END:SUBMISSION_STATUS -->
     in docs/index.html and docs/review/submit-checklist.html.

The status panel is built from disk:
  * a candidate is listed for every downloadable GeoTIFF in docs/downloads/;
  * its holdout numbers come from evidence/holdout_*.json or from a *-run-card.json beside it;
  * READY appears only when a *.receipt.json in docs/downloads/ has release_status exactly "READY".
    No receipt with that status exists, so nothing is READY.
Every number is labelled HOLDOUT-DTI or MEASURED-LOCAL, and the panel says which gate each candidate fails.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REVIEW = DOCS / "review"
DATA = REVIEW / "data"
DOWNLOADS = DOCS / "downloads"
EVIDENCE = ROOT / "evidence"

NAV = [
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
<div class="status hold"><p class="big">{_esc(card.get('status',''))}</p>
<p>{_esc(card.get('blocker',''))}</p></div>
<pre>{_esc(json.dumps(card, indent=2, ensure_ascii=False))}</pre>
"""
    (REVIEW / "run-card.html").write_text(page("Run card", body, "run-card.html"))


# ---------------------------------------------------------------- status panel

def _candidates():
    """Return one dict per candidate raster in docs/downloads, with its holdout facts."""
    out = []
    tifs = sorted(p for p in DOWNLOADS.glob("*zeros.tif"))
    for tif in tifs:
        name = tif.name
        c = {"file": name, "name": name, "rows": []}
        if "h74-alt-spring" in name:
            c["name"] = "H74-A alt-spring (other session)"
            v1 = _load(EVIDENCE / "holdout_h74a.json") or {}
            v2 = _load(EVIDENCE / "holdout_h74a_segments.json") or {}
            cand1 = (v1.get("candidate") or {}).get("pooled_DTI_cat_hidden")
            rnd1 = (v1.get("random_control") or {}).get("pooled_DTI_cat_hidden")
            cand2 = (v2.get("candidate") or {}).get("pooled_DTI_cat")
            rnd2 = (v2.get("random_control") or {}).get("pooled_DTI_cat")
            c["holdouts"] = [
                ("v0.1 4-quadrant", cand1, rnd1, v1.get("passes_random")),
                ("v0.2 segments", cand2, rnd2, v2.get("passes_random_cat")),
            ]
            c["random_gate"] = bool(v1.get("passes_random")) and bool(v2.get("passes_random_cat"))
            c["provenance"] = "inputs fetched from a sibling mirror (scripts/fetch_data.sh); rights unverified (IR-74-04)"
            c["incumbent_gate"] = "not shown"
        elif "basement-step" in name:
            c["name"] = "H74-1 basement-step (other session)"
            rc_path = next(iter(DOWNLOADS.glob("*h74-1*run-card.json")), None)
            rc = _load(rc_path) if rc_path else None
            rc = rc or {}
            mean = rc.get("holdout_dti_mean")
            rnd = rc.get("random_baseline_mean")
            c["holdouts"] = [("4-quadrant, catalogue + scatter", mean, rnd, (rc.get("delta_vs_random") or 0) > 0)]
            c["random_gate"] = (rc.get("delta_vs_random") or 0) > 0
            c["provenance"] = "not recorded in its run card (IR-74-25)"
            c["incumbent_gate"] = "not shown: its arms are H74-1, a random control and a uniform 2.8 lattice; H33-2-B2 is not in the run card"
            canary = rc.get("leakage_canary") or []
            canary = canary[0] if isinstance(canary, list) and canary else (canary if isinstance(canary, dict) else {})
            c["extra"] = (
                f"leakage canary AUC {canary.get('auc')}; "
                f"uniqueness rho {rc.get('correlation_vs_registry')}, overlap {rc.get('overlap_within_3px_pct')}%; "
                f"verdict field '{rc.get('verdict')}'"
            )
        else:
            c["holdouts"] = []
            c["random_gate"] = False
            c["provenance"] = "not recorded"
            c["incumbent_gate"] = "not shown"
        out.append(c)
    return out


def _fmt(x):
    return "n/a" if x is None else f"{x:.5f}"


def submission_status_html(prefix: str) -> str:
    """prefix: relative path from the host page to docs/ ('' for docs/index.html, '../' for docs/review/)."""
    ready = []
    for rp in sorted(DOWNLOADS.glob("*.receipt.json")):
        r = _load(rp)
        if r and r.get("release_status") == "READY":
            ready.append(r)

    review_nav = (
        f'<div class="nav">Review pages: <a href="{prefix}review/submit-checklist.html">submit checklist</a> · '
        f'<a href="{prefix}review/analysis-0-2778.html">0.2778 analysis</a> · '
        f'<a href="{prefix}review/hypotheses.html">hypotheses</a> · '
        f'<a href="{prefix}review/irregularities.html">irregularities</a> · '
        f'<a href="{prefix}review/sources.html">sources</a> · '
        f'<a href="{prefix}review/leaderboard.html">leaderboard</a> · '
        f'<a href="{prefix}review/run-card.html">run card</a></div>'
    )

    if ready:
        parts = []
        for r in ready:
            parts.append(
                f"<h2>READY TO SUBMIT: {_esc(r.get('submission_name', ''))}</h2>"
                f"<ul><li>File: <a href=\"{prefix}downloads/{_esc(r['file'])}\">{_esc(r['file'])}</a></li>"
                f"<li>Note ({r.get('note_chars', '?')}/200): {_esc(r.get('submission_note', ''))}</li>"
                f"<li>sha256: <code>{_esc(r.get('sha256', ''))}</code></li></ul>"
                f"<a class=\"btn go\" href=\"{prefix}downloads/{_esc(r['file'])}\">Download submission .tif</a>"
            )
        return f'<div class="gstat ready">{"".join(parts)}{review_nav}</div>'

    cands = _candidates()
    if not cands:
        return f"""<div class="gstat notready">
<h2>NO SUBMISSION FILE IS READY. DO NOT SUBMIT ANYTHING FROM THIS SITE YET.</h2>
<p>No GeoTIFF is in <code>docs/downloads/</code>, so there is nothing to submit.</p>
{review_nav}
</div>"""

    blocks = []
    for c in cands:
        hold_rows = []
        for label, cand, rnd, passes in c["holdouts"]:
            hold_rows.append(
                f"<tr><td>{_esc(label)}</td><td><span class=\"lab\">HOLDOUT-DTI</span> {_fmt(cand)}</td>"
                f"<td>{_fmt(rnd)}</td><td class=\"{'yes' if passes else 'no'}\">{'passes' if passes else 'FAILS'} random control</td></tr>"
            )
        if not hold_rows:
            hold_rows.append("<tr><td colspan=\"4\">no holdout evidence found</td></tr>")
        gate = [
            ("Beats random control on its holdout", c["random_gate"]),
            ("Beats the incumbent H33-2-B2 on the same holdout", False),
            ("Holdout truth independent of the catalogue", False),
            ("Input rights and provenance recorded", False),
            ("Organiser receipt and READY promotion", False),
        ]
        gate_rows = "".join(
            f"<tr><td>{_esc(g)}</td><td class=\"{'yes' if ok else 'no'}\">{'yes' if ok else 'NO'}</td></tr>"
            for g, ok in gate
        )
        extra = f"<p class=\"mut\">{_esc(c['extra'])}</p>" if c.get("extra") else ""
        blocks.append(
            f"""<h2>{_esc(c['name'])}</h2>
<p><a class="btn review" href="{prefix}downloads/{_esc(c['file'])}">Download for review only (not cleared)</a> <code>{_esc(c['file'])}</code></p>
<table><tr><th>Holdout</th><th>Candidate</th><th>Random control</th><th>Result</th></tr>{''.join(hold_rows)}</table>
<table><tr><th>Gate</th><th>Met?</th></tr>{gate_rows}</table>
<p class="mut">Provenance: {_esc(c['provenance'])}. Incumbent comparison: {_esc(c['incumbent_gate'])}.</p>
{extra}"""
        )

    return f"""<div class="gstat hold">
<h2>HOLD: DO NOT SUBMIT. Candidates exist, and none is cleared.</h2>
<p><b>Submit: NO.</b> <b>Download:</b> review copies only. This project's gate requires all five checks below. None of the candidates meets all five.</p>
{''.join(blocks)}
<p class="mut">HOLDOUT-DTI numbers are from local evaluators on catalogue-based truth. None is an organiser score. The 0.2778 figure is self-reported for the GEMSDOE32 file. The only 0.2778 on the public board is extradr19 (IR-74-03).</p>
{review_nav}
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
