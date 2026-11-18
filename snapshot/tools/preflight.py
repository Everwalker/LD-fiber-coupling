"""Entry point: python -m tools.preflight

Prints the v3 preflight JSON report and returns a meaningful exit code:
  0 all software/input/math checks PASS
  1 at least one check FAIL
  2 configuration/input could not be loaded or processed
This tool never starts, connects to, or claims anything about COMSOL.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from validation.preflight_v3 import run

ROOT = Path(__file__).resolve().parents[1]

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='python -m tools.preflight', description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT,
                        help='package root containing configs/, inputs/, validation/, src/')
    parser.add_argument('--save-source', type=Path, default=None,
                        help='optional path for the MATHEMATICAL source record '
                             '(a mathematical artifact, never a COMSOL conclusion)')
    args = parser.parse_args(argv)
    try:
        result = run(args.root)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({'record_type': 'PREFLIGHT_V3', 'overall_status': 'ERROR',
                          'error': str(exc), 'comsol_executed': False},
                         ensure_ascii=False, indent=2))
        return 2
    if args.save_source is not None:
        record = result['checks']['source_math_974'].get('record')
        if record is not None:
            args.save_source.parent.mkdir(parents=True, exist_ok=True)
            args.save_source.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n',
                                        encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['overall_status'] == 'SOFTWARE_CHECKS_PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
