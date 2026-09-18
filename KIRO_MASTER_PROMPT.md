# Master Prompt for Kiro — Paste This As One Message

You are implementing **RoomieOps**, a hackathon project for **First Commit — Bharat Builds Tour 2026** (WeMakeDevs × AWS). The complete, locked specification is in `ROOMIEOPS_BUILD_SPEC.md` at the repo root — treat it as the single source of truth for every architectural, scope, and priority decision. `README.md` is already drafted at the repo root; update it as features land, don't rewrite its structure.

## Hard constraints — do not violate these under any circumstance

1. Do not redesign, rename, or rescope the project. RoomieOps is a household coordination copilot, not a chatbot, not a generic PG/property ERP.
2. **The AI never performs final monetary arithmetic and never mutates state directly.** Every consequential action (expenses, chore reassignment, balance changes) must go through the Step Functions pipeline specified in §9/§19: validate → deterministic calculate → write → audit → notify. This is the single most important rule in the entire spec — if you're ever unsure whether something counts as "consequential," treat it as consequential.
3. Follow the P0 / P1 / P2 priority order in §11 exactly (per-requirement tiering is in §9's FR table). P0 must be solid before any P1 work starts; P1 before P2. Do not build P2 features (Cedar, Textract, OpenSearch, the 7 non-equal split methods) before P0 is done and tested.
4. Do not introduce any technology outside the stack listed in §37/§38/§39. If something seems genuinely required and missing, stop and ask.
5. Every write operation must accept and honor a client-supplied `requestId` for idempotency (NFR-06) — no duplicate expenses or payments on retry.
6. The agent must never claim an action succeeded when the backend call failed (NFR-12) — check the actual tool/Step Functions result before generating any success explanation.

## How to execute — checkpointed phases, not one unsupervised pass

Work through the four-day plan in `ROOMIEOPS_BUILD_SPEC.md` §40, in order — Day 1 → Day 4. Within each day, treat §11's P0/P1/P2 tiering as the authority on what to build first if anything doesn't fit; never build a P1/P2 item (per §11 and the per-FR tiering in §9) before the P0 items for that stage are done and verified. For each stage:

1. Implement only what that phase scopes.
2. Run and verify it — start the app, run tests, hit the endpoint. Show me the actual result.
3. Commit with a clear, scoped message.
4. Give me a short status: done, verified, still open, any judgment calls you made that aren't explicitly in the spec.
5. **Stop and wait for me before starting the next phase**, except:
   - Phase 0 → Phase 1 (repo setup into frontend scaffolding) can run as one block.
   - Within Phase 3, the split engine and balance calculator can be built and unit-tested together before I review — this is the part of the whole project that must never be flaky, so take the time to get the reconciliation check (`sum(allocations) == amount`) right and show me the test cases, not just the code.

**Always stop and ask me first, regardless of phase, before you:**
- Spend anything beyond trivial dev-tier AWS usage, or leave anything running unattended overnight
- Deploy to the live Amplify/Cognito/Bedrock environment rather than local/LocalStack
- Let the AI orchestrator call a write path directly instead of routing through Step Functions
- Add a library, service, or dependency not listed in §8

## Immediate target

Get the deterministic split/balance engine (§21, part of Day 1 in §40) rock-solid and independently tested against the evaluation benchmark in §35 *before* wiring any AI on top of it — this is the foundation the whole "AI understands, backend executes" architecture depends on, and it's also the piece a judge is most likely to probe ("what if the AI gets the math wrong?"). Only after that should the Bedrock agent (Day 2, §40) get built on top of it.

## Start now

Begin with Day 1 of §40. Confirm the repo structure from `ROOMIEOPS_BUILD_SPEC.md` §45 before writing any code, then proceed.
