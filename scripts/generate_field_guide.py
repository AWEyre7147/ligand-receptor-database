"""Generate/check the authoritative field guide from curated descriptions and local schemas."""
from __future__ import annotations
import argparse
import ast
from collections import defaultdict
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from database_build import SCHEMAS, ROOT
from normalize_sources import TABLES
from normalization_core import SOURCE_IDS

SUFFIXES = {'Nonprotein-Proxy':'interactions', 'Assertions':'assertions', 'Review':'assertions', 'Evidence':'evidence',
            'Entities':'entities','Complex-Members':'memberships','Complex-Definitions':'definitions','Regulators':'regulators',
            'Sources':'sources','Source-Members':'source_members','Source-Annotations':'source_annotations','Readme':'readme'}
ENUM_FIELDS = set('source sources species species_group dataset_species dataset_provenance evidence_provenance provenance disposition status tier sign_summary orientation sign_basis entity_type ligand_type receptor_type ligand_mapping receptor_mapping mapping_basis mapping_status relationship role namespace ligand_namespace receptor_namespace type completeness acquisition_status original_role_a original_role_b species_basis reasons review_reasons exclusion_reasons normalized_review_reasons limitations'.split())

# =============================================================================
# Schema inventory and reproducible documentation
# =============================================================================

def inventory() -> dict:
    """Read every final/intermediate table, including zero-row tables.

    Returns
    -------
    dict
        Logical schema groups with physical paths, typed fields and actual rows.

    Raises
    ------
    AssertionError
        If an exported or normalized table differs from its implementation schema.
    """
    groups = {}
    for path in sorted((ROOT / 'data/processed').glob('*.parquet')):
        name = 'interactions' if path.stem.startswith('Ligand-Receptor-') else SUFFIXES[path.stem.split('-', 1)[1]]
        table = pq.read_table(path)
        assert table.schema.equals(SCHEMAS[name]), str(path)
        group = groups.setdefault('final/'+name, {'schema':SCHEMAS[name], 'files':[], 'rows':[]})
        group['files'].append(path.relative_to(ROOT).as_posix()); group['rows'].extend(table.to_pylist())
    for name, (_, schema) in TABLES.items():
        group = groups['intermediate/'+name] = {'schema':schema, 'files':[], 'rows':[]}
        for source in SOURCE_IDS:
            path = ROOT / 'data/interim' / source / (name+'.parquet')
            table = pq.read_table(path)
            assert table.schema.equals(schema), str(path)
            group['files'].append(path.relative_to(ROOT).as_posix()); group['rows'].extend(table.to_pylist())
    return groups


def observed(groups: dict) -> dict:
    """Collect observed controlled labels separately from unrestricted source text.

    Parameters
    ----------
    groups : dict
        Typed table inventory returned by inventory.

    Returns
    -------
    dict
        Per-table/field sorted observed labels; null is documented separately.
    """
    result = {}
    for name, group in groups.items():
        for field in group['schema']:
            if field.name in ENUM_FIELDS:
                values = set()
                for row in group['rows']:
                    value = row[field.name]
                    values.update(value if isinstance(value,list) else [] if value is None else [value])
                result[name+'/'+field.name] = sorted(values)
    return result


def cell(value: object, limit: int = 190) -> str:
    """Encode an actual value safely inside a Markdown table.

    Parameters
    ----------
    value : object
        Verified JSON-compatible value.
    limit : int
        Display-only character bound; ellipsis is explicitly marked.

    Returns
    -------
    str
        Escaped JSON example, with a display-truncation notice if needed.
    """
    text = json.dumps(value, ensure_ascii=False, separators=(',',':'))
    text = text.replace('|','&#124;').replace('`','&#96;').replace('\n','\\n')
    return '`'+text[:limit]+('…` (display excerpt)' if len(text)>limit else '`')


def origin(group: str, field: str) -> str:
    """Locate the transformation responsible for a documented field.

    Parameters
    ----------
    group : str
        Final/intermediate logical table name.
    field : str
        Exact schema field name.

    Returns
    -------
    str
        Markdown source/implementation mapping and transformation scope.
    """
    name=group.split('/')[1]
    if group.startswith('intermediate/'):
        return ('Source fields: see source mapping below; [source_normalizers.py](../scripts/source_normalizers.py) provider adapter → '
                '[normalization_core.py](../scripts/normalization_core.py) `Source.'+{'records':'add','evidence':'add','memberships':'complex','regulators':'add'}[name]+'`; regulator rows are appended directly by `cellchat`.' if name=='regulators' else
                'Source fields: see source mapping below; [source_normalizers.py](../scripts/source_normalizers.py) provider adapter → [normalization_core.py](../scripts/normalization_core.py) `Source.'+{'records':'add','evidence':'add','memberships':'complex'}[name]+'`. Location/keys/status flags are pipeline-derived; original payload is `raw_json`.')
    if field in ('interaction_id', 'related_interaction_id', 'entity_id', 'ligand_entity_id',
                 'receptor_entity_id', 'member_entity_id', 'membership_id', 'regulator_id',
                 'definition_id', 'supporting_definition_ids', 'annotation_id', 'record_id',
                 'evidence_id', 'source_complex_id'):
        return 'Release-local numbering by [database_ids.py](../scripts/database_ids.py) `assign_readable_ids` after canonical assembly; all final foreign keys are rewritten together. Original normalized provenance keys and provider accessions are preserved.'
    if name in ('entities','memberships','definitions'):
        return 'Pipeline-derived by [database_identity.py](../scripts/database_identity.py) `Identities.store/gene/complex/endpoint`; source definitions plus pinned same-species identity columns (source mapping below).'
    if name=='readme': return 'Pipeline-authored [database_export.py](../scripts/database_export.py) `readme_rows`; no upstream biological claim.'
    if name=='sources': return 'Pipeline-derived [database_build.py](../scripts/database_build.py) `make_tables`: normalized manifest `source_citation`, `acquisition_selection`, verified status and source record count.'
    if name=='interactions': return 'Pipeline-derived [database_build.py](../scripts/database_build.py) `make_tables/interaction_id`: resolved entities and eligible assertion/evidence aggregation only; original source fields mapped below.'
    if name=='source_annotations':
        return 'Record-linked extraction from normalized `records.raw_json` by [database_build.py](../scripts/database_build.py) `extract_source_annotations`; final links and summary eligibility follow the assertion disposition and OmniPath orientation safeguard.'
    if name=='source_members':
        return 'Copied unchanged from normalized `memberships.'+field+'`; `source`, `definition_id`, `entity_id` are added by [database_build.py](../scripts/database_build.py) `make_tables`.' if field not in ('source','definition_id','entity_id') else 'Pipeline-derived [database_build.py](../scripts/database_build.py) `make_tables`, source and canonical definition/entity lookup.'
    original={'assertions':{'ligand':'ligand_label','receptor':'receptor_label','normalized_review_reasons':'review_reasons'},'evidence':{},'regulators':{}}[name].get(field,field)
    base='records' if name=='assertions' else name
    retained=set(TABLES[base][1].names)
    if original in retained:
        return f'Copied unchanged from normalized `{base}.{original}`; source mapping below. [database_build.py](../scripts/database_build.py) `make_tables` adds final links without replacing this value.'
    return 'Pipeline-derived [database_build.py](../scripts/database_build.py) `make_tables/disposition`; accepted policies and resolved same-species identities.'


def worked_examples(groups: dict) -> str:
    """Verify representative real joins before showing compact worked examples.

    Parameters
    ----------
    groups : dict
        Actual final and normalized table inventory.

    Returns
    -------
    str
        Markdown examples with real interaction, assertion and entity identifiers.

    Raises
    ------
    AssertionError
        If any illustrated key is absent from its referenced table.
    """
    rows=groups['final/interactions']['rows']; assertions=groups['final/assertions']['rows']
    entities={r['entity_id']:r for r in groups['final/entities']['rows']}
    evidence=defaultdict(list); by_id=defaultdict(list)
    for e in groups['final/evidence']['rows']: evidence[e['record_key']].append(e)
    for a in assertions: by_id[a['interaction_id']].append(a)
    selections=[('Simple pair',next(r for r in rows if r['tier']=='primary' and r['ligand_type']==r['receptor_type']=='gene_product')),
                ('Complete complex',next(r for r in rows if r['tier']=='primary' and 'complex' in (r['ligand_type'],r['receptor_type']))),
                ('Inferred mouse',next(r for r in rows if r['species']=='mouse' and 'provider_orthology' in r['provenance'])),
                ('Proxy companion',next(r for r in rows if r['ligand_type']=='nonprotein_proxy'))]
    lines=['## Verified worked examples','','IDs below are read from current Parquet tables, not illustrative invented rows. Evidence is shown only when that exact assertion has a retained evidence row.','']
    for title,r in selections:
        candidates=by_id[r['interaction_id']]
        a=next(x for x in candidates if x['evidence_provenance']=='provider_orthology') if title=='Inferred mouse' else candidates[0]
        assert r['ligand_entity_id'] in entities and r['receptor_entity_id'] in entities
        lines += ['### '+title,'',f"`{r['interaction_id']}`: **{r['ligand']} → {r['receptor']}** ({r['species']}, {r['tier']}).",'',f"Follow `{a['record_key']}` in Assertions to normalized `{a['source']}/records.parquet`, then `raw_json`. Original location: `{a['source_file']}`, table {cell(a['source_table'])}, row {cell(a['source_row'])}. Provenance: `{a['evidence_provenance']}`.",'',f"Entities: ligand `{r['ligand_entity_id']}`; receptor `{r['receptor_entity_id']}`.",'']
        if evidence[a['record_key']]:
            e=evidence[a['record_key']][0]; lines += [f"Evidence `{e['evidence_key']}` joins by that `record_key`: `{e['type']}`, {cell(e['value'])}, upstream field {cell(e['source_field'])}.",'']
        else: lines += ['This assertion has no evidence row; its presence is not proof of a direct publication reference.','']
        related=[m for m in groups['final/memberships']['rows'] if m['entity_id'] in (r['ligand_entity_id'],r['receptor_entity_id'])]
        for m in related:
            assert m['member_entity_id'] in entities
            lines += [f"- Member `{m['member_entity_id']}` ({entities[m['member_entity_id']]['display_label']}): `{m['relationship']}`, stoichiometry {cell(m['stoichiometry'])}."]
        definitions=[d for d in groups['final/definitions']['rows'] if d['entity_id'] in (r['ligand_entity_id'],r['receptor_entity_id'])]
        for d in definitions[:2]: lines += [f"- Definition `{d['definition_id']}` → Source-Members `{d['source']}` / `{d['source_complex_key']}`; `{d['completeness']}`."]
        lines += ['']
    a=next(a for a in assertions if a['disposition']=='review' and a['related_interaction_id'])
    assert any(r['interaction_id']==a['related_interaction_id'] for r in rows)
    lines+=['### Review does not support a pair','',f"Review assertion `{a['record_key']}` ({a['source']}, {a['species_group']}) has `interaction_id=null`. Reasons: {cell(a['reasons'],1000)}. Its `related_interaction_id={a['related_interaction_id']}` is navigation only. Follow the record to `{a['source_file']}` row {cell(a['source_row'])}; do not count it as supporting evidence.",'']
    return '\n'.join(lines)


def render(groups: dict, metadata: dict) -> str:
    """Render curated scientific descriptions with verified fields and values.

    Parameters
    ----------
    groups : dict
        Actual schema/row inventory.
    metadata : dict
        Maintained field descriptions and reviewed observed vocabularies.

    Returns
    -------
    str
        Complete authoritative field guide Markdown.

    Raises
    ------
    AssertionError
        If descriptions or reviewed vocabulary coverage are stale.
    """
    fields={f.name for g in groups.values() for f in g['schema']}
    layout = json.loads((ROOT/'data/templates/manifest.json').read_text(encoding='utf-8'))
    table_names = {'Ligand-Receptor':'interactions', 'Nonprotein-Proxy':'interactions',
                   'Entities':'entities', 'Complex-Members':'memberships', 'Regulators':'regulators'}
    aliases = {'gene_accession':'gene_id'}
    excel_columns = {table_names[s['name']]: {aliases.get(h,h):h for h in s['headers']}
                     for s in layout['sheets']}
    assert fields==set(metadata['fields']), 'Field description coverage differs'
    assert observed(groups)==metadata['observed_vocabularies'], 'Vocabulary snapshot changed; review config/field-guide.json'
    # Closed labels must be implemented literals, not merely repeated in prose.
    literals=set()
    for script in (ROOT/'scripts').glob('*.py'):
        if script.name.startswith(('generate_','validate_documentation')): continue
        tree=ast.parse(script.read_text(encoding='utf-8'))
        docs={id(n.body[0].value) for n in ast.walk(tree) if isinstance(n,(ast.Module,ast.FunctionDef,ast.ClassDef)) and ast.get_docstring(n)}
        literals.update(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and id(n) not in docs)
    closed={'disposition','tier','sign_summary','mapping_status','evidence_provenance','species_group','entity_type'}
    for field,values in metadata['observed_vocabularies'].items():
        if field.split('/')[-1] in closed:
            assert set(values)<=literals, 'Documented closed vocabulary not implemented: '+field

    lines=[(ROOT/'config/field-guide-introduction.md').read_text(encoding='utf-8'),worked_examples(groups)]
    lines+=['## Table and file map','','Each logical schema below applies identically to human and mouse. Shared tables use the same assertion/evidence/source-member schemas. Review is a filtered assertion view (`review` plus `excluded`), not a second kind of assertion.','']
    for name,g in groups.items():
        paths=g['files']; listing=', '.join('`'+Path(p).name+'`' for p in paths) if name.startswith('final/') else '`data/interim/<each of 16 source IDs>/'+Path(paths[0]).name+'`'
        lines += [f'- **{name}**: {listing}.']
    lines += ['', '## Fields: final tables', '', 'Every field remains typed in Parquet. Only approved template columns appear in Excel. Excel lists display with semicolon separators and empty lists are blank; use Parquet for exact boundaries. Scalar text stays text, numbers and booleans remain typed, and absent values display blank. Intermediate tables have no Excel workbook. All Arrow fields are nullable; logical required keys are checked separately. Count/order units are records, datasets, publications or member positions as described.', '', 'Missing semantics: null generally means not supplied, unresolved or not applicable. `[]` means no retained values, not evidence of biological absence. Empty source_table means a flat/default table. Count zero is not proof that none exists in biology.','']
    for name,g in groups.items():
        if name=='intermediate/records': lines+=['## Fields: normalized intermediates','','These preserve source assertions before accepted-policy assembly. Their statuses and source definition roles need not agree with final eligibility or canonical membership.','']
        lines+=['### '+name,'','| Field | Parquet type / Excel | Definition, format and missing meaning | Verified example | Origin |','|---|---|---|---|---|']
        for f in g['schema']:
            values=[r[f.name] for r in g['rows'] if r[f.name] is not None and r[f.name]!=[]]
            example=min(values,key=lambda x:len(json.dumps(x))) if values else None
            visible = excel_columns.get(name.split('/')[-1], {}) if name.startswith('final/') else {}
            rep = ('not exported to Excel' if f.name not in visible else
                   'semicolon-separated text' if pa.types.is_list(f.type) else
                   'number' if pa.types.is_integer(f.type) else
                   'boolean' if pa.types.is_boolean(f.type) else 'text')
            if f.name in visible and visible[f.name] != f.name:
                rep += ' as ' + visible[f.name]
            lines.append(f"| `{f.name}` | `{f.type}` / {rep} | {metadata['fields'][f.name]} | {cell(example)} | {origin(name,f.name)} |")
        lines+=['']
    lines+=['## Reviewed vocabulary snapshot','','These are the **observed** values in this release, not permission to silently accept future values. The check command compares every set with the maintained catalog. Upstream labels and parameterized reason strings are open vocabularies; new values require review. Code branches may allow values not currently observed (e.g. nonprotein_molecule, boolean false in nullable schemas); no unobserved biological coverage is implied. Reason prefixes `ligand:`/`receptor:` identify the failing endpoint; N01–N04 refer to the accepted policies. Multiple flags overlap.','']
    for name,values in sorted(metadata['observed_vocabularies'].items()):
        lines += [f'- **{name}**: '+(', '.join(cell(v,1000) for v in values) or '(no observed non-null values)')+'.']
    lines+=['', (ROOT/'config/source-field-mapping.md').read_text(encoding='utf-8')]
    return '\n'.join(lines).rstrip()+'\n'


def main() -> None:
    """Generate or check documentation without changing scientific data.

    Returns
    -------
    None
        Writes the guide, or confirms exact agreement with --check.

    Raises
    ------
    AssertionError
        If schema, reviewed values, worked joins or checked documentation differ.
    """
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Compare instead of writing the guide')
    args=parser.parse_args()
    metadata=json.loads((ROOT/'config/field-guide.json').read_text(encoding='utf-8'))
    text=render(inventory(),metadata); path=ROOT/'docs/Database dictionary.md'
    if args.check: assert path.read_text(encoding='utf-8')==text, 'Field guide is stale'
    else: path.write_text(text,encoding='utf-8')
    print('Field guide: all final/intermediate fields, observed vocabularies and worked joins verified.')


if __name__=='__main__':
    main()
