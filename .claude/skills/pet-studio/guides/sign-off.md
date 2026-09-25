# Sign-off

Nothing is final until the `pet-director` reviewer signs it off. A second pair of eyes catches
what the author no longer sees, such as a prop covering the pet's face at the story's peak.

1. Build the review material:
   - Films: `python3 -m kit film review <name>`.
   - Images: render every preset you'll deliver.
   - Moves: run `move build` and include the strip.
2. Run the `pet-director` agent (`.claude/agents/pet-director.md`) as a subagent on the strongest
   model available. Give it:
   - the brief, word for word
   - the paths to the deliverable and the review folder
   - the beat list
   - from the second round on, the last verdict and what you changed
3. Fix every must-fix, re-render, rebuild the review and ask again.
4. Stop when the first line says `VERDICT: SIGNED OFF`, and quote the verdict when you deliver.

If you can't start subagents, review the work yourself against the checklist in
`pet-director.md`, as strictly as a second person would, and tell the user that no independent
sign-off happened.
