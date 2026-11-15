"""Compare the 55 MILEPOST values of a result with the reference (exit 0 when equal).

Usage: python3 compare.py <result.json> <reference.json>
"""
import json
import sys


def values(path):
    try:
        with open(path, encoding='utf-8') as stream:
            return json.load(stream).get('values') or {}
    except (OSError, ValueError):
        return {}


result, reference = values(sys.argv[1]), values(sys.argv[2])
if result and result == reference:
    print('Reference check: the %d values equal those of 2026-10-20 (%s).' % (len(result), sys.argv[2]))
    sys.exit(0)
differ = sorted(k for k in reference if result.get(k) != reference[k])
print('Reference check: DIFFERENT from %s: %s' % (sys.argv[2], ', '.join(differ) if result else 'no values in ' + sys.argv[1]))
sys.exit(1)
