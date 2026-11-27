# Offer workspaces

Each private offer repository owns its brand context, versioned offers, app code, experiments and curated results. Prizm owns shared skills, tools and components. A Git submodule at `vendor/prizm-labs` pins the shared revision. Dependency updates are explicit and reversible; no daily updater is installed.

Layer order: workspace identity → brand facts/customer evidence → offer/version → experiment/angle/channel → run/output/result. Each layer references its parent ID. Evidence keeps its source and confidence; a draft price never becomes approved because it is in a repository.

The workspace manifest is `offer-workspace.json`. Read it first. Brand context lives under `brands/<brand-id>/`; offers under `offers/<offer-id>/offer.json`; app and content code under `apps/`; curated runs under `runs/`. Large originals stay in the brand's Google Drive folder; runtime leads and credentials remain outside version control.

`python3 scripts/prizm.py check` checks the context contract. `context` resolves the exact brand and shared skill/tool paths. `page`, `offer`, and `skills-find` are explicit adapters. Page sections belong to the consuming app; the renderer/validator belongs to Prizm. Legacy tools that derive outputs beside their own code require adapters before execution. This runner is not a security sandbox.

A clean clone needs `git submodule update --init --depth 1`. Both the offer repo and the upstream dependency are private and use the operator's existing GitHub authorization. No credentials are copied or committed. Access to an offer repository does NOT grant access to Prizm. Do not give a partner full Prizm access merely to make cloning work: provision an approved toolkit artifact or scoped execution bridge first. The current implementation is the owner's development setup, not an activated partner node.

The existing `tools/client-copies/` system is a legacy alternative. These workspaces do not use its credential copying or scheduled workflow. New workspaces use the submodule contract.

## Shared foundation

The page assembler, offer validator and avatar reference material were brought into this layer from the reviewed local offer prototype. They were previously extracted from established tooling. `provenance.json` records content hashes and origin paths without private machine paths. The page assembler gains a `PRIZM_PAGE_SECTIONS` input so per-offer sections never modify shared code.
