# Sign-off

Nothing is final until the `pet-director` reviewer signs it off. Coding World went through three
rounds: the first review caught a butterfly covering the pet's heart antennae at the film's
emotional peak, a problem that was invisible in the code.

## How

1. Build the review package: `python3 -m kit film review <name>` (for images:
   render every preset you will deliver; for moves: `kit move build` and the strip).
2. Run the `pet-director` agent (`.claude/agents/pet-director.md`) as a subagent, using the most
   capable model you have (the Coding World sign-off used Claude Opus 5.5). Give it:
   - the user's brief, word for word
   - the paths of the deliverable and the review folder
   - a beat list: what happens and when
   - for later rounds, the previous verdict and what you changed
3. Read the verdict. Fix every **must-fix**. Do the nice-to-haves that improve the piece.
   Re-render, rebuild the review package, and ask again with the change list.
4. Stop when the first line is `VERDICT: SIGNED OFF`. Quote the verdict when you deliver.

If you cannot start subagents, review it yourself against the same checklist in
`pet-director.md`, as strictly as a second person would, and tell the user that no independent
sign-off happened.

## What reviewers check

- The brief: the right subject, length, format and tone. It is the VS Code pet, unnamed.
- The story reads without sound, and the first second works as a thumbnail.
- Composition: nothing covers faces or text, text is on screen long enough, no clutter at
  important moments, safe margins.
- Craft: real sprites, whole pixels, correct colorways, eyes and blinks, no popping, timing that
  breathes, a clear ending.
- Sound: hits on cues, levels, no clipping (true peak at most -1 dBTP).
- Delivery: the report's X checks pass; the determinism check is OK.
