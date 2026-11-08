# Game knowledge

Follow the [highest-priority lightweight workflow](agent-autonomy.md).
Markdown is sufficient. Reuse existing knowledge notes and organize new material
by the uncertainty or subsystem it helps resolve. A useful entry records:

- the finding or hypothesis;
- applicable game, target, compiler/profile or subsystem;
- evidence links and useful commands;
- failed attempts worth avoiding and remaining questions.

Write naturally and directly. Keep the finding, reasoning and useful action
connected. Remove filler, circular restatements, repeated conclusions and
unnecessary jargon. Avoid defensive-claim boilerplate; state genuine uncertainty
or applicability once where it helps the reader decide what to do.

Search the relevant entries rather than loading a large journal. Keep handoff
short and focused on current work, blockers and next actions. Generate progress
from canonical ledgers; ordinary notes need no test, native replay, source-SHA
pin refresh or schema conversion. Preserve useful older research and evidence.

Every registered repository can read the other games through `/references` in
Factory shells. Notes are immediately useful for cross-game reference without
a promotion or publication workflow. Record scope and uncertainty when applying
one game's lesson to another. Knowledge and analysis alone confer no exactness
credit; complete comparison evidence and the acceptance boundary remain separate.

## Optional legacy JSON

Existing `.reconstruction/game-knowledge.json` files and the
[legacy schema](../schemas/v1/game-knowledge-input.schema.json) remain supported.
The [template](../templates/game-knowledge-v1.json) and
`python -m reconstruction_factory validate-game-knowledge` are optional tools
for projects already using that representation. Its existing vocabulary and
validation rules still apply when used. Agents need not create the file, copy
Markdown into it, maintain two knowledge sources or validate an ordinary note
through Factory.

The packaged Factory catalog is a separate set of reviewed rules that can
influence automated decisions. Validating a rule for that catalog is an explicit
maintenance task; it is not a prerequisite for retaining or sharing useful
observations in game notes.
