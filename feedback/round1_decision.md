# Round 1 Decision

## Summary of feedback

- **Overall: thumbs-up.** The Round 1 presentation met the rubric — no red flags on the
  industry, use case, dashboard, approach itself.
- **Dataset lock-in date.** To hit an MVP by end of day Thursday, 2026-09-03, the datasets being used need to be finalized by the morning of Tuesday, 2026-09-01 — no swapping data sources mid-build.
- **Watch scope creep.** Explicit caution against over-extending scope: keep checking how much data is actually enough, and whether each additional trend/sector genuinely adds value rather than just adding volume.
- **Certification requirement (AI Manager program, separate from the capstone rubric):** the Round 2 presentation needs to explicitly include User Stories, a clear Definition of Done, Acceptance Criteria, a Sprint plan, and a Timeline — none of which were part of the Round 1 deck.

## Decision: KEEP

Industry, sector, and use case are unchanged — cross-border trend intelligence for Indian
micro-VCs, sourced from China/US funding data. Nothing in the feedback questioned the premise; the notes are about build discipline (data lock-in, scope) and presentation completeness (certification-required sections), not about the idea itself.

## What we'll deepen in Round 2

- **Finalize datasets by 2026-09-01 morning** and treat that as a hard cutoff — no new raw data sources added to `data/raw/` after that point for this round.
- **Scope discipline check**: before adding any sector, data source, or feature, ask whether it demonstrably strengthens the transfer-probability signal — not just whether it's available. If a sector's data doesn't move the needle on the thesis, it doesn't make the cut.
- **Add the certification-required project-management artifacts** to the Round 2 deck: User Stories for the core "partner picks a sector, gets a brief" flow, a Definition of Done for the MVP, Acceptance Criteria per user story, a Sprint plan, and a Timeline — currently missing entirely from Round 1 materials.

## First idea for MVP scope

A working end-to-end path a partner can actually use by Thursday, 2026-09-03:
load → clean → feature → score → brief generation (already built), fronted by the n8n chat
demo, over the dataset set locked in on 2026-09-01 — no additional sectors or data sources
added after that date unless a specific one is shown to materially improve the transfer-score
signal, per the scope-discipline note above.
