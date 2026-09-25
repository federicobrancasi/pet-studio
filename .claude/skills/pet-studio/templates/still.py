"""{{name}}: a VS Code pet image.

Made from the Pet Studio still template. Render with:

    python3 -m kit still render {{name}}                    # default preset
    python3 -m kit still render {{name}} --preset wallpaper
    python3 -m kit still render {{name}} --all

``render(width, height)`` is called with each preset's base size (see
``python3 -m kit still presets``). ``layout.poster`` adapts the composition to wide,
square and tall canvases; draw your own scene instead when you need something else.
"""

from __future__ import annotations

from PIL import Image

from kit import layout
from kit import pet as P

TITLE = '{{name}}'
DEFAULT_PRESET = 'x-post'
HEADLINE = 'Happy coding!'
CODE = ['pets.sayHello();', 'hello();']  # longest first; the first that fits is used
PETS = [
	P.PetPose('idleTracking', 0, 0, 0, gaze=(4, -4)),
	P.PetPose('idleTracking', 0, 0, 0, gaze=(4, -4), variant='insiders'),
]


def render(width: int, height: int) -> Image.Image:
	if width <= 512:  # sticker: transparent background, just the pets
		return layout.sticker(width, height, [P.PetPose('love', 5, 0, 0), P.PetPose('love', 5, 0, 0, variant='insiders')])
	return layout.poster(width, height, HEADLINE, CODE, PETS)
