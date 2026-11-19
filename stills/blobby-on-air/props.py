"""Pixel props for the Blobby On Air avatars and emoji, as letter grids on the pet's grid.

Shaded like the pet's own art: lit from the upper right, a dark outline, 3-4 tones per prop.
The side-view camera is the same one taught to the pet in ``moves/on-air/move.txt``.
"""

PALETTE = {
	'K': '#1f2328',  # outline
	'D': '#3d444d',  # shadow
	'G': '#6e7781',  # body
	'H': '#afb8c1',  # highlight
	'S': '#d0d7de',  # reel
	'W': '#ffffff',
	'R': '#f14c4c',  # recording red
	'h': '#ffb4ab',  # red highlight
	'r': '#6e2420',  # red, off
	'q': '#8c3a33',  # red highlight, off
	'L': '#75beff',  # lens glint
	'N': '#0d1117',  # lens glass
	'Y': '#ffc205',  # gold
	'y': '#ffe994',  # light gold
	'P': '#0077b8',  # play triangle
}

# --- The second, simpler set: clean silhouettes, no thin lines, nothing that turns to noise at 48 px

# Movie camera: two round reels, one rounded body, a lens hood and a red dot.
CAMERA_CLEAN = [
	'.KK..KK....',
	'KSSKKSSK...',
	'KSSKKSSK...',
	'.KKKKKKK...',
	'KGGGGGGHK.K',
	'KGRGGGGHKKL',
	'KGGGGGGHKKL',
	'KDDGGGGHK.K',
	'.KKKKKKK...',
]

# Clapperboard like the emoji: a white arm with diagonal black stripes, a gap, a plain dark slate.
# The gap row is left empty so the light outline draws the line between arm and slate.
CLAPBOARD = [
	'KKWWKKW',
	'WKKWWKK',
	'WWKKWWK',
	'.......',
	'DDDDDDD',
	'DDDDDDD',
	'DDDDDDD',
]
CLAPBOARD_BIG = [
	'KKWWKKWWKKWWKK',
	'WKKWWKKWWKKWWK',
	'WWKKWWKKWWKKWW',
	'..............',
	'DDDDDDDDDDDDDD',
	'DDDDDDDDDDDDDD',
	'DDDDDDDDDDDDDD',
	'DDDDDDDDDDDDDD',
]

REC_DOT_BIG = [
	'.RRR.',
	'RRRhR',
	'RRRRR',
	'RRRRR',
	'.RRR.',
]

PLAY_BUBBLE = [  # a speech bubble with a play triangle, its tail toward the pet's head
	'.KKKKKK.',
	'KWWWWWWK',
	'KWWPWWWK',
	'KWWPPWWK',
	'KWWPPPWK',
	'KWWPPWWK',
	'KWWPWWWK',
	'.KKKKKK.',
	'.KK.....',
]

# Movie camera seen from the side, lens to the right: two reels on top, record light on.
CAMERA = [
	'.KK.KK...',
	'KSHKSHK..',
	'KKKKKKK.K',
	'KDGGGHKKL',
	'KDRGGHKNL',
	'KDGGGHKKL',
	'KKKKKKK.K',
]
# The reels half a turn on (alternate with CAMERA to spin them).
CAMERA_SPIN = [row.replace('SH', 'HS') for row in CAMERA]

# The same camera seen from the front, lens toward the viewer.
CAMERA_FRONT = [
	'.KK..KK.',
	'KSHKKSHK',
	'KKKKKKKK',
	'KGGKKGRK',
	'KGKLNKHK',
	'KGKNNKHK',
	'KDGKKGHK',
	'KKKKKKKK',
]

TRIPOD = [  # hangs under CAMERA's body; column 4 is the post
	'....G....',
	'....G....',
	'...GGG...',
	'..G.G.G..',
	'.G..G..G.',
	'G...G...G',
]

CLAPPER_OPEN = [  # the striped stick hinged at the left, raised
	'.....KWK',
	'...KWWK.',
	'.KWK....',
	'KKKKKKKK',
	'KWWKKWWK',
	'KDHHHHDK',
	'KKKKKKKK',
]
CLAPPER_HALF = [  # on its way down
	'........',
	'....KWWK',
	'KWWK....',
	'KKKKKKKK',
	'KWWKKWWK',
	'KDHHHHDK',
	'KKKKKKKK',
]
CLAPPER_SHUT = [
	'........',
	'........',
	'WWKKWWKK',
	'KKKKKKKK',
	'KWWKKWWK',
	'KDHHHHDK',
	'KKKKKKKK',
]

CLAPPER_BIG = [  # the same clapperboard, big enough to sit on: shut, stripes running diagonally
	'WWKKWWKKWWKKWW',
	'KWWKKWWKKWWKKW',
	'KKKKKKKKKKKKKK',
	'KDDDDDDDDDDDGK',
	'KDHHHHHDHHHHGK',
	'KDDDDDDDDDDDGK',
	'KDHHHDDHHHHDGK',
	'KDDDDDDDDDDDGK',
	'KKKKKKKKKKKKKK',
]

POPCORN = [
	'.yW.y.',
	'yWyWyW',
	'WyWyWy',
	'KRWRWK',
	'KRWRWK',
	'.RWRW.',
	'.KKKK.',
]

LAMP_ON = [
	'.KKKK.',
	'KRRRhK',
	'KRRRRK',
	'.KKKK.',
]
LAMP_OFF = [row.replace('R', 'r').replace('h', 'q') for row in LAMP_ON]

REC_DOT = [
	'.RR.',
	'RRhR',
	'RRRR',
	'.RR.',
]

SPARKLE = [
	'.Y.',
	'YyY',
	'.Y.',
]
