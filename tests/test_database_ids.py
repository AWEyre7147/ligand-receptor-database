"""Exercise release-local numbering without loading scientific input files."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from database_ids import assign_readable_ids


def fixture() -> dict[str, list[dict]]:
    """Return a two-species graph with source provenance and supporting definitions.

    Returns
    -------
    dict[str, list[dict]]
        Synthetic canonical rows containing every numbered relationship.
    """
    return {
        'interactions': [
            {'interaction_id': 'i2', 'species': 'mouse', 'ligand_entity_id': 'e2', 'receptor_entity_id': 'e2'},
            {'interaction_id': 'i1', 'species': 'human', 'ligand_entity_id': 'e1', 'receptor_entity_id': 'e1'}],
        'entities': [{'entity_id': 'e2', 'species': 'mouse', 'gene_id': '2', 'identity': '["e1"]'},
                     {'entity_id': 'e1', 'species': 'human', 'gene_id': '1'}],
        'assertions': [
            {'record_key': 'a2', 'interaction_id': None, 'related_interaction_id': 'i2', 'source_record_id': 'PROVIDER-2'},
            {'record_key': 'a1', 'interaction_id': 'i1', 'related_interaction_id': None}],
        'evidence': [{'evidence_key': 'ev1', 'record_key': 'a1', 'interaction_id': 'i1', 'value': '12345'}],
        'memberships': [{'membership_id': 'm1', 'entity_id': 'e1', 'member_entity_id': 'e1', 'stoichiometry': None}],
        'regulators': [{'regulator_id': 'r1', 'record_key': 'a2', 'interaction_id': None, 'member_entity_id': None}],
        'definitions': [
            {'definition_id': 'd1', 'entity_id': 'e1', 'source': 'one', 'source_complex_key': 'c', 'supporting_definition_ids': ['d2']},
            {'definition_id': 'd2', 'entity_id': 'e2', 'source': 'two', 'source_complex_key': 'c', 'supporting_definition_ids': []}],
        'source_members': [
            {'source': 'one', 'complex_key': 'c', 'definition_id': 'd1', 'entity_id': 'e1', 'member_id': 'PROVIDER-1'},
            {'source': 'two', 'complex_key': 'c', 'definition_id': None, 'entity_id': None, 'member_id': 'PROVIDER-2'}],
        'source_annotations': [{'annotation_id': 'an1', 'record_key': 'a2', 'interaction_id': None,
                                'related_interaction_id': 'i2', 'original_value': 'unknown'}],
    }


class ReadableIdTests(unittest.TestCase):
    def test_references_and_original_provenance_are_preserved(self):
        tables = fixture()
        assign_readable_ids(tables)
        self.assertEqual(tables['interactions'][0]['interaction_id'], 'LRI-000002')
        self.assertEqual(tables['interactions'][1]['interaction_id'], 'LRI-000001')
        self.assertEqual(tables['entities'][0]['entity_id'], 'ENT-000002')
        self.assertEqual(tables['memberships'][0]['membership_id'], 'MEM-000001')
        self.assertEqual(tables['regulators'][0]['regulator_id'], 'REG-000001')
        self.assertEqual(tables['definitions'][0]['supporting_definition_ids'], ['CDF-000002'])
        self.assertEqual(tables['source_annotations'][0]['annotation_id'], 'ANN-000001')
        self.assertEqual(tables['source_annotations'][0]['related_interaction_id'], 'LRI-000002')
        self.assertEqual(tables['source_annotations'][0]['record_id'], tables['assertions'][0]['record_id'])
        self.assertEqual(tables['assertions'][0]['record_id'], 'AST-000002')
        self.assertEqual(tables['evidence'][0]['evidence_id'], 'EVD-000001')
        self.assertEqual(tables['source_members'][0]['source_complex_id'], tables['definitions'][0]['source_complex_id'])
        self.assertNotEqual(tables['source_members'][0]['source_complex_id'], tables['source_members'][1]['source_complex_id'])
        self.assertEqual(tables['evidence'][0]['record_key'], 'a1')
        self.assertEqual(tables['evidence'][0]['evidence_key'], 'ev1')
        self.assertEqual(tables['assertions'][0]['source_record_id'], 'PROVIDER-2')
        self.assertEqual(tables['source_members'][0]['member_id'], 'PROVIDER-1')
        self.assertEqual(tables['entities'][0]['gene_id'], '2')
        self.assertEqual(tables['entities'][0]['identity'], '["e1"]')
        self.assertIsNone(tables['regulators'][0]['member_entity_id'])
        self.assertIsNone(tables['memberships'][0]['stoichiometry'])

    def test_numbering_is_independent_of_traversal_order(self):
        first, second = fixture(), fixture()
        for rows in second.values():
            rows.reverse()
        assign_readable_ids(first)
        assign_readable_ids(second)
        for name in first:
            self.assertEqual(sorted(map(repr, first[name])), sorted(map(repr, second[name])))

    def test_broken_graph_and_duplicate_keys_fail_without_mutation(self):
        for defect in ('foreign_key', 'duplicate'):
            tables = fixture()
            if defect == 'foreign_key':
                tables['interactions'][0]['ligand_entity_id'] = 'absent'
            else:
                tables['entities'].append(deepcopy(tables['entities'][0]))
            original = deepcopy(tables)
            with self.assertRaises(ValueError):
                assign_readable_ids(tables)
            self.assertEqual(tables, original)

    def test_double_numbering_fails_without_mutation(self):
        tables = fixture()
        assign_readable_ids(tables)
        original = deepcopy(tables)
        with self.assertRaisesRegex(ValueError, 'Already numbered'):
            assign_readable_ids(tables)
        self.assertEqual(tables, original)

    def test_readable_ids_survive_small_excel_parquet_export(self):
        from database_export import export_xlsx, validate_excel, write_parquet
        import pyarrow.parquet as pq

        tables = fixture()
        assign_readable_ids(tables)
        specs = [{'sheet': name, 'filename': name + '.parquet',
                  'rows': rows, 'schema': name} for name, rows in tables.items()]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = write_parquet({'test': specs}, root)
            self.assertEqual(len(metadata), len(specs))
            self.assertEqual(pq.read_table(root / 'evidence.parquet').to_pylist()[0]['evidence_id'], 'EVD-000001')
            self.assertEqual(pq.read_table(root / 'evidence.parquet').to_pylist()[0]['record_id'], 'AST-000001')
            self.assertEqual(pq.read_table(root / 'interactions.parquet').to_pylist()[0]['interaction_id'], 'LRI-000002')
            workbook = root / 'ids.xlsx'
            export_xlsx(specs, workbook, root, 'test')
            self.assertEqual(validate_excel(workbook, specs)['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
