---
name: pet-studio
description: Use when the user wants to make anything with the VS Code pet (the pixel mascot that sits above the VS Code chat input) - animated videos and films for X or social media, still images such as posters, wallpapers, X headers, phone screens and stickers, GIFs, or new moves and animations ("teach the pet to ..."). Covers the whole workflow in this repo - brief, choreography, the kit tools, the review package and the pet-director sign-off.
---

# VS Code pet studio

Everything is made with the Python kit in `kit/` (run `python3 -m kit --help`). Always use the
**real** pet sprites through `kit.pet`; never redraw the pet's body from memory.

## First

1. Set up, as in the README: `python3 -m pip install -r requirements.txt`, then
   `python3 -m kit doctor`, which checks Python, Pillow, numpy and ffmpeg and downloads the real
   pet sprites (pinned in `kit/sprites.json`).
2. Read [guides/style.md](guides/style.md): the pet's rules (pixel grid, colors, eyes, what
   never to do). Then load the guide for the job:

| The user wants | Read | Make | Deliver |
| --- | --- | --- | --- |
| a video, film, animation for X, a GIF of a scene | [guides/video.md](guides/video.md) and [guides/sound.md](guides/sound.md) | `films/<name>/film.py` (from `python3 -m kit film new <name>`) | `out/<name>/<name>.mp4` + review package |
| an image, poster, wallpaper, header, sticker | [guides/image.md](guides/image.md) | `stills/<name>/still.py` (from `python3 -m kit still new <name>`) | PNGs in `out/<name>/` |
| a new move, reaction or animation for the pet | [guides/move.md](guides/move.md) | `moves/<name>/move.txt` (from `python3 -m kit move new <name>`) | `moves/<name>/` sprites + previews |

Several at once is fine ("teach it to juggle, then put that in a video"): build the move first,
then use it in the film with `moves.use('<name>')`.

## Non-negotiable pet rules (details in guides/style.md)

- The pet is an **unnamed** character. Say "the VS Code pet"; never invent a name.
- Only whole pixels: pets draw at integer scales (`scale=2` in films, where one logical pixel is
  16 screen px). No smoothing, blur, rotation or non-integer resizing of pet art.
- Stable is blue, Insiders is green: same shape, different palette. Two pets on screen should be
  one of each.
- Live eyes are 1x2 logical pixels and look at what matters (`gaze`); blink by hand on quiet beats.
- Keep it friendly, cute and on-brand: no violence, no mocking people, products or companies.
  The pet fixes bugs by bonking them into butterflies, not by squashing them dead.
- This is an unofficial fan kit: no Visual Studio Code logo, no "Visual Studio Code" bylines on
  outputs, nothing that looks like an official announcement (guides/style.md, Brand).

## Workflow

1. **Brief.** Pull out the subject, the feeling, the length, the format (16:9 for X by default)
   and anything the user insists on. For an open brief, choose a direction yourself and go;
   write down your assumptions in the final message.
2. **Plan the beats.** Write the timeline first as constants at the top of the file (seconds),
   with a `CUES` list of story beats. A beat is an action and its consequence, readable without
   sound: X autoplays muted.
3. **Prove the hard part.** Render the single most important frame
   (`python3 -m kit film frame <name> --at 12.3`) and look at it before building the rest.
   Commands take a film or still by name (`my-film`, `coding-world`) or by path.
4. **Build**, re-checking with `python3 -m kit film sheet <name>` (a contact sheet every 0.5 s),
   frames around tricky moments, and `--draft` renders.
5. **Review.** `python3 -m kit film review <name>` renders the MP4 and writes
   `out/<name>/review/` (contact sheets, cue frames, motion strips, audio spectrogram, specs,
   loudness, determinism). Look at every image it produced. Fix what you see.
6. **Sign-off.** Ask the `pet-director` agent (`.claude/agents/pet-director.md`) for a verdict,
   following [guides/sign-off.md](guides/sign-off.md). Fix every must-fix and review again until
   it says `VERDICT: SIGNED OFF`.
7. **Deliver.** Give the user the file path(s), what happens (a short beat list), the verdict,
   and how to re-render. Say plainly what you looked at and what you could not check (for
   example, you cannot listen to the audio; you read the spectrogram and loudness instead).

## Kit map

| Module | Use it for |
| --- | --- |
| `kit.pet` | real states (`python3 -m kit poses --list`), `PetPose`, `draw_pose`, `frame_at`, `durations`, live eyes |
| `kit.motion` | `Hop` arcs with real crouch/stretch/air/squash poses, `FollowCamera`, `blinking`, `shake` |
| `kit.world` | `CodeCity` backdrop, `CodeLine` platforms with `code()` highlighting, `chat_input`, `terminal_panel`, `window`, titles |
| `kit.fx` | dust, sparks, confetti, fireworks, hearts, zzz, stars, speech bubble, `!`, respawn, poof |
| `kit.art` | ladybug, butterfly, star, heart, `!`; add props as letter grids with `draw.grid_sprite` |
| `kit.audio` | `Mixer`, chiptune instruments, SFX (`boing`, `land`, `click`, `coin`, `bonk`, `twinkle`...), `groove`, `roll` |
| `kit.layout` | `poster` and `sticker` compositions that adapt to every still preset |
| `kit.moves` | `use(name)` makes a taught move usable like a built-in state |

`examples/coding-world/film.py` is a complete, signed-off 30 s film: open it before inventing a
routine that already exists (hops, camera, typing, a bug fix, a code bridge, a terminal, a
respawning friend, an end card, a full score). `examples/lgtm-poster/still.py` shows a still
that uses a custom move.

## Rules for code you write

- `render(t)` must be a pure function of `t`: no state kept between frames and no unseeded
  randomness (`random.Random(seed)` built once at import is fine). `python3 -m kit film check`
  proves it.
- Keep every timing in the timeline constants, and reuse them in `score()` so picture and sound
  stay in sync.
- Snap positions of small things to the pixel grid (`draw.snap(v, 4)`), and draw text with
  `kit.font` at px 16 (titles), 8 (code, body) or 4 (small UI labels only).
- Don't modify the kit for one film. Put film-only helpers in the film's folder. If something
  is generally useful, add it to the kit with a docstring.
- `out/` is disposable and ignored by git. Films, stills and moves live in `films/`, `stills/`
  and `moves/`.
