"""Small fixtures use the actual supplied source column names and record semantics."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import normalization_core as core
import source_normalizers as adapters
from normalize_sources import validate


def context(source, tables, species='human', provenance='unknown'):
    """Build an in-memory source reader so adapter tests cannot acquire data.
    
    Parameters
    ----------
    source : str
        Registered provider being tested.
    tables : dict
        Source-shaped fixture tables indexed by file/object location.
    species : str
        Provider asset species label.
    provenance : str
        Provider asset provenance label.
    
    Returns
    -------
    Source
        Source accumulator with its reader replaced by fixture lookup.
    """
    filenames = sorted({k[0] if isinstance(k, tuple) else k for k in tables})
    ctx = core.Source(source, {'files': [{'path': source + '/' + f, 'species': species, 'provenance': provenance} for f in filenames]})
    def read(file, location='', header=0, role='support'):
        file = file.removeprefix(source + '/')
        return tables[(file, location)] if (file, location) in tables else tables[file]
    ctx.table = read
    return ctx


def gtop_row(**updates):
    """Create a source-shaped endogenous GtoPdb interaction fixture.
    
    Parameters
    ----------
    updates : dict
        Fields to replace for one pharmacology/species regression.
    
    Returns
    -------
    dict
        Synthetic GtoPdb input row.
    """
    row = {k: '' for k in ['Ligand Species', 'Target Species', 'Ligand Type', 'Ligand', 'Ligand ID', 'Target', 'Target ID',
                           'Ligand Subunit IDs', 'Target Subunit IDs', 'Ligand Gene Symbol', 'Target Ligand ID', 'Target Ligand',
                           'PubMed ID', 'Webpage URLs', 'Patent Numbers', 'Action', 'Type', 'Endogenous']}
    row.update({'Ligand': 'CCL19', 'Ligand ID': '4417', 'Target': 'CCR7', 'Target ID': '64',
                'Ligand Type': 'Peptide', 'Endogenous': 'true', 'Ligand Gene Symbol': 'Ccl19', 'Action': 'Agonist'})
    row.update(updates)
    return row


def gtop_context(rows, peptides=None):
    """Wrap GtoPdb interaction and peptide fixtures in a local source context.
    
    Parameters
    ----------
    rows : list[dict]
        Synthetic interaction rows.
    peptides : list[dict], optional
        Same-ligand peptide lookup fixtures.
    
    Returns
    -------
    Source
        Fixture-only adapter context.
    """
    return context('gtopdb', {'interactions.csv': pd.DataFrame(rows), 'peptides.csv': pd.DataFrame(peptides or [], columns=['Ligand id', 'Species', 'Subunit ids', 'UniProt id']),
                             'targets_and_families.csv': pd.DataFrame()}, species='multispecies')


class NormalizationTests(unittest.TestCase):
    def test_pavlicev_receptor_first_is_reversed_without_case_conversion(self):
        f = 'supp_gr.207597.116_Supplemental_Tables.xlsx'
        ctx = context('pavlicev', {(f, 'S5'): pd.DataFrame([{'Receptor': 'PAQR7 ', 'Ligand': 'HSD3B1'}, {'Receptor': 'CCR7', 'Ligand': 'CCl19'}])})
        adapters.simple_pairs(ctx)
        row = ctx.records[0]
        self.assertEqual((row['ligand_id'], row['receptor_id']), ('HSD3B1', 'PAQR7'))
        self.assertEqual(row['original_endpoint_a'], 'PAQR7 ')
        self.assertEqual(json.loads(row['raw_json'])['Receptor'], 'PAQR7 ')
        self.assertEqual(ctx.records[1]['ligand_id'], 'CCl19')
        self.assertIn('N03_unclassified_proxy_possible_in_publication', row['review_reasons'])

    def test_gtop_missing_species_is_not_inferred_from_target_or_case(self):
        ctx = gtop_context([gtop_row(**{'Target Species': 'Mouse', 'Ligand Species': ''})])
        adapters.gtopdb(ctx)
        self.assertEqual(ctx.records[0]['ligand_species'], [])
        self.assertEqual(ctx.records[0]['receptor_species'], ['mouse'])
        self.assertEqual(ctx.records[0]['species_group'], 'unknown_species')

    def test_gtop_mixed_and_cross_species_are_not_expanded(self):
        ctx = gtop_context([gtop_row(**{'Target Species': 'Mouse', 'Ligand Species': 'Human|Mouse|Rat'}),
                            gtop_row(**{'Target Species': 'Mouse', 'Ligand Species': 'Human'})])
        adapters.gtopdb(ctx)
        self.assertEqual(len(ctx.records), 2)
        self.assertEqual(ctx.records[0]['species_group'], 'mixed_species')
        self.assertEqual(ctx.records[1]['species_group'], 'cross_species')

    def test_same_id_peptide_lookup_fills_species_without_conversion(self):
        ctx = gtop_context([gtop_row(**{'Target Species': 'Mouse'})], [{'Ligand id': '4417', 'Species': 'Human', 'Subunit ids': '', 'UniProt id': 'Q99731'}])
        adapters.gtopdb(ctx)
        self.assertEqual(ctx.records[0]['species_group'], 'cross_species')
        self.assertIn('same_ligand_id', ctx.records[0]['species_basis'])

    def test_gtop_repeated_assays_and_evidence_are_retained(self):
        a = gtop_row(**{'Target Species': 'Human', 'Ligand Species': 'Human', 'PubMed ID': '11148224', 'Affinity Median': '7.0'})
        b = {**a, 'PubMed ID': '11416224', 'Affinity Median': '8.1'}
        ctx = gtop_context([a, b])
        adapters.gtopdb(ctx)
        self.assertEqual(len({r['semantic_key'] for r in ctx.records}), 1)
        self.assertEqual(len({r['record_key'] for r in ctx.records}), 2)
        self.assertEqual({r['value'] for r in ctx.evidence}, {'11148224', '11416224'})
        self.assertTrue(all(r['is_stimulation'] is None and r['is_inhibition'] is None for r in ctx.records))

    def test_synthetic_drug_retained_with_exclusion_reason(self):
        ctx = gtop_context([gtop_row(**{'Ligand Type': 'Synthetic organic', 'Endogenous': 'false', 'Target Species': 'Human'})])
        adapters.gtopdb(ctx)
        self.assertEqual(len(ctx.records), 1)
        self.assertEqual(ctx.records[0]['status'], 'excluded')
        self.assertEqual(ctx.records[0]['ligand_type'], 'synthetic')

    def test_cellcall_lr_tf_repetitions_and_obligate_complex(self):
        row = {'Ligand_ID': '7040', 'Receptor_ID': '7046,7048', 'Ligand_Symbol': 'TGFB1', 'Receptor_Symbol': 'TGFBR1,TGFBR2', 'TF_ID': '4086', 'TF_Symbol': 'SMAD1', 'pathway_ID': 'hsa04350'}
        f = 'new_ligand_receptor_TFs.txt'
        ctx = context('cellcall', {f: pd.DataFrame([row, {**row, 'TF_ID': '4087', 'TF_Symbol': 'SMAD2'}])})
        adapters.cellcall(ctx)
        self.assertEqual(len(ctx.records), 2)
        self.assertEqual(len({r['semantic_key'] for r in ctx.records}), 1)
        self.assertEqual(len(ctx.members), 2)
        self.assertEqual({m['member_id'] for m in ctx.members}, {'TGFBR1', 'TGFBR2'})
        self.assertTrue(all(r['receptor_type'] == 'complex' for r in ctx.records))
        self.assertEqual({e['type'] for e in ctx.evidence}, {'pathway'})

    def test_provider_orthology_and_literal_underscore_label(self):
        ctx = context('nichenet', {'lr_network_human_21122021.rds': pd.DataFrame([{'from': 'C4B_2', 'to': 'CD46', 'database': 'omnipath', 'source': 'omnipath'}]),
                                  'lr_network_mouse_21122021.rds': pd.DataFrame([{'from': 'C4b', 'to': 'Cd46', 'database': 'omnipath', 'source': 'omnipath'}])})
        ctx.manifest['files'][1]['species'] = 'mouse'
        ctx.manifest['files'][1]['provenance'] = 'orthology-derived'
        adapters.nichenet(ctx)
        self.assertEqual(ctx.records[0]['ligand_id'], 'C4B_2')
        self.assertEqual(ctx.records[0]['ligand_type'], 'gene_product')
        self.assertEqual(ctx.records[1]['evidence_provenance'], 'provider_orthology')
        self.assertIn('N01_provider_mouse_orthology', ctx.records[1]['review_reasons'])

    def test_icellnet_multisubunit_ligand_and_receptor_not_cartesian_product(self):
        row = {'Ligand 1': 'IL12A', 'Ligand 2': 'IL12B', 'Receptor 1': 'IL12RB1', 'Receptor 2': 'IL12RB2', 'Reference': '8943050'}
        ctx = context('icellnet', {'ICELLNETdb.tsv': pd.DataFrame([row])})
        adapters.icellnet(ctx)
        self.assertEqual(len(ctx.records), 1)
        self.assertEqual(len(ctx.members), 4)
        self.assertEqual({m['relationship'] for m in ctx.members}, {'required_subunit'})

    def test_cellphonedb_proxy_is_not_chat_gene_or_acetylcholine_molecule(self):
        tables = {'gene_input.csv': pd.DataFrame([{'uniprot': 'P28329', 'hgnc_symbol': 'CHAT'}, {'uniprot': 'P11229', 'hgnc_symbol': 'CHRM1'}]),
                  'protein_input.csv': pd.DataFrame([{'uniprot': 'P11229'}]),
                  'complex_input.csv': pd.DataFrame([{'complex_name': 'Acetylcholine_byCHAT', 'uniprot_1': 'P28329', 'other_desc': 'biosynthesis_enzyme'}]),
                  'interaction_input.csv': pd.DataFrame([{'partner_a': 'Acetylcholine_byCHAT', 'partner_b': 'P11229', 'directionality': 'Ligand-Receptor', 'source': 'reactome',
                    'is_ppi': 'False', 'reactome_reaction': 'R-HSA-390649', 'reactome_complex': '', 'reactome_pathway': '', 'complexPortal_complex': '', 'id_cp_interaction': '', 'modulatory_effect': ''}])}
        ctx = context('cellphonedb', tables)
        adapters.cellphonedb(ctx)
        self.assertEqual(ctx.records[0]['ligand_id'], 'Acetylcholine_byCHAT')
        self.assertEqual(ctx.records[0]['ligand_type'], 'nonprotein_proxy')
        self.assertEqual(ctx.members[0]['member_label'], 'CHAT')
        self.assertEqual(ctx.members[0]['relationship'], 'biosynthetic_proxy_component')

    def test_cellchat_cofactors_separate_from_required_subunits(self):
        tables = {}
        for sp in ['human', 'mouse']:
            f, base = 'CellChatDB.' + sp + '.rda', 'CellChatDB.' + sp
            tables[(f, base + '/interaction')] = pd.DataFrame([{'ligand': 'TGFB1', 'receptor': 'TGFbR1_R2', 'annotation': 'Secreted Signaling', 'evidence': 'KEGG: hsa04350',
              'interaction_name': 'TGFB1_TGFBR1_TGFBR2', 'is_neurotransmitter': 'FALSE', 'agonist': '', 'antagonist': 'TGFb antagonist', 'co_A_receptor': '', 'co_I_receptor': ''}], index=['row1'])
            tables[(f, base + '/complex')] = pd.DataFrame([{'subunit_1': 'TGFBR1', 'subunit_2': 'TGFBR2'}], index=['TGFbR1_R2'])
            tables[(f, base + '/cofactor')] = pd.DataFrame([{'cofactor1': 'DCN'}], index=['TGFb antagonist'])
            tables[(f, base + '/geneInfo')] = pd.DataFrame([{'Symbol': 'TGFB1'}])
        ctx = context('cellchat', tables)
        adapters.cellchat(ctx)
        self.assertNotIn('DCN', {m['member_id'] for m in ctx.members})
        self.assertEqual(ctx.regulators[0]['role'], 'antagonist')
        self.assertEqual(ctx.regulators[0]['member_label'], 'DCN')

    def test_ambiguous_mapping_and_unknown_conflicting_signs(self):
        self.assertEqual(core.unique_mapping(['A', 'B']), (None, 'ambiguous'))
        self.assertIsNone(core.positive('False'))
        self.assertIsNone(core.positive(''))
        ctx = context('test', {'x.tsv': pd.DataFrame()})
        ctx.add('x.tsv', '', 2, {}, core.endpoint('A', species_values=['human']), core.endpoint('B', species_values=['human']), stimulation=True, inhibition=True)
        self.assertIn('conflicting_signs', ctx.records[0]['review_reasons'])

    def test_release_comment_is_not_the_csv_header(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(core, 'RAW', Path(tmp)):
            p = Path(tmp) / 'test'
            p.mkdir()
            (p / 'x.csv').write_text('"# GtoPdb Version: 2026.3 - published: 2026-09-16"\n"Ligand ID","Ligand"\n"4417","CCL19"\n', encoding='utf-8')
            ctx = core.Source('test', {'files': [{'path': 'test/x.csv'}]})
            df = ctx.table('x.csv', role='interaction')
            self.assertEqual(list(df.columns), ['Ligand ID', 'Ligand'])
            self.assertEqual(len(df), 1)
            self.assertIn('2026.3', ctx.inventory[0]['release_comments'][0])

    def test_keys_are_deterministic_and_keep_source_species_and_complex_identity(self):
        def build(sp):
            ctx = context('test', {'x.tsv': pd.DataFrame()})
            ctx.add('x.tsv', '', 2, {'field': 'value'}, core.endpoint('A', species_values=[sp]), core.endpoint('B', species_values=[sp]))
            return ctx.records[0]
        self.assertEqual(build('human'), build('human'))
        self.assertNotEqual(build('human')['semantic_key'], build('mouse')['semantic_key'])

    def test_italk_missing_approved_symbol_keeps_name_and_unknown_species(self):
        ctx = context('italk', {('LR_database.rda', 'database'): pd.DataFrame([{'Ligand.ApprovedSymbol': 'CXCL1', 'Receptor.ApprovedSymbol': None,
                'Ligand.Name': 'CXCL1', 'Receptor.Name': 'ECRF3', 'Pair.Name': 'CXCL1_ECRF3'}])})
        adapters.simple_pairs(ctx)
        self.assertEqual(ctx.records[0]['receptor_id'], 'ECRF3')
        self.assertEqual(ctx.records[0]['source_row'], '1')
        self.assertEqual(ctx.records[0]['species_group'], 'unknown_species')

    def test_encoded_complex_retains_source_symbol_label_and_accession_identity(self):
        ctx = context('test', {'x.tsv': pd.DataFrame()})
        result = adapters.encoded_complex(ctx, 'COMPLEX:P1_P2', 'IL12A_IL12B', 'human', 'x.tsv', 2)
        self.assertEqual(result['id'], 'COMPLEX:P1_P2')
        self.assertEqual(result['label'], 'IL12A_IL12B')
        self.assertEqual([m['member_id'] for m in ctx.members], ['P1', 'P2'])

    def test_omnipath_reverse_orientation_does_not_reverse_sign(self):
        inter = pd.DataFrame([{'scope': 'generic', 'source': 'composite', 'category': 'ligand', 'uniprot': 'P2'},
                              {'scope': 'generic', 'source': 'composite', 'category': 'receptor', 'uniprot': 'P1'}])
        row = {'source': 'P1', 'target': 'P2', 'source_genesymbol': 'NOTCH1', 'target_genesymbol': 'JAG2',
               'ncbi_tax_id_source': '9606', 'ncbi_tax_id_target': '9606', 'references': 'SPIKE:16713569', 'sources': 'SPIKE;CellCall',
               'is_stimulation': 'False', 'is_inhibition': 'True', 'is_directed': 'True'}
        ctx = context('omnipathppis', {'intercell.tsv': inter, 'complexes.tsv': pd.DataFrame(),
             'human/interactions.tsv': pd.DataFrame([row]), 'mouse/interactions.tsv': pd.DataFrame([{**row, 'ncbi_tax_id_source': '10090', 'ncbi_tax_id_target': '10090'}])})
        adapters.omnipath(ctx)
        self.assertEqual(ctx.records[0]['ligand_id'], 'P2')
        self.assertEqual(ctx.records[0]['orientation'], 'reversed_to_ligand_receptor')
        self.assertIsNone(ctx.records[0]['is_inhibition'])
        self.assertEqual(json.loads(ctx.records[0]['raw_json'])['is_inhibition'], 'True')
        self.assertEqual(ctx.records[1]['orientation'], 'unresolved_source_target')


if __name__ == '__main__':
    unittest.main()
