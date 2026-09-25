# Sound

Films have an original chiptune score and sound effects, written as code in `score(mix)`.
Never use copyrighted music or samples.

## Levels and balance

| Part | Gain in `mix.put` / `mix.melody` |
| --- | --- |
| lead melody (`lead`) | 0.10-0.16 |
| bass (`bass`, already an octave up for phone speakers) | 0.24-0.26 |
| plucks, arpeggios | 0.03-0.09 |
| bells, music box | 0.05-0.10 |
| drums (`groove`, `roll`) | built in; use `soft=0.6-1.0` |
| sound effects | 0.08-0.30; the big hit of the film up to 0.45 |

Mastering soft-clips and normalizes the whole mix to about -15 LUFS with a true peak near -2 dBTP
after AAC encoding, so overall gain in `score()` does not matter: balance does. Keep the melody on
top of the bass. To change the master, set `MASTER` at the top of the film, for example
`MASTER = {'ceiling': 0.7}` (quieter, lower peak), `{'drive': 1.2}` (less squashed) or
`{'fade_out': 1.0}` (a longer fade at the end).

## Write music for the picture

- 120 BPM: one beat = 0.5 s, one bar (4 beats) = 2 s. `mix.beat(b)` converts beats to seconds.
  Put scene changes on bar lines and big actions on beats.
- Give each section its own texture: a music-box lullaby while the pet sleeps, a bouncy theme
  on hops, a minor-key tiptoe line for tension, a fanfare for success, a sweet slow melody for
  hearts, and a final major chord on the end card.
- `mix.melody([(beat, length_beats, 'C5'), ...], start_beat, 'lead' | 'bell' | 'pluck', gain)`.
  Chords and progressions: see `music()` in `examples/coding-world/film.py`.
- Silence and space are allowed. Don't fill every beat.

## Sound effects follow the timeline

Read the same timing constants the picture uses, so they can never drift:

```python
for h in HOPS:
    mix.put(A.boing(), h.t0, 0.16)      # take-off
    mix.put(A.land(), h.t1, 0.30)       # landing
for i, ch in enumerate(PROMPT):
    if ch != ' ':
        mix.put(A.click(1.0 + 0.06 * (i % 4)), T_KEYS0 + i * T_KEY_STEP, 0.18, pan=-0.3)
```

Available: `click`, `boing`, `land`, `coin`, `blip(note)`, `sweep(f0, f1, dur)`, `whoosh`, `uh_oh`,
`bonk`, `twinkle([notes])`, `firework()` (returns whistle and boom), `spring`,
`noise_burst`, and the instruments `lead`, `pluck`, `bass`, `bell`, `kick`, `snare`, `hat`,
`crash`. Pan effects toward where things happen on screen (`pan` from -1 to 1).

## Checking

You cannot listen, so measure:

- `python3 -m kit film audio <name>` writes the WAV and prints loudness.
- The review package's `audio.png` shows a spectrogram and waveform with every cue marked.
  Check that hits line up with cues, that no section is empty by accident, and that nothing
  clips.
- The review report flags a true peak above -1 dBTP; if so, set `MASTER = {'ceiling': 0.7}`.

When you deliver, say that the audio was checked by measurement, not by ear.
