"""Choreography helpers: hops with real squash and stretch, blinks, and a follow camera."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

from .draw import clamp, seg
from .pet import AIRBORNE_OFFSET, PetPose

STRETCH = 0.07  # seconds in the take-off stretch pose
SQUASH = 0.10   # seconds in the landing squash pose
RECOVER = 0.08  # seconds in the recover pose after the squash


@dataclass
class Hop:
	"""A parabolic hop from ``(x0, y0)`` to ``(x1, y1)`` between ``t0`` and ``t1`` seconds.

	``y`` is the ground under the pet's feet (world px, growing downward). ``h`` is the
	arc height. ``crouch`` is the anticipation before take-off; ``recover=False`` skips
	the recover pose (useful when the next action starts right away).
	"""
	t0: float
	t1: float
	x0: float
	y0: float
	x1: float
	y1: float
	h: float = 170.0
	star: bool = False
	crouch: float = 0.10
	recover: bool = True

	def pos(self, t: float) -> tuple[float, float]:
		u = seg(t, self.t0, self.t1)
		x = self.x0 + (self.x1 - self.x0) * u
		y = self.y0 + (self.y1 - self.y0) * u - 4 * self.h * u * (1 - u)
		return x, y


def hop_pose(hops: Sequence[Hop], t: float, variant: str = 'stable', facing: str = 'right') -> PetPose | None:
	"""The real jump pose for time ``t`` (crouch, stretch, air, squash, recover), or None."""
	# Latest hop first: a following hop's anticipation overrides the previous landing recovery.
	for h in reversed(hops):
		if h.t0 - h.crouch <= t < h.t0:
			return PetPose('jump', 1, h.x0, h.y0, facing, variant=variant)
		if h.t0 <= t < h.t1:
			x, y = h.pos(t)
			if t < h.t0 + STRETCH:
				return PetPose('jump', 2, x, y, facing, variant=variant)
			return PetPose('jump', 3, x, y, facing, variant=variant, air_offset=AIRBORNE_OFFSET)
		if h.t1 <= t < h.t1 + SQUASH:
			return PetPose('jump', 4, h.x1, h.y1, facing, variant=variant)
		if h.recover and h.t1 + SQUASH <= t < h.t1 + SQUASH + RECOVER:
			return PetPose('jump', 5, h.x1, h.y1, facing, variant=variant)
	return None


def ground_at(hops: Sequence[Hop], t: float, start: tuple[float, float]) -> tuple[float, float]:
	"""Where the pet stands at ``t``: the end of the last finished hop, else ``start``."""
	x, y = start
	for h in hops:
		if t >= h.t1:
			x, y = h.x1, h.y1
	return x, y


def heading_y(hops: Sequence[Hop], t: float, default: float, lead: float = 0.2) -> float:
	"""The ground the pet is on or about to land on (lets a camera move early)."""
	y = default
	for h in hops:
		if h.t0 - lead <= t < h.t1:
			y = h.y1
	return y


def landings(hops: Sequence[Hop]) -> list[tuple[float, float, float]]:
	return [(h.t1, h.x1, h.y1) for h in hops]


def blinking(t: float, blinks: Sequence[float], length: float = 0.13) -> bool:
	"""True during a blink. List blink start times by hand so they land on quiet moments."""
	return any(0 <= t - b < length for b in blinks)


class FollowCamera:
	"""A critically damped camera that follows ``target(t) -> (x, y)`` (top-left corner).

	It is simulated once for every frame, so ``at(t)`` is exact and history-free: rendering
	frame 900 alone gives the same picture as playing up to it.
	"""

	def __init__(self, target: Callable[[float], tuple[float, float]], duration: float, fps: int, omega: tuple[float, float] = (5.0, 3.0)):
		self.fps = fps
		self.frames = int(fps * duration)
		dt = 1.0 / fps
		cx, cy = target(0.0)
		vx = vy = 0.0
		wx, wy = omega
		self.path: list[tuple[float, float]] = []
		for i in range(self.frames):
			tx, ty = target(i / fps)
			ax = wx * wx * (tx - cx) - 2 * wx * vx
			ay = wy * wy * (ty - cy) - 2 * wy * vy
			vx += ax * dt
			vy += ay * dt
			cx += vx * dt
			cy += vy * dt
			self.path.append((cx, cy))

	def at(self, t: float) -> tuple[float, float]:
		i = int(clamp(round(t * self.fps), 0, self.frames - 1))
		return self.path[i]


def shake(t: float, t0: float, length: float = 0.3, amplitude: tuple[float, float] = (14.0, 10.0), decay: float = 14.0) -> tuple[float, float]:
	"""A short decaying screen shake starting at ``t0`` (add it to the camera position)."""
	if not (t0 <= t < t0 + length):
		return 0.0, 0.0
	k = math.exp(-(t - t0) * decay)
	return amplitude[0] * k * math.sin(t * 90), amplitude[1] * k * math.cos(t * 77)
