"""Same-species identities and explicit complex definitions. Never reads orthology fields."""
from collections import defaultdict, Counter
import json
import re
import warnings

import pandas as pd
import pyarrow.parquet as pq
import rdata

from normalization_core import ROOT, RAW, clean, key, file_hash, species, parts

ANNOTATIONS = ROOT.parent / 'gene-annotation-resources/annotations'


# =============================================================================
# Same-species identity and complete definitions
# =============================================================================
class IdentityError(ValueError):
    pass


class Identities:
    def __init__(self, annotation_root=ANNOTATIONS):
        """Load only same-species identity columns and explicit local complex definitions.
        Annotation and source hashes are retained for provenance; orthology columns are never read.
        
        Parameters
        ----------
        annotation_root : Path, optional
            Annotation manifest/Parquet directory; default is the sibling project.
        
        Returns
        -------
        None
            Mutates the documented destination/context; returns no value.
        
        Raises
        ------
        ValueError
            If reference status, file hashes, taxon or protein-coding scope fails validation.
        """
        self.index = defaultdict(set)
        self.genes, self.entities, self.definitions, self.memberships = {}, {}, {}, {}
        self.inputs = []
        manifest_path = annotation_root / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest['status'] != 'success':
            raise ValueError('Annotation resource is not successful')
        self.inputs.append({'path': str(manifest_path.resolve()), 'sha256': file_hash(manifest_path)})
        self.annotation_version = {k: manifest.get(k) for k in ['run_id', 'schema_version']}
        for sp, taxid in [('human', 9606), ('mouse', 10090)]:
            path = annotation_root / 'Parquet' / (sp + '.parquet')
            digest = manifest['species'][sp]['sha256']['annotations/Parquet/' + sp + '.parquet']
            if file_hash(path) != digest:
                raise ValueError('Stale annotation bytes: ' + str(path))
            self.inputs.append({'path': str(path.resolve()), 'sha256': digest})
            cols = ['symbol', 'entrezgene', 'taxid', 'type_of_gene', 'alias', 'ensembl.gene', 'uniprot.Swiss-Prot', 'uniprot.TrEMBL', 'HGNC' if sp == 'human' else 'MGI']
            for row in pq.read_table(path, columns=cols).to_pylist():
                if row['taxid'] != taxid or row['type_of_gene'] != 'protein-coding':
                    raise ValueError('Annotation species/type mismatch')
                gid = row['entrezgene']
                self.genes[sp, gid] = row['symbol']
                fields = {'NCBIGene': [gid], 'symbol': [row['symbol']], 'alias': row['alias'],
                          'Ensembl': row['ensembl.gene'], 'UniProt': (row['uniprot.Swiss-Prot'] or []) + (row['uniprot.TrEMBL'] or []),
                          'HGNC' if sp == 'human' else 'MGI': [row.get('HGNC' if sp == 'human' else 'MGI')]}
                for ns, values in fields.items():
                    for v in values or []:
                        if v:
                            self.index[sp, ns, self.norm(ns, v)].add(gid)
        # Source lookup first: a source accession's supplied gene symbol is independently
        # resolved in the SAME species; conflicting authoritative mappings are not discarded.
        self.source_index = defaultdict(set)
        for row in pd.read_csv(RAW / 'cellphonedb/gene_input.csv', dtype=str, keep_default_na=False).to_dict('records'):
            hits = self.index['human', 'symbol', row['hgnc_symbol']]
            self.source_index['cellphonedb', 'human', 'UniProt', row['uniprot']].update(hits)
        self.cp_complex = {r['complex_name']: r for r in pd.read_csv(RAW / 'cellphonedb/complex_input.csv', dtype=str, keep_default_na=False).to_dict('records')}
        self.peptides = {r['Ligand id']: r for r in pd.read_csv(RAW / 'gtopdb/peptides.csv', skiprows=1, dtype=str, keep_default_na=False).to_dict('records')}
        self.targets = defaultdict(list)
        for row in pd.read_csv(RAW / 'gtopdb/targets_and_families.csv', skiprows=1, dtype=str, keep_default_na=False).to_dict('records'):
            self.targets[row['Target id']].append(row)
        self.cache = {}
        self.declared = {}
        for sp in ('human', 'mouse'):
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                obj = rdata.read_rda(RAW / 'cellchat' / ('CellChatDB.' + sp + '.rda'))['CellChatDB.' + sp]
            for label, row in obj['complex'].iterrows():
                self.declared['cellchat', sp, label] = [clean(v) for v in row.tolist() if clean(v)]
            for row in pd.read_csv(RAW / 'cellinker' / (sp + '-complex.csv'), dtype=str, keep_default_na=False).to_dict('records'):
                values = [row.get('subunit ' + str(i) + '.1') or row.get('subunit ' + str(i)) for i in range(1, 6)]
                for name in ('ligand compond ID', 'receptor compond ID'):
                    if row.get(name):
                        self.declared['cellinker', sp, row[name]] = [v for v in values if v]

    @staticmethod
    def norm(ns, value):
        """Normalize namespace prefixes for exact same-species lookup, preserving symbol case.
        
        Parameters
        ----------
        ns : str
            Exact identifier namespace.
        value : object
            Source or canonical value to interpret.
        
        Returns
        -------
        str
            Namespace-normalized identifier.
        """
        value = clean(value) or ''
        return value.removeprefix(ns + ':') if ns in ('HGNC', 'MGI', 'NCBIGene') else value

    def store(self, sp, kind, identity, label, basis, gene_id=None, notes=()):
        """Register a species-local entity with deterministic identity and explicit limitations.
        
        Parameters
        ----------
        sp : str
            Species used for identity lookup or output partition.
        kind : str
            Endpoint/entity class, not a species conversion rule.
        identity : object
            Canonical species-local identity components.
        label : str, optional
            Original endpoint/member display label.
        basis : str
            First successful deterministic resolution basis.
        gene_id : str, optional
            Resolved NCBI Gene identifier; not a mature peptide identifier.
        notes : str or sequence[str]
            Explicit scope or unresolved identity limitations.
        
        Returns
        -------
        str
            Registered canonical entity ID.
        """
        eid = 'E:' + key(sp, kind, identity)
        row = {'entity_id': eid, 'species': sp, 'entity_type': kind, 'display_label': label,
               'identity': identity, 'mapping_basis': basis, 'gene_id': gene_id,
               'limitations': sorted(set(notes))}
        if eid not in self.entities:
            self.entities[eid] = row
        return eid

    def gene(self, sp, ns, ident, label=None, source='', strict=False):
        """Resolve a unique same-species source/annotation identity.
        Ambiguous mappings stay review; only non-strict endpoints may retain unverified literal symbols.
        
        Parameters
        ----------
        sp : str
            Species used for identity lookup or output partition.
        ns : str
            Exact identifier namespace.
        ident : str
            Original stable identifier in its source namespace.
        label : str, optional
            Original endpoint/member display label.
        source : str
            Registered provider identifier.
        strict : bool
            Reject unverified literal symbols when True, including complex members.
        
        Returns
        -------
        str
            Canonical entity ID; ambiguous or strict unresolved identities raise IdentityError.
        
        Raises
        ------
        IdentityError
            If an identifier/alias is ambiguous, conflicts with its label, or cannot resolve under strict matching.
        """
        ident, label = self.norm(ns, ident), clean(label)
        cachekey = (sp, ns, ident, label, source, strict)
        if cachekey in self.cache:
            return self.cache[cachekey]
        direct = self.index[sp, ns, ident]
        local = self.source_index[source, sp, ns, ident]
        hits = direct | local
        basis = 'source_lookup+same_species_annotation' if local else 'same_species_annotation'
        if len(hits) > 1:
            raise IdentityError('ambiguous_identifier')
        if not hits and ns == 'symbol':
            hits = self.index[sp, 'alias', ident]
            basis = 'unique_exact_alias_same_species_annotation'
        if len(hits) > 1:
            raise IdentityError('ambiguous_alias')
        if hits:
            gid = next(iter(hits))
            label_hits = self.index[sp, 'symbol', label] if label else set()
            if label_hits and gid not in label_hits:
                raise IdentityError('identifier_symbol_conflict')
            eid = self.store(sp, 'gene_product', 'NCBIGene:' + gid, self.genes[sp, gid], basis, gid)
        elif ns == 'symbol' and not strict and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', ident):
            # Literal exact matching only; punctuation is NEVER expanded into genes.
            eid = self.store(sp, 'gene_product', 'unverified_symbol:' + ident, ident, 'exact_unverified_symbol', notes=['unverified_symbol_no_authoritative_match'])
        else:
            raise IdentityError('unresolved_same_species_identifier')
        self.cache[cachekey] = eid
        return eid

    def gto_gene(self, sp, namespace, ident):
        """Resolve GtoPdb gene cross-references without replacing molecular ligand identities.
        
        Parameters
        ----------
        sp : str
            Species used for identity lookup or output partition.
        namespace : str
            Identifier namespace; symbols remain case sensitive.
        ident : str
            Original stable identifier in its source namespace.
        
        Returns
        -------
        str
            Canonical gene entity ID.
        
        Raises
        ------
        IdentityError
            If source cross-references fail unique, species-compatible encoding-gene resolution.
        """
        if namespace == 'GtoPdb_ligand':
            row = self.peptides.get(ident, {})
            if species(row.get('Species')) != [sp]:
                raise IdentityError('peptide_companion_species_not_single_compatible')
            ids = parts(row.get('UniProt id'), '|')
            if len(ids) != 1:
                raise IdentityError('peptide_encoding_not_unique')
            return self.gene(sp, 'UniProt', ids[0], strict=True)
        rows = self.targets.get(ident, [])
        prefix = 'Human' if sp == 'human' else 'Mouse'
        ids = {r[prefix + ' Entrez Gene'] for r in rows if clean(r[prefix + ' Entrez Gene'])}
        if len(ids) != 1:
            raise IdentityError('target_companion_encoding_not_unique')
        return self.gene(sp, 'NCBIGene', next(iter(ids)), strict=True)

    def complex(self, r, side, members):
        """Resolve the complete declared member set without splitting obligate complexes.
        Unknown stoichiometry and incompatible assembly context remain distinct identities.
        
        Parameters
        ----------
        r : dict
            One normalized source assertion or dependency row.
        side : str
            ligand or receptor endpoint.
        members : sequence or dict
            Declared source members; not inferred pairwise gene combinations.
        
        Returns
        -------
        str
            Source complex key or resolved canonical entity ID.
        
        Raises
        ------
        IdentityError
            If a declared member is missing, duplicated ambiguously, species-uncertain or unresolved; also if GtoPdb obligate-complex support is absent.
        """
        sp, source = r['species_group'], r['source']
        label, kind, ck = r[side + '_label'], r[side + '_type'], r[side + '_complex_key']
        definition_id = 'D:' + key(source, ck)
        if definition_id in self.definitions:
            return self.definitions[definition_id]['entity_id']
        rows = members.get((source, ck), [])
        if not rows:
            raise IdentityError('missing_complex_definition')
        raw = json.loads(r['raw_json'])
        expected = self.declared.get((source, sp, r[side + '_id']))
        if source in ('cellchat', 'cellinker') and expected is None:
            raise IdentityError('missing_source_complex_definition')
        if source in ('omnipathppis', 'dimitrov'):
            expected = parts(r[side + '_id'].removeprefix('COMPLEX:'), '_')
        elif source == 'cellcall':
            expected = parts(raw['Receptor_Symbol'], ',')
        elif source == 'icellnet':
            expected = [clean(raw.get(side.title() + ' ' + str(i))) for i in range(1, 6) if clean(raw.get(side.title() + ' ' + str(i)))]
        if expected is not None and Counter(expected) != Counter(m['member_id'] for m in rows):
            raise IdentityError('incomplete_complex_definition')
        resolved = []
        for m in rows:
            if species(m['species']) != [sp]:
                raise IdentityError('complex_member_species_uncertain')
            if m['namespace'].startswith('GtoPdb'):
                member = self.gto_gene(sp, m['namespace'], m['member_id'])
            else:
                member = self.gene(sp, m['namespace'], m['member_id'], m['member_label'], source, strict=True)
            resolved.append((member, m))
        if len({e for e, _ in resolved}) != len(resolved):
            raise IdentityError('duplicate_complex_components_without_explicit_stoichiometry')
        # Definition integrity: compare the FULL source-defined set with the normalized set.
        context = None
        quantities = {e: m['stoichiometry'] for e, m in resolved}
        supporting_definitions = []
        if source == 'cellphonedb':
            definition = self.cp_complex.get(r[side + '_id'])
            if not definition:
                raise IdentityError('missing_source_complex_definition')
            expected = {definition.get('uniprot_' + str(i)) for i in range(1, 6)} - {'', None}
            if expected != {m['member_id'] for _, m in resolved}:
                raise IdentityError('incomplete_complex_definition')
            context = clean(definition['stoichiometry'])
            if context:
                try:
                    counts = Counter(self.gene(sp, 'symbol', token, strict=True) for token in parts(context, ';'))
                    if set(counts) == set(quantities):
                        quantities = {e: str(counts[e]) for e in counts}
                    else:
                        # Often describes ligand-bound receptor assembly, not endpoint ratios.
                        context = 'assembly_context:' + context
                except IdentityError:
                    context = 'uninterpreted:' + context
        if source == 'gtopdb':
            # These exports can supply just a subset of a pharmacological receptor assembly.
            # Require at least two independently resolvable members; single-subunit partial
            # definitions are not assumed to establish a homomer.
            if len(resolved) < 2 or 'unresolved_member_id_in_companion_table' in r['review_reasons']:
                raise IdentityError('gtopdb_complex_completeness_unestablished')
            if side == 'receptor':
                # A GtoPdb target's subunit field also encodes alternative receptor
                # families (e.g. the seven BMP receptors). A list alone cannot establish
                # obligatory membership. Require the identical complete gene set in
                # a locally available, explicitly obligatory non-GtoPdb definition.
                target_set = {e for e, _ in resolved}
                for did, d in self.definitions.items():
                    if d['source'] == 'gtopdb' or self.entities[d['entity_id']]['entity_type'] != 'complex':
                        continue
                    support = [m for m in self.memberships.values() if m['entity_id'] == d['entity_id']]
                    if {m['member_entity_id'] for m in support} == target_set and all(m['relationship'].startswith('required_subunit') for m in support):
                        supporting_definitions.append(did)
                if not supporting_definitions:
                    raise IdentityError('gtopdb_subunit_list_not_confirmed_obligate_complex')
        canonical_role = lambda role: 'required_subunit' if role.startswith('required_subunit') else role
        structure = sorted((e, canonical_role(m['relationship']), quantities[e]) for e, m in resolved)
        uncertainty_context = context if context and ':' in context else None
        identity = json.dumps([structure, uncertainty_context], sort_keys=True, separators=(',', ':'))
        # Source-defined proxies with unknown product remain distinct even if enzymes coincide.
        if kind == 'nonprotein_proxy':
            identity = json.dumps([source, r[side + '_id'], structure], separators=(',', ':'))
        elif source == 'gtopdb' and side == 'ligand':
            identity = json.dumps(['GtoPdb_ligand', r[side + '_id'], structure], separators=(',', ':'))
        display = label if kind == 'nonprotein_proxy' else ' + '.join(self.entities[e]['display_label'] + ((' ×' + quantities[e]) if quantities[e] not in (None, '1') else '') for e, _ in sorted(resolved))
        eid = self.store(sp, kind, identity, display, 'complete_source_definition', notes=['product_identifier_missing'] if kind == 'nonprotein_proxy' else ['unknown_stoichiometry'] if any(v is None for v in quantities.values()) else [])
        self.definitions[definition_id] = {'definition_id': definition_id, 'entity_id': eid, 'source': source,
            'source_complex_key': ck, 'source_label': label, 'source_file': rows[0]['source_file'],
            'source_table': rows[0]['source_table'], 'source_row': rows[0]['source_row'], 'stoichiometry_context': context,
            'completeness': 'all_declared_components_resolved', 'supporting_definition_ids': sorted(supporting_definitions)}
        for e, m in resolved:
            role = canonical_role(m['relationship'])
            mid = key(eid, e, role, quantities[e])
            self.memberships[mid] = {'membership_id': mid, 'entity_id': eid, 'member_entity_id': e,
                                    'relationship': role, 'stoichiometry': quantities[e], 'species': sp}
        return eid

    def endpoint(self, r, side, members):
        """Resolve one source endpoint under accepted identity, peptide and proxy policies.
        A biosynthetic dependency is never renamed as its nonprotein product.
        
        Parameters
        ----------
        r : dict
            One normalized source assertion or dependency row.
        side : str
            ligand or receptor endpoint.
        members : sequence or dict
            Declared source members; not inferred pairwise gene combinations.
        
        Returns
        -------
        dict or str
            Source endpoint descriptor, or canonical entity ID in Identities.
        
        Raises
        ------
        IdentityError
            If normalized identity/type is uncertain or a molecule has no supported source namespace.
        """
        sp, kind = r['species_group'], r[side + '_type']
        if r[side + '_mapping'] in ('unresolved', 'ambiguous'):
            raise IdentityError('unresolved_normalized_identifier')
        if kind in ('complex', 'nonprotein_proxy'):
            if kind == 'nonprotein_proxy' and not r[side + '_complex_key'] and r['source'] == 'cellchat':
                member = self.gene(sp, 'symbol', r[side + '_id'], strict=True)
                eid = self.store(sp, kind, 'cellchat:' + r[side + '_id'], r[side + '_label'], 'source_single_gene_proxy', notes=['product_identifier_missing'])
                mid = key(eid, member, 'biosynthetic_or_transport_proxy')
                self.memberships[mid] = {'membership_id': mid, 'entity_id': eid, 'member_entity_id': member, 'relationship': 'biosynthetic_or_transport_proxy', 'stoichiometry': None, 'species': sp}
                return eid
            return self.complex(r, side, members)
        if kind not in ('gene_product', 'nonprotein_molecule'):
            raise IdentityError('uncertain_endpoint_type')
        ns, ident, label = [r[side + '_' + f] for f in ['namespace', 'id', 'label']]
        if kind == 'nonprotein_molecule':
            if ns != 'GtoPdb_ligand':
                raise IdentityError('unresolved_molecule_namespace')
            return self.store(sp, kind, ns + ':' + ident, label, 'source_molecule_id')
        if ns.startswith('GtoPdb'):
            raw = json.loads(r['raw_json'])
            if side == 'receptor':
                if clean(raw.get('Target UniProt ID')):
                    return self.gene(sp, 'UniProt', raw['Target UniProt ID'], raw.get('Target Gene Symbol'), strict=True)
                return self.gto_gene(sp, ns, ident)
            gene = self.gene(sp, 'symbol', raw.get('Ligand Gene Symbol'), strict=True) if clean(raw.get('Ligand Gene Symbol')) else self.gto_gene(sp, ns, ident)
            # Preserve distinct endogenous peptides/proteoforms rather than merging them all
            # with their precursor gene. Encoding is a relationship, not entity equivalence.
            eid = self.store(sp, 'encoded_peptide', ns + ':' + ident, label, 'source_peptide_with_gene_encoding', self.entities[gene]['gene_id'], notes=['peptide_identity_retained_separately_from_precursor'])
            mid = key(eid, gene, 'encoded_by')
            self.memberships[mid] = {'membership_id': mid, 'entity_id': eid, 'member_entity_id': gene, 'relationship': 'encoded_by', 'stoichiometry': None, 'species': sp}
            return eid
        return self.gene(sp, ns, ident, label, r['source'])
