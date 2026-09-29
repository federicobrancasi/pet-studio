# Teaching the pet a new move

A move is a text file of frames, one letter per logical pixel. The kit turns it into sprite
sheets for both colorways, in the same format as the pet's own, plus a GIF and a preview. Moves
work in films and stills too.

## Steps

1. **Design it.** Work out the trigger, the peak pose and the result, and whether it loops or
   plays once. Aim for 8-13 frames lasting 1.5-3 s. Study the closest ready-made move first
   (see [Ready-made moves](#ready-made-moves)).
2. **Start from the real pet.** Never draw the body from memory:

   ```sh
   python3 -m kit move new juggle --frames 6 --height 16   # every frame starts as the idle pose
   python3 -m kit move grid jump:3                         # print any real pose as text
   ```

   `--height 16` adds headroom for props above the pet, and `--width 16` adds room on the right.
3. **Edit `moves/<name>/move.txt`.** Change only what the move needs, and paste in real poses where
   they fit.
4. **Build and look.** Run `python3 -m kit move build juggle`, then read every warning and look at
   `out/moves/juggle/strip.png` and `moves/juggle/preview.gif`. Iterate, show the user the strip,
   and then run `python3 -m kit move gallery`.

Frames are numbered from 1 on the command line and in move files (`jump:2` is the second frame).
In Python they're indexed from 0.

| Recipe | Frames |
| --- | --- |
| Nod yes | `idle:1` 160 ms, `jump:2` 110 ms, `idle:1` 160 ms, `jump:2` 110 ms, `idle:1` 300 ms |
| Bounce | `jump:2` crouch, `jump:3` stretch, `jump:4` air, `jump:5` squash, `jump:6` recover |
| Blink | `idle:1`, then the same grid with the top `E` of each eye set to `C`, for 80 ms |
| Wave | move one antenna outward and up over two frames (`moves/wave`) |
| Hearts, shades, sweat | start from `love:6`, `cool:9` or `worry:1`, keeping their colors |
| Prop overhead | `--height 16`, with the prop in the top rows in its own letters (`moves/lgtm`) |

## Format

```text
name: juggle
about: Juggles curly braces with its antennae.
loop: yes            # yes = loops; no = plays once and holds the last frame
still: 3             # optional: the frame used as the static image
colors: Y=#ffd700 W=#ffffff
fixed: Y             # optional: prop letters that must not mirror (text, checks, notes)

frame 120            # duration in ms (the pet's own frames run 40-600 ms)
..A......A..
...A....A...
....A..A....
.....BA.....
....BACC....
...BACCCC...
..BACCCCCC..
.BACCCCCCCC.
BAACCECCECCC
BAACCECCECCC
BAACCCCCCCCC
.BAAACCCCCC.
```

- **Letters:**
  - `.` is transparent.
  - `C`, `A` and `B` are the body's light, mid and dark colors; they become blue or green
    automatically.
  - `E` is an eye.
  - Any other letter is a prop and must be declared in `colors:`.
- **Frames:** every frame has the same size, at least 12 x 12.
- **Comments:** start a line with `#`, or add ` #` after a value.
- **Names:** built-in state names such as `jump` are taken.

## Good moves

Draw like the pet's own art:

- **Shade props** with 3 or 4 tones of one color, lit from the upper right: the lightest on the
  top and right, the base in the middle, a shadow at the bottom and left, and the darkest as
  the outline, so the prop reads on light and dark backgrounds.
- **Size props** like the head, 6 to 12 logical pixels, with clean silhouettes: no stray
  pixels and no dithering.
- **Hats replace the antennae:** clear the rows above the head and sit the brim on the head
  top. Held things start at an antenna tip. Floating things keep a row of air above the
  antennae and stay off the eyes. Things beside the pet start at column 13 to 15.
- **One short word at most,** in a bold, shaded font (see `yes` and `angry`). Put its letters
  in `fixed:` so they stay readable when the pet faces left by mirroring.

Animate like the pet's own reactions:

- Start and end on the idle pose so the move doesn't pop in or out.
- Anticipate (a crouch, 80-150 ms), act, hold the key pose 400-900 ms so people can read it,
  then settle. Keep fast frames at 60-120 ms.
- Props and words pop in over 2 or 3 frames (small, big, settled) and leave the same way.
  Particles fly on arcs and fade.
- The body reacts: the eyes follow the action, it crouches to take a hit, it hops for joy.
- Keep the body in the bottom-left 12 x 12 box, touching the bottom row except in the air.
  Change as few body pixels as possible.

## Ready-made moves

`moves/` has moves designed for the VS Code pet. Use them in films and stills, or study the
closest one before drawing your own:

| Move | Shows how to |
| --- | --- |
| `yes` | pop a word in above the head: small, big, settled |
| `idea` | hang a prop above the head and light it up |
| `build` | drop a prop's parts in one by one beside the pet, then present it |
| `ship-it` | launch a prop from beside the pet and follow it with the eyes |
| `cowboy` | wear a hat instead of the antennae, and twirl a lasso with one |
| `rubber-duck` | squash a prop and react with a hop |
| `magic` | hold a wand at an antenna tip and burst sparkles on arcs |
| `trophy` | sweep a shine across a shaded prop |
| `debug` | swing a held hammer and land a cartoon impact |
| `coffee` | rise steam and close the eyes in bliss |
| `zapped` | weather, a flash that recolors the whole body, and x eyes |
| `angry` | shake, turn red and flash a shaded word |
| `wave`, `lgtm` | wave an antenna; a check mark over a hop |

`python3 -m kit move montage all` plays them all in one animated grid.

## Using and sharing

```python
moves.use('juggle')
P.draw_pose(img, P.PetPose('juggle', P.frame_at('juggle', ms), x, y), cx, cy)
```

`moves/<name>/` holds:
- `move.txt`: the whole move, which you can share as it is
- the previews
- `vscode/`: the sprite sheets, the static images, `timing.ts` and `move.json`

Visual Studio Code only plays its built-in animations, so a new move won't appear in the editor.
The `vscode/` files let you try it in a local build.
