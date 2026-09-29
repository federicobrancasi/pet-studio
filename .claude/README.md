# The skill and the reviewer

- [`skills/pet-studio/`](skills/pet-studio/SKILL.md): the `pet-studio` skill, with its guides
  and file templates. The agent uses it for any video, image or new move.
- [`agents/pet-director.md`](agents/pet-director.md): the `pet-director` agent, which reviews
  the work and signs it off.

GitHub Copilot (in Visual Studio Code and the Copilot CLI) and Claude Code load both from this
folder, so there is nothing to set up: open the repo and ask.

It's called `.claude` because it's the one folder all of them read. Copilot also reads `.github/`
and `.agents/`, but Claude Code doesn't, so the files live here once instead of in two copies that
could drift apart. The rules for the whole repo are in [`AGENTS.md`](../AGENTS.md), which Claude
Code reads through [`CLAUDE.md`](../CLAUDE.md).
