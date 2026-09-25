"""ffmpeg helpers: X-ready video encoding, GIF/APNG export and file inspection.

ffmpeg comes from the ``imageio-ffmpeg`` package, so nothing needs to be installed by
hand. Set ``FFMPEG=/path/to/ffmpeg`` to use your own build (it needs libx264).
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np
from PIL import Image

# Encoding presets. Films choose their own size and fps; presets choose quality.
PRESETS = {
	'x': {'crf': 12, 'speed': 'slow', 'audio_kbps': 192, 'about': 'Final upload quality for X: H.264 High, CRF 12, AAC 192k, BT.709, faststart.'},
	'draft': {'crf': 23, 'speed': 'veryfast', 'audio_kbps': 128, 'about': 'Quick look while iterating (about 4x faster).'},
}

# Limits for a standard X (Twitter) video upload (landscape; portrait swaps width and height).
X_LIMITS = {'max_seconds': 140, 'max_bytes': 512 * 1024 * 1024, 'max_fps': 60, 'max_long_side': 1920, 'max_short_side': 1200}


def ffmpeg_exe() -> str:
	override = os.environ.get('FFMPEG')
	if override:
		return override
	import imageio_ffmpeg

	return imageio_ffmpeg.get_ffmpeg_exe()


def run(args: Sequence[str], **kwargs) -> subprocess.CompletedProcess:
	return subprocess.run([ffmpeg_exe(), '-hide_banner', *args], **kwargs)


class VideoWriter:
	"""Pipes RGB frames into an H.264 encode, then optionally muxes a WAV.

	Use as a context manager::

	    with VideoWriter('out.mp4', (1920, 1080), 60, audio='score.wav') as video:
	        for i in range(frames):
	            video.write(render(i / 60))
	"""

	def __init__(self, path: str | Path, size: tuple[int, int], fps: int, audio: str | Path | None = None, preset: str = 'x'):
		settings = PRESETS[preset]
		self.path = Path(path)
		self.path.parent.mkdir(parents=True, exist_ok=True)
		self.size = size
		w, h = size
		cmd = [ffmpeg_exe(), '-y', '-hide_banner', '-loglevel', 'error',
			'-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(fps), '-i', '-']
		if audio:
			cmd += ['-i', str(audio)]
		cmd += [
			'-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
			'-c:v', 'libx264', '-preset', settings['speed'], '-crf', str(settings['crf']), '-tune', 'animation',
			'-profile:v', 'high', '-level', '4.2', '-g', str(fps * 2),
			'-x264-params', 'colorprim=bt709:transfer=bt709:colormatrix=bt709',
			'-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
		]
		if audio:
			cmd += ['-c:a', 'aac', '-b:a', f"{settings['audio_kbps']}k", '-ar', '48000', '-shortest']
		cmd += ['-movflags', '+faststart', str(self.path)]
		self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

	def write(self, frame: Image.Image) -> None:
		if frame.size != self.size:
			raise ValueError(f'Frame is {frame.size}, expected {self.size}')
		self.proc.stdin.write(frame.convert('RGB').tobytes())

	def close(self) -> None:
		if self.proc.stdin and not self.proc.stdin.closed:
			self.proc.stdin.close()
		if self.proc.wait():
			raise RuntimeError(f'ffmpeg failed while writing {self.path}')

	def __enter__(self) -> 'VideoWriter':
		return self

	def __exit__(self, exc_type, exc, tb) -> None:
		if exc_type is None:
			self.close()
		else:
			self.proc.kill()


def probe(path: str | Path) -> dict:
	"""Basic facts about a media file (parsed from ``ffmpeg -i``)."""
	text = run(['-i', str(path)], capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
	info: dict = {'path': str(path), 'bytes': Path(path).stat().st_size}
	m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', text)
	if m:
		info['duration'] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
	m = re.search(r'Stream #\S+: Video: (\w+)(?: \((\w[\w ]*)\))?.*?, (\w+)\(([^)]*)\).*?, (\d+)x(\d+).*?, ([\d.]+) fps', text)
	if m:
		info['video'] = {'codec': m.group(1), 'profile': m.group(2), 'pix_fmt': m.group(3), 'color': m.group(4), 'width': int(m.group(5)), 'height': int(m.group(6)), 'fps': float(m.group(7))}
	m = re.search(r'Stream #\S+: Audio: (\w+).*?, (\d+) Hz, (\w+)', text)
	if m:
		info['audio'] = {'codec': m.group(1), 'sample_rate': int(m.group(2)), 'channels': m.group(3)}
	if Path(path).suffix.lower() in ('.mp4', '.mov', '.m4v'):
		with open(path, 'rb') as handle:
			head = handle.read(4096)
		moov, mdat = head.find(b'moov'), head.find(b'mdat')
		info['faststart'] = moov != -1 and (mdat == -1 or moov < mdat)
	return info


def x_checks(info: dict) -> list[tuple[str, bool, str]]:
	"""Checks a probed MP4 against X's upload requirements: ``[(name, ok, detail), ...]``."""
	v = info.get('video') or {}
	a = info.get('audio')
	long_side = max(v.get('width', 0), v.get('height', 0))
	short_side = min(v.get('width', 0), v.get('height', 0))
	checks = [
		('H.264 video', v.get('codec') == 'h264', f"codec {v.get('codec')}"),
		('yuv420p pixels', v.get('pix_fmt') == 'yuv420p', f"pix_fmt {v.get('pix_fmt')}"),
		('frame size', 0 < long_side <= X_LIMITS['max_long_side'] and short_side <= X_LIMITS['max_short_side'], f"{v.get('width')}x{v.get('height')}"),
		('frame rate', 0 < v.get('fps', 0) <= X_LIMITS['max_fps'], f"{v.get('fps')} fps"),
		('length', 0 < info.get('duration', 0) <= X_LIMITS['max_seconds'], f"{info.get('duration', 0):.2f} s"),
		('file size', info['bytes'] <= X_LIMITS['max_bytes'], f"{info['bytes'] / 1e6:.1f} MB"),
		('AAC audio', a is None or a.get('codec') == 'aac', 'no audio' if a is None else f"codec {a.get('codec')}"),
		('faststart', bool(info.get('faststart')), 'moov atom first' if info.get('faststart') else 'moov atom at the end'),
	]
	return checks


def decode_frames(path: str | Path, fps: float, width: int, start: float = 0.0, duration: float | None = None) -> Iterable[tuple[float, Image.Image]]:
	"""Yields ``(t, image)`` sampled at ``fps`` from a video, scaled to ``width`` px wide."""
	info = probe(path)
	v = info['video']
	height = int(round(v['height'] * width / v['width'] / 2)) * 2
	args = ['-loglevel', 'error']
	if start:
		args += ['-ss', f'{start:.4f}']
	args += ['-i', str(path)]
	if duration is not None:
		args += ['-t', f'{duration:.4f}']
	args += ['-vf', f'fps={fps},scale={width}:{height}:flags=area', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
	proc = subprocess.Popen([ffmpeg_exe(), '-hide_banner', *args], stdout=subprocess.PIPE)
	size = width * height * 3
	i = 0
	while True:
		buf = proc.stdout.read(size)
		if len(buf) < size:
			break
		yield start + i / fps, Image.frombytes('RGB', (width, height), buf)
		i += 1
	proc.wait()


def frame_at(path: str | Path, t: float) -> Image.Image:
	"""One full-size frame of a video at ``t`` seconds."""
	info = probe(path)
	v = info['video']
	w, h = v['width'], v['height']
	out = run(['-loglevel', 'error', '-ss', f'{t:.4f}', '-i', str(path), '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
	return Image.frombytes('RGB', (w, h), out[:w * h * 3])


def decode_audio(path: str | Path, rate: int = 48000) -> np.ndarray:
	"""Mono float samples of a file's audio track."""
	out = run(['-loglevel', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-'], capture_output=True).stdout
	return np.frombuffer(out, dtype=np.float32)


# --------------------------------------------------------------------------------------------
# Animated images


def save_animation(frames: Sequence[Image.Image], durations_ms: Sequence[int], path: str | Path, loop: bool = True) -> Path:
	"""Saves an APNG (``.png``) or GIF (``.gif``) with exact per-frame durations.

	GIF frame times are stored in 10 ms steps, so durations are rounded; APNG keeps them
	exact. GIFs have no partial transparency, so pass frames on a solid background.
	"""
	path = Path(path)
	path.parent.mkdir(parents=True, exist_ok=True)
	durations = [max(20, int(d)) for d in durations_ms]
	if path.suffix.lower() == '.gif':
		palette_src = _palette_source(frames)
		palette = palette_src.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
		out = [f.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
		out[0].save(path, save_all=True, append_images=out[1:], duration=[int(round(d / 10)) * 10 for d in durations], loop=0 if loop else 1, disposal=1, optimize=False)
	else:
		rgba = [f.convert('RGBA') for f in frames]
		rgba[0].save(path, format='PNG', save_all=True, append_images=rgba[1:], duration=durations, loop=0 if loop else 1, disposal=0, blend=0)
	return path


def _palette_source(frames: Sequence[Image.Image]) -> Image.Image:
	"""A tall image made of (downsampled) frames, used to build one shared GIF palette."""
	step = max(1, len(frames) // 24)
	picks = [f.convert('RGB') for f in frames[::step]]
	w = max(p.width for p in picks)
	thumbs = [p.resize((min(w, 480), max(1, int(p.height * min(w, 480) / p.width))), Image.NEAREST) for p in picks]
	h = sum(t.height for t in thumbs)
	canvas = Image.new('RGB', (thumbs[0].width, h))
	y = 0
	for t in thumbs:
		canvas.paste(t, (0, y))
		y += t.height
	return canvas


def video_to_gif(video: str | Path, path: str | Path, start: float, duration: float, fps: int = 20, width: int = 960) -> Path:
	"""A looping GIF (or APNG for ``.png``) clip of an existing video file."""
	path = Path(path)
	path.parent.mkdir(parents=True, exist_ok=True)
	vf = f'fps={fps},scale={width}:-2:flags=neighbor'
	if path.suffix.lower() == '.gif':
		filters = f'{vf},split[a][b];[a]palettegen=max_colors=255:stats_mode=full[p];[b][p]paletteuse=dither=none'
		run(['-loglevel', 'error', '-y', '-ss', f'{start:.3f}', '-t', f'{duration:.3f}', '-i', str(video), '-filter_complex', filters, '-loop', '0', str(path)], check=True)
	else:
		run(['-loglevel', 'error', '-y', '-ss', f'{start:.3f}', '-t', f'{duration:.3f}', '-i', str(video), '-vf', vf, '-plays', '0', '-f', 'apng', str(path)], check=True)
	return path


def frames_to_gif(make_frames: Callable[[], Iterable[Image.Image]], size: tuple[int, int], fps: float, path: str | Path) -> Path:
	"""Encodes frames as a looping GIF with one shared 256-color palette and no dithering.

	It takes two passes (palette, then encode), so ``make_frames`` is called twice and must
	return a fresh iterator of same-size images each time.
	"""
	path = Path(path)
	path.parent.mkdir(parents=True, exist_ok=True)
	w, h = size
	source = ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', f'{fps:g}', '-i', '-']
	palette = path.with_name(path.stem + '.palette.png')
	passes = [
		[*source, '-vf', 'palettegen=max_colors=256:stats_mode=full', '-update', '1', str(palette)],
		[*source, '-i', str(palette), '-lavfi', '[0:v][1:v]paletteuse=dither=none:diff_mode=rectangle', '-loop', '0', str(path)],
	]
	try:
		for args in passes:
			proc = subprocess.Popen([ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y', *args], stdin=subprocess.PIPE)
			for frame in make_frames():
				proc.stdin.write(frame.convert('RGB').tobytes())
			proc.stdin.close()
			if proc.wait():
				raise RuntimeError(f'ffmpeg failed while writing {path}')
	finally:
		if palette.exists():
			palette.unlink()
	return path
