"""Build both databases offline; stage, validate, then promote the complete release."""
import argparse
from collections import Counter
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from database_build import *
from database_export import partitions, write_parquet, export_xlsx, validate_excel, render_previews
from database_excel import workbook_partitions, digest_workbook
from download_sources import atomic_json, remove_tree

OUTPUT = ROOT / 'data/processed'
IMPLEMENTATION = ['build_databases.py', 'database_build.py', 'database_identity.py', 'database_ids.py', 'database_export.py', 'database_excel.py', 'export_database_workbooks.mjs']


# =============================================================================
# Public workflow and supporting operations
# =============================================================================
def verification_plan(release_verification: bool, previews: bool) -> dict[str, bool]:
    """Select routine or explicit release-verification operations.

    Parameters
    ----------
    release_verification : bool
        Whether to run the expensive release checks after canonical assembly.
    previews : bool
        Whether to render optional bounded spreadsheet previews.

    Returns
    -------
    dict[str, bool]
        Named operations used by the build orchestration and focused tests.

    Raises
    ------
    ValueError
        If previews are requested outside explicit release verification.
    """
    if previews and not release_verification:
        raise ValueError('--previews requires --release-verification')
    return {
        'full_test_suite': release_verification,
        'repeat_assembly': release_verification,
        'excel_parquet_parity': release_verification,
        'previews': previews,
    }


def verify_hashes(inputs):
    """Detect any input mutation between the beginning and end of the offline build.
    
    Parameters
    ----------
    inputs : list[dict]
        Input paths and expected SHA-256 digests.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    
    Raises
    ------
    ValueError
        If an input no longer matches its recorded build-start checksum.
    """
    for item in inputs:
        if file_hash(Path(item['path'])) != item['sha256']:
            raise ValueError('Input changed during build: ' + item['path'])


def promote(stage, output=OUTPUT):
    """Replace processed outputs only after validation, restoring the old directory on failure.
    
    Parameters
    ----------
    stage : Path
        Validated staged release directory under data.
    output : Path
        Destination artifact or release directory.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    
    Raises
    ------
    ValueError
        If paths escape the owned release directory or a prior backup needs inspection.
    """
    parent = (ROOT / 'data').resolve()
    stage, output = stage.resolve(), output.resolve()
    if stage.parent != parent or not stage.name.startswith('.processed-') or output != parent / 'processed':
        raise ValueError('Unsafe release directory')
    backup = parent / '.processed-backup'
    if backup.exists():
        raise ValueError('Unresolved prior backup: ' + str(backup))
    existed = output.exists()
    if existed:
        os.replace(output, backup)
    try:
        os.replace(stage, output)
    except BaseException:
        if existed:
            os.replace(backup, output)
        raise
    if existed:
        remove_tree(backup)


def report(tables, counts, validation, annotation_version):
    """Generate the final build report from verified counts and validation results.
    
    Parameters
    ----------
    tables : dict[str, list[dict]]
        Canonical tables or source inventory used by this operation.
    counts : dict
        Validated species/disposition and support totals.
    validation : dict
        Recorded test, parity and determinism outcomes.
    annotation_version : dict
        Version of the same-species reference assets.
    
    Returns
    -------
    str
        Markdown build report.
    """
    a = tables['assertions']
    lines = ['# Final database build', '',
             'Offline build applying [Accepted database policies](Accepted%20database%20policies.md) N01–N04. All 16 sources have a documented disposition. Original source assertions remain traceable; these outputs do not certify biological validation.', '',
             '| Species | Primary interactions | Nonprotein/proxy interactions | Review assertions | Excluded assertions |', '|---|---:|---:|---:|---:|']
    for sp in ('human', 'mouse'):
        c = counts['species'][sp]
        lines.append(f"| {sp} | {c['primary']:,} | {c['companion']:,} | {sum(r['species_group']==sp and r['disposition']=='review' for r in a):,} | {sum(r['species_group']==sp and r['disposition']=='excluded' for r in a):,} |")
    lines += ['', '| Species | Primary interactions with complexes | Distinct encoded-peptide ligands in primary interactions* | Primary interactions with unverified symbols | Companion ligand types |',
              '|---|---:|---:|---:|---|']
    for sp in ('human','mouse'):
        primary = [r for r in tables['interactions'] if r['species']==sp and r['tier']=='primary']
        companion = [r for r in tables['interactions'] if r['species']==sp and r['tier']=='companion']
        complexes = sum('complex' in (r['ligand_type'],r['receptor_type']) for r in primary)
        peptides = len({r['ligand_entity_id'] for r in primary if r['ligand_type']=='encoded_peptide'})
        unverified = sum('unverified_symbol_no_authoritative_match' in r['limitations'] for r in primary)
        types = ', '.join(f'{v:,} {k}' for k,v in sorted(Counter(r['ligand_type'] for r in companion).items()))
        lines.append(f'| {sp} | {complexes:,} | {peptides:,} | {unverified:,} | {types} |')
    lines += ['', '*Peptide count here is distinct ligand entities, not interaction rows. The current companions contain source-defined proxies; no molecule-only GtoPdb assertion passes all endogenous, identity, direction and same-species eligibility checks. Missing product identifiers are retained explicitly, not invented from proxy names.']
    lines += ['', f"All **{counts['assertions']:,} normalized assertions** reconcile: " + ', '.join(f'{v:,} {k}' for k,v in sorted(counts['by_disposition'].items())) + '. These are source records; primary/companion totals above are merged interactions.', '',
              '## Files and command', '',
              '- [Human Excel](../data/processed/Ligand-Receptor-Human-DB.xlsx) and [Human Parquet](../data/processed/Ligand-Receptor-Human-DB.parquet).',
              '- [Mouse Excel](../data/processed/Ligand-Receptor-Mouse-DB.xlsx) and [Mouse Parquet](../data/processed/Ligand-Receptor-Mouse-DB.parquet).',
              '- Excel follows the approved five-sheet templates. `Human-*` and `Mouse-*` Parquet files retain all companion/support/readme tables, including evidence, review and record-linked annotations omitted from Excel. Shared tables retain species-incompatible or unknown assertions separately.',
              '- [Build manifest](../data/processed/build-manifest.json) records input/policy/implementation hashes, versions, output checksums, counts and validation. See [Database dictionary](Database%20dictionary.md) for exact columns and joins.', '',
              '```powershell', '.venv/Scripts/python scripts/build_databases.py --annotation-dir "../gene-annotation-resources/annotations"', '```', '',
              'This routine command performs input, schema, identifier, relationship, policy, record-accounting and output-write checks. Add `--release-verification` for the full test suite, repeat canonical assembly and exhaustive Excel/Parquet parity; add `--previews` only when bounded layout rendering is also wanted. No additional Python dependencies, downloader, new annotation download or species conversion runs. A complete build is staged before replacing processed outputs. Failure preserves the prior release; unrelated processed files are copied through. A stale backup/lock requires inspection rather than automatic deletion.', '',
              '## Source contributions', '',
              'Counts below are distinct eligible interaction IDs per source. A pair may appear in several source rows; the columns must not be added as unique biological pairs. LIANA constituent memberships are retained as provenance only.', '',
              '| Source | Human primary | Mouse primary | Human companion | Mouse companion | Review | Excluded | Provenance only |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in SOURCE_IDS:
        rows = [r for r in a if r['source'] == s]
        values = [len({r['interaction_id'] for r in rows if r['species_group']==sp and r['disposition']==tier}) for tier in ('primary','companion') for sp in ('human','mouse')]
        values += [sum(r['disposition']==state for r in rows) for state in ('review','excluded','provenance_only')]
        lines.append('| ' + s + ' | ' + ' | '.join(f'{v:,}' for v in values) + ' |')
    shared = [r for r in a if r['species_group'] not in ('human','mouse')]
    lines += ['', f"Shared outputs contain **{len(shared):,} assertions**: " + ', '.join(f'{v:,} {k}' for k,v in sorted(Counter(r['species_group'] for r in shared).items())) + '.', '',
              '## Applied identity and evidence rules', '',
              '- Source lookups precede same-species annotation mappings. The local annotation run `' + str(annotation_version['run_id']) + '` is used only for identity columns (NCBI Gene, HGNC/MGI, UniProt, Ensembl, exact symbols/aliases and taxon). Its human/mouse files and manifest hashes are recorded. Orthology columns are never read. No enrichment columns are added.',
              '- Stable identifiers map to a unique same-species NCBI Gene identity. Conflicting identifier/symbol mappings or ambiguous aliases remain review. Unmapped literal symbols use exact case-sensitive identities, carry an explicit unverified limitation, and cannot merge with stable identities without a mapping. Unverified symbols are not allowed to establish complex-member completeness.',
              '- Complete complexes merge only on resolved members, dependency roles, known stoichiometry and incompatible assembly context. Unknown stoichiometry remains unknown. CellPhoneDB semicolon stoichiometry lists are counted only when their complete set matches endpoint members; ligand-bound assembly context otherwise stays separate. Full explicit definition lists are checked, not merely the presence of membership rows.',
              '- Endogenous GtoPdb peptides retain their molecular ligand identity and an `encoded_by` gene relationship, preventing collapse of distinct mature peptides/proteoforms into one precursor. Receptor classes are restricted to source `gpcr`, `catalytic_receptor`, `lgic` and `nhr`; other pharmacology classes stay review. GtoPdb subunit lists can describe alternative families (e.g. BMP receptors), not obligate complexes. Receptor lists require an identical complete gene set in an explicit local non-GtoPdb complex definition, linked by `supporting_definition_ids`; single-subunit lists remain review. This tightens interpretation at final disposition without editing the normalized inputs; `Source-Members` retains their original membership assertions without endorsing their roles.',
              '- Explicit source proxies retain their source entity identity, dependency roles and a missing-product annotation. Enzymes are never renamed as their products. CellChat regulators remain separate from complex members. Pavlicev and description-only possible enzyme proxies remain review.',
              '- Eligible provider-derived mouse evidence is accepted and labeled inferred. Unknown provenance remains unknown. `native_reported` means a provider assertion, not independently verified experimental evidence. Per-record labels remain in Assertions even when a merged interaction has multiple labels.',
              '- Only eligible assertions contribute to source/publication/sign summaries. Putative, excluded, unresolved and LIANA constituent assertions can have `related_interaction_id` links without becoming support. Missing references alone do not exclude an interaction. Aggregator/source overlap is exposed and not scored as independent replication.', '',
              '## Unresolved limitations', '',
              '| Reason (overlapping counts) | Assertions |', '|---|---:|']
    reasons = Counter(reason for r in a if r['disposition']=='review' for reason in r['reasons'])
    for reason, number in reasons.most_common():
        lines.append(f'| `{reason}` | {number:,} |')
    eligible_mouse = [r for r in a if r['species_group']=='mouse' and r['disposition'] in ('primary','companion')]
    parity = validation['excel_parquet']
    parity_text = ('every template-projected Excel cell compared with its canonical Parquet value after display serialization'
                   if all(v.get('status') == 'passed' for v in parity.values()) else 'not run in routine mode')
    test_text = (str(validation['unit_tests']) + ' tests passed' if isinstance(validation['unit_tests'], int)
                 else str(validation['unit_tests']))
    lines += ['', 'Eligible mouse source-assertion provenance: ' + ', '.join(f'{v:,} {k}' for k,v in sorted(Counter(r['evidence_provenance'] for r in eligible_mouse).items())) + '.', '',
              'OmniPath mouse orientation remains unresolved and contributes no automatic mouse support. Pavlicev S5 cannot be divided reliably into proteins and proxies using its local per-row fields. GtoPdb missing/multispecies ligand metadata is not filled from target species; synthetic/nonendogenous rows remain auditable exclusions. Source symbol aliases, incomplete complexes and conflicting metadata remain explicit. No online acquisition issue blocked this offline build.', '',
              '## Validation', '',
              '- Build mode: ' + validation['mode'] + '.',
              '- Full test suite: ' + test_text + '.',
              '- Excel/Parquet exhaustive parity: ' + parity_text + '.',
              '- All normalized records have one disposition; every evidence, regulator and source-annotation row is retained; source totals, schemas, keys and joins reconcile.',
              '- Repeat canonical-build semantic determinism: ' + validation['repeat_semantic_determinism'] + '.',
              '- Input checksums verified before and after the build. Protected input/historical/intermediate/vault snapshot: ' + str(validation.get('protected_files', 'not supplied')) + '.',
              '- Workbook output writing completed. Template headers and sheet structure are checked during exhaustive projection parity. Optional preview status: ' + str(validation.get('previews', 'not recorded')) + '. Detailed evidence remains in Parquet; displayed values exceeding Excel limits fail rather than being truncated.', '']
    return '\n'.join(lines)


def main():
    """Parse command-line options and execute this module workflow with its documented safety checks.
    
    Returns
    -------
    int or None
        Nonzero status on explicitly handled workflow failure; otherwise success.
    
    Raises
    ------
    ValueError
        If an explicit release-verification test run fails; other input/export
        and integrity errors propagate.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-verification', action='store_true', help='Run the full test suite, repeat canonical assembly and exhaustive Excel/Parquet parity')
    parser.add_argument('--previews', action='store_true', help='Render bounded spreadsheet previews during explicit release verification')
    parser.add_argument('--protected-baseline', type=Path)
    parser.add_argument('--node')
    parser.add_argument('--annotation-dir', type=Path, help='Directory containing the pinned annotation manifest and Parquet/human.parquet and mouse.parquet')
    args = parser.parse_args()
    plan = verification_plan(args.release_verification, args.previews)
    work = ROOT / '.build-work'
    work.mkdir(exist_ok=True)
    (work / '.gitignore').write_text('*\n')
    lock = work / 'build.lock'
    with lock.open('x') as f:
        f.write(str(os.getpid()))
    stage = None
    try:
        tables, inputs, annotation_version, normalized = make_tables(args.annotation_dir)
        counts = validate_tables(tables, normalized)
        repeat = 'not run in routine mode'
        if plan['repeat_assembly']:
            again, again_inputs, _, _ = make_tables(args.annotation_dir)
            assert inputs == again_inputs, 'Repeat inputs changed'
            assert {n:digest_table(v,n) for n,v in tables.items()} == {n:digest_table(v,n) for n,v in again.items()}, 'Repeat semantics changed'
            del again
            repeat = 'passed'
        unit_tests = 'not run in routine mode'
        if plan['full_test_suite']:
            test = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, capture_output=True, text=True)
            if test.returncode:
                raise ValueError(test.stdout + test.stderr)
            import re
            unit_tests = int(re.search(r'Ran (\d+) tests', test.stderr)[1])
        validation = {'mode': 'release' if args.release_verification else 'routine', 'unit_tests': unit_tests,
                      'repeat_semantic_determinism': repeat, 'excel_parquet': {}}
        stage = Path(tempfile.mkdtemp(prefix='.processed-', dir=ROOT / 'data'))
        if OUTPUT.exists():
            shutil.copytree(OUTPUT, stage, dirs_exist_ok=True)
        pieces = partitions(tables)
        excel_pieces, template_inputs = workbook_partitions(pieces, SCHEMAS)
        inputs.extend(template_inputs)
        outputs = write_parquet(pieces, stage)
        for sp in ('mouse', 'human'):
            path = stage / ('Ligand-Receptor-' + sp.title() + '-DB.xlsx')
            export_xlsx(excel_pieces[sp], path, work / 'excel', sp, args.node)
            validation['excel_parquet'][sp] = validate_excel(path, excel_pieces[sp]) if plan['excel_parquet_parity'] else {'status': 'not run in routine mode'}
            if plan['previews']:
                render_previews(excel_pieces[sp], work / 'excel', sp, args.node)
            outputs.append({'path': path.name, 'sha256': file_hash(path),
                            'semantic_sha256': digest_workbook(excel_pieces[sp])})
        validation['previews'] = 'rendered' if plan['previews'] else 'not requested'
        verify_hashes(inputs)
        if args.protected_baseline:
            baseline = json.loads(args.protected_baseline.read_text(encoding='utf-8'))
            for p, h in baseline.items():
                assert file_hash(ROOT / p) == h, 'Protected file changed: ' + p
            validation['protected_files'] = {'count': len(baseline), 'status': 'unchanged'}
        build = {'status': 'success', 'schema_version': VERSION, 'policy_sha256': file_hash(POLICY), 'inputs': inputs,
                 'identifier_policy': {'scope': 'release-local; all species before partitioning',
                                       'format': 'PREFIX-000001 (six-digit minimum)',
                                       'ordering': 'sorted canonical keys; numbering may change in later releases',
                                       'normalized_keys': 'preserved alongside readable record_id and evidence_id'},
                 'annotation_version': annotation_version, 'implementation': {n:file_hash(ROOT / 'scripts' / n) for n in IMPLEMENTATION},
                 'dependencies': {n:importlib.metadata.version(n) for n in ('pandas','numpy','pyarrow','openpyxl','rdata')},
                 'counts': counts, 'validation': validation, 'outputs': outputs}
        atomic_json(stage / 'build-manifest.json', build)
        report_text = report(tables, counts, validation, annotation_version)
        promote(stage)
        stage = None
        report_path = ROOT / 'docs/archived/Final database build.md'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding='utf-8')
        print(json.dumps({'counts': counts, 'validation': validation}, indent=2), flush=True)
    finally:
        lock.unlink(missing_ok=True)
        if stage and stage.exists():
            assert stage.resolve().parent == (ROOT / 'data').resolve() and stage.name.startswith('.processed-')
            remove_tree(stage)


if __name__ == '__main__':
    main()
