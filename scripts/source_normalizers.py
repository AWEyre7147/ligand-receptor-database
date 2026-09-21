"""Source-specific, offline adapters. Each source interaction row is retained once."""
from collections import defaultdict
import re
from urllib.parse import unquote

from normalization_core import (Source, clean, endpoint, key, mixed_evidence, parts, pmids,
                                positive, species, unique_mapping)


# =============================================================================
# Species-preserving source adapters
# =============================================================================
def symbol(label, sp, identifier=None, namespace=None):
    """Describe a source symbol or stable identifier without silently certifying symbol validity.
    
    Parameters
    ----------
    label : str, optional
        Original endpoint/member display label.
    sp : str
        Species used for identity lookup or output partition.
    identifier : str, optional
        Source identifier in the declared namespace.
    namespace : str
        Identifier namespace; symbols remain case sensitive.
    
    Returns
    -------
    dict
        Species-preserving endpoint descriptor.
    """
    return endpoint(label, identifier, namespace or ('NCBIGene' if identifier else 'symbol'),
                    species_values=species(sp), mapping='source_identifier' if identifier else 'source_symbol_unverified')


def compound(ctx, label, members, sp, file, row, table='', namespace='symbol', kind='complex', relationship='required_subunit'):
    """Create a source endpoint and preserve its declared membership dependencies.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    label : str, optional
        Original endpoint/member display label.
    members : sequence or dict
        Declared source members; not inferred pairwise gene combinations.
    sp : str
        Species used for identity lookup or output partition.
    file : str
        Original asset name/path registered in acquisition metadata.
    row : object
        Original source row/index used for traceability.
    table : str
        Source worksheet/nested object; empty for a flat table.
    namespace : str
        Identifier namespace; symbols remain case sensitive.
    kind : str
        Endpoint/entity class, not a species conversion rule.
    relationship : str
        Required subunit, proxy dependency or encoding relationship.
    
    Returns
    -------
    dict
        Source complex/proxy endpoint linked to its members.
    """
    ck = ctx.complex(label, members, sp, file, table, row, namespace=namespace, relationship=relationship)
    return endpoint(label, label, 'source_complex', kind, species(sp), complex_key=ck)


def source_refs(value, field):
    """Retain database memberships as provenance, not publication evidence.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    field : str
        Exact upstream field from which evidence was extracted.
    
    Returns
    -------
    list[tuple]
        Database-membership evidence tuples.
    """
    return [('database_membership', v, v, field) for v in parts(value)]


def cellcall(ctx):
    """Retain LR-TF/pathway rows and provider mouse provenance; KEGG IDs remain pathway evidence.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    for meta in ctx.manifest['files']:
        if 'new_ligand_receptor_TFs' not in meta['path']:
            continue
        f, sp = meta['path'], meta['species']
        df = ctx.table(f, role='interaction')
        for n, row in enumerate(df.to_dict('records'), 2):
            left = symbol(row['Ligand_Symbol'], sp, row['Ligand_ID'])
            right = symbol(row['Receptor_Symbol'], sp, row['Receptor_ID'])
            if ',' in (clean(row['Receptor_Symbol']) or ''):
                right = compound(ctx, row['Receptor_Symbol'], parts(row['Receptor_Symbol'], ','), sp, f, n)
            ctx.add(f, '', n, row, left, right, evidence=[('pathway', row['pathway_ID'], 'KEGG', 'pathway_ID')],
                    original=(row['Ligand_Symbol'], row['Receptor_Symbol'], row['Ligand_ID'], row['Receptor_ID'], 'ligand', 'receptor'))
    ctx.limitations.append('Each LR-TF/pathway row is retained; core/extended identity remains in source_file. KEGG pathway IDs are not PubMed evidence. Human native asset provenance does not establish per-record experimental evidence.')


def cellinker(ctx):
    """Resolve provider complex lookup tables and retain Pmubmed.ID evidence verbatim by type.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    for sp, f in [('human', 'Homo sapiens.txt'), ('mouse', 'Mus musculus.txt')]:
        cf = sp + '-complex.csv'
        complexes = ctx.table(cf)
        lookup = {}
        for n, row in enumerate(complexes.to_dict('records'), 2):
            ids = [clean(row.get('ligand compond ID')), clean(row.get('receptor compond ID'))]
            members = []
            for k in range(1, 6):
                label, mid = clean(row.get(f'subunit {k}')), clean(row.get(f'subunit {k}.1'))
                if label or mid:
                    members.append((mid or label, label))
            for ident in filter(None, ids):
                lookup[ident] = compound(ctx, ident, members, sp, cf, n, namespace='NCBIGene')
        for n, row in enumerate(ctx.table(f, role='interaction').to_dict('records'), 2):
            ends = []
            for side in ['Ligand', 'Receptor']:
                ident, label = row[side + '_id'], row[side + '_symbol']
                e = dict(lookup[ident]) if ident in lookup else symbol(label, sp, ident)
                e['label'] = clean(label)
                if ident.startswith(('CH', 'CM')) and ident not in lookup:
                    e.update(type='complex', mapping='unresolved')
                ends.append(e)
            ctx.add(f, '', n, row, *ends, record_id=row['LRID'], underlying=parts(row['Other.DB']),
                    evidence=pmids(row['Pmubmed.ID'], 'Pmubmed.ID') + source_refs(row['Other.DB'], 'Other.DB'))


def encoded_complex(ctx, ident, label, sp, file, row):
    """Decode only the explicit COMPLEX: identifier syntax into UniProt members.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    ident : str
        Original stable identifier in its source namespace.
    label : str, optional
        Original endpoint/member display label.
    sp : str
        Species used for identity lookup or output partition.
    file : str
        Original asset name/path registered in acquisition metadata.
    row : object
        Original source row/index used for traceability.
    
    Returns
    -------
    dict
        Protein or explicit source complex endpoint.
    """
    if (clean(ident) or '').startswith('COMPLEX:'):
        # Explicit source complex ID syntax, NOT arbitrary punctuation in a gene label.
        members = parts(ident.removeprefix('COMPLEX:'), '_')
        result = compound(ctx, ident, [(m, None) for m in members], sp, file, row, namespace='UniProt')
        result['label'] = clean(label)
        return result
    return endpoint(label, ident, 'UniProt', species_values=species(sp))


def dimitrov(ctx):
    """Retain consensus and constituent LIANA rows separately; constituents are not independent support.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    f = 'omni_resource.csv'
    for n, row in enumerate(ctx.table(f, role='interaction').to_dict('records'), 2):
        left = encoded_complex(ctx, row['source'], row['source_genesymbol'], 'human', f, n)
        right = encoded_complex(ctx, row['target'], row['target_genesymbol'], 'human', f, n)
        resource = row['resource']
        reasons = ['N04_constituent_resource_not_consensus'] if resource != 'consensus' else []
        ctx.add(f, '', n, row, left, right, record_id=row.get('Unnamed: 0'), underlying=[resource], reasons=reasons,
                evidence=[('aggregate_membership', resource, 'LIANA', 'resource')])
    ctx.limitations.append('Entire LIANA distribution retained; consensus is the Dimitrov candidate subset. Constituent rows remain for audit and are not independent evidence. Complex UniProt IDs and symbol lists are not positionally paired without a lookup.')


def omnipath(ctx):
    """Orient human PPI edges only with unambiguous ligand/receptor roles.
    Mouse direction stays unresolved; reversing an edge never transfers its original sign.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    inter = ctx.table('intercell.tsv')
    roles = inter[(inter['scope'] == 'generic') & (inter['source'] == 'composite')]
    ligands = set(roles.loc[roles.category == 'ligand', 'uniprot'])
    receptors = set(roles.loc[roles.category == 'receptor', 'uniprot'])
    complex_table = ctx.table('complexes.tsv')
    by_components = defaultdict(list)
    for row in complex_table.to_dict('records'):
        by_components[row['components']].append(row)
    for sp in ['human', 'mouse']:
        f = sp + '/interactions.tsv'
        for n, row in enumerate(ctx.table(f, role='interaction').to_dict('records'), 2):
            left = encoded_complex(ctx, row['source'], row['source_genesymbol'], row['ncbi_tax_id_source'], f, n)
            right = encoded_complex(ctx, row['target'], row['target_genesymbol'], row['ncbi_tax_id_target'], f, n)
            forward = sp == 'human' and row['source'] in ligands and row['target'] in receptors
            reverse = sp == 'human' and row['target'] in ligands and row['source'] in receptors
            orientation = 'unresolved_source_target'
            if forward and not reverse:
                orientation = 'ligand_to_receptor'
            elif reverse and not forward:
                left, right = right, left
                orientation = 'reversed_to_ligand_receptor'
            evidence = []
            for ref in parts(row['references']):
                provider, sep, value = ref.rpartition(':')
                evidence.append(('pubmed' if value.isdigit() and sep else 'source_evidence_text', value if sep else ref, provider if sep else None, 'references'))
            stim, inhib = positive(row['is_stimulation']), positive(row['is_inhibition'])
            # Source PPI sign is not necessarily the sign of the LR orientation (especially after reversal).
            ctx.add(f, '', n, row, left, right, original=(row['source_genesymbol'], row['target_genesymbol'], row['source'], row['target'], 'source', 'target'),
                    orientation=orientation, species_basis='explicit_endpoint_taxon', underlying=parts(row['sources']), evidence=evidence,
                    stimulation=stim if orientation == 'ligand_to_receptor' else None,
                    inhibition=inhib if orientation == 'ligand_to_receptor' else None,
                    directed=positive(row['is_directed']), sign_basis='source PPI sign; retained in raw_json if LR orientation is reversed/unresolved')
    ctx.limitations.append('Human orientation uses generic composite ligand/receptor annotations. Ambiguous and mouse source-target edges are retained pending LR direction review; human roles are never translated to mouse. PPI signs are not transferred across a reversal. Complex member IDs are explicit; the human support table is not used to invent mouse membership.')


def cellphonedb(ctx):
    """Resolve protein/complex partners through provider lookups and retain assembly context.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    genes = ctx.table('gene_input.csv')
    proteins = {r['uniprot']: r for r in ctx.table('protein_input.csv').to_dict('records')}
    gene_map = defaultdict(set)
    for row in genes.to_dict('records'):
        if clean(row['hgnc_symbol']):
            gene_map[row['uniprot']].add(row['hgnc_symbol'])
    complexes = {r['complex_name']: (n, r) for n, r in enumerate(ctx.table('complex_input.csv').to_dict('records'), 2)}
    def resolve(ident):
        if ident in complexes:
            n, row = complexes[ident]
            mids = [row.get(f'uniprot_{i}') for i in range(1, 6) if clean(row.get(f'uniprot_{i}'))]
            is_proxy = 'biosynth' in str(row.get('other_desc', '')).lower() or '_by' in ident
            ck = ctx.complex(ident, [(mid, unique_mapping(gene_map[mid])[0]) for mid in mids], 'human', 'complex_input.csv', row=n,
                             namespace='UniProt', relationship='biosynthetic_proxy_component' if is_proxy else 'required_subunit')
            return endpoint(ident, ident, 'CellPhoneDB_entity', 'nonprotein_proxy' if is_proxy else 'complex', ['human'], complex_key=ck)
        label, mapping = unique_mapping(gene_map[ident])
        return endpoint(label or ident, ident, 'UniProt', species_values=['human'], mapping=mapping)
    f = 'interaction_input.csv'
    for n, row in enumerate(ctx.table(f, role='interaction').to_dict('records'), 2):
        left, right = resolve(row['partner_a']), resolve(row['partner_b'])
        direction = row['directionality']
        orientation = 'ligand_to_receptor' if direction == 'Ligand-Receptor' else 'source_' + direction.lower()
        evidence = mixed_evidence(row['source'], 'source')
        reasons = ['N03_conflicting_nonprotein_flag'] if row['is_ppi'] == 'False' and all(e['type'] != 'nonprotein_proxy' for e in (left, right)) else []
        for field in ['reactome_reaction', 'reactome_complex', 'reactome_pathway', 'complexPortal_complex']:
            if clean(row[field]):
                evidence.append(('database_record', row[field], field.split('_')[0], field))
        ctx.add(f, '', n, row, left, right, record_id=row['id_cp_interaction'], orientation=orientation,
                original=(row['partner_a'], row['partner_b'], row['partner_a'], row['partner_b'], 'partner_a', 'partner_b'),
                evidence=evidence, reasons=reasons, underlying=[v for v in parts(row['source']) if not v.startswith('PMID:')],
                inhibition=True if row['modulatory_effect'] == 'Inhibitory' else None,
                sign_basis='explicit CellPhoneDB modulatory_effect; absent activation remains unknown')
    ctx.limitations.append('Non-LR adhesion/gap/ligand-ligand/receptor-receptor rows remain review records. Biosynthetic enzyme representations keep distinct source-entity identities and component roles; no enzyme is relabeled as the ligand molecule.')


def cellchat(ctx):
    """Separate required complexes, nonprotein proxies and optional signaling regulators.
    The neurotransmitter flag alone does not classify an endpoint as nonprotein.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    for sp in ['human', 'mouse']:
        f, base = 'CellChatDB.' + sp + '.rda', 'CellChatDB.' + sp
        df = ctx.table(f, base + '/interaction', role='interaction')
        complexes = ctx.table(f, base + '/complex')
        cofactors = ctx.table(f, base + '/cofactor')
        gene_info = ctx.table(f, base + '/geneInfo')
        known_symbols = set(gene_info['Symbol'])
        for index, row in df.iterrows():
            raw = row.to_dict()
            nonprotein = row['annotation'] == 'Non-protein Signaling'
            def resolve(label, is_ligand):
                proxy = nonprotein and is_ligand
                if label in complexes.index:
                    members = [v for v in complexes.loc[label].tolist() if clean(v)]
                    return compound(ctx, label, members, sp, f, label, base + '/complex',
                                    kind='nonprotein_proxy' if proxy else 'complex',
                                    relationship='biosynthetic_or_transport_proxy' if proxy else 'required_subunit')
                return endpoint(label, label, 'symbol', 'nonprotein_proxy' if proxy else 'gene_product', [sp],
                                mapping='source_lookup' if label in known_symbols else 'unresolved')
            left, right = resolve(row['ligand'], True), resolve(row['receptor'], False)
            rec = ctx.add(f, base + '/interaction', index, raw, left, right, record_id=row['interaction_name'],
                          evidence=mixed_evidence(row['evidence'], 'evidence'),
                          reasons=['neurotransmitter_flag_not_used_for_entity_type'] if positive(row['is_neurotransmitter']) and not nonprotein else [])
            for role in ['agonist', 'antagonist', 'co_A_receptor', 'co_I_receptor']:
                group = clean(row[role])
                if group:
                    members = [clean(x) for x in cofactors.loc[group].tolist() if clean(x)] if group in cofactors.index else [None]
                    for member in members:
                        ctx.regulators.append({'record_key': rec, 'role': role, 'group_label': group, 'member_label': member,
                                               'species': sp, 'source_file': ctx.meta(f)['path']})
    ctx.limitations.append('Non-protein Signaling annotation identifies proxy records. is_neurotransmitter is not sufficient: it also marks protein signaling rows. Complex-table proxy components are biosynthetic/transport dependencies, not subunits of the molecule. Agonists, antagonists and co-receptors are separate regulator links.')


def connectomedb(ctx):
    """Preserve species-specific provider assertions and distinguish summary-linked PMIDs.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    for sp in ['human', 'mouse']:
        f = 'ConnectomeDB2025_' + sp + '.csv'
        for n, row in enumerate(ctx.table(f, role='interaction').to_dict('records'), 2):
            ends = []
            for side in ['Ligand', 'Receptor']:
                label = re.sub(r'\s+\(.*$', '', row[side + ' Symbols']).strip()
                field = side + (' HGNC ID' if sp == 'human' else ' MGI ID')
                ident = clean(row[field])
                e = endpoint(label, ident, 'HGNC' if sp == 'human' else 'MGI', species_values=[sp], mapping='source_identifier' if ident else 'unresolved')
                if ident and any(d in ident for d in [';', '|', ',']):
                    e.update(type='ambiguous_entity', mapping='ambiguous')
                ends.append(e)
            refs = []
            match = re.search(r'Pubmed-ID-([\d, %]+)', unquote(row['AI summary']), re.I)
            if match:
                refs = [('pubmed_embedded_in_provider_link', p, 'ConnectomeDB', 'AI summary URL') for p in re.findall(r'\d{5,9}', match[1])]
            refs.append(('provider_evidence_class', row['Evidence'], 'ConnectomeDB', 'Evidence'))
            ctx.add(f, '', n, row, *ends, record_id=row['Interaction ID'], evidence=refs,
                    original=(row['Ligand Symbols'], row['Receptor Symbols'], ends[0]['id'], ends[1]['id'], 'ligand', 'receptor'),
                    provenance='native_reported' if sp == 'human' and row['Evidence'] == 'Direct' else None)
    ctx.limitations.append('Parenthetical aliases are preserved in raw_json and original labels, not split as subunits. PubMed IDs embedded in provider AI-summary links have their own evidence type; generated summaries were not fetched or treated as experimental evidence.')


def simple_pairs(ctx):
    """Normalize simple source pairs while preserving unknown symbols and source scope.
    Pavlicev proxy ambiguity and Kirouac free-text receptor groups remain explicit.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    config = {
        'lrdb': ('LRdb.txt', '', 0, 'ligand', 'receptor'),
        'italk': ('LR_database.rda', 'database', 0, 'Ligand.ApprovedSymbol', 'Receptor.ApprovedSymbol'),
        'ramilowski': ('PairsLigRec.txt', '', 0, 'Ligand.ApprovedSymbol', 'Receptor.ApprovedSymbol'),
        'pavlicev': ('supp_gr.207597.116_Supplemental_Tables.xlsx', 'S5', 3, 'Ligand', 'Receptor'),
        'kirouac': ('msb201071-s2.xls', 'SF_R assign', 0, 'SF Symbol', 'R Symbol'),
    }
    f, table, header, lc, rc = config[ctx.id]
    for n, row in enumerate(ctx.table(f, table, header, role='interaction').to_dict('records'), 1 if ctx.id == 'italk' else header + 2):
        left = symbol(row[lc], 'human', row.get('SF ID'))
        right = symbol(row[rc], 'human', row.get('R ID'))
        if ctx.id == 'italk':
            for e, field in [(left, 'Ligand.Name'), (right, 'Receptor.Name')]:
                if not e['id']:
                    e.update(label=clean(row[field]), id=clean(row[field]), namespace='source_label',
                             type='unknown', species=[], mapping='unresolved')
        evidence, underlying, reasons = [], [], []
        if ctx.id == 'ramilowski':
            evidence = pmids(row['PMID.Manual'], 'PMID.Manual')
            underlying = [col for col in ['DLRP', 'HPMR', 'IUPHAR', 'HPRD', 'STRING.binding', 'STRING.experiment'] if clean(row[col])]
            evidence += [('source_evidence_class', row['Pair.Evidence'], None, 'Pair.Evidence')] + source_refs(';'.join(underlying), 'source columns')
            if 'putative' in str(row['Pair.Evidence']).lower() or row['Pair.Source'] == 'putative':
                reasons.append('N04_putative_interaction')
        if ctx.id == 'pavlicev':
            underlying = ['GtoPdb', 'DLRP', 'publication additions']
            reasons.append('N03_unclassified_proxy_possible_in_publication')
            original = (row[rc], row[lc], row[rc], row[lc], 'receptor', 'ligand')
        else:
            original = (row[lc], row[rc], row.get('SF ID', row[lc]), row.get('R ID', row[rc]), 'ligand', 'receptor')
        descriptions = ' '.join(str(row.get(c, '')) for c in ['d.ligand', 'Ligand.Name']).lower()
        if any(w in descriptions for w in ['synthase', 'synthetase', 'decarboxylase', 'acetyltransferase']):
            reasons.append('N03_enzyme_named_ligand_requires_review')
            left['type'] = 'potential_enzyme_proxy'
        ctx.add(f, table, n, row, left, right, record_id=row.get('Pair.Name'), underlying=underlying, evidence=evidence,
                reasons=reasons, original=original, orientation='reversed_to_ligand_receptor' if ctx.id == 'pavlicev' else 'ligand_to_receptor')
    if ctx.id == 'kirouac':
        # The publication also supplies a broader, free-text mapping table. Do not silently discard it.
        f, table = 'msb201071-s3.xls', 'S12'
        for n, row in enumerate(ctx.table(f, table, 1, role='interaction').to_dict('records'), 3):
            left = endpoint(row['LIGAND'], namespace='publication_label', kind='unknown', species_values=['human'], mapping='unresolved')
            right = endpoint(row['RECEPTOR(S)'], namespace='publication_label', kind='unknown', species_values=['human'], mapping='unresolved')
            ctx.add(f, table, n, row, left, right, reasons=['N04_free_text_receptor_alternatives_or_complex'])
        ctx.limitations.append('SF_R assign supplies explicit gene-ID edges; S12 separately supplies free-text receptor lists. S12 punctuation is not expanded into guessed alternatives/complexes, and those unresolved assertions are counted separately from numeric pairs. Dataset bibliography is not pair evidence.')
    if ctx.id == 'pavlicev':
        ctx.limitations.append('Only S5 is interactions (Receptor first, Ligand second). Header explicitly states enzyme proxies are included, but supplies no per-row proxy marker. All rows retain that review flag; no exact total of true proxies is claimed. Legacy labels/case remain unchanged, including CCl19.')
    if ctx.id in ('italk', 'lrdb'):
        ctx.limitations.append('No pair-level publication evidence is supplied. Database citation is not assigned to every pair. Enzyme descriptions only flag possible proxies, not proven molecule identity.')


def nichenet(ctx):
    """Preserve provider orthology labels and literal symbols, including underscores.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    for sp in ['human', 'mouse']:
        f = 'lr_network_' + sp + '_21122021.rds'
        for n, row in enumerate(ctx.table(f, role='interaction').to_dict('records'), 1):
            ctx.add(f, '', n, row, symbol(row['from'], sp), symbol(row['to'], sp), underlying=[row['database'], row['source']],
                    evidence=[('aggregate_membership', row[c], 'NicheNet', c) for c in ['database', 'source']])
    ctx.limitations.append('Network provider membership is not PubMed evidence. C4B_2 and other labels are kept intact; underscore is not assumed to mean complex membership.')


def celltalkdb(ctx):
    """Retain provider human/mouse pairs, source gene IDs and row-level evidence.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    for sp in ['human', 'mouse']:
        f = sp + '_lr_pair.rds'
        for n, row in enumerate(ctx.table(f, role='interaction').to_dict('records'), 1):
            ends = [symbol(row[side + '_gene_symbol'], sp, row[side + '_gene_id']) for side in ['ligand', 'receptor']]
            ctx.add(f, '', n, row, *ends, record_id=row['lr_pair'], evidence=pmids(row['evidence'], 'evidence'))
    ctx.limitations.append('NCBI gene IDs and Ensembl identifiers are already source-supplied; no external alias mapping or species conversion is needed. Manual annotation support columns can contain symbols despite an Entrez-looking column name; they are not coerced to numeric IDs.')


def icellnet(ctx):
    """Retain explicit ligand and receptor subunit columns as intact definitions.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    f = 'ICELLNETdb.tsv'
    for n, row in enumerate(ctx.table(f, role='interaction').to_dict('records'), 2):
        ends = []
        for side, count in [('Ligand', 4), ('Receptor', 5)]:
            members = [clean(row.get(f'{side} {i}')) for i in range(1, count + 1) if clean(row.get(f'{side} {i}'))]
            if len(members) > 1:
                ends.append(compound(ctx, '+'.join(members), members, 'human', f, n))
            else:
                ends.append(symbol(members[0] if members else None, 'human'))
        ctx.add(f, '', n, row, *ends, evidence=pmids(row['Reference'], 'Reference'))


def gtopdb(ctx):
    """Retain pharmacology endpoints, molecular identities and endogenous/species metadata.
    Missing ligand species is never filled from the receptor; synthetic rows remain auditable.
    
    Parameters
    ----------
    ctx : Source
        Accumulating provider records, support tables and evidence.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    peptide_df = ctx.table('peptides.csv')
    peptides = {row['Ligand id']: row for row in peptide_df.to_dict('records')}
    targets = ctx.table('targets_and_families.csv')
    target_names = defaultdict(set)
    for item in targets.to_dict('records'):
        for id_field, name_field in [('Target id', 'Target name'), ('Subunit id', 'Subunit name')]:
            if clean(item.get(id_field)) and clean(item.get(name_field)):
                target_names[item[id_field]].add(item[name_field])
    f = 'interactions.csv'
    for n, row in enumerate(ctx.table(f, role='interaction').to_dict('records'), 3):
        pep = peptides.get(row['Ligand ID'], {})
        ls, rs = species(row['Ligand Species']), species(row['Target Species'])
        basis = 'explicit_endpoint_species'
        if not ls and clean(pep.get('Species')):
            ls = species(pep['Species'])
            basis = 'ligand_species_from_same_ligand_id_peptide_lookup; target_explicit'
        ltype = row['Ligand Type']
        kind = {'Synthetic organic': 'synthetic', 'Peptide': 'gene_product', 'Antibody': 'gene_product',
                'Metabolite': 'nonprotein_molecule', 'Natural product': 'nonprotein_molecule',
                'Inorganic': 'nonprotein_molecule', 'Nucleic acid': 'nonprotein_molecule'}.get(ltype, 'unknown')
        left = endpoint(row['Ligand'], row['Ligand ID'], 'GtoPdb_ligand', kind, ls)
        right = endpoint(row['Target'], row['Target ID'], 'GtoPdb_target', 'gene_product', rs)
        reasons, exclusions = [], []
        if ltype in ('Synthetic organic', 'Antibody') or (ltype == 'Peptide' and row['Endogenous'].lower() == 'false'):
            exclusions.append('nonendogenous_pharmacological_ligand')
        elif row['Endogenous'].lower() != 'true':
            reasons.append('N03_endogenous_status_not_positive')
        if rs and not any(s in ('human', 'mouse') for s in rs):
            exclusions.append('target_species_outside_human_mouse')
        if kind == 'gene_product' and not clean(row['Ligand Gene Symbol']) and not clean(pep.get('UniProt id')):
            left['mapping'] = 'unresolved'
            reasons.append('gene_encoded_ligand_unconfirmed')
        for side, e, field, namespace in [('ligand', left, 'Ligand Subunit IDs', 'GtoPdb_ligand'), ('receptor', right, 'Target Subunit IDs', 'GtoPdb_target')]:
            subs = parts(row[field], '|')
            if side == 'ligand' and not subs:
                subs = parts(pep.get('Subunit ids'), '|')
            if subs:
                members = [(s, clean(peptides.get(s, {}).get('Name')) if side == 'ligand' else unique_mapping(target_names.get(s, set()))[0]) for s in subs]
                missing_members = any(s not in peptides for s in subs) if side == 'ligand' else any(s not in target_names for s in subs)
                if missing_members:
                    reasons.append('unresolved_member_id_in_companion_table')
                ck = ctx.complex(e['id'], members, '|'.join(e['species']), f, row=n, namespace=namespace,
                                 relationship='required_subunit_stoichiometry_unknown')
                e.update(type='complex', complex_key=ck)
        # A target can itself be a ligand entity rather than a gene-encoded receptor.
        if clean(row['Target Ligand ID']):
            right = endpoint(row['Target Ligand'], row['Target Ligand ID'], 'GtoPdb_ligand', 'unknown', rs, mapping='unresolved')
            reasons.append('N04_target_is_ligand_entity')
        evidence = pmids(row['PubMed ID'], 'PubMed ID')
        for value in parts(row['Webpage URLs'], '|'):
            evidence.append(('url', value, None, 'Webpage URLs'))
        for value in parts(row['Patent Numbers'], '|'):
            evidence.append(('patent', value, None, 'Patent Numbers'))
        # Action, agonism and binding are preserved without translating them into LR activation.
        ctx.add(f, '', n, row, left, right, species_basis=basis, reasons=reasons, exclusions=exclusions, evidence=evidence,
                original=(row['Ligand'], row['Target'], row['Ligand ID'], row['Target ID'], 'ligand', 'target'),
                sign_basis='GtoPdb Action/Type retained verbatim; no agonism-to-stimulation mapping')
    ctx.limitations.append('All pharmacology rows are retained, including explicit exclusions. Molecular ligand IDs remain distinct from gene symbols/proteoforms. Species sets are not expanded or matched to target species; same-ID peptide lookup fills only missing ligand species. No universal LR sign is inferred from binding/agonism. Nonprotein ligands lack a comprehensive small-molecule companion table; no structure or gene mapping is invented.')


ADAPTERS = {'cellcall': cellcall, 'cellinker': cellinker, 'omnipathppis': omnipath, 'dimitrov': dimitrov,
            'cellphonedb': cellphonedb, 'cellchat': cellchat, 'connectomedb': connectomedb,
            'nichenet': nichenet, 'celltalkdb': celltalkdb, 'icellnet': icellnet, 'gtopdb': gtopdb,
            **{s: simple_pairs for s in ['lrdb', 'italk', 'ramilowski', 'pavlicev', 'kirouac']}}


def normalize(source_id, manifest):
    """Dispatch one verified local source to its adapter and inventory remaining support assets.
    
    Parameters
    ----------
    source_id : str
        One registered provider identifier.
    manifest : dict
        Recorded source selections, checksums and processing state.
    
    Returns
    -------
    Source
        All normalized source records, evidence, memberships and inventory.
    """
    ctx = Source(source_id, manifest)
    ADAPTERS[source_id](ctx)
    ctx.support_remaining()
    return ctx
