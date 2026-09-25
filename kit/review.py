"""Review packages: everything a reviewer needs to judge a video without watching it.

``python3 -m kit film review films/<name>/film.py`` renders (or reuses) the MP4 and writes
``out/<name>/review/``:

* ``contact-NN.png``  one frame every 0.5 s, 15 s per sheet, timestamped
* ``cue-*.png``       full-resolution frames at every story cue
* ``strip-*.png``     12 fps strips around every cue, to judge motion and timing
* ``audio.png``       spectrogram and waveform with the cues marked
* ``report.md``       file specs, X upload checks, loudness and true peak

Every image comes from the encoded file, so it shows exactly what viewers will get.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image, ImageDraw

from . import audio as A
from . import media
from .font import draw_text

INK = (255, 220, 90, 255)
BG = (24, 24, 28)


def _slug(text: str) -> str:
	return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:32] or 'cue'


def _label(img: Image.Image, x: int, y: int, text: str) -> None:
	canvas = img.convert('RGBA') if img.mode != 'RGBA' else img
	draw_text(canvas, x, y, text, INK, 2)
	if canvas is not img:
		img.paste(canvas.convert(img.mode))


def contact_sheets(video: Path, folder: Path, every: float = 0.5, per_sheet: float = 15.0, cols: int = 5, width: int = 384) -> list[Path]:
	frames = list(media.decode_frames(video, 1 / every, width))
	per = int(round(per_sheet / every))
	paths = []
	for k in range(0, len(frames), per):
		chunk = frames[k:k + per]
		th = chunk[0][1].height
		rows = (len(chunk) + cols - 1) // cols
		sheet = Image.new('RGB', (cols * (width + 6) + 6, rows * (th + 28) + 6), BG)
		for i, (t, im) in enumerate(chunk):
			x = 6 + (i % cols) * (width + 6)
			y = 6 + (i // cols) * (th + 28)
			sheet.paste(im, (x, y + 22))
			_label(sheet, x + 2, y + 2, f'{t:05.2f}s')
		path = folder / f'contact-{len(paths) + 1:02d}.png'
		sheet.save(path)
		paths.append(path)
	return paths


def cue_frames(video: Path, folder: Path, cues: Sequence[tuple[float, str]], duration: float) -> list[Path]:
	paths = []
	for (t, label) in cues:
		t = min(max(t, 0.0), max(0.0, duration - 0.02))
		path = folder / f'cue-{t:06.2f}s-{_slug(label)}.png'
		media.frame_at(video, t).save(path)
		paths.append(path)
	return paths


def strips(video: Path, folder: Path, cues: Sequence[tuple[float, str]], duration: float, fps: int = 12, before: float = 0.4, after: float = 0.6, cols: int = 6, width: int = 320) -> list[Path]:
	paths = []
	for (t, label) in cues:
		start = max(0.0, t - before)
		length = min(duration - start, before + after)
		frames = list(media.decode_frames(video, fps, width, start, length))
		if not frames:
			continue
		th = frames[0][1].height
		rows = (len(frames) + cols - 1) // cols
		sheet = Image.new('RGB', (cols * (width + 4) + 4, rows * (th + 26) + 30), BG)
		_label(sheet, 6, 6, f'{label} @ {t:.2f}s')
		for i, (ft, im) in enumerate(frames):
			x = 4 + (i % cols) * (width + 4)
			y = 30 + (i // cols) * (th + 26)
			sheet.paste(im, (x, y + 20))
			_label(sheet, x + 2, y + 2, f'{ft:.2f}')
		path = folder / f'strip-{t:06.2f}s-{_slug(label)}.png'
		sheet.save(path)
		paths.append(path)
	return paths


def spectrogram(samples: np.ndarray, path: Path, duration: float, cues: Sequence[tuple[float, str]], width: int = 2000, height: int = 320, rate: int = 48000) -> Path:
	img = Image.new('RGB', (width, height + 230), BG)
	if len(samples) >= 4096:
		nfft = 2048
		hop = max(1, (len(samples) - nfft) // width)
		win = np.hanning(nfft)
		ys = np.array([50 * (16000 / 50) ** (1 - y / height) for y in range(height)])
		bins = np.clip((ys / (rate / nfft)).astype(int), 0, nfft // 2)
		spec = np.zeros((height, width))
		for i in range(width):
			seg = samples[i * hop:i * hop + nfft]
			if len(seg) < nfft:
				break
			sp = 20 * np.log10(np.abs(np.fft.rfft(seg * win)) + 1e-6)
			spec[:, i] = sp[bins]
		v = np.clip((spec + 30) / 70, 0, 1)
		img.paste(Image.fromarray(np.stack([255 * v, 180 * v * v, 80 * v], -1).astype(np.uint8)), (0, 0))
		d = ImageDraw.Draw(img)
		per = len(samples) / width
		for i in range(width):
			seg = samples[int(i * per):int((i + 1) * per)]
			a = float(np.abs(seg).max()) if len(seg) else 0.0
			d.line([(i, height + 45 - a * 40), (i, height + 45 + a * 40)], fill=(120, 200, 255))
	d = ImageDraw.Draw(img)
	step = 1 if duration <= 12 else 2 if duration <= 40 else 5
	s = 0
	while s <= duration + 1e-6:
		x = int(s / duration * (width - 1))
		d.line([(x, 0), (x, height + 90)], fill=(70, 70, 70))
		_label(img, x + 3, height + 94, f'{s}s')
		s += step
	row_ends: list[int] = []
	for (t, label) in cues:
		x = int(t / duration * (width - 1))
		text = label[:28]
		text_w = (len(text) * 6 - 1) * 2 + 12
		row = next((r for r, end in enumerate(row_ends) if end <= x), None)
		if row is None:
			row = len(row_ends)
			row_ends.append(0)
		row_ends[row] = x + text_w
		if row > 3:
			continue  # too crowded to label; the line still marks the cue
		d.line([(x, height + 116), (x, height + 124 + row * 26)], fill=(255, 120, 120))
		_label(img, x + 3, height + 118 + row * 26, text)
	img.save(path)
	return path


def build(video: str | Path, cues: Sequence[tuple[float, str]] = (), folder: str | Path | None = None, determinism: dict | None = None) -> Path:
	"""Writes the review package for ``video``; returns the folder."""
	video = Path(video)
	folder = Path(folder) if folder else video.parent / 'review'
	folder.mkdir(parents=True, exist_ok=True)
	for pattern in ('contact-*.png', 'cue-*.png', 'strip-*.png', 'audio.png', 'report.md', 'report.json'):
		for old in folder.glob(pattern):  # only the files a previous review wrote
			old.unlink()
	info = media.probe(video)
	duration = info.get('duration', 0.0)
	cues = [(t, label) for (t, label) in cues if 0 <= t < duration]
	sheets = contact_sheets(video, folder)
	keys = cue_frames(video, folder, cues, duration)
	dense = strips(video, folder, cues, duration)
	audio_png = None
	loud = {'lufs': None, 'true_peak_db': None}
	if info.get('audio'):
		audio_png = spectrogram(media.decode_audio(video), folder / 'audio.png', duration, cues)
		loud = A.loudness(video)
	checks = media.x_checks(info)
	report = {'video': str(video), 'specs': info, 'loudness': loud, 'x_checks': [{'check': n, 'ok': ok, 'detail': d} for (n, ok, d) in checks], 'cues': cues}
	if determinism is not None:
		report['determinism'] = determinism
	(folder / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
	v = info.get('video', {})
	lines = [
		f'# Review package: {video.name}',
		'',
		f"- **File:** {info['bytes'] / 1e6:.1f} MB, {duration:.2f} s, {v.get('width')}x{v.get('height')} at {v.get('fps')} fps, {v.get('codec')} {v.get('profile') or ''} {v.get('pix_fmt')}",
		f"- **Audio:** {info['audio']['codec']} {info['audio']['sample_rate']} Hz {info['audio']['channels']}, {loud['lufs']} LUFS, true peak {loud['true_peak_db']} dBTP" if info.get('audio') else '- **Audio:** none',
	]
	if determinism is not None:
		lines.append(f"- **Determinism:** {'OK' if determinism.get('ok') else 'FAILED'} ({determinism.get('frames_checked')} frames re-rendered in a different order)")
	lines += ['', '## X upload checks', '']
	lines += [f"- {'PASS' if ok else 'FAIL'} {name}: {detail}" for (name, ok, detail) in checks]
	if loud['true_peak_db'] is not None and loud['true_peak_db'] > -1.0:
		lines.append(f"- WARN true peak {loud['true_peak_db']} dBTP is above -1 dBTP; lower the master ceiling")
	lines += ['', '## Files', '']
	lines += [f'- `{p.name}`' for p in [*sheets, *keys, *dense] + ([audio_png] if audio_png else [])]
	lines += ['', '## Cues', '']
	lines += [f'- {t:6.2f}s  {label}' for (t, label) in cues] or ['- (none: add CUES to the film)']
	(folder / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
	return folder
