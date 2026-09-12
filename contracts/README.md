# Session contract versions

Versioned JSON contracts are retained so old prompts, transcripts, and
regression scenarios remain interpretable. Select the highest version named as
current below; older versions are historical inputs, not launch defaults.

| Workflow | Current contract | Historical contracts |
| --- | --- | --- |
| General exact/source reconstruction | [`gpt-web-reconstruction-session-v5.json`](gpt-web-reconstruction-session-v5.json) | `v1` through `v4` |
| Semantic reconstruction | [`gpt-web-semantic-reconstruction-session-v4.json`](gpt-web-semantic-reconstruction-session-v4.json) | `v1` through `v3` |
| Dirty-work and analysis-artifact recovery | [`worktree-recovery-and-analysis-artifacts-v1.json`](worktree-recovery-and-analysis-artifacts-v1.json) | none |

Do not choose an older contract because a dated report or commit mentions it.
Use one only when reproducing that historical checkpoint or testing a migration.
A behavior change to a current contract should normally create a new version,
retain the old file, update this index and the matching prompt, and validate the
machine-readable asset.

These contracts direct agent workflow; they do not define Oracle verdicts or
grant phase-completion authority.
