# GPT-web prompt selection

Choose one prompt from the current phase and game. These prompts are launch and
continuation inputs, not completion certificates.

| Use case | Prompt |
| --- | --- |
| Generic registered-game reconstruction | [`gpt-web-reconstruction.md`](gpt-web-reconstruction.md) |
| Semantic campaign after exact and native-product prerequisites | [`gpt-web-semantic-reconstruction.md`](gpt-web-semantic-reconstruction.md) |
| TH04 PC-98 exact campaign | [`gpt-web-th04-exact-reconstruction.md`](gpt-web-th04-exact-reconstruction.md) |
| TH09 Factory-native IDA exact campaign | [`gpt-web-th09-exact-reconstruction.md`](gpt-web-th09-exact-reconstruction.md) |
| TH10 Factory-native Ghidra exact campaign | [`gpt-web-th10-exact-reconstruction.md`](gpt-web-th10-exact-reconstruction.md) |

Each maintained prompt includes a complete standalone form for deployments
where ChatGPT exposes the MCP tools but does not inject plugin skills. Preserve
explicit Factory guidance paths in that form.

Every new conversation starts by reviewing current HEAD, recent history, dirty,
untracked, and relevant ignored state. It assumes the phase remains incomplete,
audits earlier readiness prose for a counterexample, and resumes useful work.
A local search plateau rotates coverage; it is not permission to announce
completion. Each conversation is bounded for browser and context reliability,
while the repository, local `gpt-web:` commits, and handoff state carry the
longer campaign. Do not add a Web-authored phase-close condition.

The moving 99.5% pressure target in exact prompts encourages work across hard
and easy authored surfaces. It is not whole-image coverage, an acceptance
policy, or a stop condition.
