# Factory Repository Instructions

## Highest priority: lightweight exact reconstruction and useful knowledge

These are the user's current workflow requirements. They override older
instructions that mandate broad CI, repeated preflights, document/source-pin
refreshes, per-checkpoint audits or extra workflow machinery. Preserve the
actual exactness, target identity, natural-source and state-isolation rules.

- Prioritize exact reconstruction and reusable knowledge. Use the shortest
  useful loop: inspect relevant state, analyze/edit, compile and compare the
  affected scope, retain useful learning, and create a coherent checkpoint.
- Use existing repository scripts and composable Bash. Add only the smallest
  change needed for an observed problem. Do not introduce a framework, schema,
  registry, state machine, generalized validator, test family or reporting
  process merely to make a local reconstruction task look more engineered.
- Keep discovery and ordinary repository work independent of other games and
  optional tools. Do not add registry-wide file, prefix or provider preflights.
  Resolve availability when a command actually uses a resource; report its
  error on that call and let other work continue.
- Documentation, knowledge and handoff edits require no compiler, analyzer,
  full CI, cold replay or receipt refresh. Inspect the diff. Check syntax only
  for machine-readable inputs actually changed.
- Source changes need the complete affected exact comparison, including its
  owned extents and relocations. Recheck known consumers of changed shared
  inputs. Tool changes need relevant positive/negative cases and a bounded
  real smoke. Run a broad suite only for an explicit request or a demonstrated
  impact that cannot be narrowed; state that reason first.
- Do not add tests or live freshness gates for prose hashes, prompt wording,
  progress totals, handoff source-SHA tables or ordinary source spelling.
  Bind exact evidence to executable inputs and relevant verification settings.
  Keep Git metadata as provenance. A document genuinely consumed by a build
  remains a build input. Never edit historical receipts to manufacture a pass.
- Plain Markdown is sufficient for knowledge: record the finding, applicable
  target/compiler/scope, evidence links, useful failed attempts and open
  questions. No mandatory JSON conversion, promotion workflow or test per note.
  Search relevant sections; do not read an entire large knowledge journal.
- Write documentation and knowledge in natural, fluent English. Lead with the
  concrete finding and connect the evidence and next action clearly. Remove
  filler, circular restatements, repeated conclusions and unnecessary jargon.
  Do not add defensive-claim boilerplate. State a real uncertainty or scope
  limit once when it changes a decision; do not repeat disclaimers about what
  a note does not prove, certify or authorize. Prefer a small useful note over
  an exhaustive report that is difficult to read.
- Keep handoff focused on current work, evidence references, blockers and the
  next useful action. Generate progress from canonical ledgers; avoid manual
  duplicate counts, recurring full reports and unrelated documentation chores.
- Preserve dirty/untracked work, targets, useful evidence, game-specific Wine
  prefixes and analyzer projects. Exactness still requires a complete strict
  comparison; knowledge and successful commands alone confer no exact credit.


These instructions apply to the entire Factory repository.

## Start here

1. Follow the highest-priority requirements above; read
   [`docs/agent-autonomy.md`](docs/agent-autonomy.md) for the common workflow.
2. Read [`docs/README.md`](docs/README.md) before treating any document as
   current authority.
3. When a launch contract is needed, select it through [`contracts/README.md`](contracts/README.md)
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
- Follow [`docs/shared-runtimes.md`](docs/shared-runtimes.md) for Ghidra, JDK,
  and Wine. Reuse Factory installations through the repository's
  `scripts/shared_runtime.py`; keep prefixes and Ghidra settings/cache local.
  Do not copy installations or borrow another game's prefix/project. Preserve
  locked tool versions when attaching a repository.
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
  changes, run the checks proportional to that surface and select only checks
  relevant to the changed behavior. Full release validation is explicit.
- Make coherent, detailed English commits. Push only when the user has asked to
  publish or preserve the completed checkpoint.

Root-level date-stamped `.txt` files may be operator chat transcripts. Leave
them untracked unless the user explicitly requests publication.
