# Independent Verification Planes

Reconstruction is not one percentage and not a rigid two-stage pipeline. The
Factory records independent truth claims while the engineering workflow loops
between them. A result in one plane may identify work for another plane, but it
never grants that other plane's status.

## Canonical planes

| Plane | Canonical subject and claim | A pass establishes | A pass does not establish |
| --- | --- | --- | --- |
| Function or extent exactness | `function`/`extent`; `codegen_exact` or `owned_extent_exact` | The declared target-bound bytes and required comparison structure pass the selected exact oracle. | Production translation-unit coverage, link closure, whole-image equality, owner lifetime, or runtime behavior. |
| Production closure | extent-free `product`; `whole_build_closed` | The complete declared production source graph cold-compiles, links without unresolved symbols or force-link escape hatches, and produces the declared executable format under the attested toolchain. | Function exactness, whole-image equality, correct runtime storage aliases/lifetimes, or any runtime scenario. |
| Runtime storage identity | `data` or `runtime_scenario`; `runtime_storage_identity` | A bounded runtime oracle observed the declared physical storage, alias, publication, and lifetime relationship. | General scenario behavior, portability, product closure, or byte exactness. |
| Runtime scenario | `runtime_scenario`; `runtime_scenario_validated` | One artifact-, asset-, environment-, input-, and observable-bound scenario passed. | Unexercised paths, another runtime environment, product closure, or byte exactness. |

`whole_image_exact` and `portable_runtime_validated` remain stronger, separate
claims. They are not completion aliases for any row above.

The runtime vocabulary is normative now, but the initial strict live policy has
no runtime driver or oracle allowlist. Manual observations and repository prose
therefore remain useful engineering evidence while Factory live runtime status
stays `unknown`. A future provider must define deterministic scenario input,
writable-state isolation, asset identity, environment identity, bounded
observables, artifact retention, and fail-closed timeout/crash semantics before
the policy can admit a runtime receipt.

## Coupled feedback loop

The normal loop is cheap and focused first, broad and cold at meaningful
boundaries:

1. run syntax, tracking, and focused source checks;
2. replay every affected exact function or owned extent;
3. compile affected production translation units;
4. run a cold whole-product build after owner, ABI, layout, shared-header,
   link-input, or build-graph changes and at bounded closure milestones;
5. diagnose link/runtime failures as owner, ABI, data, layout, or lifetime work;
6. repair natural source and ledgers, then replay affected exact units again.

A linker failure does not revoke an unaffected exact receipt. Conversely, an
exact receipt cannot close a linker error. This separation lets reconstruction
work preserve real progress without hiding integration failures.

## TH095 as the first positive product fixture

TH095 now provides both sides of the same executable regression contract:

| Immutable checkpoint | Function plane | Product plane | Expected Factory fixture verdict |
| --- | --- | --- | --- |
| `b864c31b0896eca14988e1af8e4d642a9d337c0a` | 696 of 697 source-present functions exact | 88 of 88 production objects compiled, but 239 unique unresolved symbols remained | `fail` |
| `3442dcf29d9e0b5bef384a49bd0c9ad32a711826` | 696 of 697 source-present functions exact | 88 of 88 production objects compiled and the clean link had zero unresolved symbols | `pass` |

The second checkpoint proves that `whole_build_closed` can pass while one
source-present function remains deliberately non-exact. It also proves no
runtime claim by itself. TH095 has substantial manual runtime and owner-audit
evidence, but no committed deterministic Factory runtime-scenario provider yet;
those live Factory planes remain `unknown` rather than being inferred from the
successful build.

## Receipt and MCP behavior

The durable job and MCP layers do not need one tool per plane. GPT-web discovers
typed claims with `factory_list_claims`, submits the selected claim with
`factory_submit_replay`, observes the durable job, then queries the acceptance
registry. The selected driver supplies the claim-specific coverage domain:

- exact drivers report `claimed-bytes`;
- the TH095 product driver reports `production-translation-units`;
- future runtime providers must report their declared scenario-observable
  domain.

This keeps one composable GPT-web surface while preventing a generic job state,
process exit, or build message from becoming truth.
