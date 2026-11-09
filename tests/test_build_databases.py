"""Policy and identity regressions with small source-shaped fixtures."""
from collections import defaultdict
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from database_identity import Identities, IdentityError
import database_build as build
from database_export import excel_value, export_xlsx, partitions, validate_excel, write_parquet
from build_databases import promote, verification_plan, verify_hashes


def resolver():
    """Create a minimal two-species resolver without loading real datasets.
    
    Returns
    -------
    Identities
        Synthetic genes, aliases and empty definition stores for policy regressions.
    """
    ids = object.__new__(Identities)
    ids.index, ids.source_index = defaultdict(set), defaultdict(set)
    ids.genes, ids.entities, ids.definitions, ids.memberships, ids.cache, ids.declared = {}, {}, {}, {}, {}, {}
    ids.targets, ids.peptides, ids.cp_complex = {}, {}, {}
    for sp, symbol, gid in [('human','A','1'),('human','B','2'),('human','C','3'),('mouse','A','11'),('mouse','B','12')]:
        ids.genes[sp,gid] = symbol
        ids.index[sp,'symbol',symbol].add(gid)
        ids.index[sp,'NCBIGene',gid].add(gid)
    ids.index['human','UniProt','P1'].add('1')
    ids.index['human','HGNC','101'].add('1')
    return ids


def record(**extra):
    """Construct a complete source-shaped assertion with explicit test overrides.
    
    Parameters
    ----------
    extra : dict
        Field overrides that isolate the policy condition under test.
    
    Returns
    -------
    dict
        Synthetic normalized interaction record.
    """
    r = {'source':'cellcall','species_group':'human','orientation':'ligand_to_receptor', 'exclusion_reasons':[], 'review_reasons':[],
         'underlying_sources':[], 'raw_json':'{}'}
    for side, label in [('ligand','A'),('receptor','B')]:
        r.update({side+'_id':label,side+'_label':label,side+'_type':'gene_product',side+'_mapping':'source_identifier',side+'_namespace':'symbol',side+'_complex_key':None})
    return {**r, **extra}


def member(label, order):
    """Construct one required-subunit source membership fixture.
    
    Parameters
    ----------
    label : str
        Synthetic member symbol in the resolver fixture.
    order : int
        One-based source member position.
    
    Returns
    -------
    dict
        Membership row with unknown stoichiometry.
    """
    return {'member_id':label,'member_label':label,'namespace':'symbol','species':'human','relationship':'required_subunit',
            'stoichiometry':None,'source_file':'test/complex.csv','source_table':'','source_row':'1','member_order':order}


class BuildTests(unittest.TestCase):
    def test_routine_and_release_verification_plans_are_explicit(self):
        routine = verification_plan(False, False)
        self.assertFalse(any(routine.values()))
        release = verification_plan(True, False)
        self.assertTrue(release['full_test_suite'])
        self.assertTrue(release['repeat_assembly'])
        self.assertTrue(release['excel_parquet_parity'])
        self.assertFalse(release['previews'])
        self.assertTrue(verification_plan(True, True)['previews'])
        with self.assertRaisesRegex(ValueError, 'release-verification'):
            verification_plan(False, True)

    def test_source_annotations_preserve_missing_negative_multiple_and_record_context(self):
        def annotation_record(source, record_key, raw, species='human', orientation='ligand_to_receptor'):
            return {
                'source': source, 'record_key': record_key, 'raw_json': json.dumps(raw),
                'source_file': source + '.csv', 'source_table': '', 'source_row': record_key,
                'source_record_id': 'provider-' + record_key, 'species_group': species,
                'orientation': orientation,
            }
        def assertion(record_key, disposition='primary', interaction='I:test', orientation='ligand_to_receptor'):
            return {
                'record_key': record_key, 'disposition': disposition, 'interaction_id': interaction,
                'related_interaction_id': None, 'orientation': orientation,
            }

        first = annotation_record('omnipathppis', 'one', {
            'is_stimulation': False, 'is_inhibition': None, 'is_directed': True,
        })
        rows = build.extract_source_annotations(first, assertion('one'))
        self.assertEqual({r['original_value'] for r in rows}, {'false', 'true'})
        self.assertNotIn('is_inhibition', {r['source_field'] for r in rows})

        second = annotation_record('gtopdb', 'two', {
            'Action': 'Agonist', 'Action comment': 'record-specific', 'Selectivity': 'Selective',
            'Endogenous': 'True', 'Ligand Type': 'Peptide', 'Type': 'Functional',
        })
        third = annotation_record('gtopdb', 'three', {'Action': 'Antagonist', 'Endogenous': 'False'})
        rows += build.extract_source_annotations(second, assertion('two'))
        rows += build.extract_source_annotations(third, assertion('three'))
        summary = build.source_annotation_summary('I:test', rows)
        self.assertEqual(summary['gtopdb_action'], ['Agonist', 'Antagonist'])
        self.assertEqual(summary['gtopdb_endogenous'], ['False', 'True'])
        action = [r for r in rows if r['record_key'] == 'two' and r['source_field'] == 'Action'][0]
        comment = [r for r in rows if r['record_key'] == 'two' and r['source_field'] == 'Action comment'][0]
        self.assertEqual(action['source_record_id'], comment['source_record_id'])

        blocked = annotation_record('italk', 'four', {'Classification': 'growth factor'}, species='mouse')
        blocked_rows = build.extract_source_annotations(blocked, assertion('four', 'review', None))
        self.assertFalse(blocked_rows[0]['summary_eligible'])
        self.assertIsNone(blocked_rows[0]['interaction_id'])
        self.assertEqual(build.source_annotation_summary('I:test', rows + blocked_rows)['italk_classification'], [])

        human_assertion = {'record_key': 'one', 'species_group': 'human', 'disposition': 'primary'}
        mouse_assertion = {'record_key': 'four', 'species_group': 'mouse', 'disposition': 'review'}
        tables = {name: [] for name in build.SCHEMAS}
        tables['assertions'] = [human_assertion, mouse_assertion]
        tables['source_annotations'] = [rows[0], blocked_rows[0]]
        split = partitions(tables)
        human_rows = next(s['rows'] for s in split['human'] if s['sheet'] == 'Source-Annotations')
        mouse_rows = next(s['rows'] for s in split['mouse'] if s['sheet'] == 'Source-Annotations')
        self.assertEqual([r['record_key'] for r in human_rows], ['one'])
        self.assertEqual([r['record_key'] for r in mouse_rows], ['four'])

        reversed_record = annotation_record('omnipathppis', 'five', {'is_stimulation': True}, orientation='reversed_to_ligand_receptor')
        reversed_rows = build.extract_source_annotations(reversed_record, assertion('five', orientation='reversed_to_ligand_receptor'))
        self.assertFalse(reversed_rows[0]['summary_eligible'])
        self.assertIn('orientation safeguard', reversed_rows[0]['interpretation_note'])

    def test_source_annotation_small_excel_and_parquet_roundtrip(self):
        row = {
            'annotation_id': 'A:test', 'record_key': 'human-record', 'interaction_id': 'I:test',
            'related_interaction_id': None, 'disposition': 'primary', 'source': 'gtopdb',
            'source_file': 'gtopdb/interactions.csv', 'source_table': '', 'source_row': '3',
            'source_record_id': '42', 'species_group': 'human', 'source_field': 'Endogenous',
            'summary_field': 'gtopdb_endogenous', 'original_value': 'False',
            'interpretation_note': None, 'summary_eligible': True,
        }
        spec = [{'sheet': 'Source-Annotations', 'filename': 'Human-Source-Annotations.parquet',
                 'rows': [row], 'schema': 'source_annotations'}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'annotations.xlsx'
            export_xlsx(spec, path, root, 'human')
            self.assertEqual(validate_excel(path, spec)['status'], 'passed')
            metadata = write_parquet({'human': spec}, root)
            self.assertEqual(metadata[0]['rows'], 1)

    def test_same_species_identifiers_merge_but_species_never_do(self):
        ids=resolver()
        self.assertEqual(ids.gene('human','symbol','A'),ids.gene('human','HGNC','HGNC:101'))
        self.assertEqual(ids.gene('human','symbol','A'),ids.gene('human','UniProt','P1'))
        self.assertNotEqual(ids.gene('human','symbol','A'),ids.gene('mouse','symbol','A'))
        with self.assertRaises(IdentityError): ids.gene('mouse','NCBIGene','1')

    def test_ambiguous_alias_and_identifier_symbol_conflict(self):
        ids=resolver()
        ids.index['human','alias','old'].update(['1','2'])
        with self.assertRaisesRegex(IdentityError,'ambiguous'): ids.gene('human','symbol','old')
        with self.assertRaisesRegex(IdentityError,'conflict'): ids.gene('human','UniProt','P1','B')

    def test_exact_unverified_symbol_does_not_case_fold_or_establish_complex(self):
        ids=resolver()
        self.assertNotEqual(ids.gene('human','symbol','Unknown'),ids.gene('human','symbol','UNKNOWN'))
        with self.assertRaises(IdentityError): ids.gene('human','symbol','Unknown',strict=True)
        with self.assertRaises(IdentityError): ids.gene('human','symbol','A/B')

    def test_provider_mouse_acceptance_does_not_resolve_direction(self):
        ids=resolver()
        r=record(species_group='mouse',review_reasons=['N01_provider_mouse_orthology'])
        self.assertEqual(build.disposition(r,ids,{})[0],'primary')
        r['orientation']='unresolved_source_target'
        self.assertEqual(build.disposition(r,ids,{})[0],'review')

    def test_unknown_evidence_provenance_is_not_identifier_failure(self):
        r=record(species_group='mouse',review_reasons=['N01_mouse_evidence_provenance_unknown'])
        self.assertEqual(build.disposition(r,resolver(),{})[0],'primary')

    def test_unknown_and_cross_species_are_never_forced_into_species_view(self):
        for sp in ['unknown_species','mixed_species','cross_species']:
            state,reasons,left,right=build.disposition(record(species_group=sp),resolver(),{})
            self.assertEqual(state,'review'); self.assertIsNone(left); self.assertIsNone(right)

    def test_liana_constituents_remain_provenance_not_extra_support(self):
        r=record(source='dimitrov',underlying_sources=['CellPhoneDB'])
        self.assertEqual(build.disposition(r,resolver(),{})[0],'provenance_only')
        r['underlying_sources']=['consensus']
        self.assertEqual(build.disposition(r,resolver(),{})[0],'primary')

    def test_putative_and_possible_proxy_are_review_even_with_valid_ids(self):
        for reason in ['N04_putative_interaction','N03_unclassified_proxy_possible_in_publication','N03_enzyme_named_ligand_requires_review']:
            self.assertEqual(build.disposition(record(review_reasons=[reason]),resolver(),{})[0],'review')

    def test_complex_identity_ignores_source_name_but_not_members_or_stoichiometry(self):
        ids=resolver()
        r=record(source='icellnet',ligand_type='complex',ligand_id='AB',ligand_complex_key='ab',raw_json=json.dumps({'Ligand 1':'A','Ligand 2':'B'}))
        members={('icellnet','ab'):[member('A',1),member('B',2)]}
        first=ids.complex(r,'ligand',members)
        r2={**r,'ligand_complex_key':'ab2','ligand_id':'different source name'}
        members['icellnet','ab2']=[member('B',1),member('A',2)]
        self.assertEqual(first,ids.complex(r2,'ligand',members))
        r3={**r,'ligand_complex_key':'ab3'}
        members['icellnet','ab3']=[{**member('A',1),'stoichiometry':'2'},member('B',2)]
        self.assertNotEqual(first,ids.complex(r3,'ligand',members))
        self.assertEqual(len([m for m in ids.memberships.values() if m['entity_id']==first]),2)

    def test_partial_member_list_does_not_establish_complete_complex(self):
        ids=resolver()
        r=record(source='icellnet',ligand_type='complex',ligand_id='AB',ligand_complex_key='ab',raw_json=json.dumps({'Ligand 1':'A','Ligand 2':'B'}))
        with self.assertRaisesRegex(IdentityError,'incomplete'):
            ids.complex(r,'ligand',{('icellnet','ab'):[member('A',1)]})

    def test_source_single_gene_proxy_preserves_dependency_not_molecule(self):
        ids=resolver()
        r=record(source='cellchat',ligand_type='nonprotein_proxy',review_reasons=['N03_nonprotein_or_proxy'])
        state,_,left,_=build.disposition(r,ids,{})
        self.assertEqual(state,'companion')
        self.assertEqual(ids.entities[left]['entity_type'],'nonprotein_proxy')
        self.assertNotIn('product_id', ids.entities[left])
        self.assertEqual(next(iter(ids.memberships.values()))['relationship'],'biosynthetic_or_transport_proxy')

    def test_gtopdb_family_list_needs_independent_obligate_definition(self):
        ids=resolver()
        ids.targets={str(n):[{'Human Entrez Gene':str(n)}] for n in (1,2,3)}
        r=record(source='gtopdb',receptor_type='complex',receptor_id='family',receptor_complex_key='family')
        members={('gtopdb','family'):[{**member(str(n),n),'namespace':'GtoPdb_target'} for n in (1,2,3)]}
        with self.assertRaisesRegex(IdentityError,'not_confirmed_obligate'):
            ids.complex(r,'receptor',members)
        obligate=record(source='icellnet',ligand_type='complex',ligand_id='AB',ligand_complex_key='ab',raw_json=json.dumps({'Ligand 1':'A','Ligand 2':'B'}))
        ids.complex(obligate,'ligand',{('icellnet','ab'):[member('A',1),member('B',2)]})
        # Even a known subset does not prove that the whole family is one complex.
        with self.assertRaises(IdentityError): ids.complex(r,'receptor',members)
        members['gtopdb','pair']=members['gtopdb','family'][:2]
        ids.complex({**r,'receptor_complex_key':'pair','receptor_id':'pair'},'receptor',members)
        d=next(d for d in ids.definitions.values() if d['source']=='gtopdb')
        self.assertEqual(len(d['supporting_definition_ids']),1)

    def test_conflicting_signs_stay_eligible_assertions_not_invented_inhibition(self):
        r=record(review_reasons=['conflicting_signs'],is_stimulation=True,is_inhibition=True)
        self.assertEqual(build.disposition(r,resolver(),{})[0],'primary')
        self.assertTrue(r['is_stimulation']); self.assertTrue(r['is_inhibition'])

    def test_cross_source_interaction_key_is_not_source_local(self):
        ids=resolver()
        a=ids.gene('human','NCBIGene','1'); b=ids.gene('human','symbol','B')
        self.assertEqual(build.interaction_id('human',a,b,'primary'),build.interaction_id('human',ids.gene('human','UniProt','P1'),b,'primary'))

    def test_stale_bytes_and_failed_normalized_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'x'; path.write_text('changed')
            with self.assertRaisesRegex(ValueError,'Input changed'):
                verify_hashes([{'path':str(path),'sha256':'stale'}])
        with patch.object(build,'file_hash',return_value='ok'), patch.object(Path,'read_text',return_value=json.dumps({'acquisition_manifest_sha256':'ok','sources':{s:{'status':'failed'} for s in build.SOURCE_IDS}})):
            with self.assertRaisesRegex(ValueError,'Failed normalized'):
                build.verify_inputs()

    def test_failed_promotion_restores_previous_release(self):
        import build_databases as runner
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'data').mkdir()
            output=root/'data/processed'; output.mkdir(); (output/'good').write_text('old')
            stage=root/'data/.processed-test'; stage.mkdir()
            real=runner.os.replace
            def fail_stage(src,dest):
                if Path(src)==stage: raise OSError('promotion failure')
                return real(src,dest)
            with patch.object(runner,'ROOT',root),patch.object(runner.os,'replace',side_effect=fail_stage):
                with self.assertRaises(OSError): runner.promote(stage,output)
            self.assertEqual((output/'good').read_text(),'old')

    def test_excel_nullable_lists_and_formula_strings_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'x.xlsx'
            rows=[{'topic':'=not a formula','description':''},{'topic':'~json:literal','description':None}]
            spec=[{'sheet':'Readme','rows':rows,'schema':'readme'}]
            export_xlsx(spec,p,Path(tmp),'test')
            self.assertEqual(validate_excel(p,spec)['status'],'passed')
        self.assertEqual(json.loads(excel_value(['a','b'])),['a','b'])


if __name__=='__main__': unittest.main()
