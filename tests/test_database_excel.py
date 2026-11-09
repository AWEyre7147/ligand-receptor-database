"""Test the approved workbook projection without real-data builds."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from database_build import SCHEMAS, summarize_sign
from database_excel import TEMPLATE_ROOT, display_value, workbook_partitions, digest_workbook
from database_export import export_xlsx, validate_excel, write_parquet


class WorkbookProjectionTests(unittest.TestCase):
    def pieces(self):
        """Return complete empty partitions with a few synthetic values.

        Returns
        -------
        dict
            Species partitions, including technical Parquet-only tables.
        """
        names = {'Ligand-Receptor': 'interactions', 'Nonprotein-Proxy': 'interactions',
                 'Entities': 'entities', 'Complex-Members': 'memberships',
                 'Regulators': 'regulators', 'Assertions': 'assertions'}
        pieces = {sp: [{'sheet': name, 'schema': schema, 'rows': [],
                       'filename': sp + '-' + name + '.parquet'} for name, schema in names.items()]
                  for sp in ('human', 'mouse')}
        pieces['human'][0]['rows'] = [{'interaction_id': 'LRI-000001', 'ligand_entity_id': 'ENT-000001',
            'receptor_entity_id': 'ENT-000002', 'ligand': '=literal', 'species': 'human', 'tier': 'primary',
            'sources': ['celltalkdb', 'dimitrov'], 'sign_summary': None,
            'omnipath_reported_stimulation': ['false'], 'gtopdb_action_comment': ['a; b', 'c']}]
        pieces['human'][2]['rows'] = [{'entity_id': 'ENT-000001', 'gene_id': '123',
            'display_label': '=literal', 'species': 'human'}]
        pieces['human'][4]['rows'] = [
            {'regulator_id': 'REG-000001', 'interaction_id': 'LRI-000001', 'disposition': 'primary'},
            {'regulator_id': 'REG-000002', 'interaction_id': None, 'disposition': 'excluded'}]
        pieces['human'][-1]['rows'] = [{'record_key': 'normalized-key', 'record_id': 'AST-000001'}]
        return pieces

    def test_template_projection_retains_canonical_values_and_all_parquet_tables(self):
        import pyarrow.parquet as pq

        pieces = self.pieces()
        original = deepcopy(pieces)
        projected, inputs = workbook_partitions(pieces, SCHEMAS)
        self.assertEqual(len(inputs), 3)
        expected_sheets = ['Ligand-Receptor', 'Nonprotein-Proxy', 'Entities', 'Complex-Members', 'Regulators']
        for sp in projected:
            self.assertEqual([s['sheet'] for s in projected[sp]], expected_sheets)
            self.assertEqual(projected[sp][0]['excel_fields'].names[:3],
                             ['interaction_id', 'ligand_entity_id', 'receptor_entity_id'])
            self.assertNotIn('species', projected[sp][0]['excel_fields'].names)
        self.assertEqual(pieces, original)
        digest = digest_workbook(projected['human'])
        self.assertEqual(digest, digest_workbook(projected['human']))
        pieces['human'][0]['rows'][0]['ligand'] = 'changed'
        self.assertNotEqual(digest, digest_workbook(projected['human']))
        pieces['human'][0]['rows'][0]['ligand'] = '=literal'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_parquet(pieces, root)
            self.assertTrue((root / 'human-Assertions.parquet').exists())
            self.assertEqual(pq.read_table(root / 'human-Regulators.parquet').num_rows, 2)
            self.assertEqual(len(projected['human'][4]['rows']), 1)
            self.assertEqual(pq.read_table(root / 'human-Ligand-Receptor.parquet')['sources'].to_pylist(),
                             [['celltalkdb', 'dimitrov']])
            for sp in ('human', 'mouse'):
                path = root / (sp + '.xlsx')
                export_xlsx(projected[sp], path, root, sp)
                self.assertEqual(validate_excel(path, projected[sp])['status'], 'passed')
                wb = openpyxl.load_workbook(path)
                try:
                    ws = wb['Ligand-Receptor']
                    self.assertTrue(ws['A1'].font.bold)
                    self.assertEqual(ws['A1'].alignment.horizontal, 'left')
                    self.assertEqual(ws['A1'].alignment.vertical, 'center')
                    self.assertIsNone(ws.freeze_panes)
                    self.assertTrue(all(s.pane in (None, 'topLeft') for s in ws.sheet_view.selection))
                    if sp == 'human':
                        values = dict(zip([c.value for c in ws[1]], [c.value for c in ws[2]]))
                        self.assertEqual(values['sources'], 'celltalkdb; dimitrov')
                        self.assertEqual(values['gtopdb_action_comment'], 'a; b; c')
                        self.assertIsNone(values['sign_summary'])
                        self.assertEqual(ws['D2'].data_type, 's')
                        self.assertEqual(wb['Entities']['B2'].value, '123')
                        self.assertNotIn('product_accession', [c.value for c in wb['Entities'][1]])
                        self.assertEqual(wb['Entities']['C2'].value, '=literal')
                finally:
                    wb.close()

    def test_missing_sign_is_not_explicit_unknown_or_inhibition(self):
        missing = [{'is_stimulation': None, 'is_inhibition': None}]
        negative = [{'is_stimulation': False, 'is_inhibition': False}]
        self.assertIsNone(summarize_sign(missing, []))
        self.assertIsNone(summarize_sign(negative, []))
        annotation = {'summary_eligible': True, 'source': 'omnipathppis',
                      'source_field': 'is_stimulation', 'original_value': 'unknown'}
        self.assertEqual(summarize_sign(missing, [annotation]), 'unknown')
        self.assertIsNone(summarize_sign(missing, [{**annotation, 'summary_eligible': False}]))
        positive = [{'is_stimulation': True, 'is_inhibition': False}]
        self.assertEqual(summarize_sign(positive, [annotation]), 'stimulation_reported')
        self.assertEqual(summarize_sign(positive + [{'is_stimulation': False, 'is_inhibition': True}], []),
                         'conflicting_positive_assertions')

    def test_missing_and_literal_display_values(self):
        self.assertIsNone(display_value([]))
        self.assertIsNone(display_value(None))
        self.assertEqual(display_value(False), False)
        self.assertEqual(display_value('unknown'), 'unknown')
        self.assertEqual(display_value('~json:literal'), '~json:literal')

    def test_changed_template_bytes_are_rejected(self):
        import shutil

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in TEMPLATE_ROOT.iterdir():
                if path.suffix in ('.json', '.xlsx'):
                    shutil.copyfile(path, root / path.name)
            manifest = json.loads((root / 'manifest.json').read_text())
            target = root / manifest['files'][0]['path']
            target.write_bytes(target.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                workbook_partitions(self.pieces(), SCHEMAS, root)

if __name__ == '__main__':
    unittest.main()
