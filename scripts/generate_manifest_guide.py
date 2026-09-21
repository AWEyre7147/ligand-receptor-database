"""Generate/check operational manifest field coverage without changing provenance."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
from normalization_core import ROOT

FILES=['data/sources/versions.txt','data/interim/manifest.json','data/processed/build-manifest.json']
MEANINGS={
'schema_version':'Version of this manifest/table contract; versions from different workflow stages are not interchangeable.',
'adapter_version':'Version of normalization adapter interpretation.',
'acquisition_manifest_sha256':'SHA-256 of the complete acquisition log consumed by normalization.',
'policy_sha256':'SHA-256 of the accepted scientific policy note used for the build.',
'implementation':'Filename-to-SHA-256 map of implementation inputs; comments affect these hashes.',
'dependencies':'Package-name-to-installed-version map; direct dependencies only, not a full environment lock.',
'sources':'Per-source state map, or list of sources requested in a run.',
'last_run':'Start/end and requested-source metadata for the latest acquisition invocation.',
'started':'UTC ISO-8601 run start time.', 'finished':'UTC ISO-8601 run completion time.',
'name':'Provider display name.', 'provider':'Official provider URL or source attribution, according to enclosing object.',
'citation_url':'Dataset-level citation URL, not interaction evidence.', 'terms_url':'Provider terms/documentation URL; not a grant of redistribution rights.',
'coverage':'Provider-declared species availability.', 'notes':'Human-readable acquisition or provenance limitations.',
'aliases':'Alternative source spellings recognized in documentation.', 'redistribution':'Recorded restriction or unresolved terms warning.',
'latest_attempt':'UTC time of latest acquisition attempt, successful or otherwise.',
'status':'Workflow state in its enclosing context. Acquisition can be blocked while preserved files remain usable; normalized/build success means local checks passed.',
'error':'Recorded failed-attempt error; null means no recorded error for that attempt.',
'content_change':'Whether valid source payload bytes changed, separately from a failed or unchanged check.',
'attempted_selection':'Version metadata discovered for the latest attempted download, not necessarily promoted.',
'selection':'Promoted source selection associated with retained files.',
'acquisition_selection':'Copy of the acquisition selection consumed by normalization.',
'repository':'Official owner/repository name.', 'release':'Selected official release tag; null when a commit or unversioned endpoint is used.',
'commit':'Immutable Git commit SHA used for original assets.', 'selection_policy':'Rule choosing release, commit or endpoint; not a biological eligibility rule.',
'files':'Original acquisition asset records with path, size, checksums and provenance.',
'path':'File path: acquisition/intermediate paths are relative to their data root; build input paths may be absolute local paths and must be reviewed before publication; output paths are release-relative.',
'sha256':'SHA-256 of exact file bytes, distinct from semantic row hashes.',
'size':'Exact original payload size in bytes.', 'download_url':'Resolved asset download URL without credentials.',
'reported_download_url':'Provider-reported location preserved during manual import.',
'upstream_checksum':'Provider checksum or recorded Git blob/commit reference, when supplied.',
'upstream_version':'Provider release, version or endpoint metadata, not an independently inferred version.',
'etag':'HTTP cache validator, when provided; not treated as a content hash.',
'last_modified':'HTTP Last-Modified metadata, when provided; not proof of biological data age.',
'last_download':'UTC timestamp of successful acquisition of this asset.',
'last_successful_check':'UTC time a source check last succeeded.',
'last_successful_download':'UTC time the source payload set last downloaded successfully.',
'changed_files':'Original file paths whose valid bytes changed in this attempt.',
'downloaded_files':'Original file paths downloaded in this attempt.',
'removed_files':'Old selected asset paths no longer present in the newly promoted selection.',
'repaired_files':'Local missing/corrupt asset paths restored from verified upstream bytes.',
'manual_import':'Explicit metadata describing authorized original files imported outside the downloader.',
'imported_at':'UTC manual-import timestamp.', 'method':'Recorded import/acquisition method.',
'original_filename':'Unmodified filename supplied by the provider.',
'automated_access_status':'Result of automated provider access, separate from locally usable manual imports.',
'automated_refresh':'Whether automated refresh is currently supported/blocked and why.',
'data_version':'Provider data version or explicit unversioned-endpoint limitation.',
'discovery_url':'Official page used to discover original files.',
'discovery_method':'How the selected immutable version was resolved.',
'catalog_dates':'Provider catalog timestamps retained without replacing them with local retrieval times.',
'publication_date':'Provider publication/release date, when supplied.',
'doi':'Provider dataset DOI.', 'zenodo_record':'Official Zenodo record identifier.',
'distribution':'Original distribution or download container selected.',
'archive_member':'Original member path inside a downloaded publication archive.',
'source_page':'Official landing page for manual import/discovery.',
'version_evidence':'Provider page/file evidence supporting the claimed version.',
'version':'Provider version; null means no explicit version supplied.',
'query_parameters':'Exact provider query parameters; academic access is not a redistribution license.',
'organisms':'Provider-requested taxon identifiers, without local conversion.',
'license':'Provider query license filter, not a blanket license on all derived results.',
'format':'Requested original transport format.', 'fields':'Requested provider response columns.',
'genesymbols':'Provider query option requesting gene labels.',
'datasets':'Provider query dataset selection.', 'service':'Provider API/service endpoint.',
'inputs':'Paths and checksums consumed by this stage.',
'outputs':'Paths, byte hashes and where applicable rows/semantic hashes produced by this stage.',
'semantic_sha256':'Hash of canonical typed rows (or ordered workbook sheet digests), independent of XLSX ZIP timestamps.',
'source_citation':'Copied provider citation URL from acquisition metadata.',
'summary':'Per-source normalization totals and overlapping classifications; no cross-source merging.',
'inventory':'All original interaction/support tables inspected, including unused support assets.',
'file':'Original source asset location recorded during inventory.',
'table':'Worksheet or nested R object; empty means a flat/default table.',
'rows':'Number of records in this specific source/output table, excluding the header.',
'columns':'Exact source column names, retaining source spelling.',
'release_comments':'Leading source release/comment lines removed before tabular parsing and retained here.',
'role':'Inventory interaction/support role, distinct from regulator biological roles.',
'header_zero_based':'Zero-based header row used when reading the original table.',
'examples':'Bounded deterministic review examples; not the complete review data.',
'raw_interaction_records':'Count of inventoried original interaction rows.',
'normalized_records':'Count of retained normalized records.',
'distinct_semantic_interactions':'Count of source-local semantic keys, not final merged interaction IDs.',
'repeated_records_beyond_distinct':'Normalized records minus distinct source-local semantic keys.',
'dropped_records':'Number of original assertions dropped; required to remain zero.',
'expanded_interaction_records':'Number of original records expanded into extra pairs; required to remain zero.',
'by_species':'Counts by species agreement classification.', 'by_status':'Counts by normalization candidate/review/excluded state.',
'by_provenance':'Counts by provider evidence provenance label.', 'by_orientation':'Counts by source ordering interpretation.',
'ligand_types':'Counts by normalized ligand entity class.',
'distinct_by_species':'Distinct source-local semantic keys in each species group.',
'candidate_distinct_by_species':'Distinct semantic keys with at least one candidate record.',
'review_distinct_by_species':'Distinct semantic keys with at least one review record; can overlap candidate keys.',
'nonexcluded_distinct_by_species':'Union of nonexcluded semantic keys, avoiding addition of overlapping status subsets.',
'unresolved_records':'Records flagged with unresolved_identifier.',
'nonexcluded_unresolved_records':'Unresolved records outside explicit exclusions.',
'unverified_symbol_records':'Records with at least one endpoint using an unverified literal source symbol.',
'complex_records':'Records with at least one source complex endpoint.',
'complex_interactions':'Distinct source-local semantic keys involving a complex.',
'multisubunit_records':'Records whose source definition has multiple required members.',
'multisubunit_interactions':'Distinct source-local semantic keys involving multiple required members.',
'nonprotein_proxy_records':'Records with the normalized N03 nonprotein/proxy review flag.',
'nonprotein_proxy_interactions':'Distinct source-local semantic keys carrying that flag.',
'evidence_rows':'Number of typed evidence rows retained, including nonpublication evidence.',
'membership_rows':'Number of source or canonical membership rows at the enclosing workflow stage.',
'regulator_rows':'Number of retained optional regulator-member rows.',
'review_reason_counts':'Overlapping per-flag record counts; do not sum as distinct records.',
'exclusion_reason_counts':'Overlapping exclusion-flag record counts.',
'annotation_version':'Version identifiers for the separate same-species identity reference.',
'run_id':'Reference-build identifier, not this repository build timestamp.',
'counts':'Validated final totals by species/disposition and supporting-table type.',
'assertions':'All normalized records, each with exactly one final disposition.',
'by_disposition':'Counts of primary, companion, review, excluded and provenance_only assertions.',
'primary':'Distinct eligible primary interaction IDs for this species.',
'companion':'Distinct eligible nonprotein/proxy interaction IDs for this species.',
'checks':'Named scientific/table reconciliation checks passed by validation.',
'validation':'Recorded test, repeat, Excel and optional protected-input results.',
'unit_tests':'Passed unit-test count (build) or status/count object (normalization validator).',
'repeat_semantic_determinism':'passed when a second canonical build matched all semantic digests; otherwise not requested.',
'excel_parquet':'Per-species full-workbook comparison results.',
'cells_compared':'Number of exported data cells decoded and compared with canonical values.',
'sheets':'Number of validated Excel worksheets.',
'protected_files':'Count/status of caller-supplied protected path hashes checked; scope is limited to that baseline.',
'count':'Number of items in the enclosing validation result.',
'scope':'Human-readable description of validation coverage.',
'previews':'Whether optional sample PNGs were rendered or explicitly skipped.',
'preview_rows':'Bounded source-table preview rows/cells retained for inspection, not the complete table.',
'previous_success':'Prior successful normalization metadata retained after a failed attempt.',
'attempted_inputs':'Inputs observed for a failed normalization attempt.',
}
DYNAMIC={'sources':'<source>', 'implementation':'<filename>', 'dependencies':'<package>', 'species':'<species>', 'excel_parquet':'<species>',
         'catalog_dates':'<asset>', 'checks':'<check>'}
DYNAMIC.update({k:'<label>' for k in ['by_species','by_status','by_provenance','by_orientation','ligand_types','distinct_by_species','candidate_distinct_by_species','review_distinct_by_species','nonexcluded_distinct_by_species','review_reason_counts','exclusion_reason_counts','by_disposition']})

# =============================================================================
# Exhaustive nested metadata coverage
# =============================================================================

def field_paths(value: object, path: str = '', parent: str = '') -> dict:
    """Inventory all observed object/list paths, collapsing named map keys explicitly.

    Parameters
    ----------
    value : object
        Parsed JSON metadata.
    path : str
        Current dotted field path; empty at the manifest root.
    parent : str
        Original enclosing key used to identify a variable-key map.

    Returns
    -------
    dict
        Path-to-observed-JSON-type-set mapping, including containers and nulls.
    """
    result=defaultdict(set)
    if path: result[path].add(type(value).__name__)
    if isinstance(value,dict):
        for key,item in value.items():
            label=DYNAMIC.get(parent,key)
            if label==key and key.endswith(('.csv','.tsv','.txt','.xlsx','.xls','.rds','.rda')): label='<asset>'
            child=path+'.'+label if path else label
            for k,types in field_paths(item,child,key).items(): result[k].update(types)
    elif isinstance(value,list):
        for item in value:
            for k,types in field_paths(item,path+'[*]',parent).items(): result[k].update(types)
    return result


def render() -> str:
    """Render exact manifest field paths with curated operational meanings.

    Returns
    -------
    str
        Markdown field reference for all three current manifests.

    Raises
    ------
    AssertionError
        If an observed field has no explicit maintained explanation.
    """
    fields=json.loads((ROOT/'config/field-guide.json').read_text(encoding='utf-8'))['fields']
    lines=['# Manifest reference','','Generated by [generate_manifest_guide.py](../scripts/generate_manifest_guide.py), whose maintained explanations are checked against all current nested fields. These are operational metadata, not biological table columns. `[*]` means an array element; `<source>`, `<filename>`, `<package>`, `<species>`, `<asset>`, `<label>` and `<check>` denote variable map keys. Types are observed JSON/Python representations (`dict` object, `list` array, `str` text, `int` integer, `bool` boolean, `NoneType` null).','','A missing key is unrecorded for that workflow/provider/version. A present null is unavailable or not applicable; metadata does not consistently distinguish those states. Empty arrays/maps mean no recorded entries, not necessarily absence of biological evidence. Status labels are interpreted within their enclosing workflow. Timestamps are UTC strings where recorded; sizes are bytes; row/cell/count metrics are integers. Checksums are hexadecimal SHA-256 unless an upstream checksum explicitly carries a different prefix.','','Do not hand-edit hashes after changing code: use supported regeneration and validation. Build inputs currently include local absolute paths; these are provenance, not portable download instructions, and require privacy review before publication. See [Script guide](Script%20guide.md) and the [field guide](Database%20dictionary.md).','']
    for filename in FILES:
        paths=field_paths(json.loads((ROOT/filename).read_text(encoding='utf-8')))
        lines+=['## '+filename,'','| Exact nested path | Observed types | Meaning |','|---|---|---|']
        for path,types in sorted(paths.items()):
            leaf=path.split('.')[-1].replace('[*]','')
            if leaf.startswith('<'):
                parent=path.rsplit('.',1)[0].split('.')[-1]
                meaning=MEANINGS.get(parent,fields.get(parent))
                if leaf=='<filename>': meaning='Implementation file byte SHA-256; file names are retained exactly in the manifest.'
                elif leaf=='<package>': meaning='Installed package version string.'
                elif leaf=='<source>': meaning='Metadata for one registered provider; each source remains independent.'
                elif leaf=='<species>': meaning='Per-species result object; human and mouse stay separate.'
                elif leaf=='<label>': meaning='Integer count for this observed category/flag. '+(meaning or '')
                elif leaf=='<asset>': meaning='Provider catalog date or manual-import validation metadata associated with the named original asset, according to the enclosing object.'
            else: meaning=MEANINGS.get(leaf,fields.get(leaf))
            assert meaning, 'Undocumented manifest field: '+path
            lines.append('| `'+path+'` | '+', '.join(sorted(types))+' | '+meaning+' |')
        lines+=['']
    return '\n'.join(lines)


def main() -> None:
    """Write the reference or compare it without altering manifests.

    Returns
    -------
    None
        Prints success; --check performs no writes.

    Raises
    ------
    AssertionError
        If checked documentation is stale or an observed field is undocumented.
    """
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(); path=ROOT/'docs/Manifest reference.md'; text=render()
    if args.check: assert path.read_text(encoding='utf-8')==text,'Manifest reference is stale'
    else: path.write_text(text,encoding='utf-8')
    print('All observed acquisition, normalization and build manifest fields documented.')


if __name__=='__main__':
    main()
