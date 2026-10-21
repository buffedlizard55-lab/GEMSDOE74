#!/usr/bin/env python3
"""Fail closed: the former generator fabricated geology and evaluation evidence.

No replacement training pipeline is claimed. Restore the shared real feature cache,
repair buffered out-of-fold evaluation, and pass both registry gates first.
The historical implementation remains available in Git at 2c31407.
"""
import sys

def main():
    print('BLOCKED: H74-1 used synthetic inputs and hard-coded AUC/uniqueness. '
          'No new TIFF was generated. See docs/audit-20261021.html.', file=sys.stderr)
    return 2

if __name__ == '__main__':
    raise SystemExit(main())
