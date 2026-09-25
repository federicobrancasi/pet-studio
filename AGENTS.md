# Pet Studio for Visual Studio Code: agent guide

This repo makes videos, images and new moves with the VS Code pet. It is a personal fan project,
not an official Microsoft one: outputs must not carry the Visual Studio Code logo or byline. Use the **`pet-studio`
skill** in `.claude/skills/pet-studio/SKILL.md` for any such request: it has the pet's rules,
the workflow and links to the detailed guides. Reviews go to the **`pet-director`** agent in
`.claude/agents/pet-director.md`.

## Setup

```sh
python3 -m pip install -r requirements.txt
python3 -m kit doctor
```

## Map

| Path | Holds |
| --- | --- |
| `kit/` | the Python tools (`python3 -m kit --help`) |
| `.claude/skills/pet-studio/` | the skill, guides and file templates |
| `.claude/agents/pet-director.md` | the reviewer that signs work off |
| `examples/coding-world/film.py` | the complete signed-off 30 s film; reuse its routines |
| `examples/lgtm-poster/still.py` | a still that uses a custom move |
| `moves/` | taught moves: `move.txt` plus generated sprites and previews |
| `films/`, `stills/` | new work (created by `kit film new` and `kit still new`) |
| `out/` | disposable renders, ignored by git |
| `tests/` | smoke tests: `python3 -m unittest discover -s tests -v` |

## Invariants

- The pet always comes from the real sprites via `kit.pet`; never redraw its body from memory.
- The pet has no name. Never invent one.
- `render(t)` is a pure function of time with seeded randomness only; `python3 -m kit film check`
  verifies it.
- Whole-pixel art only: integer scales, nearest-neighbor, no smoothing.
- Look at every sheet and frame you render before saying something is done, and say what you
  could not check (you cannot hear the audio: read the spectrogram and loudness instead).
