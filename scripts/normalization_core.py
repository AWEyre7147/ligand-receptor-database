"""Information-preserving offline normalization primitives (no species conversion)."""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import warnings

import pandas as pd
import pyarrow as pa
import rdata

SCHEMA_VERSION = '1.0'
ADAPTER_VERSION = '1.0'
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/sources'
SOURCE_IDS = ('cellcall cellinker omnipathppis dimitrov cellphonedb kirouac cellchat '
              'connectomedb italk lrdb ramilowski pavlicev nichenet gtopdb celltalkdb icellnet').split()


# =============================================================================
# Public workflow and supporting operations
# =============================================================================
def clean(value):
    """Normalize missing display/identifier values without case folding.
    Raw source payload preservation uses native instead of this cleaning rule.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    
    Returns
    -------
    str or None
        Cleaned scalar text or missing marker.
    """
    if value is None or value is pd.NA:
        return None
    if not isinstance(value, (list, dict, tuple)) and pd.isna(value):
        return None
    text = str(value).strip()
    return None if text in ('', 'NA', 'N/A', 'nan', '<NA>') else text


def native(value):
    """Convert raw values to JSON-safe strings while retaining original whitespace and case.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    
    Returns
    -------
    object
        JSON-safe raw payload preserving literal source text.
    """
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    if value is None or value is pd.NA or pd.isna(value):
        return None
    # Raw fields keep original whitespace/case and literal missing-value spellings.
    return str(value)


def js(value: object) -> str:
    """Serialize deterministic compact JSON without nonstandard NaN values.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    
    Returns
    -------
    str
        Canonical compact JSON.
    """
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def key(*parts: object) -> str:
    """Derive a deterministic 128-bit hexadecimal key from ordered canonical JSON parts.
    This is a content identifier, not a security token; changed identity inputs change the key.
    
    Parameters
    ----------
    parts : tuple
        Ordered identity components; order participates in the key.
    
    Returns
    -------
    str
        First 32 hexadecimal SHA-256 characters.
    """
    return hashlib.sha256(js(parts).encode()).hexdigest()[:32]


def file_hash(path: Path) -> str:
    """Compute SHA-256 over original file bytes for provenance and stale-input checks.
    
    Parameters
    ----------
    path : Path
        Local file or directory used by this operation.
    
    Returns
    -------
    str
        SHA-256 hexadecimal digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parts(value, delimiter=';'):
    """Split a source-declared list delimiter and remove empty tokens.
    Do not use punctuation splitting to infer complexes from arbitrary gene labels.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    delimiter : str
        Source-declared separator; default semicolon.
    
    Returns
    -------
    list[str]
        Nonempty stripped tokens.
    """
    return [v.strip() for v in (clean(value) or '').split(delimiter) if v.strip()]


def species(value):
    """Normalize explicit species labels/taxonomy identifiers without orthology conversion.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    
    Returns
    -------
    list[str]
        Sorted explicit species names.
    """
    mapping = {'9606': 'human', '10090': 'mouse', '10116': 'rat', 'homo sapiens': 'human',
               'mus musculus': 'mouse', 'human': 'human', 'mouse': 'mouse', 'rat': 'rat'}
    values = {mapping.get(v.lower(), v.lower()) for v in parts(value, '|')}
    return sorted(v for v in values if v not in ('unknown', 'unspecified'))


def species_group(left, right):
    """Classify endpoint species agreement without filling missing species from its partner.
    
    Parameters
    ----------
    left : dict or sequence or str
        Ligand endpoint, species list or canonical entity ID for this operation.
    right : dict or sequence or str
        Receptor endpoint, species list or canonical entity ID for this operation.
    
    Returns
    -------
    str
        human, mouse, unknown_species, mixed_species, cross_species or other_species.
    """
    if not left or not right:
        return 'unknown_species'
    if len(left) != 1 or len(right) != 1:
        return 'mixed_species'
    if left != right:
        return 'cross_species'
    return left[0] if left[0] in ('human', 'mouse') else 'other_species'


def positive(value):
    # False indicates no positive assertion, not evidence of the opposite sign.
    """Retain only a positive source sign assertion; all other values become unknown.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    
    Returns
    -------
    bool or None
        True only for a positive source assertion.
    """
    return True if (clean(value) or '').lower() in ('true', '1', 'yes') else None


def endpoint(label, identifier=None, namespace='symbol', kind='gene_product', species_values=None,
             mapping='source_identifier', complex_key=None):
    """Construct an unresolved-or-source-defined endpoint, preserving its species list.
    
    Parameters
    ----------
    label : str, optional
        Original endpoint/member display label.
    identifier : str, optional
        Source identifier in the declared namespace.
    namespace : str
        Identifier namespace; symbols remain case sensitive.
    kind : str
        Endpoint/entity class, not a species conversion rule.
    species_values : list[str], optional
        Explicit source endpoint species; empty means unknown.
    mapping : str
        Recorded source lookup or unresolved mapping label.
    complex_key : str, optional
        Source definition key, distinct from the final entity ID.
    
    Returns
    -------
    dict or str
        Source endpoint descriptor, or canonical entity ID in Identities.
    """
    label, identifier = clean(label), clean(identifier)
    return {'label': label, 'id': identifier or label, 'namespace': namespace, 'type': kind,
            'species': species_values or [], 'mapping': mapping if identifier or label else 'unresolved',
            'complex_key': complex_key}


def unique_mapping(values):
    """Accept a lookup only when one distinct cleaned identity remains.
    
    Parameters
    ----------
    values : iterable
        Candidate identity values before uniqueness checking.
    
    Returns
    -------
    tuple
        Unique value and mapping state, or None and ambiguity state.
    """
    values = sorted({clean(v) for v in values if clean(v)})
    return (values[0], 'source_lookup') if len(values) == 1 else (None, 'ambiguous' if values else 'unresolved')


STRING_FIELDS = ('record_key semantic_key source source_file source_table source_row source_record_id '
                 'dataset_species dataset_provenance evidence_provenance original_endpoint_a original_endpoint_b '
                 'original_id_a original_id_b original_role_a original_role_b '
                 'ligand_label ligand_id ligand_namespace ligand_type ligand_mapping ligand_complex_key '
                 'receptor_label receptor_id receptor_namespace receptor_type receptor_mapping receptor_complex_key '
                 'species_basis species_group orientation sign_basis status raw_json').split()
RECORD_SCHEMA = pa.schema([(f, pa.string()) for f in STRING_FIELDS] +
                         [(f, pa.list_(pa.string())) for f in ['ligand_species', 'receptor_species', 'underlying_sources', 'review_reasons', 'exclusion_reasons']] +
                         [(f, pa.bool_()) for f in ['is_stimulation', 'is_inhibition', 'is_directed']])
EVIDENCE_SCHEMA = pa.schema([(f, pa.string()) for f in ['evidence_key', 'record_key', 'type', 'value', 'provider', 'source_field']])
MEMBER_SCHEMA = pa.schema([(f, pa.string()) for f in ['complex_key', 'complex_label', 'member_id', 'member_label', 'namespace', 'species', 'relationship', 'stoichiometry', 'source_file', 'source_table', 'source_row']] + [('member_order', pa.int64())])
REGULATOR_SCHEMA = pa.schema([(f, pa.string()) for f in ['record_key', 'role', 'group_label', 'member_label', 'species', 'source_file']])


class Source:
    def __init__(self, source_id, manifest):
        """Load source-specific state for evidence-preserving processing.
        
        Parameters
        ----------
        source_id : str
            One registered provider identifier.
        manifest : dict
            Recorded source selections, checksums and processing state.
        
        Returns
        -------
        None
            Mutates the documented destination/context; returns no value.
        """
        self.id, self.manifest = source_id, manifest
        self.files = {Path(f['path']).name: f for f in manifest['files']}
        self.records, self.evidence, self.members, self.regulators = [], [], [], []
        self.inventory, self.limitations = [], []
        self.member_cache = set()
        self.tables = {}

    def meta(self, filename):
        # Species subfolders can contain the same basename; accept full relative paths.
        """Locate one acquisition asset, rejecting ambiguous duplicate basenames.
        
        Parameters
        ----------
        filename : str
            Original filename used for format selection.
        
        Returns
        -------
        dict
            Unique matching acquisition asset metadata.
        
        Raises
        ------
        ValueError
            If the requested asset has zero or multiple matching acquisition records.
        """
        matches = [f for f in self.manifest['files'] if f['path'] == filename or f['path'] == self.id + '/' + filename]
        if not matches:
            matches = [f for f in self.manifest['files'] if Path(f['path']).name == filename]
        if len(matches) != 1:
            raise ValueError(f'Expected one input for {self.id}/{filename}, got {len(matches)}')
        return matches[0]

    def table(self, filename, location='', header=0, role='support'):
        """Load a source table or nested R object and inventory its exact fields and location.
        Caches avoid parsing support tables repeatedly; source files are never edited.
        
        Parameters
        ----------
        filename : str
            Original filename used for format selection.
        location : str
            Nested R object or worksheet location; empty for flat files.
        header : int or None
            Zero-based source header location, or None when absent.
        role : str
            Source inventory or regulator/dependency role.
        
        Returns
        -------
        pandas.DataFrame
            Cached source table with original fields.
        
        Raises
        ------
        ValueError
            If a nested R object is neither a supported table nor traversable container.
        """
        meta = self.meta(filename)
        path = RAW / meta['path']
        cache = (meta['path'], location, header)
        if cache in self.tables:
            return self.tables[cache]
        ext = path.suffix.lower()
        if ext in ('.rds', '.rda'):
            with warnings.catch_warnings(record=True) as notices:
                warnings.simplefilter('always')
                data = rdata.read_rda(path) if ext == '.rda' else rdata.read_rds(path)
            if notices:
                self.limitations.extend(sorted({str(w.message) for w in notices}))
            def walk(obj, label):
                if isinstance(obj, pd.DataFrame):
                    frame = obj.copy()
                    frame.columns = [str(c) for c in frame.columns]
                    self.tables[(meta['path'], label, 0)] = frame
                    self.inventory.append({'file': meta['path'], 'table': label, 'rows': len(frame), 'columns': list(frame.columns), 'role': 'support'})
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        walk(v, '/'.join(filter(None, [label, str(k)])))
                else:
                    raise ValueError(f'Unsupported R object {label}: {type(obj).__name__}')
            walk(data, '')
            frame = self.tables[cache]
        elif ext in ('.xls', '.xlsx'):
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with pd.ExcelFile(path) as book:
                    for sheet in book.sheet_names:
                        # Noninteraction sheet counts explicitly include headings; no expression normalization.
                        raw = pd.read_excel(book, sheet_name=sheet, header=None, dtype=str, keep_default_na=False)
                        self.inventory.append({'file': meta['path'], 'table': sheet, 'rows': len(raw), 'columns': [str(i + 1) for i in range(raw.shape[1])],
                                               'preview_rows': native(raw.head(4).values.tolist()), 'role': 'support_sheet_including_headings'})
                    frame = pd.read_excel(book, sheet_name=location, header=header, dtype=str, keep_default_na=False)
        else:
            text = path.read_text(encoding='utf-8-sig')
            lines = text.splitlines()
            comments = []
            while lines and lines[0].lstrip('"').startswith('#'):
                comments.append(lines.pop(0))
            frame = pd.read_csv(io.StringIO('\n'.join(lines)), sep=',' if ext == '.csv' else '\t',
                                dtype=str, keep_default_na=False, header=header)
            self.inventory.append({'file': meta['path'], 'table': location, 'rows': len(frame),
                                   'columns': list(map(str, frame.columns)), 'release_comments': comments, 'role': role})
        self.tables[cache] = frame
        for item in self.inventory:
            if item['file'] == meta['path'] and item['table'] == location:
                item['role'] = role
                if role == 'interaction':
                    item.update(rows=len(frame), columns=list(map(str, frame.columns)), header_zero_based=header)
        return frame

    def support_remaining(self):
        """Inventory unused support assets so the review accounts for every acquired file.
        
        Returns
        -------
        None
            Mutates the documented destination/context; returns no value.
        """
        seen = {i['file'] for i in self.inventory}
        for f in self.manifest['files']:
            if f['path'] not in seen:
                name = f['path']
                self.table(name, header=None if name.endswith('KEGG_SYMBOL_ID.txt') else 0)

    def complex(self, label, members, species_value, file, table='', row='', relationship='required_subunit', namespace='symbol', stoichiometry=None):
        """Preserve all declared members under a source-specific definition key.
        A member list does not itself prove an obligate biological complex.
        
        Parameters
        ----------
        label : str, optional
            Original endpoint/member display label.
        members : sequence or dict
            Declared source members; not inferred pairwise gene combinations.
        species_value : str
            Species attached to the source definition.
        file : str
            Original asset name/path registered in acquisition metadata.
        table : str
            Source worksheet/nested object; empty for a flat table.
        row : object
            Original source row/index used for traceability.
        relationship : str
            Required subunit, proxy dependency or encoding relationship.
        namespace : str
            Identifier namespace; symbols remain case sensitive.
        stoichiometry : sequence or str, optional
            Known source copy counts; None remains unknown, never one.
        
        Returns
        -------
        str
            Source complex key or resolved canonical entity ID.
        """
        members = [(clean(m[0]), clean(m[1])) if isinstance(m, tuple) else (clean(m), clean(m)) for m in members]
        members = [(i, l) for i, l in members if i or l]
        ident = key(self.id, species_value, label, relationship, members)
        if ident not in self.member_cache:
            self.member_cache.add(ident)
            for i, (mid, mlabel) in enumerate(members):
                self.members.append({'complex_key': ident, 'complex_label': clean(label), 'member_id': mid, 'member_label': mlabel,
                                     'namespace': namespace, 'species': species_value, 'relationship': relationship,
                                     'stoichiometry': (stoichiometry or [None] * len(members))[i] if i < len(stoichiometry or members) else None,
                                     'source_file': self.meta(file)['path'], 'source_table': table, 'source_row': str(row), 'member_order': i + 1})
        return ident

    def add(self, file, table, row_number, raw, left, right, *, record_id=None, original=None,
            orientation='ligand_to_receptor', species_basis='dataset', underlying=(), reasons=(), exclusions=(),
            evidence=(), stimulation=None, inhibition=None, directed=None, sign_basis=None, provenance=None):
        """Retain one original interaction row, its endpoints, evidence and unresolved policy flags.
        Record keys track file/table/row identity; semantic keys exclude record location.
        
        Parameters
        ----------
        file : str
            Original asset name/path registered in acquisition metadata.
        table : str
            Source worksheet/nested object; empty for a flat table.
        row_number : int or str
            Source row/index convention retained as text.
        raw : dict
            Complete original source row before endpoint interpretation.
        left : dict or sequence or str
            Ligand endpoint, species list or canonical entity ID for this operation.
        right : dict or sequence or str
            Receptor endpoint, species list or canonical entity ID for this operation.
        record_id : str, optional
            Provider interaction ID when available.
        original : tuple, optional
            Original endpoint labels, identifiers and roles before reorientation.
        orientation : str
            How source endpoint ordering was interpreted.
        species_basis : str
            Basis for species labels; no partner-species imputation.
        underlying : sequence[str]
            Underlying database memberships, not independent replicates.
        reasons : sequence[str]
            Unresolved review flags.
        exclusions : sequence[str]
            Explicit exclusion flags; excluded rows remain retained.
        evidence : sequence[tuple]
            Typed source evidence values, providers and source fields.
        stimulation : bool or None
            Positive stimulation assertion; None means not positively asserted.
        inhibition : bool or None
            Positive inhibition assertion; None means not positively asserted.
        directed : bool or None
            Positive source direction assertion.
        sign_basis : str, optional
            Source sign interpretation and orientation context.
        provenance : str, optional
            Provider provenance label; absent is not native experimental proof.
        
        Returns
        -------
        str
            Newly retained source record key.
        """
        meta = self.meta(file)
        prov = 'provider_orthology' if meta.get('provenance') == 'orthology-derived' else 'unknown'
        prov = provenance or prov
        group = species_group(left['species'], right['species'])
        reviews = set(reasons)
        if prov == 'provider_orthology':
            reviews.add('N01_provider_mouse_orthology')
        if group == 'mouse' and prov == 'unknown':
            reviews.add('N01_mouse_evidence_provenance_unknown')
        if group not in ('human', 'mouse'):
            reviews.add('N04_' + group)
        if orientation not in ('ligand_to_receptor', 'reversed_to_ligand_receptor'):
            reviews.add('N04_direction_or_interaction_scope')
        for e in (left, right):
            if e['type'] == 'complex':
                reviews.add('N02_complex_representation')
            if e['type'] in ('nonprotein_proxy', 'nonprotein_molecule', 'potential_enzyme_proxy'):
                reviews.add('N03_nonprotein_or_proxy')
            if e['mapping'] in ('unresolved', 'ambiguous'):
                reviews.add('unresolved_identifier')
        if stimulation and inhibition:
            reviews.add('conflicting_signs')
        identity = key(self.id, meta['path'], table, str(row_number), clean(record_id))
        original = original or (left['label'], right['label'], left['id'], right['id'], 'ligand', 'receptor')
        record = {'record_key': identity, 'source': self.id, 'source_file': meta['path'], 'source_table': table,
                  'source_row': str(row_number), 'source_record_id': clean(record_id), 'dataset_species': meta.get('species'),
                  'dataset_provenance': meta.get('provenance'), 'evidence_provenance': prov,
                  'original_endpoint_a': native(original[0]), 'original_endpoint_b': native(original[1]),
                  'original_id_a': native(original[2]), 'original_id_b': native(original[3]),
                  'original_role_a': original[4], 'original_role_b': original[5],
                  'ligand_species': left['species'], 'receptor_species': right['species'], 'species_basis': species_basis,
                  'species_group': group, 'orientation': orientation, 'is_stimulation': stimulation,
                  'is_inhibition': inhibition, 'is_directed': directed, 'sign_basis': sign_basis,
                  'underlying_sources': sorted(set(filter(None, underlying))), 'review_reasons': sorted(reviews),
                  'exclusion_reasons': sorted(set(exclusions)), 'raw_json': js(native(raw))}
        for side, e in [('ligand', left), ('receptor', right)]:
            for field in ['label', 'id', 'namespace', 'type', 'mapping', 'complex_key']:
                record[side + '_' + field] = e[field]
        record['semantic_key'] = key(self.id, [(e['id'], e['namespace'], e['type'], e['species'], e['complex_key']) for e in (left, right)], orientation)
        record['status'] = 'excluded' if exclusions else 'review' if reviews else 'candidate'
        self.records.append(record)
        for etype, value, provider, source_field in evidence:
            if clean(value):
                self.evidence.append({'evidence_key': key(identity, etype, str(value), provider, source_field),
                                      'record_key': identity, 'type': etype, 'value': str(value), 'provider': provider, 'source_field': source_field})
        return identity

    def summary(self):
        """Count raw assertions, distinct source semantics and overlapping review flags separately.
        
        Returns
        -------
        dict
            Record, distinct-interaction and overlapping-reason counts.
        """
        records = self.records
        pairs = {r['semantic_key'] for r in records}
        counter = lambda field: dict(sorted(Counter(r[field] for r in records).items()))
        def distinct(predicate):
            return len({r['semantic_key'] for r in records if predicate(r)})
        multi_keys = {k for k, count in Counter(m['complex_key'] for m in self.members if m['relationship'].startswith('required_subunit')).items() if count > 1}
        return {'raw_interaction_records': sum(i['rows'] for i in self.inventory if i['role'] == 'interaction'),
                'normalized_records': len(records), 'distinct_semantic_interactions': len(pairs),
                'repeated_records_beyond_distinct': len(records) - len(pairs), 'dropped_records': 0, 'expanded_interaction_records': 0,
                'by_species': counter('species_group'), 'by_status': counter('status'), 'by_provenance': counter('evidence_provenance'),
                'by_orientation': counter('orientation'), 'ligand_types': counter('ligand_type'),
                'distinct_by_species': {s: distinct(lambda r: r['species_group'] == s) for s in sorted({r['species_group'] for r in records})},
                'candidate_distinct_by_species': {s: distinct(lambda r: r['species_group'] == s and r['status'] == 'candidate') for s in ('human', 'mouse')},
                'review_distinct_by_species': {s: distinct(lambda r: r['species_group'] == s and r['status'] == 'review') for s in ('human', 'mouse')},
                'nonexcluded_distinct_by_species': {s: distinct(lambda r: r['species_group'] == s and r['status'] != 'excluded') for s in ('human', 'mouse')},
                'unresolved_records': sum('unresolved_identifier' in r['review_reasons'] for r in records),
                'nonexcluded_unresolved_records': sum('unresolved_identifier' in r['review_reasons'] and r['status'] != 'excluded' for r in records),
                'unverified_symbol_records': sum(any(r[e + '_mapping'] == 'source_symbol_unverified' for e in ['ligand', 'receptor']) for r in records),
                'complex_records': sum(r['ligand_type'] == 'complex' or r['receptor_type'] == 'complex' for r in records),
                'complex_interactions': distinct(lambda r: r['ligand_type'] == 'complex' or r['receptor_type'] == 'complex'),
                'multisubunit_records': sum(r['ligand_complex_key'] in multi_keys or r['receptor_complex_key'] in multi_keys for r in records),
                'multisubunit_interactions': distinct(lambda r: r['ligand_complex_key'] in multi_keys or r['receptor_complex_key'] in multi_keys),
                'nonprotein_proxy_records': sum('N03_nonprotein_or_proxy' in r['review_reasons'] for r in records),
                'nonprotein_proxy_interactions': distinct(lambda r: 'N03_nonprotein_or_proxy' in r['review_reasons']),
                'evidence_rows': len(self.evidence), 'membership_rows': len(self.members), 'regulator_rows': len(self.regulators),
                'review_reason_counts': dict(sorted(Counter(reason for r in records for reason in r['review_reasons']).items())),
                'exclusion_reason_counts': dict(sorted(Counter(reason for r in records for reason in r['exclusion_reasons']).items()))}


def pmids(value, field, provider=None, prefixed=False):
    """Extract explicit PMID tokens into typed evidence without treating database names as papers.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    field : str
        Exact upstream field from which evidence was extracted.
    provider : str, optional
        Original evidence provider or official provider URL.
    prefixed : bool
        Require an explicit PMID prefix when True.
    
    Returns
    -------
    list[tuple]
        Typed PubMed evidence with provider and exact source field.
    """
    text = clean(value) or ''
    pattern = r'PMID\s*:\s*(\d+)' if prefixed else r'(?<![A-Za-z0-9])\d{5,9}(?![A-Za-z0-9])'
    return [('pubmed', p, provider, field) for p in sorted(set(re.findall(pattern, text, flags=re.I)))]


def mixed_evidence(value, field):
    """Retain complete source evidence text alongside any explicitly prefixed PMIDs.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    field : str
        Exact upstream field from which evidence was extracted.
    
    Returns
    -------
    list[tuple]
        PubMed and complete source-text evidence.
    """
    result = pmids(value, field, prefixed=True)
    # Retain entire evidence assertion even when some explicit PMIDs were extracted.
    if clean(value):
        result.append(('source_evidence_text', clean(value), None, field))
    return result
