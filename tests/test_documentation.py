"""Regression checks for configuration-only portability changes and reference pinning."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import database_build
from validate_documentation import check_annotations


class PortabilityTests(unittest.TestCase):
    """Keep location overrides separate from biological policy changes."""

    def test_annotation_override_reaches_resolver(self):
        """A caller-selected directory reaches identity resolution unchanged."""
        selected=Path('authorized-reference-copy')
        with patch.object(database_build,'verify_inputs',return_value=({},[])), patch.object(database_build,'Identities',side_effect=RuntimeError('stop after configuration')) as resolver:
            with self.assertRaisesRegex(RuntimeError,'stop after configuration'):
                database_build.make_tables(selected)
            resolver.assert_called_once_with(selected)

    def test_default_reference_location_preserved(self):
        """Existing callers retain the resolver's original sibling-directory default."""
        with patch.object(database_build,'verify_inputs',return_value=({},[])), patch.object(database_build,'Identities',side_effect=RuntimeError('stop after configuration')) as resolver:
            with self.assertRaises(RuntimeError): database_build.make_tables()
            resolver.assert_called_once_with()

    def test_reference_pin_detects_changed_bytes(self):
        """Matching local assets pass; changed reference bytes must fail."""
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); asset=root/'reference.parquet'; asset.write_bytes(b'fixture')
            pin=root/'pin.json'; pin.write_text(json.dumps({'files':{asset.name:hashlib.sha256(asset.read_bytes()).hexdigest()}}))
            self.assertEqual(check_annotations(root,pin),1)
            asset.write_bytes(b'changed')
            with self.assertRaises(AssertionError): check_annotations(root,pin)


if __name__=='__main__':
    unittest.main()
