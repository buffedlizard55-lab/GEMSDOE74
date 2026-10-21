#!/usr/bin/env python3
"""Build authoritative HOLD pages from measured file audits; never auto-promote.

Historical pages are retained with a prominent retraction notice. Release selection
is intentionally not implemented: a receipt containing READY alone is insufficient.
"""
import html
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT/'docs'

def page(title, body):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · GEMSDOE74</title>
<style>body{{font:17px/1.65 system-ui,sans-serif;background:#f4f6f8;color:#172b36;margin:0}}main{{max-width:960px;margin:auto;padding:30px 24px}}nav a{{margin-right:20px}}a{{color:#065b78}}h1{{line-height:1.2}}.hold{{border-left:6px solid #a82b20;background:#fff0ed;padding:20px}}article{{background:white;padding:22px;margin:22px 0;border:1px solid #dae1e5;border-radius:10px}}code{{overflow-wrap:anywhere;font-size:.85em}}.btn{{display:inline-block;padding:10px 16px;border:1px solid #065b78;border-radius:6px}}small{{color:#536574}}</style></head><body><main>
<nav><a href="index.html">Status & downloads</a><a href="executive-summary.html">Submission guide</a><a href="audit-20261021.html">Integrity audit</a><a href="review/session-review-2026-10-21.html">Current review</a><a href="review/leaderboard.html">Leaderboard snapshot</a></nav>
<h1>{html.escape(title)}</h1><section class="hold"><strong>DO NOT SUBMIT — research hold.</strong><br>Review downloads are available. No new competition-ready TIFF, valid holdout result, or complete uniqueness clearance exists.</section>{body}
<footer><small>Static audit dated 2026-10-21. No weekly submission slot used. File checks are not competition scores.</small></footer></main></body></html>'''

def build_review_pages():
    """Regenerate the current machine-readable run card and leaderboard review pages."""
    review = DOCS / 'review'
    data_dir = review / 'data'
    card = json.loads((data_dir / 'run-card.json').read_text())
    card_pre = html.escape(json.dumps(card, indent=2, ensure_ascii=False))
    run_html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Current run card · GEMSDOE74</title><link rel="stylesheet" href="../assets/site.css"></head><body><header class="top"><span class="brand">GEMSDOE74</span><a href="../index.html">Status</a><a href="session-review-2026-10-21.html">Current review</a><a href="leaderboard.html">Leaderboard</a></header><main><h1>Current run card</h1><div class="status hold"><p class="big">NEGATIVE — no candidate is cleared</p><p>No new TIFF was generated. HOLDOUT-DTI, CI and submission validator for a new candidate are not available.</p></div><p>Machine-readable record: <a href="data/run-card.json">run-card.json</a>.</p><pre>{card_pre}</pre></main><footer>HOLD · inherited raster audit is not an organizer score.</footer></body></html>'''
    (review / 'run-card.html').write_text(run_html)

    board = json.loads((data_dir / 'leaderboard_2026-10-21.json').read_text())
    rows = []
    for row in board['rows']:
        cls = ' class="hl"' if row.get('participant') == 'extradr19' else ''
        rows.append(f'''<tr{cls}><td>{row['rank']}</td><td>{html.escape(row['participant'])}</td><td>{row['public_dw_tversky']:.4f}</td><td>{row['submissions']}</td></tr>''')
    board_html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Public leaderboard snapshot · GEMSDOE74</title><link rel="stylesheet" href="../assets/site.css"></head><body><header class="top"><span class="brand">GEMSDOE74</span><a href="../index.html">Status</a><a href="session-review-2026-10-21.html">Current review</a><a href="run-card.html">Run card</a></header><main><h1>Public leaderboard snapshot</h1><p>Source: <a href="{html.escape(board['source'])}">official DrivenData leaderboard</a> · retrieved {board['retrieved']} · <span class="pill p-pl">PUBLIC-LEADERBOARD</span>. These are participant public scores, not private-test results, organizer receipts, or raster attribution.</p><p>Rank 1 is 0.4413; the rank-47 value 0.2778 belongs to participant extradr19. The page does not link that row to the named GEMSDOE32 file.</p><table><thead><tr><th>Rank</th><th>Participant</th><th>Public DW-Tversky</th><th>Submissions</th></tr></thead><tbody>{''.join(rows)}</tbody></table><p>No row in this table is an ORGANIZER-CONFIRMED result for a file in this repository.</p></main><footer>Public test only. See current review for source and attribution limits.</footer></body></html>'''
    (review / 'leaderboard.html').write_text(board_html)


def write_current_aliases():
    """Replace stale top-level pages retained from earlier parallel runs."""
    aliases = {
        'hypotheses.html': ('review/hypotheses.html', 'Current H74-1 hypothesis slate'),
        'leaderboard.html': ('review/leaderboard.html', 'Dated public leaderboard snapshot'),
        'irregularities.html': ('review/irregularities.html', 'Current audit irregularities'),
        'sources.html': ('review/sources.html', 'Current source register'),
        'research.html': ('review/session-review-2026-10-21.html', 'Current source-checked session review'),
    }
    for filename, (target, label) in aliases.items():
        (DOCS/filename).write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0; url={target}"><title>{html.escape(label)} · GEMSDOE74</title></head><body><p>This page has moved to the current, source-checked record: <a href="{target}">{html.escape(label)}</a>.</p></body></html>''')

def main():
    audit = json.loads((ROOT/'evidence/file-audit-20261021.json').read_text())
    cards = []
    for a in audit['files']:
        file = html.escape(a['file'])
        cards.append(f'''<article><h2>{'H74-1 — synthetic, retracted' if 'basement-step' in file else 'H74-A — historical, not promoted'}</h2>
<p><a class="btn" download href="downloads/{file}">Download TIFF for review only</a></p><p><code>{file}</code></p>
<p>Measured file checks: <b>{'PASS' if a['passed'] else 'FAIL'}</b>. Nonzero cells outside mirrored footprint: {a['n_outside_nonzero_finite']:,}.</p>
<p>SHA-256: <code>{a['sha256']}</code></p><p>Not cleared for submission. Range and grid checks do not establish model skill.</p></article>''')
    (DOCS/'index.html').write_text(page('GEMSDOE74 · submission status', '''<p>Fault-discovery research for geothermal exploration. The audit found fabricated evaluation evidence in the former generator; that path is now disabled.</p>'''+''.join(cards)+'''<p><a href="review/data/run-card.json">Download negative run card (JSON)</a></p><ul><li><a href="review/session-review-2026-10-21.html">Current source-checked executive review</a></li><li><a href="review/hypotheses.html">Ranked H74-1 hypothesis slate</a></li><li><a href="review/leaderboard.html">Dated official public leaderboard snapshot</a></li><li><a href="review/sources.html">Primary-source register and access status</a></li></ul>'''))
    (DOCS/'executive-summary.html').write_text(page('Executive summary · how submission works', '''<article><h2>Today: download for review, not submission</h2><p>The primary requested deliverable—a new, scientifically evaluated and unique TIFF—is blocked, not complete. Do not upload a legacy file merely because its numeric range passes validation.</p><p><a class="btn" href="index.html">View review downloads</a></p></article>
<article><h2>After independent promotion</h2><ol><li>Recover the genuine shared cache, source rights and real template. Validate feature names and grid metadata.</li><li>Run buffered whole-segment hide-and-recover, recomputing catalogue features from visible faults only. Require pooled DTI, withheld-positive count, block-bootstrap confidence interval and valid feature canaries.</li><li>Compare against the incumbent on identical folds. Check the entire registry before placement and final dot overlap after placement. Unknown comparisons block release.</li><li>Write a unique single-band GeoTIFF using the existing writer. Reopen bytes; validate shape, CRS, transform, finite footprint values and range [0,1]. Use a unique name and note no longer than 140 characters.</li><li>A separate selector checks the current weekly cap and rules. Only then use the competition's New submission form, select the promoted TIFF and paste its note.</li><li>Save the organizer's submission-page receipt and file hash. Only a score from that receipt may be labeled ORGANIZER-CONFIRMED.</li></ol></article>
<article><h2>Range error troubleshooting</h2><p>Reject NaN or infinity inside the footprint and reject negative nodata sentinels or values above one. Do not clip unknown bad inputs into apparent validity. All-finite zero-outside output avoids numeric NaN/sentinel ambiguity but does not guarantee portal acceptance; the authenticated organizer template and current rules still govern.</p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official format and problem description (fetched 2026-10-21)</a></article>'''))
    (DOCS/'audit-20261021.html').write_text(page('Integrity audit · negative result', '''<article><h2>Verified defects</h2><ul><li>The old generator synthesized geology, catalogue and hidden truth; its AUC and registry figures were hard-coded. The old run card is retracted.</li><li>The H74-1 TIFF has 20,013 nonzero cells outside the recovered mirrored footprint. Its earlier synthetic-footprint validation was insufficient.</li><li>The segment evaluator disables the requested buffer and evaluates a precomputed raster. Its legacy scores are not protocol-compliant HOLDOUT-DTI.</li><li>Preparation used to report success with missing data. It now fails closed and clears stale success.</li><li>The legacy metric binarized soft predictions. It now delegates to the canonical soft metric. Canary failures no longer become a reassuring AUC.</li></ul></article>
<article><h2>H33 interpretation</h2><p>The retrieved owner audit documents catalogue-flank pruning of a sparse baseline, but says UNSCORED. The user's reported result has no organizer receipt here. Pruning redundant or unproductive prediction mass can help a recall-weighted metric; it does not prove that a novel geological detector improved. Kernel supports still overlap at the documented spacing. No higher leaderboard score is promised.</p></article>
<article><h2>Evidence and research plan</h2><p>Read the repository README for four ranked, untested hypotheses within the basement-step lane, limitations, source links and next-session priorities. No new experiment was run, and no synthetic stand-in is being offered as a competition prediction.</p><ul><li><a href="https://github.com/buffedlizard55-lab/GEMSDOE74/blob/main/evidence/file-audit-20261021.json">Measured file audit</a></li><li><a href="https://github.com/buffedlizard55-lab/GEMSDOE74/blob/main/README.md">Research plan and source status</a></li><li><a href="review/session-review-2026-10-21.html">Current source-checked session review</a></li><li><a href="review/data/run-card.json">Negative run card</a></li><li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference repository (read)</a></li></ul><p>GitHub Pages is a static site, not a live leaderboard feed or browser training tool.</p></article>'''))
    build_review_pages()
    write_current_aliases()
    # A consistent first-fold warning overrides historical claims without erasing history.
    aliases = {'hypotheses.html', 'leaderboard.html', 'irregularities.html', 'sources.html', 'research.html'}
    for p in DOCS.rglob('*.html'):
        if p.parent == DOCS and p.name in {'index.html','executive-summary.html','audit-20261021.html'} | aliases:
            continue
        s = p.read_text()
        import os, re
        link = os.path.relpath(DOCS/'audit-20261021.html', p.parent)
        current_pages = {'session-review-2026-10-21.html', 'run-card.html', 'leaderboard.html', 'hypotheses.html', 'irregularities.html', 'sources.html', 'submit-checklist.html'}
        if p.parent == DOCS/'review' and p.name in current_pages:
            label = 'CURRENT RESEARCH HOLD — DO NOT SUBMIT.'
            message = 'Historical synthetic claims are retracted. No valid HOLDOUT-DTI, new candidate TIFF, or complete uniqueness clearance exists.'
        else:
            label = 'HISTORICAL PAGE — DO NOT SUBMIT.'
            message = 'Prior synthetic H74-1 scores, AUC and registry claims are retracted. Other legacy holdouts do not meet the buffered protocol.'
        warning = f'<aside id="INTEGRITY-RETRACTION-20261021" style="padding:24px;background:#fff0ed;color:#752217;border:4px solid #a82b20"><b>{label}</b> {message} <a href="{link}">Read the authoritative audit.</a></aside>'
        if 'INTEGRITY-RETRACTION-20261021' in s:
            s = re.sub(r'<aside id="INTEGRITY-RETRACTION-20261021".*?</aside>', lambda m: warning, s, count=1, flags=re.S)
        else:
            s = re.sub(r'(<body[^>]*>)', lambda m: m.group(1)+warning, s, count=1)
        p.write_text(s)
    print('Built HOLD site and historical retraction notices.')

if __name__ == '__main__':
    main()
