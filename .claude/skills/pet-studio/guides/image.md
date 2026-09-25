# Making an image

A still is one Python file, `stills/<name>/still.py`, with `render(width, height)`. Start from
the template:

```sh
python3 -m kit still new space-wallpaper
python3 -m kit still render space-wallpaper --all      # by name or by path
python3 -m kit still presets
```

## Presets

| Preset | Output | Rendered as |
| --- | --- | --- |
| `x-post` | 1920 x 1080 | native |
| `square` | 1080 x 1080 | native |
| `x-header` | 1500 x 500 | native (wide layout) |
| `wallpaper` | 3840 x 2160 | 1920 x 1080 scaled up 2x |
| `phone` | 1170 x 2532 | 585 x 1266 scaled up 2x |
| `sticker` | 512 x 512 | native, transparent background |

Scaling is always by a whole number with nearest-neighbor sampling, so every pixel stays crisp.
`render` receives the base size, so lay things out relative to `width` and `height`.

## The easy way: `layout.poster`

```python
from kit import layout, pet as P

def render(width, height):
    if width <= 512:
        return layout.sticker(width, height, [P.PetPose('love', 5, 0, 0)])
    return layout.poster(width, height, 'Ship it!', ['git push origin main', 'git push'],
                         [P.PetPose('press', 5, 0, 0), P.PetPose('idleTracking', 0, 0, 0, gaze=(4, -4), variant='insiders')])
```

`poster` draws the Coding World backdrop, fits the headline at the largest crisp size (long
headlines and subtitles wrap), picks the first code line that fits, and stands the pets on it
(the right-hand pet faces left). Very wide canvases get an editor-window headline on the left
and the pets on the right. Short headlines read best on phones: aim for under 20 characters.

## Your own composition

Draw anything with the same pieces as films (`world`, `fx`, `art`, `pet.draw_pose`) using
`cx = cy = 0`. Good pet images:

- Give the pets something to do or feel: pick a meaningful frame (`python3 -m kit poses` shows
  every frame of every state). The last frame of `press`, frame 5 of `love` and the `cool`
  sunglasses are crowd-pleasers.
- Keep the pets big and clear of text; leave margins of at least 64 px for social crops.
- One focal point. The backdrop stays dark and quiet so the pets and headline read.
- Stickers: transparent background, just the pet (and its prop), no text.

Look at every preset you render, especially `x-header` (very wide) and `phone` (very tall).
