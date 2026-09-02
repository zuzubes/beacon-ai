# Audit your own project

Apply EU AI Act compliance thinking to work you actually built. Instead of a hypothetical scenario, the subject is your own Week 5 Project project — the AI system you designed and built earlier in the course.

This is harder than auditing a fictional case. You know the system well, which means you have blind spots. You made design choices that felt reasonable at the time, and now you have to hold them up to a regulatory lens.

## Lesson alignment

- **Lesson setup requirements:** Review the risk tiers (Article 5 prohibited, Annex III high-risk, Article 50 limited risk, minimal risk), the provider/deployer distinction, and the list of high-risk obligations from `01_eu-ai-act-fundamentals.md`.

## Kick-off

Before you can audit a system, you need to describe it precisely. Vague descriptions produce vague audits.

Your first task is to write a **system brief** — a one-page description of what you actually built, written as if you were handing it to an external reviewer who has never seen it before.

Your system brief must answer:

- What does the system do? (In plain language — no buzzwords)
- What inputs does it take? (Data types, sources, whether any of it is personal data)
- What does it output? (A score, a decision, a recommendation, generated text, a flag, a notification?)
- Who is affected by the output? (Employees, customers, applicants, members of the public?)
- Does a human review the output before any action is taken? If yes, what does that review look like in practice?
- Who built it? (You, a team, a third-party tool you configured?)
- Who would use it in production? (Your client, their staff, end users?)

Write this brief now. It becomes the foundation for every step that follows. Do not skip or shortcut it — a vague brief produces a vague audit.

---

## CFU checkpoints

### 1. Recognize

Read your own system brief and assign a first-pass risk tier: prohibited, high-risk, limited risk / transparency, or minimal risk. Write one paragraph justifying your classification by reference to the specific Article 5 category, Annex III area, or Article 50 obligation that applies. If you believe the system is minimal risk, justify that too — "nothing applies" is a conclusion that requires evidence, not just a default.

### 2. Map roles

Identify your role, your client's role, and any third-party vendor's role in the AI Act's terms. Use the provider/deployer/importer framework.

- If you delivered a custom-built system: you are likely a **provider** for the purposes of this exercise.
- If you configured or integrated a third-party AI tool: you helped a **deployer**.
- If both: map each component separately.

Note: role mapping in consulting often requires a lawyer to confirm. Your task here is to produce the first-pass map, not the final legal determination.

### 3. Identify obligations

If your system is high-risk, list which of the 11 provider obligations apply. For each one, state whether your current design satisfies it, partially satisfies it, or does not satisfy it.

If your system triggers transparency obligations under Article 50, identify exactly what disclosure would be required and whether your current design includes it.

If your system is minimal risk, confirm that no specific AI Act obligations apply — and note any other EU law (GDPR, consumer protection) that might still be relevant.

### 4. Gap analysis

For every obligation you identified in step 3 that is not currently met, describe the gap concisely: what is missing, and what would need to change to close it.

This is the core consulting output. Be specific. "Human oversight is insufficient" is not a gap description. "The system outputs a candidate score that is displayed to the hiring manager without any mandatory review step, which fails Article 14's requirement that human overseers be able to intervene before decisions are taken" is a gap description.

### 5. Remediation

For each gap, propose a remediation step. This should be practical: something the team could actually implement. Note where a gap would require legal review or specialist input to resolve correctly.

---

> **Tool:** The European Commission's [EU AI Act Compliance Checker](https://ai-act-service-desk.ec.europa.eu/en/eu-ai-act-compliance-checker) can help you cross-check your classification. Use it after you have filled in the table below — not before. Forming your own assessment first is the point of the exercise.

| Question | Your answer |
|---|---|
| Does this system fall under any prohibited category (Article 5)? | |
| Does this system operate in any of the eight Annex III areas? | |
| If Annex III: does it "significantly influence" decisions in that area, or is it narrow/preparatory? | |
| Does this system interact with end users or generate content requiring disclosure (Article 50)? | |
| First-pass risk tier | |
| One-sentence justification citing the specific article or Annex entry | |

If you are unsure between two tiers, state the ambiguity and explain what additional information would resolve it. In a real engagement, this is where you would flag for legal review.

### Phase 3: Role map

Draw or describe the following for your system:

- **Provider:** Who developed the system and placed it on the market (or would, if deployed)?
- **Deployer:** Who uses it in a professional context?
- **Third-party vendors:** Any AI APIs, platforms, or tools embedded in the system? What tier do their own obligations fall under?

For each role, state the key obligations that flow from that role under the AI Act.

Use this template:

| Role | Entity | Key AI Act obligations |
|---|---|---|
| Provider | | |
| Deployer | | |
| Vendor (if applicable) | | |

### Phase 4: Obligation checklist (high-risk only)

If your system is high-risk, complete this checklist. For each obligation, mark **Met**, **Partial**, or **Gap** and add a one-line note.

| Obligation | Article | Status | Note |
|---|---|---|---|
| Risk management system | 9 | | |
| Data and data governance | 10 | | |
| Technical documentation | 11 | | |
| Record-keeping and logging | 12 | | |
| Transparency and user information | 13 | | |
| Human oversight | 14 | | |
| Accuracy, robustness, cybersecurity | 15 | | |
| Conformity assessment | 43 | | |
| EU declaration of conformity + CE marking | 47–48 | | |
| Registration | 49 | | |
| Post-market monitoring | 72 | | |

If your system is not high-risk, skip this table and proceed to Phase 5.

### Phase 5: Gap analysis and remediation plan

For each Gap or Partial in your checklist (or, for non-high-risk systems, any transparency gap or parallel legal issue), write a brief entry:

**Gap [number]**
- **Obligation:** which requirement is not met
- **Current state:** what your design currently does
- **Required state:** what the regulation requires
- **Remediation:** what change would close the gap
- **Escalation needed?** Yes / No — and if yes, to whom (lawyer, data protection officer, third-party conformity body)

### Phase 6: Compliance memo

Write a one-page compliance memo addressed to a fictional "Head of Product" at your Week 5 Project client. It should cover:

1. **System classification** — one sentence stating the tier and the basis
2. **Role map** — who is provider, who is deployer
3. **Key findings** — the top two or three compliance gaps, stated in plain language
4. **Recommended next steps** — what to do, in what order, and what needs external review
5. **Caveats** — what this memo is not (a legal opinion, a conformity assessment, a certification)

Keep the tone professional. Avoid jargon. This memo should be readable by a non-technical stakeholder.
