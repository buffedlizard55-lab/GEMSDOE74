#!/usr/bin/env bash
set -euo pipefail
DEST=${1:-/tmp/gems74_data}
mkdir -p "$DEST/external" "$DEST"
echo "Fetching pinned mirrors via gh api to $DEST"
fetch() {
  repo=$1; ref=$2; path=$3; out=$4; sha=$5
  echo "→ $out"
  mkdir -p "$(dirname "$out")"
  if [ -f "$out" ] && [ -n "$sha" ]; then
    cur=$(sha256sum "$out" | awk '{print $1}')
    if [ "$cur" = "$sha" ]; then echo "  already OK $sha"; return 0; fi
  fi
  gh api "repos/$repo/contents/$path?ref=$ref" -H "Accept: application/vnd.github.raw" > "$out"
  cur=$(sha256sum "$out" | awk '{print $1}')
  if [ -n "$sha" ] && [ "$cur" != "$sha" ]; then echo "FAIL sha mismatch $cur != $sha"; exit 1; fi
  echo "  OK $cur"
}
fetch buffedlizard55-lab/GEMSDOE24 07345ea0604953d7efb858d9cfbc21e20c7aca0b data/bridge/sample_submission.tif "$DEST/sample_submission.tif" 2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc
fetch buffedlizard55-lab/GEMSDOE24 07345ea0604953d7efb858d9cfbc21e20c7aca0b data/bridge/labels.tif "$DEST/labels.tif" 7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093
fetch buffedlizard55-lab/GEMSDOE24 07345ea0604953d7efb858d9cfbc21e20c7aca0b data/external/gdr_wellspring_in_footprint.csv "$DEST/external/gdr_wellspring_in_footprint.csv" 122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea
fetch buffedlizard55-lab/GEMSDOE24 07345ea0604953d7efb858d9cfbc21e20c7aca0b data/external/derived_sgmc_faults_100m_u8.tif "$DEST/external/derived_sgmc_faults_100m_u8.tif" 643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0
fetch buffedlizard55-lab/GEMSDOE24 07345ea0604953d7efb858d9cfbc21e20c7aca0b data/external/geodawn_rad_u8.tif "$DEST/external/geodawn_rad_u8.tif" c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682
echo "All 5/5 verified"
