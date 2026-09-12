# Factory Repository Instructions

These instructions apply to the entire Factory repository.

## Start here

1. Read [`README.md`](README.md) for the system boundary and end-to-end flow.
2. Read [`docs/README.md`](docs/README.md) before treating any document as
   current authority.
3. Select the current contract through [`contracts/README.md`](contracts/README.md)
   and the appropriate Web launch input through
   [`prompts/README.md`](prompts/README.md).
4. Inspect the real Git status and recent history before editing. Preserve and
   review dirty, untracked, and ignored state; an interrupted session may have
   left valuable continuation work.

## Authority and accuracy

- Accuracy is more important than completeness. Record `unknown` when evidence
  is insufficient; never fill a gap with a plausible guess.
- Source code, schemas, policies, current version indexes, and executable tests
  define the implemented contract. Dated validation reports and architecture
  archaeology are evidence about earlier checkpoints, not live service state.
- Never infer current accepted facts, repository progress, provider
  availability, or service health from a recorded count, receipt ID, commit, or
  benchmark. Query the live interface or inspect the current local state.
- Imported claims, analyzer output, successful commands, builds, and Git
  commits have zero exactness authority. Only policy-accepted, integrity- and
  freshness-checked receipts enter the Truth Kernel.
- Keep exact reconstruction, corresponding historical-platform product
  closure, semantic reconstruction, and later ports separate. GPT-web explores
  and checkpoints work; it cannot prove an open-world phase complete.

## Architecture boundaries

- One Factory MCP serves every registered game. Do not add a game-specific
  public URL or copy `mcp_for_gptweb` into a new game.
- Prefer Factory-native, target-attested providers: TH09 is the native IDA
  reference and TH10 is the native Ghidra reference. Earlier per-game bridges
  are migration compatibility only.
- Shared tool installations do not imply shared mutable state. Targets, Wine
  prefixes, analyzer databases/projects, ledgers, and evidence remain
  game-bound.
- Game-local knowledge may be edited in a game repository. Cross-game Factory
  knowledge is promoted only by later reviewed Factory work, never by a Web
  campaign tool.
- The framework exists to improve agent accuracy and feedback speed, not to
  replace composable repository Bash with a restrictive task catalog.

## Editing and operations

- Write repository documentation, code, prompts, contracts, and commit messages
  in English.
- Preserve unrelated user changes. Do not stage operator transcripts,
  private configuration, endpoints, credentials, target binaries, `.factory/`,
  or game-local analysis payloads.
- General public examples use placeholders. The real endpoint, high-entropy
  route, credentials, and private service-configuration path belong only in
  ignored operator state. Single-operator Web prompts intentionally name the
  mounted absolute repository and guidance paths because the agent may not
  receive injected skills; keep those paths accurate. A game's canonical
  ignored target path, such as `resources/th10.exe`, must remain explicit in
  its game instructions and prompt.
- Do not restart, deploy, rotate an endpoint, rewrite private configuration, or
  refresh provider implementation hashes unless the task explicitly requires
  it and active Web work has been coordinated.
- Treat versioned contracts as immutable history. A semantic change to a current
  version normally requires a new version and an update to the relevant index.
- Prefer focused checks for documentation-only changes. Do not add tests merely
  to freeze prose. For code, schema, prompt-contract, provider, or release
  changes, run the checks proportional to that surface and finish with
  `scripts/validate-release.py` when appropriate.
- Make coherent, detailed English commits. Push only when the user has asked to
  publish or preserve the completed checkpoint.

Root-level date-stamped `.txt` files may be operator chat transcripts. Leave
them untracked unless the user explicitly requests publication.
