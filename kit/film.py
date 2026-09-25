"""Films: load a film module, render frames, export an MP4 and check determinism.

A film is one Python file (usually ``films/<name>/film.py``) that defines:

``DURATION``  seconds (float)
``FPS``       frames per second (default 60)
``SIZE``      ``(width, height)`` in pixels (default 1920 x 1080)
``render(t)`` returns a PIL image of exactly ``SIZE`` for time ``t``; must be a pure
              function of ``t`` (no state carried between frames, seeded randomness only)
``score(mix)`` optional; fills a :class:`kit.audio.Mixer` that is ``DURATION`` long
``CUES``      optional ``[(t, 'label'), ...]`` story beats, used by reviews and audio checks
``SEED``      optional audio seed (default 7)
``MASTER``    optional mastering settings for :meth:`kit.audio.Mixer.master`, e.g.
              ``{'ceiling': 0.7}`` to lower the true peak, ``{'fade_out': 1.0}`` for a longer fade
``TITLE``     optional human title
"""

from __future__ import annotations

import hashlib
import importlib.util
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from PIL import Image

from . import OUT_ROOT, REPO_ROOT, KitNotFoundError
from . import audio as A
from . import media


@dataclass
class Film:
	path: Path
	module: ModuleType

	@property
	def name(self) -> str:
		stem = self.path.stem
		return self.path.parent.name if stem in ('film', 'main') else stem

	@property
	def title(self) -> str:
		return getattr(self.module, 'TITLE', self.name)

	@property
	def duration(self) -> float:
		return float(self.module.DURATION)

	@property
	def fps(self) -> int:
		return int(getattr(self.module, 'FPS', 60))

	@property
	def size(self) -> tuple[int, int]:
		return tuple(getattr(self.module, 'SIZE', (1920, 1080)))

	@property
	def frames(self) -> int:
		return int(round(self.duration * self.fps))

	@property
	def cues(self) -> list[tuple[float, str]]:
		return [(float(t), str(label)) for (t, label) in getattr(self.module, 'CUES', [])]

	@property
	def has_score(self) -> bool:
		return callable(getattr(self.module, 'score', None))

	def out_dir(self) -> Path:
		folder = OUT_ROOT / self.name
		folder.mkdir(parents=True, exist_ok=True)
		return folder

	def render(self, t: float) -> Image.Image:
		img = self.module.render(t)
		if img.size != self.size:
			raise ValueError(f'render({t}) returned {img.size}, expected SIZE {self.size}')
		return img.convert('RGB')

	def frame(self, i: int) -> Image.Image:
		return self.render(i / self.fps)

	def mix(self) -> A.Mixer:
		mixer = A.Mixer(self.duration, seed=int(getattr(self.module, 'SEED', 7)), bpm=float(getattr(self.module, 'BPM', 120)))
		self.module.score(mixer)
		return mixer

	@property
	def master_settings(self) -> dict:
		return dict(getattr(self.module, 'MASTER', {}))

	def write_audio(self, path: str | Path | None = None) -> Path | None:
		if not self.has_score:
			return None
		return self.mix().write(path or self.out_dir() / f'{self.name}.wav', **self.master_settings)


def resolve(target: str | Path, kind: str) -> Path:
	"""Finds ``<kind>.py`` from a path, a folder, or just a name in ``<kind>s/`` or ``examples/``."""
	p = Path(target)
	if p.is_file():
		return p.resolve()
	if p.is_dir() and (p / f'{kind}.py').exists():
		return (p / f'{kind}.py').resolve()
	for base in (REPO_ROOT / f'{kind}s', REPO_ROOT / 'examples'):
		candidate = base / str(target) / f'{kind}.py'
		if candidate.exists():
			return candidate.resolve()
	raise KitNotFoundError(f'No {kind} called {str(target)!r}: give a {kind} name from {kind}s/ or examples/, or a path to {kind}.py (create one with: python3 -m kit {kind} new <name>)')


def load(path: str | Path) -> Film:
	"""Imports a film (a name, folder or file). Its folder goes on ``sys.path`` so it can import helpers next to it."""
	path = resolve(path, 'film')
	folder = str(path.parent)
	if folder not in sys.path:
		sys.path.insert(0, folder)
	name = f'_film_{hashlib.sha1(str(path).encode()).hexdigest()[:10]}'
	spec = importlib.util.spec_from_file_location(name, path)
	module = importlib.util.module_from_spec(spec)
	sys.modules[name] = module
	spec.loader.exec_module(module)
	for required in ('DURATION', 'render'):
		if not hasattr(module, required):
			raise AttributeError(f'{path} must define {required}')
	return Film(path, module)


def export(film: Film, out: str | Path | None = None, preset: str = 'x', start: float = 0.0, end: float | None = None, progress: bool = True) -> Path:
	"""Renders every frame into an MP4 (with the score when the whole film is exported)."""
	end = film.duration if end is None else min(end, film.duration)
	partial = start > 0 or end < film.duration
	suffix = '' if preset == 'x' and not partial else f'-{preset}' if not partial else f'-{start:g}-{end:g}s'
	out = Path(out) if out else film.out_dir() / f'{film.name}{suffix}.mp4'
	wav = None if partial else film.write_audio()
	first = int(round(start * film.fps))
	last = int(round(end * film.fps))
	t0 = time.time()
	with media.VideoWriter(out, film.size, film.fps, audio=wav, preset=preset) as video:
		for i in range(first, last):
			video.write(film.frame(i))
			if progress and (i - first) % (film.fps * 5) == 0:
				print(f'  frame {i - first}/{last - first}  ({time.time() - t0:.0f}s)', flush=True)
	if progress:
		print(f'  encoded {last - first} frames in {time.time() - t0:.0f}s -> {out}')
	return out


def gif(film: Film, out: str | Path | None = None, start: float = 0.0, end: float | None = None, fps: float = 20, width: int = 960) -> Path:
	"""A looping GIF rendered straight from the film, not from the MP4, so every frame is exact.
	It is downscaled by a whole number (``width`` is rounded to the nearest one) to stay sharp."""
	end = film.duration if end is None else min(end, film.duration)
	w, h = film.size
	k = max(1, round(w / width))
	size = (w // k, h // k)
	count = max(1, int(round((end - start) * fps)))

	def frames():
		for n in range(count):
			img = film.render(start + n / fps)
			yield img if k == 1 else img.resize(size, Image.NEAREST)

	out = Path(out) if out else film.out_dir() / f'{film.name}-{start:g}-{end:g}s.gif'
	return media.frames_to_gif(frames, size, fps, out)


def still(film: Film, t: float, out: str | Path | None = None) -> Path:
	out = Path(out) if out else film.out_dir() / f'{film.name}-{t:06.2f}s.png'
	out.parent.mkdir(parents=True, exist_ok=True)
	film.render(t).save(out)
	return out


def check_determinism(film: Film, samples: int = 16) -> dict:
	"""Renders frames twice in different orders; any difference means hidden state or
	unseeded randomness. Also renders the score twice when there is one."""
	rng = random.Random(1)
	frames = {0, film.frames - 1}
	frames.update(int(round(t * film.fps)) for (t, _) in film.cues if 0 <= t < film.duration)
	frames.update(rng.randrange(film.frames) for _ in range(samples))
	order = sorted(frames)
	first = {i: hashlib.sha256(film.frame(i).tobytes()).hexdigest() for i in order}
	second = {i: hashlib.sha256(film.frame(i).tobytes()).hexdigest() for i in reversed(order)}
	mismatched = [i for i in order if first[i] != second[i]]
	result = {'frames_checked': len(order), 'mismatched_frames': [round(i / film.fps, 4) for i in mismatched]}
	if film.has_score:
		a = film.mix().master(**film.master_settings).tobytes()
		b = film.mix().master(**film.master_settings).tobytes()
		result['audio_identical'] = hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()
	result['ok'] = not mismatched and result.get('audio_identical', True)
	return result
