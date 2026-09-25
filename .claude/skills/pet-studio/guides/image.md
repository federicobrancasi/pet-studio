# Making an image

A still is one file, `stills/<name>/still.py`, with a `render(width, height)` function.

```sh
python3 -m kit still new space-wallpaper
python3 -m kit still render space-wallpaper --all
```

| Preset | Output | Rendered as |
| --- | --- | --- |
| `x-post` | 1920 x 1080 | native |
| `square` | 1080 x 1080 | native |
| `x-header` | 1500 x 500 | native (wide layout) |
| `wallpaper` | 3840 x 2160 | 1920 x 1080, scaled up 2x |
| `phone` | 1170 x 2532 | 585 x 1266, scaled up 2x |
| `sticker` | 512 x 512 | native, transparent |

Scaling is always by a whole number, so pixels stay crisp. `render` is called with the base size.

## The easy way

```python
def render(width, height):
    if width <= 512:
        return layout.sticker(width, height, [P.PetPose('love', 5, 0, 0)])
    return layout.poster(width, height, 'Ship it!', ['git push origin main', 'git push'],
                         [P.PetPose('love', 5, 0, 0), P.PetPose('love', 5, 0, 0, variant='insiders')])
```

`poster` draws the backdrop, fits and wraps the headline, and picks the first code line that
fits. It also stands the pets on that line, with the right-hand pet facing left. Wide canvases
put the headline in an editor window. Headlines under 20 characters read best on phones.

## Your own composition

To build a scene yourself, use the same pieces as films (`world`, `fx`, `art`,
`pet.draw_pose`) with `cx = cy = 0`. For an example, see `examples/sticker-pack`.

- Pick a meaningful frame; `python3 -m kit poses` shows them all. Good ones are the last frame
  of `press`, frame 6 of `love`, and `cool`.
- Keep the pets big and clear of text, with margins of at least 64 px.
- Give it one focal point and keep the backdrop quiet.
- Stickers get a transparent background and no text.

Check every preset you deliver, especially `x-header` and `phone`.
