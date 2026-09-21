"""Normalize verified local source assets without acquisition, merging or species conversion."""
from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

from normalization_core import (ROOT, RAW, SOURCE_IDS, SCHEMA_VERSION, ADAPTER_VERSION, file_hash, js,
                                RECORD_SCHEMA, EVIDENCE_SCHEMA, MEMBER_SCHEMA, REGULATOR_SCHEMA)
from source_normalizers import normalize
from download_sources import atomic_json, remove_tree

BASE = ROOT / 'data/interim'
TABLES = {'records': ('records', RECORD_SCHEMA), 'evidence': ('evidence', EVIDENCE_SCHEMA),
          'memberships': ('members', MEMBER_SCHEMA), 'regulators': ('regulators', REGULATOR_SCHEMA)}


# =============================================================================
# Public workflow and supporting operations
# =============================================================================
def validate(ctx):
    """Check normalized schema/keys and ensure all input interaction rows remain traceable.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    dict
        Reconciled normalized source summary after schema and key checks.
    
    Raises
    ------
    ValueError
        If source row counts, keys, statuses, provenance or support references do not reconcile.
    """
    summary = ctx.summary()
    if summary['raw_interaction_records'] != len(ctx.records):
        raise ValueError(f"Row reconciliation failed: {summary['raw_interaction_records']} raw vs {len(ctx.records)} normalized")
    ids = [r['record_key'] for r in ctx.records]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate normalized record keys')
    valid_ids = set(ids)
    membership_ids = {m['complex_key'] for m in ctx.members}
    for r in ctx.records:
        for side in ['ligand', 'receptor']:
            if r[side + '_complex_key'] and r[side + '_complex_key'] not in membership_ids:
                raise ValueError('Unresolved membership reference: ' + r['record_key'])
        if r['species_group'] == 'mouse' and r['dataset_provenance'] == 'orthology-derived' and r['evidence_provenance'] != 'provider_orthology':
            raise ValueError('Lost mouse orthology provenance')
        if r['status'] == 'candidate' and (r['review_reasons'] or r['exclusion_reasons']):
            raise ValueError('Candidate with unresolved review/exclusion reasons')
    for table in [ctx.evidence, ctx.regulators]:
        if any(e['record_key'] not in valid_ids for e in table):
            raise ValueError('Dangling evidence/regulator record reference')
    if len({e['evidence_key'] for e in ctx.evidence}) != len(ctx.evidence):
        raise ValueError('Duplicate typed evidence keys')
    if sum(summary['by_status'].values()) != len(ctx.records):
        raise ValueError('Status reconciliation failed')
    for attr, schema in TABLES.values():
        pa.Table.from_pylist(getattr(ctx, attr), schema=schema).validate(full=True)
    return summary


def review_examples(ctx):
    """Select bounded, deterministic examples of distinct review flags without filtering the full data.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    list[dict]
        Deterministically selected review samples.
    """
    selected, seen = [], set()
    for predicate in [lambda r: True, lambda r: r['species_group'] == 'mouse',
                      lambda r: 'N02_complex_representation' in r['review_reasons'],
                      lambda r: 'N03_nonprotein_or_proxy' in r['review_reasons'],
                      lambda r: r['status'] == 'excluded', lambda r: 'unresolved_identifier' in r['review_reasons'],
                      lambda r: r['species_group'] in ('cross_species', 'mixed_species', 'unknown_species')]:
        count = 0
        for row in ctx.records:
            if predicate(row) and row['record_key'] not in seen:
                selected.append(row)
                seen.add(row['record_key'])
                count += 1
                if count == 3:
                    break
    return selected


def run_source(source_id, acquisition, manifest):
    """Normalize and validate one source in a staging directory before replacing derived tables.
    On failure, restore its prior tables and record the failed attempt in the manifest.
    
    Parameters
    ----------
    source_id : str
        One registered provider identifier.
    acquisition : dict
        Raw asset manifest with selections and checksums.
    manifest : dict
        Recorded source selections, checksums and processing state.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    
    Raises
    ------
    OSError
        If failure metadata cannot be written or filesystem recovery itself fails.
    
    Notes
    -----
    Input/validation errors are caught and recorded as a failed source attempt;
    previous tables are restored where promotion had started.
    """
    source = acquisition['sources'][source_id]
    inputs = [{k: f.get(k) for k in ['path', 'size', 'sha256', 'species', 'provenance']} for f in source['files']]
    previous = manifest['sources'].get(source_id)
    try:
        for f in inputs:
            path = RAW / f['path']
            if not path.is_file() or file_hash(path) != f['sha256'] or path.stat().st_size != f['size']:
                raise ValueError('Missing or checksum-mismatched local input: ' + f['path'])
        ctx = normalize(source_id, source)
        summary = validate(ctx)
        with tempfile.TemporaryDirectory(prefix='.normalize-', dir=BASE) as temporary:
            stage = Path(temporary)
            outputs = []
            for name, (attr, schema) in TABLES.items():
                table = pa.Table.from_pylist(getattr(ctx, attr), schema=schema)
                path = stage / (name + '.parquet')
                pq.write_table(table, path, compression='zstd')
                reread = pq.read_table(path)
                reread.validate(full=True)
                if not table.equals(reread):
                    raise ValueError('Parquet roundtrip changed values: ' + name)
                outputs.append({'path': source_id + '/' + path.name, 'rows': len(table), 'sha256': file_hash(path),
                                'semantic_sha256': __import__('hashlib').sha256(js(table.to_pylist()).encode()).hexdigest()})
            sample = review_examples(ctx)
            fields = [f for f in RECORD_SCHEMA.names if f != 'raw_json']
            with (stage / 'review_examples.tsv').open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fields, delimiter='\t', lineterminator='\n')
                writer.writeheader()
                for record in sample:
                    writer.writerow({k: js(record[k]) if isinstance(record[k], list) else record[k] for k in fields})
            outputs.append({'path': source_id + '/review_examples.tsv', 'rows': len(sample), 'sha256': file_hash(stage / 'review_examples.tsv')})
            # A source only counts as successful after input re-verification and all output validation.
            for f in inputs:
                if file_hash(RAW / f['path']) != f['sha256']:
                    raise ValueError('Input changed during normalization: ' + f['path'])
            target, backup = BASE / source_id, BASE / ('.' + source_id + '.backup')
            if backup.exists():
                raise ValueError('Inspect interrupted normalization backup before retrying: ' + str(backup))
            if target.exists():
                target.rename(backup)
            try:
                target.mkdir()
                for p in stage.iterdir():
                    shutil.move(str(p), target / p.name)
                entry = {'status': 'success', 'inputs': inputs, 'acquisition_selection': source.get('selection'),
                         'source_citation': source.get('citation_url'), 'schema_version': SCHEMA_VERSION,
                         'adapter_version': ADAPTER_VERSION, 'summary': summary, 'inventory': ctx.inventory,
                         'implementation': manifest.get('implementation'),
                         'limitations': sorted(set(ctx.limitations)), 'outputs': outputs,
                         'examples': [{k: r[k] for k in ['record_key', 'source_file', 'source_table', 'source_row', 'ligand_label', 'receptor_label',
                                                        'ligand_type', 'receptor_type', 'species_group', 'review_reasons', 'status']} for r in sample]}
                manifest['sources'][source_id] = entry
                atomic_json(BASE / 'manifest.json', manifest)
            except Exception:
                if target.exists():
                    remove_tree(target)
                if backup.exists():
                    backup.rename(target)
                raise
            if backup.exists():
                remove_tree(backup)
        print(f"  success: {summary['normalized_records']:,} records; {summary['distinct_semantic_interactions']:,} semantic interactions", flush=True)
    except Exception as exc:
        manifest['sources'][source_id] = {'status': 'failed', 'error': f'{type(exc).__name__}: {exc}', 'attempted_inputs': inputs,
                                        'previous_success': previous if previous and previous.get('status') == 'success' else None}
        atomic_json(BASE / 'manifest.json', manifest)
        print('  FAILED: ' + manifest['sources'][source_id]['error'], flush=True)


def main():
    """Parse command-line options and execute this module workflow with its documented safety checks.
    
    Returns
    -------
    int or None
        Nonzero status on explicitly handled workflow failure; otherwise success.
    
    Raises
    ------
    ValueError
        If the acquisition manifest changes while normalization is running.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=SOURCE_IDS, action='append')
    parser.add_argument('--report', action='store_true', help='Regenerate the review report from current derived manifest')
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    lock = BASE / '.normalize.lock'
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(descriptor)
    except FileExistsError:
        parser.error('Normalization lock exists; confirm no run is active before removing a stale lock')
    try:
        path = RAW / 'versions.txt'
        log_hash = file_hash(path)
        acquisition = json.loads(path.read_text(encoding='utf-8'))
        old_manifest = BASE / 'manifest.json'
        manifest = json.loads(old_manifest.read_text(encoding='utf-8')) if old_manifest.exists() else {'sources': {}}
        manifest.update(schema_version=SCHEMA_VERSION, adapter_version=ADAPTER_VERSION,
                        acquisition_manifest_sha256=log_hash,
                        implementation={p.name: file_hash(p) for p in [Path(__file__), ROOT / 'scripts/normalization_core.py', ROOT / 'scripts/source_normalizers.py']},
                        dependencies={name: importlib.metadata.version(name) for name in ['pandas', 'numpy', 'pyarrow', 'rdata', 'xlrd', 'openpyxl']})
        for source_id in args.source or SOURCE_IDS:
            print('Normalizing ' + source_id + '...', flush=True)
            run_source(source_id, acquisition, manifest)
        if file_hash(path) != log_hash:
            raise ValueError('Acquisition manifest changed during run')
        if args.report:
            from normalization_report import write_report
            write_report(manifest)
        failures = [s for s in args.source or SOURCE_IDS if manifest['sources'][s]['status'] != 'success']
        print(f'{len(args.source or SOURCE_IDS) - len(failures)}/{len(args.source or SOURCE_IDS)} requested sources normalized; failures: {failures}', flush=True)
        return bool(failures)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
