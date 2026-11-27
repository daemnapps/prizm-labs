# Use Blender and Use After Effects (/use-blender, /use-after-effects)

Setup commands: install and connect a local MCP server so a desktop client can drive Blender (.blend, background process) or Adobe After Effects on the user's own computer.

Source files: `commands/use-blender.md`, `commands/use-after-effects.md`, `commands/use-blender-references-installation.md`, `commands/use-blender-references-verification.md`, `commands/use-after-effects-references-installation.md`, `commands/use-after-effects-references-verification.md`

## Inputs it needs

- A local shell on the same computer as Blender (4.2+) or After Effects: Codex or Claude Code in Code -> Local; Claude Desktop Chat, Cowork, Code Cloud and Higgsfield `sandbox_exec` are not host shells.
- Node.js 24+ with npm; Blender: `fnf-blender-mcp@latest` version 0.2.0 or newer (0.1.0 needs an add-on and is obsolete).
- After Effects: macOS or Windows install, the `fnf-after-effects-mcp` package; Adobe licensing and OS permissions are separate.

## Steps in order

1. **Detect existing tools** - Check which `bl_*` or `ae_*` tools the conversation already has and verify a live session before reinstalling.
2. **Check Node, npm and the app** - Node 24+, npm, and the Blender or After Effects executable (Windows uses discovery steps first).
3. **Install the package** - Latest published package in a persistent directory owned by the user (never a temp or cloud path).
4. **Register the MCP server** - `higgsfield-use-blender` or `higgsfield-use-after-effects`, for the current OS user.
5. **Verify live** - Blender: `bl_health` (version, PID, background true), `bl_get_scene_summary`. AE: a live call through its local tools; a configured server alone proves nothing.
6. **Edit only on request** - Setup never authorizes editing the user's scenes or projects; Blender edits load `bl_get_skill` `blender-scene` first and render with a camera to check.

## Prompt blocks, word for word

**The setup request (Blender)** (`commands/use-blender.md`)

```text
`higgsfield mcp, /use-blender` is a request to install and connect this integration. In local Codex or Claude Code (including Claude Desktop **Code → Local**), use the host shell to complete the installation, register the server for the current OS user, and verify it. The command itself authorizes these setup steps; use the latest supported published package and do not stop to ask whether to install or which registration scope. Honor any narrower scope or other constraint the user states. 
```

**The setup request (After Effects)** (`commands/use-after-effects.md`)

```text
`higgsfield mcp, /use-after-effects` is a request to install and connect this integration. In local Codex or Claude Code (including Claude Desktop **Code → Local**), use the host shell to complete the installation, register the server for the current OS user, and verify it. The command itself authorizes these setup steps; use the latest published package and do not stop to ask whether to install, which version, or which registration scope. Honor any narrower scope or other constraint the user states. 
```

**Blender connection path** (`commands/use-blender.md`)

```text
Desktop client → stdio → fnf-blender-mcp → process pipes → Blender Python / bpy.
```

**After Effects connection path** (`commands/use-after-effects.md`)

```text
Desktop MCP client → local Node MCP server → OS scripting / ExtendScript → After Effects.
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Setup and edits | none | local npm package and MCP server on the user's computer; no generation model, no credits |

## Checks and gates

- The command itself authorizes setup steps (install, register, verify) without asking about version or scope; it does not authorize editing scenes or projects.
- Refuses to present manual setup as completed installation; asks the user to switch to Code -> Local if no local shell exists.
- Reports control only after a successful live call through the local MCP tools; four results are tracked separately (dependencies, MCP initialized, app responded, this conversation can call it).
- Obsolete 0.1.0 Blender runtime is never installed; an npm auth error means check registry config, not create an account.
- Blender: each MCP session owns its own scene; unsaved work in an open Blender window is unreadable until saved and loaded with `bl_open_project`.
- With no local After Effects, an Artcraft GPU box (bills credits, only with the user's agreement and approved price) can run the same AE workflows.

## Price pattern

No credits for setup. A rented GPU box for AE (Artcraft) is the only paid path and is not quoted here.

## Cheap swap

- Already free: local npm install on this Mac. Blender renders in a background process on this Mac for free; an AE render uses the local app, no Higgsfield credits.
