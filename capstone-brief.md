# Capstone Brief — AI Consulting Pitch

## Before You Begin: Choose Your Scenario

Before you read further, pick:

- **SECTOR:**
- **COMPANY SIZE:**

You can change these after you present to the teaching staff. Changing industry or use case is okay. You do not have to lock them forever on day one.

---

## The Scenario

Something incredible just happened and you got in a time-machine. It is post-bootcamp — you are free!

To celebrate, you go out to dinner with friends. Before you know it, friends of friends are there — among them, **Chleo**.

Chleo is the CEO of a **[COMPANY SIZE]** company. They overhear that you just finished the AI Consulting bootcamp. Their company works in the **[SECTOR]**, and they are scared of AI — they fear AI is simply not transparent.

After some talking, you sell the idea that AI can be useful. There is still confusion: Chleo keeps asking what "the AI" is and how they would sign up.

Before the end of the night, Chleo asks for a meeting where you can showcase AI potential for their company. They leave before they can give you more information.

You will prepare for that meeting — then present to the **teaching staff** (and the class standing in for Chleo and stakeholders). After that presentation, you may keep your industry and use case, or change them. Both are okay.

---

## How This Capstone Works (Two Rounds)

This is **one** project with two rounds. **Everyone does both**, and everyone builds a working MVP.

```
Round 1 (build + present to teaching staff)
    → Staff (and class) feedback
    → Keep industry/use case, or change them (okay)
        → Round 2: consulting package + working MVP (everyone)
```

| Round | What it is | Who does it |
| --- | --- | --- |
| **Round 1** | Pitch package for Chleo: research, dashboard, light POC, monitoring, cost/timeline, **presentation to teaching staff + feedback** | **Everyone** (required) |
| **Decision** | After that presentation: keep your industry / use case, or change it | **Everyone** |
| **Round 2** | Full AI consulting package: stronger POC, **working MVP**, ROI/risk, EU AI Act + GDPR, strategic deployment plan, final presentation | **Everyone** (required) |

**Keep** means: your industry and use case survived the pitch. Deepen the same idea in Round 2.

**Change** means: after you present to the teaching staff, you may change industry, sector, company size, use case, or approach. That is a normal outcome of the pitch and there is no penalty for switching. Write down what changed and build Round 2 on the new direction.

Either way, Round 2 and the MVP are required. There is no path that ends at Round 1.

---

## Project Overview

- **Project Name:** Capstone — AI Consulting Pitch (Round 1) + Consulting Package, Compliance & MVP (Round 2)
- **Duration:** Kickoff Week 8 Day 3 → Week 9 (both rounds, everyone)
- **Type:** Individual
- **Modules drawn on:** Module 5 (BI, evaluation, business impact) + Module 7 (compliance, ethics) + earlier agent/automation work

### Learning Objectives

**By the end of Round 1, you will be able to:**

- Research a sector and company size; map opportunities, risks, and relevant AI use cases
- Build a stakeholder-focused BI dashboard (PowerBI) that communicates preliminary analysis
- Design a simple n8n (or similar) proof of concept aligned to your use cases
- Set up basic LangSmith monitoring to show AI can be observed and discussed transparently
- Estimate upfront cost and timeline at a consulting-conversation level
- Present to teaching staff, take feedback, and decide whether to keep or change your industry and use case

**By the end of Round 2, you will also be able to:**

- Define and scope an AI use case with measurable success criteria
- Build a clearer no-code/low-code POC with demo evidence
- Extend the POC into a **working MVP** that runs
- Produce ROI and risk assessment suitable for a decision-maker
- Document EU AI Act classification/obligations and GDPR data-protection duties
- Write a strategic plan covering POC → pilot → deployment and commercialisation

---

## Round 1 — Required (Pitch to Chleo)

You have limited time and incomplete information. Focus on a credible **MVP pitch**, not a finished product.

### Round 1 requirements

1. **Sector research and data gathering** — public data (Kaggle, Hugging Face, etc.) relevant to your sector/size
2. **Opportunity and risk mapping** — structured analysis for AI in this context
3. **Use case proposals** — 2–3 typical use cases; justify fit for company size
4. **BI dashboard** — PowerBI `.pbix` showcasing preliminary analysis (communication-layer focus)
5. **n8n (or similar) POC** — simple workflow demo tied to a use case
6. **LangSmith monitoring sample** — small dataset + setup that shows observability/transparency
7. **Cost and timeline estimate** — upfront cost + rough timeline; document assumptions
8. **Round 1 presentation** — present to the teaching staff; collect feedback; record whether you **keep or change** your industry / use case. If they (or you) want a different one, write that down and proceed with the new direction.

### Round 1 technical stack (suggested)

- PowerBI Desktop
- n8n (cloud or self-hosted) — or equivalent no-code/low-code tool
- LangSmith
- Python + pandas as needed for data prep
- LLM API (OpenAI / Anthropic) if you add a light agent (optional in Round 1)

### Round 1 suggested repo shape

```
capstone-round1/
├── data/
├── research/
│   ├── sector_research.md
│   ├── opportunities_risks.md
│   └── use_cases.md
├── dashboard/
│   ├── dashboard.pbix
│   └── dashboard_documentation.md
├── n8n/
│   ├── workflow.json
│   └── workflow_documentation.md
├── langsmith/
├── cost_estimation/
│   ├── cost_analysis.md
│   └── timeline_estimate.md
├── feedback/
│   └── round1_decision.md          # keep or change industry/use case + why
├── requirements.txt
├── README.md
└── .env.example
```

---

## Decision Gate — After Round 1 Presentation

You present to the **teaching staff**. Classmates may still play Chleo's room, but staff feedback is the one that can send you to a new industry or use case.

Changing industry or use case after that presentation is **okay**. Do not keep a weak idea only because you already researched it.

After you present:

1. Collect structured feedback (what landed, what confused people, what felt risky, whether the industry/use case should change).
2. Write a short **`round1_decision.md`** with one of:

| Decision | Meaning | What you do next |
| --- | --- | --- |
| **KEEP** | Industry and use case hold up. Deepen the same idea. | Round 2: consulting package + MVP on the same use case |
| **CHANGE** | New industry, sector, size, use case, or approach after the staff presentation | Note what changed and why, then build Round 2 on the new direction |

Changing is not a fail. It is using the presentation the way a real client meeting works. Either way you still owe the full Round 2 package and a working MVP.

---

## Round 2 — Required (Consulting Package + MVP)

Treat Round 1 as your discovery + early POC. Round 2 is the package you would leave with a real client after the first meeting went well, plus something they can actually click.

### Round 2 requirements

1. **Use case definition** — problem, company profile, solution, stakeholders, success criteria, out-of-scope
2. **No-code/low-code POC** — working demo (2–5 min recording) + documentation
3. **Working MVP** — a functional product beyond the POC (e.g. Python + Streamlit/FastAPI + LangChain/LangGraph, or advanced n8n). The core AI capability has to actually run.
4. **ROI and risk assessment** — costs, value, 12/36-month ROI, risk matrix with mitigations
5. **EU AI Act compliance docs** — risk class, reasoning, conformity summary, technical doc outline
6. **GDPR docs** — data flows, legal bases, short DPIA, data-subject rights, third-party transfers
7. **Strategic deployment plan** — POC → **pilot** → full deployment; GTM; KPIs; commercialisation
8. **Final presentation** — pitch to a decision-maker panel, including an MVP demo (see presentation guide)

Keep the MVP small on purpose. One capability that runs end to end beats four half-wired screens.

### Round 2 suggested tools

| Component | Suggested tools |
| --- | --- |
| POC | n8n, Make, Zapier, Copilot Studio, Voiceflow, etc. |
| MVP | Python, FastAPI, Streamlit, LangChain, LangGraph |
| ROI & risk | Sheets / Excel / Markdown |
| Compliance | Manual docs; optional Giskard / model cards |
| Strategy | Slides, Notion, Markdown |

---

## Scope and Constraints

- **Public or synthetic data only** — no real personal data from live clients
- **Round 1** prioritises a clear story + working demo pieces over perfection
- **Round 2** needs rigorous consulting documentation _and_ an MVP that runs
- Be realistic about time. Scope the MVP to one capability you can finish rather than a product you can only describe

---

## Timing Guide

### Week 8, Day 3 — Kickoff

- Read this brief, planning template, and Round 1 presentation guide
- Lock a **starting** sector + company size
- Start research and planning

### Week 9 — Round 1 build, present, decide

- Finish Round 1 artifacts
- **Present to teaching staff → feedback → keep or change your industry / use case**
- Submit Round 1 deliverables

### Week 9 — Round 2 (everyone)

- Strengthen POC; build the MVP; complete ROI/risk, compliance, strategic plan
- Final presentation and Round 2 deliverables
- Use the daily check-ins (`pf-check-in-day-*.md`) to keep the MVP and the docs moving together

Exact presentation slots are set by your instructor.

---

## Use Case Examples (Round 1 flavour)

### E-commerce — Small company

- Use cases: inventory alerts, light segmentation, simple forecasting
- Dashboard: revenue, top products, acquisition cost
- n8n: order/inventory alerts

### Healthcare — Medium company

- Use cases: scheduling support, outcome summaries, resource hints
- Dashboard: patient flow, utilisation
- n8n: reminders / follow-ups _(mind compliance early — Round 2 will ask for it)_

### Financial services — Large company

- Use cases: fraud flags, risk triage, compliance reporting aids
- Dashboard: transaction patterns, risk indicators
- n8n: alert + report routing

---

## Success Criteria

### Round 1 (everyone)

- Sector/size chosen; research and use cases documented
- Dashboard communicates stakeholder-relevant metrics
- POC and LangSmith sample demonstrate "AI can be shown and monitored"
- Cost/timeline estimates have explicit assumptions
- You presented to teaching staff, captured feedback, and recorded whether you keep or change the industry / use case

### Round 2 (everyone)

- Use case and POC are clear and demoable
- **MVP runs** and its core AI capability works
- ROI/risk and compliance packs are complete and honest
- Strategic plan includes a concrete **pilot** phase before full rollout
- Final presentation speaks to business, legal, and technical concerns

---

## Deliverables and Rubrics

- Round 1 submission details: `pf-02-round1-deliverables.md`
- Round 2 submission details: `pf-02-project-deliverables.md`
- Rubric (both rounds): `pf-03-project-rubric.md`
- Planning: `pf-04-project-planning.md`
- Round 1 presentation + feedback: `pf-05-round1-presentation-feedback.md`
- Round 2 presentation: `pf-05-project-presentation.md`

---

## Getting Help

- Instructor check-ins and office hours
- Peer feedback is encouraged; all submitted work must be your own
- Prefer official docs (PowerBI, n8n, LangSmith, EU AI Act, GDPR) before asking

Good luck with Chleo — and with the call you make after the room talks back.
