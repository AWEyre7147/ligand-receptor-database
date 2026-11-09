"""Explicit accepted-policy dispositions and cross-source interaction views."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from normalization_core import ROOT, RAW, SOURCE_IDS, key, js, file_hash
from database_identity import Identities, IdentityError
from database_ids import assign_readable_ids

VERSION = '1.3.0'
POLICY = ROOT / 'docs/Accepted database policies.md'
INTERIM = ROOT / 'data/interim'


# =============================================================================
# Accepted-policy assembly and validation
# =============================================================================
def schema(strings='', lists='', ints='', bools=''):
    """Construct the fixed nullable Arrow schema from explicitly grouped field names.
    
    Parameters
    ----------
    strings : str
        Whitespace-delimited Arrow string field names.
    lists : str
        Whitespace-delimited list-of-string field names.
    ints : str
        Whitespace-delimited int64 field names.
    bools : str
        Whitespace-delimited nullable boolean field names.
    
    Returns
    -------
    pyarrow.Schema
        Ordered typed nullable fields.
    """
    return pa.schema([(f, pa.string()) for f in strings.split()] + [(f, pa.list_(pa.string())) for f in lists.split()] +
                     [(f, pa.int64()) for f in ints.split()] + [(f, pa.bool_()) for f in bools.split()])


SCHEMAS = {
 'interactions': schema('ligand receptor interaction_id species ligand_entity_id receptor_entity_id ligand_type receptor_type tier sign_summary',
                        'sources underlying_sources provenance limitations omnipath_reported_stimulation omnipath_reported_inhibition omnipath_reported_direction cellchat_interaction_annotation cellchat_pathway cellchat_ligand_location cellchat_ligand_family cellchat_receptor_location cellchat_receptor_family connectomedb_ligand_location connectomedb_receptor_location italk_classification gtopdb_ligand_type gtopdb_interaction_type gtopdb_action gtopdb_action_comment gtopdb_selectivity gtopdb_endogenous',
                        'source_count assertion_count direct_publication_count provider_summary_publication_count'),
 'assertions': schema('record_key source species_group disposition interaction_id related_interaction_id ligand receptor ligand_entity_id receptor_entity_id source_file source_table source_row source_record_id evidence_provenance orientation sign_basis',
                      'reasons normalized_review_reasons underlying_sources', bools='is_stimulation is_inhibition is_directed'),
 'evidence': schema('evidence_key record_key interaction_id disposition source type value provider source_field species_group'),
 'memberships': schema('membership_id entity_id member_entity_id relationship stoichiometry species'),
 'definitions': schema('definition_id entity_id source source_complex_key source_label source_file source_table source_row stoichiometry_context completeness', 'supporting_definition_ids'),
 'regulators': schema('regulator_id record_key interaction_id disposition role group_label member_label member_entity_id mapping_status species source_file'),
 'entities': schema('entity_id species entity_type display_label identity mapping_basis gene_id', 'limitations'),
 'sources': schema('source citation selection_json acquisition_status', ints='normalized_assertions'),
 'source_members': schema('source complex_key complex_label member_id member_label namespace species relationship stoichiometry source_file source_table source_row definition_id entity_id', ints='member_order'),
 'source_annotations': schema('annotation_id record_key interaction_id related_interaction_id disposition source source_file source_table source_row source_record_id species_group source_field summary_field original_value interpretation_note', bools='summary_eligible'),
 'readme': schema('topic description'),
}

# Add readable record IDs while preserving normalized keys for interim joins.
for _table in ('assertions', 'evidence', 'regulators', 'source_annotations'):
    SCHEMAS[_table] = SCHEMAS[_table].append(pa.field('record_id', pa.string()))
SCHEMAS['evidence'] = SCHEMAS['evidence'].append(pa.field('evidence_id', pa.string()))
for _table in ('definitions', 'source_members'):
    SCHEMAS[_table] = SCHEMAS[_table].append(pa.field('source_complex_id', pa.string()))


ANNOTATION_FIELDS = {
    'omnipathppis': {
        'is_stimulation': 'omnipath_reported_stimulation',
        'is_inhibition': 'omnipath_reported_inhibition',
        'is_directed': 'omnipath_reported_direction',
    },
    'cellchat': {
        'annotation': 'cellchat_interaction_annotation',
        'pathway_name': 'cellchat_pathway',
        'ligand.location': 'cellchat_ligand_location',
        'ligand.family': 'cellchat_ligand_family',
        'receptor.location': 'cellchat_receptor_location',
        'receptor.family': 'cellchat_receptor_family',
    },
    'connectomedb': {
        'Ligand Location': 'connectomedb_ligand_location',
        'Receptor Location': 'connectomedb_receptor_location',
    },
    'italk': {'Classification': 'italk_classification'},
    'gtopdb': {
        'Ligand Type': 'gtopdb_ligand_type',
        'Type': 'gtopdb_interaction_type',
        'Action': 'gtopdb_action',
        'Action comment': 'gtopdb_action_comment',
        'Selectivity': 'gtopdb_selectivity',
        'Endogenous': 'gtopdb_endogenous',
    },
}


def summarize_sign(assertions: list[dict], annotations: list[dict]) -> str | None:
    """Summarize reported signs without turning absent evidence into unknown.

    Parameters
    ----------
    assertions : list[dict]
        Eligible, orientation-safe assertions for one interaction.
    annotations : list[dict]
        Detailed provider values for that same interaction.

    Returns
    -------
    str or None
        Positive or conflicting reported signs, explicit provider unknown, or
        null when no sign was reported. False stimulation is not inhibition.
    """
    stimulation = any(row['is_stimulation'] is True for row in assertions)
    inhibition = any(row['is_inhibition'] is True for row in assertions)
    if stimulation and inhibition:
        return 'conflicting_positive_assertions'
    if stimulation:
        return 'stimulation_reported'
    if inhibition:
        return 'inhibition_reported'
    if any(row['summary_eligible'] and row['source'] == 'omnipathppis'
           and row['source_field'] in ('is_stimulation', 'is_inhibition')
           and row['original_value'].strip().casefold() == 'unknown' for row in annotations):
        return 'unknown'
    return None


def verify_inputs():
    """Verify acquisition, normalized input and implementation hashes before building.
    
    Returns
    -------
    tuple
        Normalized manifest and verified input hash records.
    
    Raises
    ------
    ValueError
        If acquisition metadata, source sets, implementation hashes or input bytes are stale/incomplete.
    """
    path = INTERIM / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    hashes = [{'path': str(path), 'sha256': file_hash(path)}, {'path': str(POLICY), 'sha256': file_hash(POLICY)}]
    versions = RAW / 'versions.txt'
    if file_hash(versions) != manifest['acquisition_manifest_sha256']:
        raise ValueError('Stale acquisition manifest')
    hashes.append({'path': str(versions), 'sha256': file_hash(versions)})
    if set(manifest['sources']) != set(SOURCE_IDS):
        raise ValueError('Missing/unexpected normalized sources')
    for s in SOURCE_IDS:
        entry = manifest['sources'][s]
        if entry['status'] != 'success':
            raise ValueError('Failed normalized input: ' + s)
        for name, digest in entry['implementation'].items():
            if file_hash(ROOT / 'scripts' / name) != digest:
                raise ValueError('Stale normalized implementation: ' + s)
        for base, files in [(RAW, entry['inputs']), (INTERIM, entry['outputs'])]:
            for f in files:
                p = base / f['path']
                if file_hash(p) != f['sha256']:
                    raise ValueError('Stale/mismatched input: ' + str(p))
                hashes.append({'path': str(p), 'sha256': f['sha256']})
    return manifest, hashes


RESOLVED_FLAGS = {'N01_provider_mouse_orthology', 'N01_mouse_evidence_provenance_unknown', 'N02_complex_representation',
                  'N03_nonprotein_or_proxy', 'neurotransmitter_flag_not_used_for_entity_type', 'conflicting_signs',
                  'N03_conflicting_nonprotein_flag'}


def disposition(r, identities, members):
    """Apply accepted policies to one assertion without discarding the original record.
    Only primary/companion dispositions contribute support; unresolved identities remain review.
    
    Parameters
    ----------
    r : dict
        One normalized source assertion or dependency row.
    identities : Identities
        Same-species resolver and accumulated canonical definitions.
    members : sequence or dict
        Declared source members; not inferred pairwise gene combinations.
    
    Returns
    -------
    tuple
        Disposition, reasons and resolved ligand/receptor entity IDs.
    """
    reasons = set(r['exclusion_reasons'])
    state = 'excluded' if reasons else 'review'
    reasons.update(set(r['review_reasons']) - RESOLVED_FLAGS)
    if r['species_group'] not in ('human', 'mouse'):
        reasons.add('endpoint_species_not_single_human_or_mouse')
        return state, sorted(reasons), None, None
    if r['orientation'] not in ('ligand_to_receptor', 'reversed_to_ligand_receptor'):
        reasons.add('ligand_receptor_orientation_not_established')
    if r['source'] == 'dimitrov' and 'consensus' not in r['underlying_sources']:
        state = 'provenance_only'
        reasons.add('LIANA_constituent_not_independent_consensus_support')
    if r['source'] == 'gtopdb':
        raw = json.loads(r['raw_json'])
        if raw.get('Endogenous', '').lower() != 'true':
            reasons.add('endogenous_signaling_not_established')
        target_types = {x['Type'] for x in identities.targets.get(raw['Target ID'], [])}
        if not target_types or not target_types <= {'gpcr', 'catalytic_receptor', 'lgic', 'nhr'}:
            reasons.add('pharmacology_target_not_established_receptor_class')
    ends = []
    for side in ('ligand', 'receptor'):
        try:
            ends.append(identities.endpoint(r, side, members))
        except IdentityError as e:
            ends.append(None)
            reasons.add(side + ':' + str(e))
    if reasons:
        return state, sorted(reasons), *ends
    kinds = [identities.entities[e]['entity_type'] for e in ends]
    if kinds[1] not in ('gene_product', 'complex', 'encoded_peptide'):
        return 'review', ['receptor_not_gene_encoded'], *ends
    tier = 'companion' if kinds[0] in ('nonprotein_proxy', 'nonprotein_molecule') else 'primary'
    return tier, [], *ends


def interaction_id(sp: str, left: str, right: str, tier: str) -> str:
    """Key an ordered ligand/receptor entity pair by species and eligibility tier.
    
    Parameters
    ----------
    sp : str
        Species used for identity lookup or output partition.
    left : dict or sequence or str
        Ligand endpoint, species list or canonical entity ID for this operation.
    right : dict or sequence or str
        Receptor endpoint, species list or canonical entity ID for this operation.
    tier : str
        primary or companion eligible interaction view.
    
    Returns
    -------
    str
        I-prefixed deterministic interaction key.
    """
    return 'I:' + key(sp, left, right, tier)


def extract_source_annotations(record: dict, assertion: dict) -> list[dict]:
    """Retain configured provider fields with their exact source-record association.

    Parameters
    ----------
    record : dict
        Normalized assertion containing the complete original row in ``raw_json``.
    assertion : dict
        Final disposition and interaction links for the same normalized record.

    Returns
    -------
    list[dict]
        One row per present provider field. Ineligible assertions and safeguarded
        OmniPath orientations remain traceable but cannot populate summaries.
    """
    raw = json.loads(record['raw_json'])
    fields = ANNOTATION_FIELDS.get(record['source'], {})
    eligible = assertion['disposition'] in ('primary', 'companion')
    orientation_ok = record['source'] != 'omnipathppis' or assertion['orientation'] == 'ligand_to_receptor'
    rows = []
    for source_field, summary_field in fields.items():
        value = raw.get(source_field)
        if value is None or value == '':
            continue
        original = value if isinstance(value, str) else js(value)
        summary_eligible = eligible and orientation_ok
        note = None
        if not eligible:
            note = 'not eligible accepted support; retained for source-record context only'
        elif not orientation_ok:
            note = 'withheld from summary by OmniPath ligand-receptor orientation safeguard'
        rows.append({
            'annotation_id': 'A:' + key(assertion['record_key'], source_field),
            'record_key': assertion['record_key'],
            'interaction_id': assertion['interaction_id'],
            'related_interaction_id': assertion['related_interaction_id'],
            'disposition': assertion['disposition'],
            'source': record['source'],
            'source_file': record['source_file'],
            'source_table': record['source_table'],
            'source_row': record['source_row'],
            'source_record_id': record['source_record_id'],
            'species_group': record['species_group'],
            'source_field': source_field,
            'summary_field': summary_field,
            'original_value': original,
            'summary_eligible': summary_eligible,
            'interpretation_note': note,
        })
    return rows


def source_annotation_summary(interaction_id_value: str, annotations: list[dict]) -> dict[str, list[str]]:
    """Aggregate distinct eligible values independently for each provider field.

    Parameters
    ----------
    interaction_id_value : str
        Final interaction whose eligible source records are summarized.
    annotations : list[dict]
        Record-linked provider annotation rows.

    Returns
    -------
    dict[str, list[str]]
        Every configured summary column with sorted distinct values. Empty lists
        represent no eligible reported value; explicit negatives remain strings.
    """
    result = {field: [] for fields in ANNOTATION_FIELDS.values() for field in fields.values()}
    for row in annotations:
        if row['interaction_id'] == interaction_id_value and row['summary_eligible']:
            result[row['summary_field']].append(row['original_value'])
    return {name: sorted(set(values)) for name, values in result.items()}


def make_tables(annotation_root=None):
    """Build canonical interactions and retain every assertion, evidence row and regulator.
    Resolve explicit complex definitions before checking GtoPdb family-versus-complex ambiguity.
    
    Parameters
    ----------
    annotation_root : Path, optional
        Annotation manifest/Parquet directory; default is the sibling project.
    
    Returns
    -------
    tuple
        Canonical tables, hashed inputs, annotation version and normalized manifest.
    """
    manifest, inputs = verify_inputs()
    ids = Identities() if annotation_root is None else Identities(annotation_root)
    inputs.extend(ids.inputs)
    members = defaultdict(list)
    data = {}
    for s in SOURCE_IDS:
        data[s] = {n: pq.read_table(INTERIM / s / (n + '.parquet')).to_pylist() for n in ('records', 'evidence', 'memberships', 'regulators')}
        for m in data[s]['memberships']:
            members[s, m['complex_key']].append(m)
    tables = {name: [] for name in SCHEMAS}
    # Resolve explicit definitions independently of interaction eligibility and before
    # consulting them for GtoPdb family-vs-complex disambiguation. This is structural
    # evidence only; it does not promote a weak interaction assertion into support.
    seen_definitions = set()
    for source in SOURCE_IDS:
        if source == 'gtopdb':
            continue
        for r in data[source]['records']:
            if r['species_group'] not in ('human','mouse'):
                continue
            for side in ('ligand','receptor'):
                ck = r[side + '_complex_key']
                if ck and (source,ck) not in seen_definitions:
                    seen_definitions.add((source,ck))
                    try:
                        ids.endpoint(r,side,members)
                    except IdentityError:
                        pass  # The owning assertion receives the exact failure reason below.
    links, groups = {}, defaultdict(list)
    for s in SOURCE_IDS:
        print('Applying accepted policies: ' + s, flush=True)
        for r in data[s]['records']:
            state, reasons, left, right = disposition(r, ids, members)
            iid = interaction_id(r['species_group'], left, right, state) if state in ('primary', 'companion') else None
            a = {f: r.get(f) for f in ['record_key', 'source', 'species_group', 'source_file', 'source_table', 'source_row', 'source_record_id',
                                     'evidence_provenance', 'orientation', 'sign_basis', 'is_stimulation', 'is_inhibition', 'is_directed', 'underlying_sources']}
            a.update(disposition=state, reasons=reasons, interaction_id=iid, related_interaction_id=None,
                     ligand=r['ligand_label'], receptor=r['receptor_label'], ligand_entity_id=left, receptor_entity_id=right,
                     normalized_review_reasons=r['review_reasons'])
            tables['assertions'].append(a)
            links[r['record_key']] = a
            tables['source_annotations'].extend(extract_source_annotations(r, a))
            if iid:
                groups[iid].append(a)
        entry = manifest['sources'][s]
        tables['sources'].append({'source': s, 'citation': entry['source_citation'], 'selection_json': js(entry.get('acquisition_selection')),
                                  'acquisition_status': 'local_checksums_verified', 'normalized_assertions': len(data[s]['records'])})
    for s in SOURCE_IDS:
        for e in data[s]['evidence']:
            a = links[e['record_key']]
            tables['evidence'].append({**e, 'interaction_id': a['interaction_id'], 'disposition': a['disposition'], 'source': s, 'species_group': a['species_group']})
        for n, r in enumerate(data[s]['regulators']):
            a = links[r['record_key']]
            try:
                e = ids.gene(r['species'], 'symbol', r['member_label'], strict=True)
                status = 'same_species_resolved'
            except IdentityError:
                e, status = None, 'unresolved_regulator'
            tables['regulators'].append({**r, 'regulator_id': 'R:' + key(s, n, r), 'member_entity_id': e, 'mapping_status': status,
                                         'interaction_id': a['interaction_id'], 'disposition': a['disposition']})
    evidence_by_interaction = defaultdict(list)
    for e in tables['evidence']:
        if e['interaction_id']:
            evidence_by_interaction[e['interaction_id']].append(e)
    annotations_by_interaction = defaultdict(list)
    for annotation in tables['source_annotations']:
        if annotation['interaction_id']:
            annotations_by_interaction[annotation['interaction_id']].append(annotation)
    for iid, assertions in sorted(groups.items()):
        a = assertions[0]
        left, right = [ids.entities[a[side + '_entity_id']] for side in ('ligand', 'receptor')]
        ev = evidence_by_interaction[iid]
        sign = summarize_sign(assertions, annotations_by_interaction[iid])
        notes = set(left['limitations'] + right['limitations'])
        referenced_records = {e['record_key'] for e in ev if e['type'] == 'pubmed'}
        if any(x['record_key'] not in referenced_records for x in assertions):
            notes.add('some_assertions_lack_direct_publication_ids')
        if any(x['orientation'] == 'reversed_to_ligand_receptor' for x in assertions):
            notes.add('reversed_PPI_sign_not_transferred')
        if sign == 'conflicting_positive_assertions':
            notes.add('source_signs_conflict')
        sources = sorted({x['source'] for x in assertions})
        tables['interactions'].append({'ligand': left['display_label'], 'receptor': right['display_label'], 'interaction_id': iid,
            'species': a['species_group'], 'ligand_entity_id': left['entity_id'], 'receptor_entity_id': right['entity_id'],
            'ligand_type': left['entity_type'], 'receptor_type': right['entity_type'], 'tier': a['disposition'], 'sign_summary': sign,
            'sources': sources, 'underlying_sources': sorted({v for x in assertions for v in x['underlying_sources']}),
            'provenance': sorted({x['evidence_provenance'] for x in assertions}), 'limitations': sorted(notes),
            'source_count': len(sources), 'assertion_count': len(assertions),
            'direct_publication_count': len({e['value'] for e in ev if e['type'] == 'pubmed'}),
            'provider_summary_publication_count': len({e['value'] for e in ev if 'pubmed' in e['type'] and e['type'] != 'pubmed'}),
            **source_annotation_summary(iid, annotations_by_interaction[iid])})
    eligible = {(r['species'], r['ligand_entity_id'], r['receptor_entity_id']): r['interaction_id'] for r in tables['interactions']}
    for a in tables['assertions']:
        if not a['interaction_id']:
            a['related_interaction_id'] = eligible.get((a['species_group'], a['ligand_entity_id'], a['receptor_entity_id']))
    related = {a['record_key']: a['related_interaction_id'] for a in tables['assertions']}
    for annotation in tables['source_annotations']:
        annotation['related_interaction_id'] = related[annotation['record_key']]
    tables['entities'] = list(ids.entities.values())
    tables['definitions'] = list(ids.definitions.values())
    tables['memberships'] = list(ids.memberships.values())
    for s in SOURCE_IDS:
        for member in data[s]['memberships']:
            did = 'D:' + key(s, member['complex_key'])
            definition = ids.definitions.get(did)
            tables['source_members'].append({**member, 'source': s, 'definition_id': did if definition else None,
                                             'entity_id': definition['entity_id'] if definition else None})
    assign_readable_ids(tables)
    for name, rows in tables.items():
        if name != 'interactions':
            rows.sort(key=js)
    return tables, inputs, ids.annotation_version, manifest


def validate_tables(tables, manifest):
    """Check scientific policy invariants, counts and referential integrity of canonical tables.
    
    Parameters
    ----------
    tables : dict[str, list[dict]]
        Canonical tables or source inventory used by this operation.
    manifest : dict
        Recorded source selections, checksums and processing state.
    
    Returns
    -------
    dict
        Reconciled counts by species, source and disposition.
    """
    assertions = {r['record_key']: r for r in tables['assertions']}
    interactions = {r['interaction_id']: r for r in tables['interactions']}
    entities = {r['entity_id']: r for r in tables['entities']}
    expected = sum(x['summary']['normalized_records'] for x in manifest['sources'].values())
    assert {r['source']:r['citation'] for r in tables['sources']} == {s:manifest['sources'][s]['source_citation'] for s in SOURCE_IDS}
    assert len(assertions) == len(tables['assertions']) == expected, 'Assertion reconciliation'
    assert len(interactions) == len(tables['interactions']), 'Duplicate interactions'
    assert len({r['annotation_id'] for r in tables['source_annotations']}) == len(tables['source_annotations']), 'Duplicate source annotations'
    for source in SOURCE_IDS:
        assert sum(a['source'] == source for a in assertions.values()) == manifest['sources'][source]['summary']['normalized_records']
    support = defaultdict(list)
    annotation_support = defaultdict(list)
    for annotation in tables['source_annotations']:
        if annotation['interaction_id']:
            annotation_support[annotation['interaction_id']].append(annotation)
    for a in assertions.values():
        assert a['disposition'] in ('primary', 'companion', 'review', 'excluded', 'provenance_only')
        if a['disposition'] in ('primary', 'companion'):
            assert not a['reasons'] and a['interaction_id'] in interactions
            i = interactions[a['interaction_id']]
            assert i['species'] == a['species_group'] in ('human', 'mouse')
            assert a['orientation'] in ('ligand_to_receptor', 'reversed_to_ligand_receptor')
            support[a['interaction_id']].append(a)
        else:
            assert a['interaction_id'] is None and a['reasons']
        if a['related_interaction_id']:
            assert a['related_interaction_id'] in interactions and not a['interaction_id']
    required = defaultdict(list)
    for m in tables['memberships']:
        assert m['entity_id'] in entities and m['member_entity_id'] in entities
        assert entities[m['entity_id']]['species'] == entities[m['member_entity_id']]['species'] == m['species']
        required[m['entity_id']].append(m)
    definitions = {d['entity_id'] for d in tables['definitions']}
    definition_ids = {d['definition_id'] for d in tables['definitions']}
    for d in tables['definitions']:
        assert set(d['supporting_definition_ids']) <= definition_ids
    for i in interactions.values():
        assert i['assertion_count'] == len(support[i['interaction_id']])
        assert i['source_count'] == len({a['source'] for a in support[i['interaction_id']]})
        for side in ('ligand', 'receptor'):
            e = entities[i[side + '_entity_id']]
            assert e['species'] == i['species']
            if e['entity_type'] == 'complex':
                assert e['entity_id'] in definitions and required[e['entity_id']]
                assert all(m['relationship'].startswith('required_subunit') for m in required[e['entity_id']])
        if i['tier'] == 'primary':
            assert i['ligand_type'] in ('gene_product', 'complex', 'encoded_peptide')
        expected_annotations = source_annotation_summary(i['interaction_id'], annotation_support[i['interaction_id']])
        assert all(i[name] == values for name, values in expected_annotations.items())
        assert i['sign_summary'] == summarize_sign(support[i['interaction_id']], annotation_support[i['interaction_id']])
    for table in ('evidence', 'regulators', 'source_annotations'):
        for e in tables[table]:
            a = assertions[e['record_key']]
            assert e['interaction_id'] == a['interaction_id'] and e['disposition'] == a['disposition']
            if table == 'source_annotations':
                assert e['source'] == a['source'] and e['species_group'] == a['species_group']
                assert not e['summary_eligible'] or a['disposition'] in ('primary', 'companion')
    assert len(tables['evidence']) == sum(x['summary']['evidence_rows'] for x in manifest['sources'].values())
    assert len(tables['regulators']) == sum(x['summary']['regulator_rows'] for x in manifest['sources'].values())
    assert len(tables['source_members']) == sum(x['summary']['membership_rows'] for x in manifest['sources'].values())
    for name, rows in tables.items():
        pa.Table.from_pylist(rows, schema=SCHEMAS[name]).validate(full=True)
    return {'assertions': len(assertions), 'by_disposition': dict(Counter(a['disposition'] for a in assertions.values())),
            'species': {sp: {tier: sum(i['species'] == sp and i['tier'] == tier for i in interactions.values()) for tier in ('primary', 'companion')} for sp in ('human', 'mouse')},
            'evidence_rows': len(tables['evidence']), 'regulator_rows': len(tables['regulators']), 'membership_rows': len(tables['memberships']),
            'checks': 'input hashes; every assertion disposition; same-species identities; unique IDs; joins; source counts; evidence and regulator retention; complete complexes'}


def digest_table(rows, name):
    """Hash schema-typed canonical rows for repeat-build semantic comparisons.
    
    Parameters
    ----------
    rows : list[dict]
        Ordered canonical rows for the named schema.
    name : str
        Schema, field or provider name selected by the caller.
    
    Returns
    -------
    str
        Semantic table SHA-256 digest.
    """
    table = pa.Table.from_pylist(rows, schema=SCHEMAS[name])
    return hashlib.sha256(js(table.to_pylist()).encode()).hexdigest()
