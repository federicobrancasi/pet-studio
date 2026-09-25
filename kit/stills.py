"""Stills: posters, wallpapers, X headers, phone screens and stickers.

A still is one Python file (usually ``stills/<name>/still.py``) that defines
``render(width, height)`` and returns a PIL image of exactly that size. Presets render
at a base size and then scale up by a whole number with nearest-neighbor sampling, so
pixel art stays perfectly crisp::

    python3 -m kit still render stills/<name>/still.py --preset wallpaper

A still may also set ``TITLE`` and ``DEFAULT_PRESET``. Draw at film scale (a pet at
``scale=2`` is 192 px tall): the base sizes below are chosen so that works everywhere.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

from PIL import Image

from . import OUT_ROOT, KitError
from .draw import upscale

# name: (base size, integer upscale, what it is for)
PRESETS = {
	'x-post': ((1920, 1080), 1, 'Image post on X, 16:9 (1920x1080)'),
	'square': ((1080, 1080), 1, 'Square post (1080x1080)'),
	'x-header': ((1500, 500), 1, 'X profile header (1500x500)'),
	'wallpaper': ((1920, 1080), 2, '4K desktop wallpaper (3840x2160)'),
	'phone': ((585, 1266), 2, 'Phone lock screen (1170x2532)'),
	'sticker': ((512, 512), 1, 'Transparent sticker (512x512); keep the background transparent'),
}


class Still:
	def __init__(self, path: Path, module):
		self.path = path
		self.module = module

	@property
	def name(self) -> str:
		stem = self.path.stem
		return self.path.parent.name if stem in ('still', 'main') else stem

	@property
	def default_preset(self) -> str:
		return getattr(self.module, 'DEFAULT_PRESET', 'x-post')

	def render(self, preset: str) -> Image.Image:
		if preset not in PRESETS:
			raise KitError(f'Unknown preset {preset!r}. Choose from: {", ".join(PRESETS)}')
		(w, h), k, _ = PRESETS[preset]
		img = self.module.render(w, h)
		if img.size != (w, h):
			raise ValueError(f'render({w}, {h}) returned {img.size}')
		img = upscale(img.convert('RGBA'), k)
		return img if preset == 'sticker' else img.convert('RGB')

	def save(self, preset: str, out: str | Path | None = None) -> Path:
		out = Path(out) if out else OUT_ROOT / self.name / f'{self.name}-{preset}.png'
		out.parent.mkdir(parents=True, exist_ok=True)
		self.render(preset).save(out, optimize=True)
		return out


def load(path: str | Path) -> Still:
	"""Imports a still (a name from ``stills/`` or ``examples/``, a folder, or a file)."""
	from .film import resolve

	path = resolve(path, 'still')
	folder = str(path.parent)
	if folder not in sys.path:
		sys.path.insert(0, folder)
	name = f'_still_{hashlib.sha1(str(path).encode()).hexdigest()[:10]}'
	spec = importlib.util.spec_from_file_location(name, path)
	module = importlib.util.module_from_spec(spec)
	sys.modules[name] = module
	spec.loader.exec_module(module)
	if not callable(getattr(module, 'render', None)):
		raise AttributeError(f'{path} must define render(width, height)')
	return Still(path, module)
