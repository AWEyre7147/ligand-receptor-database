import copy
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import download_sources as d
import source_registry as registry


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.log = {'schema_version': 1, 'sources': {}}
        self.assets = [registry.asset('https://example.org/data.tsv', headers=('ligand', 'receptor'))]
        self.data = b'ligand\treceptor\nA\tB\n'

    def run_source(self, payload=None, headers=None):
        with patch.object(d, 'fetch', return_value=(payload or self.data, headers or {}, 'https://example.org/data.tsv')):
            return d.acquire('test', {'name': 'Test'}, self.log, self.base, lambda _: ({'version': None}, self.assets))

    def test_unchanged_without_version(self):
        first = self.run_source()
        second = self.run_source()
        self.assertEqual(first['status'], 'updated')
        self.assertEqual(second['status'], 'unchanged')
        self.assertEqual(second['changed_files'], [])

    def test_changed_content_without_version(self):
        self.run_source()
        second = self.run_source(b'ligand\treceptor\nC\tD\n')
        self.assertEqual(second['status'], 'updated')
        self.assertNotEqual(d.sha(self.data), second['files'][0]['sha256'])

    def test_missing_and_corrupt_files_repaired(self):
        self.run_source(headers={'ETag': 'v1'})
        target = self.base / 'test/data.tsv'
        for corrupt in (False, True):
            if corrupt:
                target.write_bytes(b'broken')
            else:
                target.unlink()
            with patch.object(d, 'fetch', return_value=(self.data, {}, 'https://example.org/data.tsv')) as fetch:
                result = d.acquire('test', {}, self.log, self.base, lambda _: ({}, self.assets))
                self.assertEqual(fetch.call_args.args[1], {})
            self.assertEqual(result['repaired_files'], ['test/data.tsv'])
            self.assertEqual(result['content_change'], 'unchanged')
            self.assertEqual(target.read_bytes(), self.data)

    def test_304_requires_verified_local_copy(self):
        self.run_source(headers={'ETag': 'v1'})
        with patch.object(d, 'fetch', return_value=(None, {}, 'https://example.org/data.tsv')) as fetch:
            result = d.acquire('test', {}, self.log, self.base, lambda _: ({}, self.assets))
            self.assertEqual(result['status'], 'unchanged')
            self.assertEqual(fetch.call_args.args[1], {'If-None-Match': 'v1'})
            (self.base / 'test/data.tsv').unlink()
            result = d.acquire('test', {}, self.log, self.base, lambda _: ({}, self.assets))
            self.assertEqual(result['status'], 'failed')

    def test_invalid_update_preserves_success_metadata_and_bytes(self):
        prior = copy.deepcopy(self.run_source())
        result = self.run_source(b'<html>Login</html>')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['files'], prior['files'])
        self.assertEqual(result['last_successful_check'], prior['last_successful_check'])
        self.assertEqual((self.base / 'test/data.tsv').read_bytes(), self.data)

    def test_related_set_is_not_partially_promoted(self):
        self.run_source()
        self.assets.append(registry.asset('https://example.org/support.tsv'))
        with patch.object(d, 'fetch', side_effect=[(b'ligand\treceptor\nE\tF\n', {}, ''), d.Unavailable('offline')]):
            result = d.acquire('test', {}, self.log, self.base, lambda _: ({}, self.assets))
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual((self.base / 'test/data.tsv').read_bytes(), self.data)
        self.assertFalse((self.base / 'test/support.tsv').exists())

    def test_immutable_metadata_skips_download_only_if_local_valid(self):
        import hashlib
        self.assets[0]['upstream_checksum'] = 'git-blob:' + hashlib.sha1(b'blob ' + str(len(self.data)).encode() + b'\0' + self.data).hexdigest()
        self.run_source()
        with patch.object(d, 'fetch', side_effect=AssertionError('Must not download')):
            result = d.acquire('test', {}, self.log, self.base, lambda _: ({}, self.assets))
        self.assertEqual(result['status'], 'unchanged')

    def test_unchanged_preserves_file_mtime(self):
        self.run_source()
        path = self.base / 'test/data.tsv'
        timestamp = path.stat().st_mtime_ns
        self.run_source()
        self.assertEqual(path.stat().st_mtime_ns, timestamp)

    def test_archive_extraction_keeps_only_requested_members(self):
        import io
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('data.tsv', self.data)
            archive.writestr('unrelated.txt', 'excluded')
        self.assets[0]['archive_member'] = 'data.tsv'
        result = self.run_source(buffer.getvalue())
        self.assertEqual(result['status'], 'updated')
        self.assertEqual((self.base / 'test/data.tsv').read_bytes(), self.data)
        self.assertFalse((self.base / 'test/unrelated.txt').exists())

    def test_bad_upstream_checksum_preserves_old_file(self):
        self.run_source()
        self.assets[0]['upstream_checksum'] = 'git-blob:incorrect'
        result = self.run_source()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual((self.base / 'test/data.tsv').read_bytes(), self.data)

    def test_recovery_uses_manifest_to_choose_complete_set(self):
        self.run_source()
        current = self.base / 'test'
        backup = self.base / '.test.backup'
        current.rename(backup)
        current.mkdir()
        (current / 'data.tsv').write_bytes(b'uncommitted data')
        d.recover_backups(self.base, self.log)
        self.assertEqual((current / 'data.tsv').read_bytes(), self.data)
        self.assertFalse(backup.exists())
        backup.mkdir()
        (backup / 'stale').write_bytes(b'old')
        d.recover_backups(self.base, self.log)
        self.assertFalse(backup.exists())

    def test_git_rate_limit_fallback_selects_current_commit(self):
        from types import SimpleNamespace
        commit = 'a' * 40
        output = SimpleNamespace(returncode=0, stdout=commit + '\tHEAD\n')
        with patch.object(registry, 'api_repo_state', side_effect=d.RateLimited('quota')), patch('subprocess.run', return_value=output):
            selection, assets = registry.repo_assets('soumelis-lab/ICELLNET', lambda b: ['data/ICELLNETdb.tsv'], prefer_release=False)
        self.assertEqual(selection['commit'], commit)
        self.assertIn(commit, assets[0]['url'])
        self.assertTrue(assets[0]['upstream_checksum'].startswith('git-commit:'))

    def test_log_write_failure_rolls_back_promoted_directory(self):
        self.run_source()
        original = d.atomic_json
        with patch.object(d, 'atomic_json', side_effect=[OSError('disk error'), None]):
            result = self.run_source(b'ligand\treceptor\nE\tF\n')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual((self.base / 'test/data.tsv').read_bytes(), self.data)

    def test_format_validation(self):
        for payload, name in [(b'', 'a.tsv'), (b'error', 'a.tsv'), (b'<html>Login</html>', 'a.rds'),
                              (gzip.compress(b'invalid'), 'a.rds'), (b'PKbad', 'a.xlsx')]:
            with self.subTest(name=name, payload=payload), self.assertRaises(Exception):
                d.validate(payload, name)
        d.validate(gzip.compress(b'X\n\x00\x00\x00\x03'), 'a.rds')

    def test_atomic_log_is_valid_json(self):
        self.run_source()
        self.assertEqual(json.loads((self.base / 'versions.txt').read_text()), self.log)
        self.assertFalse((self.base / 'versions.tmp').exists())

    def test_species_and_scope_without_conversion(self):
        selection, assets = registry.resolve('omnipathppis')
        self.assertEqual({a['species'] for a in assets}, {'human', 'mouse'})
        mouse = next(a for a in assets if a['species'] == 'mouse')
        self.assertEqual(mouse['provenance'], 'orthology-derived')
        self.assertEqual(mouse['query_parameters']['datasets'], 'ligrecextra')
        self.assertEqual(len(registry.SOURCES), 16)
        # Only stdlib acquisition is invoked; no analysis clients or translation functions.
        with patch.object(registry, 'repo_assets', return_value=({}, [])) as repo:
            registry.resolve('cellcall')
            classify = repo.call_args.args[2]
            self.assertEqual(classify('new_ligand_receptor_TFs_homology.txt'), ('mouse', 'orthology-derived'))


if __name__ == '__main__':
    unittest.main()
