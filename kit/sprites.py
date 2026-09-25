"""Fetches, verifies and caches the real VS Code pet sprites.

The sprites are not stored in this repository. They are downloaded once from
``microsoft/vscode`` at the commit pinned in ``kit/sprites.json``, checked against the
recorded SHA-256 checksums and cached in ``~/.cache/pet-studio/<commit>``.

Set ``PET_STUDIO_VSCODE_ROOT=/path/to/vscode`` to read a local checkout instead
(useful when you are changing the pet in VS Code itself), or
``PET_STUDIO_CACHE`` to move the cache.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

from . import KIT_ROOT, KitError

MANIFEST_PATH = KIT_ROOT / 'sprites.json'
RAW_URL = 'https://raw.githubusercontent.com/{repository}/{commit}/{path}'
API_URL = 'https://api.github.com/repos/{repository}'
USER_AGENT = 'pet-studio (github.com/federicobrancasi/pet-studio)'


class SpriteError(KitError, RuntimeError):
	pass


def manifest() -> dict:
	return json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))


def local_root() -> Path | None:
	value = os.environ.get('PET_STUDIO_VSCODE_ROOT')
	return Path(value).expanduser().resolve() if value else None


def cache_dir(commit: str | None = None) -> Path:
	base = os.environ.get('PET_STUDIO_CACHE')
	root = Path(base).expanduser() if base else Path.home() / '.cache' / 'pet-studio'
	return root / (commit or manifest()['commit'])


def _sha256(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()


def _download(url: str) -> bytes:
	request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
	last_error: Exception | None = None
	for _ in range(3):
		try:
			with urllib.request.urlopen(request, timeout=30, context=_ssl_context()) as response:
				return response.read()
		except Exception as error:  # network hiccups: retry a couple of times
			last_error = error
	hint = ''
	if 'CERTIFICATE_VERIFY_FAILED' in str(last_error):
		hint = ('\nPython cannot verify HTTPS certificates. On macOS with a python.org install, run '
			'"Install Certificates.command" from your Python folder, or: python3 -m pip install certifi')
	raise SpriteError(f'Could not download {url}: {last_error}{hint}')


def _ssl_context():
	"""Uses certifi's certificates when it is installed (fixes some macOS Python installs)."""
	try:
		import ssl

		import certifi
		return ssl.create_default_context(cafile=certifi.where())
	except Exception:  # certifi is optional
		return None


def _fetch(m: dict, path: str, expected: str | None, target: Path) -> None:
	data = _download(RAW_URL.format(repository=m['repository'], commit=m['commit'], path=path))
	if expected and _sha256(data) != expected:
		raise SpriteError(f'Checksum mismatch for {path}')
	tmp = target.with_suffix(target.suffix + '.part')
	tmp.write_bytes(data)
	tmp.replace(target)


def ensure(verbose: bool = False) -> Path:
	"""Makes sure every pinned sprite is cached and valid; returns the cache folder."""
	m = manifest()
	folder = cache_dir(m['commit'])
	folder.mkdir(parents=True, exist_ok=True)
	jobs = []
	for name, digest in m['files'].items():
		target = folder / name
		if not target.exists() or _sha256(target.read_bytes()) != digest:
			jobs.append((f"{m['spritesPath']}/{name}", digest, target))
	widget_target = folder / 'chatPetWidget.ts'
	if not widget_target.exists() or _sha256(widget_target.read_bytes()) != m['widgetSha256']:
		jobs.append((m['widgetPath'], m['widgetSha256'], widget_target))
	if jobs:
		if verbose:
			print(f"Downloading {len(jobs)} pet files from {m['repository']}@{m['commit'][:7]} ...", flush=True)
		with ThreadPoolExecutor(8) as pool:
			list(pool.map(lambda job: _fetch(m, *job), jobs))
	return folder


@lru_cache(maxsize=None)
def _sprite_folder() -> Path:
	root = local_root()
	if root is not None:
		folder = root / manifest()['spritesPath']
		if not folder.is_dir():
			raise SpriteError(f'No pet sprites in {folder}')
		return folder
	return ensure(verbose=True)


def read_bytes(name: str) -> bytes:
	path = _sprite_folder() / name
	if not path.exists():
		raise SpriteError(f'Unknown pet sprite: {name}')
	return path.read_bytes()


def exists(name: str) -> bool:
	return (_sprite_folder() / name).exists()


@lru_cache(maxsize=None)
def widget_source() -> str:
	root = local_root()
	if root is not None:
		return (root / manifest()['widgetPath']).read_text(encoding='utf-8')
	return (ensure() / 'chatPetWidget.ts').read_text(encoding='utf-8')


def widget_durations(constant: str) -> list[int] | None:
	"""Reads a ``*_FRAME_DURATIONS`` array from ``chatPetWidget.ts``."""
	source = widget_source()
	match = re.search(rf'const {re.escape(constant)} = \[([^\]]+)\]', source)
	if match:
		return [int(value.replace('_', '').strip()) for value in match.group(1).split(',') if value.strip()]
	match = re.search(rf'const {re.escape(constant)} = Array\.from\(\{{ length: (\d+) \}}, \(\) => (\d[\d_]*)\)', source)
	if match:
		return [int(match.group(2).replace('_', ''))] * int(match.group(1))
	return None


# --------------------------------------------------------------------------------------------
# Maintainer tool: move the pin to a newer VS Code commit.


def _api_json(url: str) -> dict | list:
	request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/vnd.github+json'})
	token = os.environ.get('GITHUB_TOKEN')
	if token:
		request.add_header('Authorization', f'Bearer {token}')
	with urllib.request.urlopen(request, timeout=30, context=_ssl_context()) as response:
		return json.loads(response.read())


def update_pin(ref: str = 'main') -> dict:
	"""Re-pins ``kit/sprites.json`` to ``ref`` of microsoft/vscode and returns the new manifest."""
	m = manifest()
	api = API_URL.format(repository=m['repository'])
	commit = _api_json(f'{api}/commits/{ref}')['sha']
	listing = _api_json(f"{api}/contents/{m['spritesPath']}?ref={commit}")
	names = sorted(item['name'] for item in listing if item['type'] == 'file' and item['name'].startswith('buddy-') and item['name'].endswith('.png'))
	fresh = dict(m, commit=commit, files={})
	folder = cache_dir(commit)
	folder.mkdir(parents=True, exist_ok=True)

	def grab(name: str) -> tuple[str, str]:
		data = _download(RAW_URL.format(repository=m['repository'], commit=commit, path=f"{m['spritesPath']}/{name}"))
		(folder / name).write_bytes(data)
		return name, _sha256(data)

	with ThreadPoolExecutor(8) as pool:
		fresh['files'] = dict(pool.map(grab, names))
	widget = _download(RAW_URL.format(repository=m['repository'], commit=commit, path=m['widgetPath']))
	(folder / 'chatPetWidget.ts').write_bytes(widget)
	fresh['widgetSha256'] = _sha256(widget)
	MANIFEST_PATH.write_text(json.dumps(fresh, indent='\t') + '\n', encoding='utf-8')
	_sprite_folder.cache_clear()
	widget_source.cache_clear()
	return fresh


def describe() -> str:
	m = manifest()
	root = local_root()
	if root is not None:
		return f'local checkout {root}'
	return f"{m['repository']}@{m['commit'][:7]} (cache {cache_dir(m['commit'])})"


if __name__ == '__main__':
	print(ensure(verbose=True))
	sys.exit(0)
