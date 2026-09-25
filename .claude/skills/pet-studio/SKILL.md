---
name: pet-studio
description: Use when the user wants to make anything with the VS Code pet (the pixel mascot above the Visual Studio Code chat input) - videos and films for X or social media, still images (posters, wallpapers, X headers, phone screens, stickers), GIFs, or new moves and animations ("teach the pet to ..."). Covers the whole workflow in this repo - brief, choreography, the kit tools, the review package and the pet-director sign-off.
---

# Pet Studio

Everything is made with the Python kit in `kit/` (`python3 -m kit --help`), always from the real
pet sprites in `kit.pet`.

## Start

1. Setup: `python3 -m pip install -r requirements.txt`, then `python3 -m kit doctor` (it checks
   Python, Pillow, numpy and ffmpeg, and downloads the pinned pet sprites).
2. Read [guides/style.md](guides/style.md), then the guide for the job:

| The user wants | Guide | Start with | Deliver |
| --- | --- | --- | --- |
| a video or GIF | [video](guides/video.md) + [sound](guides/sound.md) | `python3 -m kit film new <name>` | `out/<name>/<name>.mp4` + review package |
| an image | [image](guides/image.md) | `python3 -m kit still new <name>` | PNGs in `out/<name>/` |
| a new move | [move](guides/move.md) | `python3 -m kit move new <name>` | `moves/<name>/` sprites + previews |

For combined requests ("teach it to juggle, then film it"), build the move first, then load it in
the film with `moves.use('<name>')`.

## Rules

- Say "the VS Code pet". Never invent a name.
- Whole pixels only: integer scales (`scale=2` in films), no smoothing, blur or rotation.
- Stable is blue, Insiders is green. When two pets are on screen, use one of each.
- Live eyes are 1x2 logical pixels; aim them with `gaze` and blink on quiet beats.
- Keep it friendly: no violence and no mockery. A bug gets bonked into a butterfly, not squashed.
- No Visual Studio Code logo, no product byline, and nothing that looks official (see Brand in
  the style guide).

## Workflow

1. **Brief.** Pin down the subject, feeling, length and format (16:9 for X by default). If the
   brief is open, choose a direction and list your assumptions at the end.
2. **Beats.** Put the timeline constants and a `CUES` list at the top of the file. Each beat is an
   action with a visible result, so it reads with the sound off (X autoplays muted).
3. **Key frame first.** Render the most important frame (`film frame <name> --at 12.3`) and look
   at it before building the rest.
4. **Build**, checking as you go with `film sheet <name>` (one frame every 0.5 s), single frames
   and `--draft` renders.
5. **Review.** `film review <name>` writes `out/<name>/review/`: contact sheets, cue frames, motion
   strips, a spectrogram, specs, loudness and determinism. Look at every image and fix what you
   see.
6. **Sign-off.** Follow [guides/sign-off.md](guides/sign-off.md) until the `pet-director` agent
   answers `VERDICT: SIGNED OFF`.
7. **Deliver.** Give the file paths, a short beat list, the verdict and the re-render command.
   Say what you could not check; for example, audio is measured, not heard.

## Kit map

| Module | For |
| --- | --- |
| `kit.pet` | real states (`poses --list`), `PetPose`, `draw_pose`, `frame_at`, live eyes |
| `kit.motion` | `Hop` (real crouch, stretch, air and squash poses), `FollowCamera`, `blinking`, `shake` |
| `kit.world` | `CodeCity` backdrop, `CodeLine` platforms, `chat_input`, `terminal_panel`, `window`, titles |
| `kit.fx` | dust, sparks, confetti, fireworks, hearts, zzz, stars, speech bubble, `!`, respawn, poof |
| `kit.art` | ladybug, butterfly, star, heart; new props as letter grids (`draw.grid_sprite`) |
| `kit.audio` | `Mixer`, chiptune instruments, sound effects, `groove`, `roll` |
| `kit.layout` | `poster` and `sticker` layouts that adapt to every image preset |
| `kit.moves` | `use(name)`: a taught move then works like a built-in state |

Reuse routines from the examples instead of rewriting them:
- `examples/coding-world/film.py` is a complete 30 s film.
- `lgtm-poster`, `ship-it` and `sticker-pack` are stills.

## Code rules

- `render(t)` must be a pure function of `t`: no state carried between frames, and no unseeded
  randomness. `film check` verifies this.
- Keep every timing in the timeline constants, and reuse them in `score()` so picture and sound
  stay in sync.
- Snap small things to the grid (`draw.snap(v, 4)`). Use text sizes 16 (titles), 8 (body) or 4
  (labels).
- Put film-specific helpers in the film's own folder. Add something to the kit only if it's
  generally useful, and give it a docstring.
- New work goes in `films/`, `stills/` and `moves/`. `out/` is disposable.
