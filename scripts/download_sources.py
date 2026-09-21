"""Acquire raw LR sources. Python 3.10+, standard library only."""
from __future__ import annotations

import argparse
import bz2
import copy
import csv
import gzip
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import shutil
import stat
import tempfile
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import zipfile


ROOT = Path(__file__).resolve().parents[1]


# =============================================================================
# Acquisition validation and transactional recovery
# =============================================================================
class Unavailable(RuntimeError):
    pass


class AuthenticationRequired(Unavailable):
    pass


class RateLimited(Unavailable):
    pass


def now():
    """Return a UTC acquisition timestamp at second precision.
    
    Returns
    -------
    str
        ISO-8601 UTC timestamp.
    """
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sha(data):
    """Hash original payload bytes before any parsing or transformation.
    
    Parameters
    ----------
    data : bytes or object
        Payload in the representation consumed by this function.
    
    Returns
    -------
    str
        SHA-256 hexadecimal digest.
    """
    return hashlib.sha256(data).hexdigest()


def fetch(url, headers=None):
    """Fetch a bounded HTTPS payload with verified TLS and at most three attempts.
    Credentials are supplied in headers, never added to source URLs.
    
    Parameters
    ----------
    url : str
        Official provider URL, without embedded credentials.
    headers : dict, optional
        Request headers; authentication belongs here, not in URLs.
    
    Returns
    -------
    tuple
        Payload bytes (None for HTTP 304), response headers and final URL.
    
    Raises
    ------
    AuthenticationRequired
        On authentication/quota/unavailable transport states or invalid payload size, according to the exception class.
    RateLimited
        On authentication/quota/unavailable transport states or invalid payload size, according to the exception class.
    Unavailable
        On authentication/quota/unavailable transport states or invalid payload size, according to the exception class.
    ValueError
        On authentication/quota/unavailable transport states or invalid payload size, according to the exception class.
    """
    request_headers = {'User-Agent': 'LR-source-acquisition/1.0', **(headers or {})}
    if urlsplit(url).netloc == 'api.github.com' and os.environ.get('GITHUB_TOKEN'):
        request_headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=request_headers), timeout=45) as response:
                data = response.read(150_000_001)
                if len(data) > 150_000_000:
                    raise ValueError('Payload exceeds 150 MB acquisition limit')
                if response.headers.get('Content-Length') and len(data) != int(response.headers['Content-Length']):
                    raise ValueError('Truncated HTTP payload')
                return data, dict(response.headers), response.geturl()
        except HTTPError as exc:
            if exc.code == 304:
                return None, dict(exc.headers), url
            if exc.code == 403 and exc.headers.get('X-RateLimit-Remaining') == '0':
                raise RateLimited(f'GitHub API rate limit at {url}; set GITHUB_TOKEN or use Git fallback') from None
            if exc.code in (401, 403):
                raise AuthenticationRequired(f'HTTP {exc.code} at {url}') from None
            if exc.code in (404, 410):
                raise Unavailable(f'HTTP {exc.code} at {url}') from None
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise Unavailable(f'HTTP {exc.code} at {url}') from None
        except (URLError, TimeoutError, ConnectionError) as exc:
            if attempt == 2:
                raise Unavailable(f'{type(exc).__name__} fetching {url}: {exc.reason if isinstance(exc, URLError) else "timeout/connection failure"}') from None
        time.sleep(1 + attempt)


def get_json(url):
    """Decode a provider JSON response after the bounded fetch policy.
    
    Parameters
    ----------
    url : str
        Official provider URL, without embedded credentials.
    
    Returns
    -------
    object
        Decoded provider JSON.
    """
    return json.loads(fetch(url)[0])


def validate(data, filename, expected=()):
    """Reject empty, truncated-format or login-page payloads before promotion.
    
    Parameters
    ----------
    data : bytes or object
        Payload in the representation consumed by this function.
    filename : str
        Original filename used for format selection.
    expected : sequence[str]
        Required source header tokens.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    
    Raises
    ------
    ValueError
        If bytes fail the selected format, expected headers or nonempty-data checks.
    """
    if not data or not data.strip():
        raise ValueError('Empty payload')
    head = data[:4096].lstrip().lower()
    if b'<html' in head or b'<!doctype html' in head or b'<form' in head:
        raise ValueError('HTML/login/error page instead of data')
    ext = Path(filename).suffix.lower()
    if ext in ('.rda', '.rdata', '.rds'):
        raw = data
        if raw.startswith(b'\x1f\x8b'):
            raw = gzip.decompress(raw)
        elif raw.startswith(b'BZh'):
            raw = bz2.decompress(raw)
        elif raw.startswith(b'\xfd7zXZ'):
            raw = lzma.decompress(raw)
        if not raw.startswith((b'RDX', b'RDA', b'RDB', b'X\n', b'A\n', b'B\n')):
            raise ValueError('Invalid R serialization signature')
    elif ext in ('.xlsx', '.zip'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if archive.testzip() is not None or not archive.namelist():
                raise ValueError('Invalid ZIP content')
            if ext == '.xlsx' and 'xl/workbook.xml' not in archive.namelist():
                raise ValueError('Missing XLSX workbook')
    elif ext == '.xls':
        if not data.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
            raise ValueError('Invalid XLS compound document')
    else:
        text = data.decode('utf-8-sig')
        lines = [line for line in text.splitlines() if line.strip() and not line.startswith('#')]
        if len(lines) < 2:
            raise ValueError('Missing tabular data rows')
        delimiter = '\t' if '\t' in lines[0] else ','
        columns = next(csv.reader([lines[0]], delimiter=delimiter))
        if len(columns) < 2:
            raise ValueError('Missing tabular header')
        if any(token.lower() not in lines[0].lower() for token in expected):
            raise ValueError(f'Missing expected header fields: {expected}')


def atomic_json(path, data):
    """Flush metadata to a temporary file and atomically replace its destination.
    The manifest must never advertise partially written JSON.
    
    Parameters
    ----------
    path : Path
        Local file or directory used by this operation.
    data : bytes or object
        Payload in the representation consumed by this function.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    temp = path.with_suffix('.tmp')
    try:
        with temp.open('w', encoding='utf-8', newline='\n') as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def remove_tree(path):
    """Remove a caller-validated disposable directory, including OneDrive read-only entries.
    Callers must establish path safety and recovery ownership before invoking this helper.
    
    Parameters
    ----------
    path : Path
        Local file or directory used by this operation.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    def writable_retry(function, target, error):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        function(target)
    shutil.rmtree(path, onerror=writable_retry)


def recover_backups(base, manifest):
    """Reconcile interrupted source promotions against recorded checksums.
    Keep ambiguous recovery state for inspection rather than guessing which copy is valid.
    
    Parameters
    ----------
    base : Path
        Source acquisition root owned by this workflow.
    manifest : dict
        Recorded source selections, checksums and processing state.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    
    Raises
    ------
    ValueError
        If neither current nor backup files establish a complete manifest-consistent source set.
    """
    for backup in base.glob('.*.backup'):
        source_id = backup.name[1:-7]
        records = manifest['sources'].get(source_id, {}).get('files', [])
        current = base / source_id
        def matches(folder):
            return bool(records) and all((folder / Path(f['path']).relative_to(source_id)).is_file() and
                sha((folder / Path(f['path']).relative_to(source_id)).read_bytes()) == f['sha256'] for f in records)
        if matches(current):
            remove_tree(backup)
        elif matches(backup):
            if current.exists():
                remove_tree(current)
            backup.rename(current)
        else:
            raise ValueError(f'Cannot safely recover {source_id}; inspect backup and versions.txt')


def acquire(source_id, definition, manifest, base, resolve):
    """Stage one complete source update and promote only validated asset sets.
    On acquisition failure, retain the previous successful assets and record the attempt.
    
    Parameters
    ----------
    source_id : str
        One registered provider identifier.
    definition : dict
        Provider discovery, citation and scope metadata.
    manifest : dict
        Recorded source selections, checksums and processing state.
    base : Path
        Source acquisition root owned by this workflow.
    resolve : callable
        Provider-specific discovery callback.
    
    Returns
    -------
    dict
        Updated source manifest record, including handled failure status.
    
    Notes
    -----
    Discovery, authentication and validation errors are recorded as failed attempts.
    Metadata write or unrecoverable filesystem errors may still propagate.
    
    Raises
    ------
    OSError
        If persisting failure metadata or restoring the previous source directory fails.
    """
    old = copy.deepcopy(manifest['sources'].get(source_id, {}))
    attempt = now()
    record = {**old, **definition, 'latest_attempt': attempt, 'status': 'failed', 'error': None,
              'content_change': 'not_checked'}
    current = base / source_id
    backup = base / ('.' + source_id + '.backup')
    promoted = False
    moved_old = False
    selection = None
    try:
        selection, assets = resolve(source_id)
        record['attempted_selection'] = selection
        if not assets:
            raise Unavailable('No relevant assets discovered')
        paths = [a['name'] for a in assets]
        if len(set(paths)) != len(paths) or any(Path(p).is_absolute() or '..' in Path(p).parts for p in paths):
            raise ValueError('Unsafe or duplicate asset paths')
        previous = {f['path']: f for f in old.get('files', [])}
        files, changed, repaired, downloaded = [], [], [], []
        responses = {}
        with tempfile.TemporaryDirectory(prefix='.download-', dir=base) as staging:
            stage = Path(staging) / source_id
            stage.mkdir()
            for asset in assets:
                relative = source_id + '/' + asset['name']
                target = base / relative
                prior = previous.get(relative, {})
                valid = target.is_file() and sha(target.read_bytes()) == prior.get('sha256')
                same_url = asset['url'] == prior.get('download_url')
                headers = {}
                if valid and same_url:
                    if prior.get('etag'):
                        headers['If-None-Match'] = prior['etag']
                    elif prior.get('last_modified'):
                        headers['If-Modified-Since'] = prior['last_modified']
                immutable = asset.get('upstream_checksum')
                if valid and same_url and immutable and immutable == prior.get('upstream_checksum'):
                    data, response_headers = target.read_bytes(), {}
                    received = False
                else:
                    cache_key = (asset['url'], tuple(sorted(headers.items())))
                    if cache_key not in responses:
                        responses[cache_key] = fetch(asset['url'], headers)
                    data, response_headers, final_url = responses[cache_key]
                    received = data is not None
                    if data is None:
                        if not valid:
                            raise ValueError('304 without verified local data')
                        data = target.read_bytes()
                    elif 'login' in urlsplit(final_url).path.lower():
                        raise AuthenticationRequired('Provider redirected to login')
                    elif asset.get('archive_member'):
                        with zipfile.ZipFile(io.BytesIO(data)) as archive:
                            data = archive.read(asset['archive_member'])
                validate(data, asset['name'], asset.get('headers', ()))
                digest = sha(data)
                if immutable and immutable.startswith('git-blob:'):
                    git_digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                    if git_digest != immutable.removeprefix('git-blob:'):
                        raise ValueError('Git blob checksum mismatch')
                if asset.get('md5') and hashlib.md5(data).hexdigest() != asset['md5']:
                    raise ValueError('Provider checksum mismatch')
                if digest != prior.get('sha256'):
                    changed.append(relative)
                if prior and not valid:
                    repaired.append(relative)
                if received:
                    downloaded.append(relative)
                staged = stage / asset['name']
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_bytes(data)
                response_headers = {k.lower(): v for k, v in response_headers.items()}
                files.append({'path': relative, 'download_url': asset['url'], 'species': asset['species'],
                              'provenance': asset['provenance'], 'size': len(data), 'sha256': digest,
                              'upstream_checksum': immutable,
                              'etag': response_headers.get('etag', prior.get('etag') if same_url else None),
                              'last_modified': response_headers.get('last-modified', prior.get('last_modified') if same_url else None),
                              'last_successful_check': now(),
                              'last_download': now() if received else prior.get('last_download'),
                              'archive_member': asset.get('archive_member'),
                              'query_parameters': asset.get('query_parameters')})
            removed = sorted(set(previous) - {f['path'] for f in files})
            record.update(selection=selection, files=files, last_successful_check=now(),
                          last_successful_download=now() if downloaded else old.get('last_successful_download'),
                          status='updated' if changed or removed else 'unchanged',
                          content_change='changed' if changed or removed else 'unchanged',
                          changed_files=changed, removed_files=removed, repaired_files=repaired,
                          downloaded_files=downloaded)
            # All related assets have validated before touching the previous set.
            if changed or removed or repaired:
                if current.exists():
                    current.rename(backup)
                    moved_old = True
                stage.rename(current)
                promoted = True
            manifest['sources'][source_id] = record
            atomic_json(base / 'versions.txt', manifest)
        if backup.exists():
            # A cleanup failure must never roll back an already committed good set.
            try:
                remove_tree(backup)
            except OSError:
                print(f'  Cleanup deferred for {backup.name}; next run verifies and removes it', flush=True)
    except Exception as exc:
        if promoted:
            remove_tree(current)
        if moved_old:
            backup.rename(current)
        record = {**old, **definition, 'latest_attempt': attempt,
                  'status': 'authentication-required' if isinstance(exc, AuthenticationRequired) else
                            'unavailable' if isinstance(exc, Unavailable) else 'failed',
                  'error': str(exc), 'content_change': 'not_checked'}
        record['attempted_selection'] = selection
        record.setdefault('files', [])
        record.setdefault('last_successful_check', None)
        record.setdefault('last_successful_download', None)
        manifest['sources'][source_id] = record
        atomic_json(base / 'versions.txt', manifest)
    return record


def main():
    # Registry imports this module; keep exception identities identical under CLI execution.
    """Parse command-line options and execute this module workflow with its documented safety checks.
    
    Returns
    -------
    int or None
        Nonzero status on explicitly handled workflow failure; otherwise success.
    
    Raises
    ------
    ValueError
        If the existing acquisition manifest uses an unsupported schema version.
    """
    import sys
    sys.modules.setdefault('download_sources', sys.modules[__name__])
    from source_registry import SOURCES, resolve
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=list(SOURCES), action='append', help='Retry one source; repeatable')
    args = parser.parse_args()
    base = ROOT / 'data' / 'sources'
    base.mkdir(parents=True, exist_ok=True)
    lock = base / '.download.lock'
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        parser.error('Another run or interrupted run exists; inspect .download.lock and recovery note')
    os.close(lock_fd)
    try:
        path = base / 'versions.txt'
        manifest = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema_version': 1, 'sources': {}}
        if manifest.get('schema_version') != 1:
            raise ValueError('Unsupported manifest schema')
        recover_backups(base, manifest)
        run = {'started': now(), 'sources': {}}
        for source_id in args.source or SOURCES:
            (base / source_id).mkdir(exist_ok=True)
            print(f'Checking {source_id}...', flush=True)
            result = acquire(source_id, SOURCES[source_id], manifest, base, resolve)
            run['sources'][source_id] = {'status': result['status'], 'content_change': result['content_change']}
            print(f"  {result['status']}: {result.get('error') or str(len(result['files'])) + ' files'}", flush=True)
        run['finished'] = now()
        manifest['last_run'] = run
        atomic_json(path, manifest)
        counts = {s: sum(x['status'] == s for x in run['sources'].values()) for s in
                  ['updated', 'unchanged', 'unavailable', 'authentication-required', 'failed']}
        print(json.dumps(counts), flush=True)
        return int(any(x['status'] not in ('updated', 'unchanged') for x in run['sources'].values()))
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
