"""Validate exported hashes, joins and exact source-support/annotation retention."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import pyarrow.parquet as pq
from database_build import ROOT, INTERIM, SOURCE_IDS, extract_source_annotations, file_hash, validate_tables, js

# =============================================================================
# Independent post-export verification
# =============================================================================

def main() -> None:
    """Check the current release independently of in-memory export validation.

    Returns
    -------
    None
        Prints success after all recorded hashes and source-support rows reconcile.

    Raises
    ------
    AssertionError
        If output bytes, implementation provenance, joins or retained rows differ.
    OSError
        If a required local release or input file is unavailable.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protected-baseline', type=Path, help='Optional root-relative path-to-byte-SHA256 map')
    parser.add_argument('--semantic-baseline', type=Path, help='Optional root-relative Parquet path-to-canonical-row-SHA256 map')
    parser.add_argument('--report', type=Path, help='Optional JSON verification report destination')
    args = parser.parse_args()
    verification = {'release_hashes_and_source_retention': 'passed'}
    for flag, semantic in [(args.protected_baseline, False), (args.semantic_baseline, True)]:
        if flag:
            baseline = json.loads(flag.read_text(encoding='utf-8'))
            for relative, expected in baseline.items():
                path = ROOT / relative.replace('\\', '/')
                actual = hashlib.sha256(js(pq.read_table(path).to_pylist()).encode()).hexdigest() if semantic else file_hash(path)
                assert actual == expected, 'Baseline changed: ' + relative
            verification['semantic_tables' if semantic else 'protected_files'] = {'count': len(baseline), 'status': 'unchanged'}
    d=ROOT / 'data/processed'
    m=json.loads((d/'build-manifest.json').read_text(encoding='utf-8'))
    for f in m['outputs']:
        assert file_hash(d/f['path'])==f['sha256'], f['path']
    for name,h in m['implementation'].items():
        assert file_hash(ROOT/'scripts'/name)==h, name
    for f in m['inputs']:
        assert file_hash(Path(f['path']))==f['sha256'], f['path']
    tables={}
    names={'assertions':'Assertions','evidence':'Evidence','source_members':'Source-Members','source_annotations':'Source-Annotations','entities':'Entities','definitions':'Complex-Definitions','memberships':'Complex-Members','regulators':'Regulators'}
    for k,suffix in names.items():
        prefixes=['Human','Mouse','Shared'] if k in ('assertions','evidence','source_members','source_annotations') else ['Human','Mouse']
        tables[k]=[r for prefix in prefixes for r in pq.read_table(d/(prefix+'-'+suffix+'.parquet')).to_pylist()]
    tables['interactions']=[r for prefix in ['Human','Mouse'] for filename in ['Ligand-Receptor-'+prefix+'-DB.parquet',prefix+'-Nonprotein-Proxy.parquet'] for r in pq.read_table(d/filename).to_pylist()]
    tables['sources']=pq.read_table(d/'Human-Sources.parquet').to_pylist()
    tables['readme']=[]
    normal=json.loads((INTERIM/'manifest.json').read_text(encoding='utf-8'))
    assert validate_tables(tables,normal)==m['counts']
    entity_ids={e['entity_id'] for e in tables['entities']}
    definition_ids={e['definition_id'] for e in tables['definitions']}
    for x in tables['source_members']:
        assert not x['entity_id'] or x['entity_id'] in entity_ids
        assert not x['definition_id'] or x['definition_id'] in definition_ids
    for x in tables['definitions']:
        assert x['entity_id'] in entity_ids
    for x in tables['regulators']:
        assert not x['member_entity_id'] or x['member_entity_id'] in entity_ids
    for source in SOURCE_IDS:
        for name, finalname in [('evidence','evidence'),('memberships','source_members'),('regulators','regulators')]:
            original=pq.read_table(INTERIM/source/(name+'.parquet'))
            rows=[r for r in tables[finalname] if r.get('source')==source] if name!='regulators' else [r for r in tables[finalname] if r['source_file'].startswith(source+'/')]
            assert Counter(js({k:r[k] for k in original.column_names}) for r in rows)==Counter(js(r) for r in original.to_pylist()), (source,name)
    assertions = {row['record_key']: row for row in tables['assertions']}
    expected_annotations = []
    for source in SOURCE_IDS:
        for record in pq.read_table(INTERIM/source/'records.parquet').to_pylist():
            expected_annotations.extend(extract_source_annotations(record, assertions[record['record_key']]))
    # Reconstruct display numbers from the original normalized keys, rather than
    # accepting exported annotation/record IDs as evidence of their correctness.
    record_ids = {key: f'AST-{n:06d}' for n, key in enumerate(sorted(assertions), 1)}
    annotation_ids = {key: f'ANN-{n:06d}' for n, key in enumerate(
        sorted(row['annotation_id'] for row in expected_annotations), 1)}
    for row in expected_annotations:
        row['annotation_id'] = annotation_ids[row['annotation_id']]
        row['record_id'] = record_ids[row['record_key']]
    assert Counter(js(row) for row in tables['source_annotations']) == Counter(js(row) for row in expected_annotations)
    verification['counts'] = m['counts']
    verification['build_validation'] = m['validation']
    if args.report:
        args.report.write_text(json.dumps(verification, indent=2) + '\n', encoding='utf-8')
    print('Release hashes, counts, joins and exact source evidence/member/regulator/annotation retention passed.')


if __name__ == '__main__':
    main()
