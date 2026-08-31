# Round 1 Decision

## Feedback summary
- Overall thumbs-up: the Round 1 presentation met the rubric — no red flags on the industry, use case, dashboard, or approach itself.
- Dataset lock-in date: to hit an MVP by end of day Thursday, 2026-09-03, the datasets in use need to be finalized by the morning of Tuesday, 2026-09-01 — no swapping data sources mid-build.
- Watch scope creep: explicit caution against over-extending scope — keep checking how much data is actually enough, and whether each additional trend/sector genuinely adds value rather than just adding volume.
- Certification requirement (AI Manager program, separate from the capstone rubric): the Round 2 presentation needs to explicitly include User Stories, a clear Definition of Done, Acceptance Criteria, a Sprint plan, and a Timeline — none of which were part of the Round 1 deck.

## Decision
KEEP

## Why
Nothing in the feedback questioned the premise — cross-border trend intelligence for Indian micro-VCs, sourced from China/US funding data, was validated as-is. The notes are entirely about build discipline (dataset lock-in, scope creep) and presentation completeness (certification-required sections), not about the industry or use case being wrong.

## If CHANGE: what changes
- New industry / sector / size / use case / approach: N/A — decision is KEEP.
- Why the teaching staff presentation drove that: N/A.

## Round 2 focus
- **POC improvements**: finalize datasets by 2026-09-01 morning as a hard cutoff (no new raw sources added to `data/raw/` after that point this round); apply a scope-discipline test before adding any sector/data/feature — does it demonstrably strengthen the transfer-probability signal, not just "is it available."
- **MVP scope (the one capability that must run)**: end-to-end `load → clean → feature → score → brief` for a partner-selected sector, delivered through the n8n chat demo, over the dataset set locked in on 2026-09-01.
- **Compliance / ROI / strategy priorities**: add the AI Manager certification's required artifacts to the Round 2 deck — User Stories for the "partner picks a sector, gets a brief" flow, a Definition of Done for the MVP, Acceptance Criteria per user story, a Sprint plan, and a Timeline; carry forward the Round 1 cost estimate (~$3K out-of-pocket / ~$20K if founder time is costed) and the Week 1 MVP → Weeks 2–3 beta → Week 4+ validate timeline as the ongoing ROI/strategy anchor for scope decisions.
