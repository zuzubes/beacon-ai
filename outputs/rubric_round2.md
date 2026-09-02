# Round 2 Rubric & Presentation Guide

## Round 2 Rubric (100 points) — Everyone

### Scoring breakdown

| Dimension | Weight | Points |
|---|---|---|
| 1. Use case definition & POC | 15% | 15 |
| 2. Working MVP | 15% | 15 |
| 3. ROI & risk assessment | 20% | 20 |
| 4. EU AI Act compliance | 20% | 20 |
| 5. GDPR documentation | 10% | 10 |
| 6. Strategic deployment plan (incl. pilot) | 10% | 10 |
| 7. Final presentation | 10% | 10 |
| **Total** | **100%** | **100** |

### Dimension details

**1. Use case & POC (15)**
Clear problem, stakeholders, success criteria, scope limits; POC demos the AI capability; documentation reproducible; Round 1 → Round 2 evolution explained, including a new industry or use case if that is what the staff presentation led to.

**2. Working MVP (15)**
Runs; core AI capability actually works; basic error handling; `mvp_documentation.md` lets someone else start it. A small MVP that runs scores above an ambitious one that does not.

**3. ROI & risk (20)**
Upfront/ongoing costs, value, 12/36-month ROI, assumptions, break-even; ≥6 risks with likelihood, impact, mitigation across regulatory/technical/ethical/operational.

**4. EU AI Act (20)**
Correct-enough classification with reasoning; obligations addressed for the class; conformity summary; technical documentation outline.

**5. GDPR (10)**
Data flows; legal bases; DPIA for highest-risk processing; rights; third-party transfers.

**6. Strategic plan (10)**
POC → pilot → full deployment with milestones; GTM; stakeholder comms; KPIs; commercialisation model. Pilot success criteria are explicit.

**7. Presentation (10)**
Speaks to business, legal, and technical concerns; MVP demo works or backup recording used; honest about uncertainty.

### Round 2 key questions
- Is this something a client could say yes/no to?
- Are compliance claims honest (including "minimal risk, and here is why")?
- Does the plan use a pilot before full rollout?

### Grading notes for instructors
- Round 2 and the MVP are required for everyone. There is no stop-after-Round-1 path.
- Changing industry or use case after the teaching staff presentation is allowed and positive. Do not mark students down for switching.
- If a student's Round 2 uses a different industry or use case than Round 1, they must document it in `round1_decision.md` / the use case doc. That is the expected path after a change, not a problem.
- Keep Campus identifiers stable: Round 1 → `project-5`; Round 2 → `final-project`.

---

## Capstone Round 2 Presentation Guide

### Overview

This guide covers the Round 2 presentation, which everyone delivers.

Your Round 2 presentation is your opportunity to act as the AI consultant you have been training to become. You are not presenting a school project — you are pitching a real AI solution to a panel of decision-makers, and you have a working MVP to show.

For the earlier Round 1 pitch to teaching staff, see `pf-05-round1-presentation-feedback.md`.

| | |
|---|---|
| **Presentation day** | Late Week 9 (instructor sets the slot) |
| **Format** | Individual presentation |
| **Total time** | 12–15 minutes (10 min presentation + 2–5 min Q&A) |

**Bridge from Round 1**: in one slide or 30 seconds, say what changed after you presented to teaching staff. If you switched industry or use case, say so plainly. That is allowed.

### Audience frame

Imagine you are presenting to a panel that includes:
- A **CEO** who wants to know if this is worth investing in
- A **Legal/Compliance Officer** who wants to know if this creates liability
- A **CTO** who wants to know if this is technically viable
- An **Operations Manager** who wants to know if this will disrupt their team

Your presentation must speak to all four. Avoid deep technical jargon — explain things as if to a smart non-specialist.

### Presentation structure

**Slide 1 — Title** *(30 seconds)*
- Project name
- Your use case / industry
- Your name

**Slide 2 — The Problem** *(1–2 minutes)*
Tell a story. Make them care.
- What is the business problem?
- Who is affected and how?
- What does the current situation cost (time, money, quality)?
- Why does this problem persist — what makes it hard to solve without AI?

> **Tip**: open with a concrete, vivid example. "Imagine you run a 50-person logistics company and your operations team spends 3 hours per day manually triaging customer complaint emails..." is more compelling than "there is inefficiency in operations."

**Slide 3 — The Proposed AI Solution** *(1–2 minutes)*
- What is your AI solution in one sentence?
- What type of AI capability does it use? (NLP, classification, generation, automation, etc.)
- How does it solve the problem described in Slide 2?
- What does the workflow look like end to end? (A simple diagram helps)

**Slide 4 — POC Demo** *(2–3 minutes)*
Show, don't tell. Run your POC live or play your recorded demo. Narrate what is happening as it runs:
- "This is the trigger — when X happens..."
- "Here the AI is doing Y..."
- "And this is the output — what the user or system receives..."

After the demo, briefly explain:
- What tools you used and why
- What the POC does and does not prove
- What would be different in a production version

> If your demo fails live: have a backup recording ready. Always have a backup.

**Slide 5 — Business Case: ROI** *(1–2 minutes)*
Make the financial case clearly and honestly.
- What does it cost to build and run? (headline numbers)
- What value does it create? (headline numbers)
- What is the ROI at 12 months? At 36 months?
- When does it break even?

One clear chart or table is worth more than three slides of numbers. Show the core calculation, not every assumption.

> Acknowledge uncertainty: "These numbers are estimates based on industry benchmarks — the actual ROI would be validated during the pilot phase."

**Slide 6 — Risk Assessment Highlights** *(1 minute)*
Do not read out the full risk matrix. Instead:
- Name the top 2–3 risks that could derail this project
- For each: state the risk in one sentence, the likelihood/impact, and the mitigation
- Close with: "These risks are manageable — here is how."

**Slide 7 — Compliance Summary** *(1–2 minutes)*
This is the slide your Legal Officer cares about most.
- **EU AI Act**: what is your risk classification? Why? What obligations apply?
- **GDPR**: what personal data does the system touch? What is the legal basis? Any DPIA findings?
- **Key compliance message**: "This system can be deployed compliantly because..."
- Any gaps you have identified and how they would be addressed before production

> **Tip**: compliance is not a checkbox. Showing that you understand *why* your system has a particular risk level is more impressive than just stating the label.

**Slide 8 — Strategic Deployment Plan** *(1–2 minutes)*
- Show the three phases (POC → Pilot → Full Deployment) with a simple timeline
- State the go-to-market strategy in 2–3 sentences: who buys this, how, at what price
- What are the success metrics that would greenlight moving from pilot to full deployment?
- What is the commercialisation model? (SaaS, service, internal tool, etc.)

**Slide 9 — MVP Demo** *(required)*
Show your MVP working. Keep it to 1–2 minutes and demo the upgrade: "Here is what the POC showed was possible. Here is the beginning of the real product."

> Have a backup recording. A live failure with no fallback costs you the easiest points in the deck.

**Slide 10 — Conclusion** *(30 seconds)*
Close with confidence:
- Restate the business value in one sentence
- Restate the compliance status in one sentence
- Call to action: "The next step is a 60-day pilot with [defined scope] to validate these assumptions."

### Slide design guidelines
- **Maximum slides**: 10–12 (excluding title and backup slides)
- **Font size**: minimum 24pt for body text — if it doesn't fit, cut the text
- **Colour**: use a clean, professional palette — avoid clashing colours
- **Images and diagrams**: use them. A POC workflow diagram, a risk matrix table, and an ROI chart will communicate more than text.
- **Avoid**: bullet points that repeat what you are saying verbatim. Your slides are visual support, not a script.
- One idea per slide — if you find yourself squeezing two ideas onto one slide, split it.

### Preparing for Q&A

Expect questions like:
- "How did you classify your system under the EU AI Act? Walk me through the reasoning."
- "Your ROI assumes X hours saved per week — how did you arrive at that number?"
- "What happens if the AI output is wrong? Who is liable?"
- "How would you handle a data subject requesting deletion of their data?"
- "Why not just use [existing tool] instead of building this?"
- "What is the first thing you would do differently if you had more time?"

**Preparation tips**:
- Know your numbers — don't read them from the slide
- Know your classification reasoning — don't just say "it's limited risk"
- Know your top risks and why you rated them the way you did
- Prepare an honest answer to "what are the main weaknesses of this project?"
