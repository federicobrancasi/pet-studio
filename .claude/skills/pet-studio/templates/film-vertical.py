"""{{name}}: a short vertical (9:16) VS Code pet film for Reels, TikTok, Shorts and X.

Made from the Pet Studio vertical film template. Preview and export with:

    python3 -m kit film sheet {{name}}          # quick contact sheet
    python3 -m kit film frame {{name}} --at 5   # one frame
    python3 -m kit film review {{name}}         # MP4 + review package, with safe-zones.png

Reels, TikTok and Shorts draw buttons, captions and profile bars over vertical video, so
keep text, faces and the action inside ``SAFE`` (x 60-960, y 260-1600). Every frame is a
pure function of time: ``render(t)`` must not remember anything between calls, and any
randomness must be seeded. Keep all timings in the timeline block so the picture and the
score stay in sync.
"""

from __future__ import annotations

from PIL import Image

from kit import fx, layout, motion, world
from kit import audio as A
from kit import pet as P
from kit.draw import seg
from kit.motion import Hop
from kit.pet import PetPose

TITLE = '{{name}}'
W, H = SIZE = (1080, 1920)  # 9:16 vertical
FPS = 60
DURATION = 10.0
SAFE = layout.safe_area(SIZE)  # (60, 260, 960, 1600): visible on every app
SAFE_X = (SAFE[0] + SAFE[2]) // 2  # the safe area's center, a little left of the frame's
SAFE_W = SAFE[2] - SAFE[0]

# --------------------------------------------------------------------------------------------
# Timeline (seconds): change the story here

CAPTION = 'watch it climb!'  # the hook: vertical videos autoplay muted, so say it in text
PROMPT = 'climb the code'
T_KEYS0, T_KEY_STEP, T_SEND = 0.9, 0.07, 2.0
T_HOPS = (2.8, 3.8, 4.8)  # three hops up the stairs of code
HOP_TIME = 0.5
# Each line types itself in just before the pet needs it, so only the next step shows.
T_LINES = (T_SEND + 0.15, T_HOPS[0] + HOP_TIME + 0.05, T_HOPS[1] + HOP_TIME + 0.05)
T_PRESS = 5.6             # button-press celebration starts on the top line
T_SUCCESS = T_PRESS + 0.8  # the press lands (frame 3 of the press sheet)
T_TITLE = 6.8
END_TITLE = 'Level up!'

CUES = [  # story beats: reviews show a full frame and a motion strip for each
	(0.0, 'caption and pet on the chat input'),
	(T_KEYS0, 'types the prompt'),
	(T_LINES[0], 'first code line appears'),
	(T_HOPS[0], 'climbs the code'),
	(T_SUCCESS, 'celebration'),
	(T_TITLE, 'end card'),
]

# --------------------------------------------------------------------------------------------
# The world: screen pixels while the camera is at the start; y shrinks as the pet climbs

INPUT_X0, INPUT_X1, INPUT_TOP = SAFE[0] + 30, SAFE[2] - 30, 1330
STEP = 420  # a step higher than the pet (192 px) plus its hop, so it never flies through a line
LINES = [
	world.CodeLine(key, number, x0, INPUT_TOP - STEP * (i + 1), world.code(text, T_LINES[i], 0.05), appear=T_LINES[i])
	for i, (key, number, x0, text) in enumerate([('one', 3, 480, 'up();'), ('two', 7, 80, 'climb();'), ('top', 12, 440, 'win();')])
]
START_X = 300
SPOTS = [(START_X, INPUT_TOP), (700, LINES[0].top), (330, LINES[1].top), (690, LINES[2].top)]  # right, left, right
HOPS = [Hop(t0, t0 + HOP_TIME, *SPOTS[i], *SPOTS[i + 1], 260) for i, t0 in enumerate(T_HOPS)]
LANDINGS = motion.landings(HOPS)
BLINKS = [0.6, 2.35, 5.05, 8.6]
CITY = world.CodeCity(SIZE, world_width=W, seed=1)
TOP = SPOTS[-1]
CONFETTI = [(T_SUCCESS, fx.confetti_burst(1, TOP[0], TOP[1] - 60, 60, 0.8))]


def facing(t: float) -> str:
	"""The pet faces the way it is about to hop: right, left, then right again."""
	direction = 'right'
	for h in HOPS:
		if t >= h.t0 - h.crouch:
			direction = 'right' if h.x1 >= h.x0 else 'left'
	return direction


def hero_pose(t: float) -> PetPose:
	hop = motion.hop_pose(HOPS, t, facing=facing(t))
	if hop is not None:
		return hop
	x, y = motion.ground_at(HOPS, t, SPOTS[0])
	blink = motion.blinking(t, BLINKS)
	if T_KEYS0 <= t < T_SEND:
		return PetPose('typing', P.frame_at('typing', (t - T_KEYS0) * 1000), x, y, gaze=(4, 0), blink=blink)
	if T_PRESS <= t < T_PRESS + P.total_ms('press') / 1000:
		return PetPose('press', P.frame_at('press', (t - T_PRESS) * 1000, loop=False), x, y, facing(t), gaze=(4, 0), blink=blink)
	gaze = (4, -4) if T_SEND <= t < T_HOPS[-1] else (0, -4) if t >= T_TITLE else (4, 0)  # look up at the next step, then at the title
	return PetPose('idleTracking', P.frame_at('idle', t * 1000), x, y, facing(t), gaze=gaze, blink=blink)


def camera_target(t: float) -> tuple[float, float]:
	# Keep the ground the pet stands on, or is about to land on, where the chat input started.
	ground = motion.ground_at(HOPS, t, SPOTS[0])[1]
	return 0.0, motion.heading_y(HOPS, t, ground) - INPUT_TOP


CAMERA = motion.FollowCamera(camera_target, DURATION, FPS, omega=(5.0, 4.0))


def render(t: float) -> Image.Image:
	img = Image.new('RGBA', SIZE)
	cx, cy = (int(round(v)) for v in CAMERA.at(t))
	CITY.draw(img, t, cx, cy)
	typing = T_KEYS0 <= t < T_SEND
	world.chat_input(img, t, INPUT_X0, INPUT_X1, INPUT_TOP, cx, cy,
		text=world.typed(PROMPT, t, T_KEYS0, T_KEY_STEP, T_SEND),
		placeholder='Ask anything' if t < T_KEYS0 else None,
		focused=T_KEYS0 - 0.05 <= t < T_SEND + 0.25, typing=typing, send_flash=T_SEND <= t < T_SEND + 0.18)
	for line in LINES:
		line.draw(img, t, cx, cy, active=motion.ground_at(HOPS, t, SPOTS[0])[1] == line.top, dip=lambda x, line=line: world.landing_dip(t, LANDINGS, line.top, x))
	P.draw_pose(img, hero_pose(t), cx, cy)
	fx.dust(img, t, LANDINGS, cx, cy)
	fx.confetti(img, t, CONFETTI, cx, cy)
	# Text stays inside the safe area: the hook (whole from the first frame, the thumbnail) until
	# the end card, then the title.
	if t < T_TITLE:
		world.title_block(img, CAPTION, SAFE[1] + 40, center_x=SAFE_X, max_width=SAFE_W, max_height=360)
	world.title_block(img, END_TITLE, SAFE[1] + 40, center_x=SAFE_X, max_width=SAFE_W, max_height=360, t=t, t0=T_TITLE)
	return img


# --------------------------------------------------------------------------------------------
# Score: 120 BPM, so one beat = 0.5 s and one bar = 2 s. Put hits on the story beats.

THEME = [(0, .5, 'C5'), (.5, .5, 'E5'), (1, .75, 'G5'), (1.75, .25, 'E5'), (2, .5, 'D5'), (2.5, .5, 'G5'), (3, .5, 'B4'), (3.5, .5, 'D5')]


def score(mix: A.Mixer) -> None:
	n = A.n
	mix.melody([(0, .5, 'E5'), (.5, .5, 'G5'), (1, .5, 'C6'), (1.5, .5, 'G5')], 0, 'bell', 0.09)
	mix.melody(THEME, 5)            # beat 5 = 2.5 s, as the code lines appear
	A.groove(mix, 5, 11)
	mix.melody([(11, .25, 'C6'), (11.25, .25, 'C6'), (11.5, .25, 'C6'), (11.75, 1.25, 'E6'), (13, 1, 'G6')], 0, 'lead', 0.14)
	A.groove(mix, 11, 16, soft=0.8)
	for i, nm in enumerate(['C4', 'E4', 'G4', 'C5']):  # final chord on the end card
		mix.put(A.lead(n(nm), 1.6, 0.125), T_TITLE + 0.01 * i, 0.05, pan=(i - 1.5) * 0.3)
	for i, ch in enumerate(PROMPT):  # sound effects follow the same timeline
		if ch != ' ':
			mix.put(A.click(1.0 + 0.06 * (i % 4)), T_KEYS0 + i * T_KEY_STEP, 0.18, pan=-0.3)
	mix.put(A.whoosh(0.3), T_SEND, 0.25)
	for k, t_line in enumerate(T_LINES):  # a rising blip as each step appears
		mix.put(A.twinkle([['C6', 'E6'], ['E6', 'G6'], ['G6', 'C7']][k]), t_line, 0.06)
	for h in HOPS:
		mix.put(A.boing(), h.t0, 0.16)
		mix.put(A.land(), h.t1, 0.30)
	mix.put(A.click(0.5, 1.0), T_SUCCESS, 0.5)
	mix.put(A.twinkle(['C7', 'E7', 'G7', 'C8']), T_SUCCESS + 0.1, 0.12)
	for k in range(8):
		mix.put(A.noise_burst(0.02, 3000, 200), T_SUCCESS + k * 0.035, 0.15, pan=float(A.rng().uniform(-0.6, 0.6)))
