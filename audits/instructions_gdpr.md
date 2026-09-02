# Audit your own project — GDPR lens

In this lab, you apply GDPR analysis to your own project. Not a fictional scenario — the system you actually built.

GDPR audits on your own work are uncomfortable for a specific reason: you know the shortcuts you took. You remember the moment you decided "this is probably fine" and moved on. This lab asks you to revisit those moments with the regulatory framework in hand.

## Kick-off

Pull up your Week 5 Project project. Before any analysis, you need a precise description of what personal data your system processes — because GDPR analysis begins with data, not with the system.

Write a **data processing brief**: a one-page description of the data flows in your system, written as if handing it to a Data Protection Officer who has never seen the project.

Your brief must answer:

- What personal data does the system process? (Names, emails, behavioural data, text content written by or about people, inferred attributes — be specific)
- Where does that data come from? (Users who submitted it directly? Existing company databases? Third-party sources?)
- What is the data used for? (List each purpose separately)
- Who processes it? (Your system, the LLM API, any other third-party service in the stack?)
- Where is the data stored and processed? (EU servers, US cloud, unknown?)
- Does the system make or assist in any decision that affects people? (Scoring, ranking, recommending, flagging — and does a human review it before action is taken?)

Write this brief before moving to Phase 1. Everything that follows is built on top of it. If the brief is vague, the audit will be vague.

**An important check before you start:** Does your system process personal data at all? Some systems process only anonymised or purely operational data. If yours does, confirm this explicitly and explain why — "no personal data is involved" is a conclusion that must be justified, not assumed.

---

## CFU checkpoints

### 1. Recognize

Read your data processing brief and identify: which categories of personal data are present, whether any special-category data (Article 9) is included or could be inferred from outputs, and whether the data flows cross an EU border at any point.

### 2. Apply

Complete the full audit worksheet (Phases 2–5 below). For every lawful basis you propose, write a one-line justification. If you are uncertain, write `TBD — legal review` rather than guessing.

### 3. Integrate

Write the client recommendation memo. It should reflect the audit findings and include a bottom-line recommendation (proceed / proceed with conditions / stop), the top three actions the client must take, and the residual risks that remain even if those actions are taken.

### 4. Verify

Before submitting, apply the accountability test: could you demonstrate compliance to a regulator using only the documentation your project currently has? Note what is missing.

---

## Core

### Phase 1: Personal data inventory

For each category of personal data you identified in your brief, complete this table:

| Data category | Source | Purpose(s) | Retention period (known/estimated) | Crosses EU border? |
|---|---|---|---|---|
| | | | | |

If you have multiple purposes for the same data category, add a row per purpose — purpose limitation applies per processing activity, not per data type.

Flag any data that was originally collected for one purpose and is being used in your system for a different purpose. This is the most common GDPR failure mode in AI projects and is likely relevant to your work.

### Phase 2: Role map

Identify every entity that processes personal data in your system and classify its role:

| Entity | Role (controller / processor / joint controller) | Processing activity | DPA in place? |
|---|---|---|---|
| Your client | | | |
| You / your team | | | |
| LLM API provider (if used) | | | |
| Any other vendor | | | |

For any processor relationship, note whether a Data Processing Agreement (DPA) exists or would need to be established. A DPA is not optional — it is a legal requirement for every controller/processor relationship.

For any international transfer (data leaving the EEA), note which transfer mechanism applies: adequacy decision, Standard Contractual Clauses (SCCs), or other.

### Phase 3: Lawful basis assessment

For each processing purpose you identified, select a lawful basis and justify it:

| Purpose | Proposed lawful basis | One-line justification | Flag for legal review? |
|---|---|---|---|
| | | | |

Use the six Article 6 bases: consent, contract, legal obligation, vital interests, public task, or legitimate interests.

If you are proposing **legitimate interests**: write out the three-part Legitimate Interests Assessment (LIA) test:
1. Is the interest legitimate? (What is the concrete business need?)
2. Is the processing necessary? (Is there a less intrusive way to achieve it?)
3. Does the individual's interest override? (Does the privacy impact outweigh the benefit?)

If you cannot complete all three parts of the LIA with confidence, mark it `TBD — legal review`.

### Phase 4: Risk and rights analysis

Answer each of the following in two to four sentences:

**Special category data (Article 9):**
Is any special-category data present or inferable from the system's outputs? (Health, biometric, political, religious, sexual orientation, ethnic origin, trade union membership) If yes, what Article 9 condition applies?

**Automated decision-making (Article 22):**
Does the system produce decisions with legal or similarly significant effects on people — and does it do so without meaningful human review? If yes, what safeguard is in place: human intervention mechanism, right to contest, explanation of the decision logic?

**DPIA trigger:**
Apply the EDPB's nine criteria. Which apply to your system? (Evaluation or scoring of people; automated decision-making with significant effects; systematic monitoring; special category data at scale; large-scale data processing; matching or combining datasets; data concerning vulnerable people; innovative technology; cross-border transfer preventing rights exercise.) If two or more criteria apply, a DPIA is generally required.

**Data subject rights friction:**
Which data subject rights are most likely to create operational challenges for your system? (The most common are: right of access to AI-processed data, right to erasure when training data is involved, right to object to profiling.) For each, note whether your current design can support a timely response.

### Phase 5: Law stacking check

One line each:

- **AI Act cross-check:** What risk tier did your system fall into (or would you hypothesize)? Does the AI Act impose any obligation that GDPR does not already require?
- **ePrivacy check:** Does your system use cookies, tracking pixels, device-level data collection, or the content of electronic communications? If yes, does ePrivacy's consent requirement apply — and is it currently satisfied?
- **Data Act check:** Does your system involve connected product data, IoT data, or cloud switching? (Usually N/A — but flag if relevant.)

### Phase 6: Compliance memo

Write 300–400 words addressed to your client's Data Protection Officer (or, if none exists, their legal counsel). Write it as a consultant delivering a short advisory note, not as a worksheet.

Your memo must include:

- **Bottom line:** proceed / proceed with conditions / stop — and the one-sentence reason.
- **Top three actions:** specific, concrete, and sequenced. For example: `(1) Establish a DPA with [API vendor] before any personal data flows; (2) conduct a DPIA before deployment — your system likely triggers at least two EDPB criteria; (3) revise the purpose for which [data category] is used, as current use is incompatible with the original collection purpose.`
- **Residual risks:** two to three risks that remain even if the client follows your recommendations.
- **What this memo is not:** a legal opinion, a DPIA, or a certification. The client must engage legal counsel before relying on this assessment for compliance decisions.
