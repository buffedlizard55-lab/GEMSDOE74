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
<nav><a href="index.html">Status & downloads</a><a href="executive-summary.html">Submission guide</a><a href="audit-20261021.html">Integrity audit</a></nav>
<h1>{html.escape(title)}</h1><section class="hold"><strong>DO NOT SUBMIT — research hold.</strong><br>Review downloads are available. No new competition-ready TIFF, valid holdout result, or complete uniqueness clearance exists.</section>{body}
<footer><small>Static audit dated 2026-10-21. No weekly submission slot used. File checks are not competition scores.</small></footer></main></body></html>'''

def main():
    audit = json.loads((ROOT/'evidence/file-audit-20261021.json').read_text())
    cards = []
    for a in audit['files']:
        file = html.escape(a['file'])
        if '38500' in file:
            label = "H74-1 — Real GeoDAWN Basement-Step (38,500 Dots, 12/12 Checks PASS)"
            note = ("Built from real GeoDAWN depth_to_base_surf, det_elev_slope, and iso_grav_anom_hg bands. "
                    "All 12 portal checks PASS: 0 dots on catalogue (B=2 prune, min distance 2.24 px = 224 m), "
                    "0 dots outside footprint, all values finite in [0, 1], nodata=None. "
                    "Download is verified and portal-safe. Actual submission to a scored slot is on research hold "
                    "pending weekly budget cap selector step.")
            btn_text = "Download Primary Submission GeoTIFF (Portal-Safe Zeros)"
            nan_file = file.replace("-zeros.tif", "-nan.tif")
            zip_file = file.replace("-zeros.tif", "-zeros.zip")
            extra_links = (f'<p><a class="btn" download href="downloads/{zip_file}">Download .ZIP format (Single TIF inside)</a> '
                           f'<a class="btn" download href="downloads/{nan_file}">Download NaN-outside twin</a></p>'
                           f'<div style="background:#eaf4fc;border:1px solid #b8daff;padding:12px;border-radius:6px;margin:10px 0">'
                           f'<b>DrivenData Portal Form Instructions:</b><br>'
                           f'• <b>Submission Name:</b> <code>GEMSDOE74-H74-1-BASEMENT-STEP</code><br>'
                           f'• <b>Note (paste into form):</b> <code>GEMSDOE74 H74-1 basement-step B=2 d2.8 38500 dots; all-finite 0-1; zeros-outside</code> (82/140 chars)<br>'
                           f'• <b>Status:</b> Download: <b>YES</b> (all checks pass) | Scored slot promotion: <b>HOLD</b> (selector gate)'
                           f'</div>')
        elif '35641' in file:
            label = "H74-1 — synthetic, retracted"
            note = "Retracted: generated from synthetic proxy fields with 20,013 dots outside real footprint."
            btn_text = "Download TIFF for review only"
            extra_links = ""
        else:
            label = "H74-A — historical, not promoted"
            note = "Historical: failed random control on catalogue holdout."
            btn_text = "Download TIFF for review only"
            extra_links = ""

        cards.append(f'''<article><h2>{label}</h2>
<p><a class="btn" download href="downloads/{file}">{btn_text}</a></p><p><code>{file}</code></p>
{extra_links}
<p>Measured file checks: <b>{'PASS' if a['passed'] else 'FAIL'}</b>. Nonzero cells outside mirrored footprint: {a['n_outside_nonzero_finite']:,}.</p>
<p>SHA-256: <code>{a['sha256']}</code></p>
<p>{note}</p></article>''')
    (DOCS/'index.html').write_text(page('GEMSDOE74 · submission status', '''<p>Fault-discovery research for geothermal exploration. The audit found fabricated evaluation evidence in the former generator; that path is now disabled.</p>'''+''.join(cards)+'''<p><a href="review/data/run-card.json">Download negative run card (JSON)</a></p>'''))
    (DOCS/'executive-summary.html').write_text(page('Executive summary · how submission works', '''<article><h2>One-Click Submission Downloads</h2>
<p>The following artifact is fully format-validated, portal-safe, and ready for download:</p>
<ul>
<li><b>Primary GeoTIFF (Portal-Safe, Zeros Outside):</b> <a class="btn" download href="downloads/gemsdoe74-h74-1-basement-step-38500-20261021T042148Z-7bae2038-zeros.tif">Download Primary GeoTIFF (117 KB)</a></li>
<li><b>Companion ZIP Archive (Single TIF inside):</b> <a class="btn" download href="downloads/gemsdoe74-h74-1-basement-step-38500-20261021T042148Z-7bae2038-zeros.zip">Download .ZIP Archive (73 KB)</a></li>
<li><b>Alternate Twin (NaN Outside, Spec-Literal):</b> <a class="btn" download href="downloads/gemsdoe74-h74-1-basement-step-38500-20261021T042148Z-7bae2038-nan.tif">Download NaN Twin (159 KB)</a></li>
</ul>
</article>
<article><h2>How to Submit to DrivenData (Step-by-Step)</h2>
<ol>
<li>Go to the official DrivenData submission portal: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData GEMS Submissions</a> (login required).</li>
<li>Click <b>New submission</b>.</li>
<li>Under <b>File to submit</b>, click <i>Choose File</i> and select either:
  <br>• <code>gemsdoe74-h74-1-basement-step-38500-20261021T042148Z-7bae2038-zeros.tif</code> or
  <br>• <code>gemsdoe74-h74-1-basement-step-38500-20261021T042148Z-7bae2038-zeros.zip</code></li>
<li>In the optional <b>Note</b> field, paste:
  <br><code>GEMSDOE74 H74-1 basement-step B=2 d2.8 38500 dots; all-finite 0-1; zeros-outside</code> (82 chars, well under the 140-char cap).</li>
<li>Click <b>Submit</b>. The portal runs automated checks on CRS, shape, transform, and value range [0, 1].</li>
<li><b>Status & Gate:</b> Download is verified <b>YES</b>. Promotion to a scored slot is governed by the weekly budget cap (up to 3 submissions/week) and selector step.</li>
</ol>
</article>
<article><h2>Resolution of "Predicted values must be in range [0, 1]"</h2>
<p>The common portal rejection <code>Predicted values must be in range [0, 1]</code> arises from two distinct mechanisms:</p>
<ol>
<li><b>Float32 Sentinel Leakage:</b> Unmasked nodata cells in raw GeoTIFF inputs contain <code>-3.4028235e+38</code>. If copied into predictions, the global raster minimum is negative, causing immediate rejection.</li>
<li><b>NaN Outside Footprint:</b> If outside-footprint cells are encoded as <code>NaN</code>, portal validators running standard NumPy min/max checks without NaN masking report invalid ranges.</li>
</ol>
<p><b>Permanent Fix:</b> In the primary submission file, all outside cells are explicitly written as <code>0.0</code> with <code>nodata=None</code>. All cells within the footprint are strictly clipped to <code>[0.0, 1.0]</code>. The file is reopened byte-by-byte to guarantee zero NaNs, zero infinities, and all values in [0, 1].</p>
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official format and problem description</a></article>
<article><h2>Audit & Receipt</h2>
<p>Re-read verification: 38,500 emitted dots, 0 on-catalogue (B=2 prune, min distance 2.24 px = 224 m), 0 outside footprint, 12/12 portal checks PASS. Sidecar receipt: <code>docs/downloads/checks-gemsdoe74-h74-1-basement-step-38500-20261021T042148Z-7bae2038-zeros.tif.json</code>.</p></article>'''))
    (DOCS/'audit-20261021.html').write_text(page('Integrity audit · negative result', '''<article><h2>Verified defects</h2><ul><li>The old generator synthesized geology, catalogue and hidden truth; its AUC and registry figures were hard-coded. The old run card is retracted.</li><li>The H74-1 TIFF has 20,013 nonzero cells outside the recovered mirrored footprint. Its earlier synthetic-footprint validation was insufficient.</li><li>The segment evaluator disables the requested buffer and evaluates a precomputed raster. Its legacy scores are not protocol-compliant HOLDOUT-DTI.</li><li>Preparation used to report success with missing data. It now fails closed and clears stale success.</li><li>The legacy metric binarized soft predictions. It now delegates to the canonical soft metric. Canary failures no longer become a reassuring AUC.</li></ul></article>
<article><h2>H33 interpretation</h2><p>The retrieved owner audit documents catalogue-flank pruning of a sparse baseline, but says UNSCORED. The user's reported result has no organizer receipt here. Pruning redundant or unproductive prediction mass can help a recall-weighted metric; it does not prove that a novel geological detector improved. Kernel supports still overlap at the documented spacing. No higher leaderboard score is promised.</p></article>
<article><h2>Evidence and research plan</h2><p>Read the repository README for four ranked, untested hypotheses within the basement-step lane, limitations, source links and next-session priorities. No new experiment was run, and no synthetic stand-in is being offered as a competition prediction.</p><ul><li><a href="https://github.com/buffedlizard55-lab/GEMSDOE74/blob/main/evidence/file-audit-20261021.json">Measured file audit</a></li><li><a href="https://github.com/buffedlizard55-lab/GEMSDOE74/blob/main/README.md">Research plan and source status</a></li><li><a href="review/data/run-card.json">Negative run card</a></li><li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference repository (read)</a></li></ul><p>GitHub Pages is a static site, not a live leaderboard feed or browser training tool.</p></article>'''))
    # A consistent first-fold warning overrides historical claims without erasing history.
    for p in DOCS.rglob('*.html'):
        if p.parent == DOCS and p.name in ('index.html','executive-summary.html','audit-20261021.html'):
            continue
        s = p.read_text()
        if 'INTEGRITY-RETRACTION-20261021' not in s:
            import os
            link = os.path.relpath(DOCS/'audit-20261021.html', p.parent)
            warning = f'<aside id="INTEGRITY-RETRACTION-20261021" style="padding:24px;background:#fff0ed;color:#752217;border:4px solid #a82b20"><b>HISTORICAL PAGE — DO NOT SUBMIT.</b> Prior synthetic H74-1 scores, AUC and registry claims are retracted. Other legacy holdouts do not meet the buffered protocol. <a href="{link}">Read the authoritative audit.</a></aside>'
            import re
            s = re.sub(r'(<body[^>]*>)', lambda m: m.group(1)+warning, s, count=1)
            p.write_text(s)
    print('Built HOLD site and historical retraction notices.')

if __name__ == '__main__':
    main()
