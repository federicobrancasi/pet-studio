# Sound

Films get an original chiptune score and sound effects, written as code in `score(mix)`. Don't
use copyrighted music or samples.

| Part | Gain |
| --- | --- |
| lead melody | 0.10-0.16 |
| bass (already an octave up, so phone speakers can play it) | 0.24-0.26 |
| plucks, arpeggios | 0.03-0.09 |
| bells | 0.05-0.10 |
| drums (`groove`, `roll`) | built in; use `soft=0.6-1.0` |
| sound effects | 0.08-0.30; up to 0.45 for the one big hit |

The mastering step normalizes the mix to about -15 LUFS with a true peak around -2 dBTP. Overall
gain doesn't matter, but the balance does: keep the melody above the bass. To change the master,
set `MASTER` in the film, for example `{'ceiling': 0.7}` (quieter), `{'drive': 1.2}` (less
squashed) or `{'fade_out': 1.0}` (a longer fade).

## Music for the picture

- At 120 BPM, a beat is 0.5 s and a bar is 2 s. `mix.beat(b)` converts beats to seconds. Put
  scene changes on bar lines and big actions on beats.
- Give each section its own texture:
  - a lullaby for sleep
  - a bouncy theme for hops
  - a minor-key tiptoe for tension
  - a fanfare for success
  - a slow melody for hearts
  - a final major chord at the end
- Write melodies with `mix.melody([(beat, length, 'C5'), ...], start_beat, 'lead' | 'bell' | 'pluck', gain)`.
  For chords, see `music()` in `examples/coding-world/film.py`.
- Leave room for silence.

## Effects on the timeline

Reuse the picture's timing constants so sound and picture never drift apart:

```python
for h in HOPS:
    mix.put(A.boing(), h.t0, 0.16)
    mix.put(A.land(), h.t1, 0.30)
```

**Effects:** `click`, `boing`, `land`, `coin`, `blip`, `sweep`, `whoosh`, `uh_oh`, `bonk`,
`twinkle`, `firework`, `spring`, `noise_burst`.
**Instruments:** `lead`, `pluck`, `bass`, `bell`, `kick`, `snare`, `hat`, `crash`.
Pan toward the action with `pan` from -1 to 1.

## Checking

You can't listen to it, so measure instead:
- `python3 -m kit film audio <name>` prints the loudness.
- The review's `audio.png` shows every cue marked on the spectrogram. Check that each hit lands
  on its cue, that no section is empty by mistake, and that nothing clips.
- If the true peak is above -1 dBTP, set `MASTER = {'ceiling': 0.7}`.

When you deliver, tell the user the audio was checked by measurement, not by ear.
