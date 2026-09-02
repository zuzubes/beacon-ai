# EU AI Act Compliance Note

## System brief
Beacon AI ingests public startup-funding and trend datasets, normalises sectors and countries, scores which sectors are rising in China and the US, and generates short sector briefs for Indian VC partners. It does not score people, decide on people, or make automated decisions with legal or similarly significant effects on natural persons.

## 1. First-pass risk class

| Question | Answer |
|---|---|
| Prohibited practice under Article 5? | No |
| Annex III high-risk area? | No |
| Article 50 transparency trigger? | No |
| First-pass risk class | Minimal risk |

### Why
- The system is market-intelligence tooling, not manipulation, biometric categorisation, emotion recognition, or criminal-risk scoring. That keeps it outside Article 5.
- It does not sit in an Annex III use case such as employment, education, credit, law enforcement, migration, or similar people-impacting decision support. The current output is sector-level research, not a decision about a natural person.
- It does not directly interact with natural persons as a chatbot or generate content that needs the Article 50 transparency disclosures for those use cases.

## 2. Role map

| Role | Current project role | Key point |
|---|---|---|
| Provider | This repo and its maintainer | Builds the pipeline and would place it into service |
| Deployer | The VC team using the briefs | Uses the output for internal research and filtering |
| Vendor | OpenAI, LangSmith | Third-party services used for brief generation and trace logging |

## 3. Conformity summary

No AI Act conformity assessment, CE marking, EU declaration of conformity, or registration is required for the current design. The project is not in a high-risk class, and it does not currently trigger the AI Act transparency duties that apply to chatbots, deepfakes, or similar direct-person interaction systems.

Internal controls still matter:
- keep the intended use narrow
- keep the scoring formula and prompt grounding documented
- keep a human in the loop before any external use
- keep trace logs for review

## 4. Technical documentation outline

If this ever needs a fuller compliance pack, document:
1. Purpose and intended users
2. Data sources and data minimisation choices
3. Cleaning, normalisation, and sector mapping rules
4. Feature engineering and scoring logic
5. LLM prompt, input schema, and output schema
6. Evaluation notes and known limitations
7. Human review steps and escalation path
8. Logging, monitoring, and change control
9. Security and access controls

## 5. Boundary note

If this system is later repurposed to score founders, applicants, customers, employees, or other natural persons, rerun the AI Act classification from scratch. That change could move it into Article 5, Article 50, or Annex III territory.
