"""Validate all offline intermediates; optionally repeat the build to check determinism."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pyarrow.parquet as pq

from normalization_core import ROOT, RAW, SOURCE_IDS, Source, file_hash, js
from normalize_sources import BASE, TABLES, validate
from download_sources import atomic_json


# =============================================================================
# Public workflow and supporting operations
# =============================================================================
def inspect():
    """Validate normalized schemas, counts, keys and recorded file hashes without downloading data.
    
    Returns
    -------
    tuple
        Validation results and per-output byte/semantic signatures.
    """
    manifest = json.loads((BASE / 'manifest.json').read_text(encoding='utf-8'))
    acquisition = json.loads((RAW / 'versions.txt').read_text(encoding='utf-8'))
    assert file_hash(RAW / 'versions.txt') == manifest['acquisition_manifest_sha256'], 'Source manifest changed'
    result = {'sources': {}, 'input_files_checked': 0, 'output_files_checked': 0, 'records': 0}
    signatures = {}
    for s in SOURCE_IDS:
        entry = manifest['sources'][s]
        assert entry['status'] == 'success', (s, entry.get('error'))
        for name, digest in entry['implementation'].items():
            assert file_hash(ROOT / 'scripts' / name) == digest, 'Stale implementation: ' + s + '/' + name
        for f in entry['inputs']:
            assert file_hash(RAW / f['path']) == f['sha256'], f['path']
            result['input_files_checked'] += 1
        ctx = Source(s, acquisition['sources'][s])
        ctx.inventory = entry['inventory']
        for name, (attr, schema) in TABLES.items():
            table = pq.read_table(BASE / s / (name + '.parquet'))
            assert table.schema.equals(schema), (s, name, 'schema')
            table.validate(full=True)
            setattr(ctx, attr, table.to_pylist())
        assert validate(ctx) == entry['summary'], 'Summary mismatch: ' + s
        for f in entry['outputs']:
            assert file_hash(BASE / f['path']) == f['sha256'], f['path']
            result['output_files_checked'] += 1
            semantic = None
            if f['path'].endswith('.parquet'):
                semantic = hashlib.sha256(js(pq.read_table(BASE / f['path']).to_pylist()).encode()).hexdigest()
                assert semantic == f['semantic_sha256'], f['path']
            signatures[f['path']] = (f['sha256'], semantic)
        result['sources'][s] = {'records': len(ctx.records), 'reconciliation': 'passed', 'types_keys_references': 'passed'}
        result['records'] += len(ctx.records)
    return result, signatures


def main():
    """Parse command-line options and execute this module workflow with its documented safety checks.
    
    Returns
    -------
    int or None
        Nonzero status on explicitly handled workflow failure; otherwise success.
    
    Raises
    ------
    RuntimeError
        If the required unit-test run fails; integrity failures stop the workflow separately.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeat', action='store_true')
    parser.add_argument('--protected-baseline', type=Path, help='Optional pre-task path-to-SHA256 snapshot')
    args = parser.parse_args()
    result, before = inspect()
    print('Initial input/output/type/key/reconciliation checks passed.', flush=True)
    if args.repeat:
        subprocess.run([sys.executable, str(ROOT / 'scripts/normalize_sources.py'), '--report'], cwd=ROOT, check=True)
        result, after = inspect()
        assert before.keys() == after.keys(), 'Changed output set'
        changed = [p for p in before if before[p] != after[p]]
        assert not changed, 'Non-deterministic byte/semantic output: ' + ', '.join(changed)
        result['full_repeat_byte_and_semantic_determinism'] = 'passed'
    else:
        result['full_repeat_byte_and_semantic_determinism'] = 'not_run'
    tests = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, capture_output=True, text=True)
    if tests.returncode:
        print(tests.stdout + tests.stderr)
        raise RuntimeError('Tests failed')
    result['unit_tests'] = {'status': 'passed', 'count': int(re.search(r'Ran (\d+) tests', tests.stderr)[1])}
    if args.protected_baseline:
        baseline = json.loads(args.protected_baseline.read_text(encoding='utf-8'))
        for p, digest in baseline.items():
            assert file_hash(ROOT / p) == digest, 'Protected file changed: ' + p
        result['protected_files'] = {'status': 'unchanged', 'count': len(baseline),
                                     'scope': 'all pre-existing raw source files, acquisition manifest, historical data, vault notes and .obsidian files'}
    atomic_json(BASE / 'validation.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'sources'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
