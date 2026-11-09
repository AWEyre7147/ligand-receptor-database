"""Assign readable, release-local IDs after scientific assembly is complete."""


# =============================================================================
# Release-local identifiers
# =============================================================================
def assign_readable_ids(tables: dict[str, list[dict]]) -> None:
    """Replace final assembly IDs without changing normalized provenance keys.

    IDs are assigned across all species before partitioning. Sorting canonical
    keys makes numbering repeatable for identical inputs, independent of row
    traversal order. They are not persistent accessions across database releases.
    The canonical identity payload and provider fields remain unchanged.

    Parameters
    ----------
    tables : dict[str, list[dict]]
        Fully assembled canonical tables, modified in place exactly once.

    Returns
    -------
    None
        All final foreign keys are rewritten together. Normalized record and
        evidence keys are retained alongside readable record/evidence IDs.

    Raises
    ------
    ValueError
        If primary keys are absent, duplicated, or already numbered, or if a
        foreign key does not resolve. Validate before applying any mutations.
    """
    specs = (
        ('interactions', 'interaction_id', 'LRI'),
        ('entities', 'entity_id', 'ENT'),
        ('memberships', 'membership_id', 'MEM'),
        ('regulators', 'regulator_id', 'REG'),
        ('definitions', 'definition_id', 'CDF'),
        ('source_annotations', 'annotation_id', 'ANN'),
        ('assertions', 'record_key', 'AST'),
        ('evidence', 'evidence_key', 'EVD'),
    )
    maps = {}
    for name, field, prefix in specs:
        values = [row[field] for row in tables[name]]
        if any(not isinstance(v, str) or not v for v in values):
            raise ValueError(f'Missing {field} in {name}')
        if len(set(values)) != len(values):
            raise ValueError(f'Duplicate {field} in {name}')
        if any(v.startswith(prefix + '-') for v in values):
            raise ValueError(f'Already numbered {name}')
        maps[field] = {value: f'{prefix}-{n:06d}'
                       for n, value in enumerate(sorted(values), 1)}

    # Source-local complex keys are meaningful only with their source. Preserve
    # that original pair, adding a readable ID rather than replacing provenance.
    complex_keys = {(r['source'], r['complex_key']) for r in tables['source_members']}
    complex_keys.update((r['source'], r['source_complex_key'])
                        for r in tables['definitions'])
    if any(not source or not key for source, key in complex_keys):
        raise ValueError('Missing source-local complex identity')
    complex_ids = {value: f'SCX-{n:06d}'
                   for n, value in enumerate(sorted(complex_keys), 1)}
    fields = {
        'interaction_id': 'interaction_id',
        'related_interaction_id': 'interaction_id',
        'entity_id': 'entity_id', 'ligand_entity_id': 'entity_id',
        'receptor_entity_id': 'entity_id', 'member_entity_id': 'entity_id',
        'membership_id': 'membership_id', 'regulator_id': 'regulator_id',
        'definition_id': 'definition_id', 'annotation_id': 'annotation_id',
    }
    updates = []
    for name, rows in tables.items():
        for row in rows:
            replacement = {}
            try:
                for field, target in fields.items():
                    if field in row and row[field] is not None:
                        replacement[field] = maps[target][row[field]]
                if 'supporting_definition_ids' in row:
                    replacement['supporting_definition_ids'] = [
                        maps['definition_id'][v] for v in row['supporting_definition_ids']]
                if 'record_key' in row:
                    replacement['record_id'] = maps['record_key'][row['record_key']]
                if 'evidence_key' in row:
                    replacement['evidence_id'] = maps['evidence_key'][row['evidence_key']]
                if name in ('source_members', 'definitions'):
                    key = row['complex_key' if name == 'source_members' else 'source_complex_key']
                    replacement['source_complex_id'] = complex_ids[row['source'], key]
            except KeyError as exc:
                raise ValueError(f'Unresolved internal reference in {name}: {exc}') from exc
            updates.append((row, replacement))
    for row, replacement in updates:
        row.update(replacement)
