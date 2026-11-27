# AGENTS.md

For any coding agent that opens this repo: Codex (ChatGPT's agent), Claude Code, or another.
The instructions are the same ones Claude Code reads. Follow them exactly.

1. Read [`.claude/CLAUDE.md`](.claude/CLAUDE.md) first: how to help the person (they are probably not technical: run
   things yourself, talk in plain words, never ask them to run a command or paste a key into chat), the hard rules
   on keys and brand data, and what "activate Prizm Lab" does.
2. Then [`CLAUDE.md`](CLAUDE.md) (the repo rules) and [`TOOLS.md`](TOOLS.md) (every tool, by job).
3. For marketing work, [`components/WORKFLOWS.md`](components/WORKFLOWS.md) is the routing index: which workflow
   makes which output, and which skill and component to use.
4. Skills: every skill is a folder with a `SKILL.md`, in `.agents/skills/` (the same folder as `.claude/skills/`).
   When the person's words match a skill's description, read that `SKILL.md` and follow it.
5. Keys come from the person's own `.env` (see `.env.example`) through `components/keys/loader.py`. Never print one.
6. Brand folders live in `brands/<brand>/`, or are linked there from the brand's own repo. They never go into this
   public repo.

A question or a read-only review does not authorize spending, generating, sending or going live.
