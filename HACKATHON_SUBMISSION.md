# JAPAC AI Hackathon — Future of Work

## Project

**Relay AI: From work signals to evidence-backed, human-approved recovery**

**One-line pitch:** Relay is an AI-powered operational intelligence teammate that shows how a change in one part of a portfolio could disrupt other work, explains the evidence and trade-offs, and turns a chosen response into a human-approved, verifiable workflow.

## Submission abstract

Work is increasingly asynchronous and cross-functional, but delivery signals still live in separate emails, project plans, task trackers, and meeting notes. A small supplier delay or requirement change can silently block dependent work across teams. People must manually reconstruct the impact before deciding what to do, while a generic AI summary often stops before the decision and follow-through.

Relay AI connects those missing steps. A user submits a change signal; Relay retrieves relevant project evidence, uses Gemini for structured analysis, maps potential cross-project impact, and compares explicit what-if scenarios. Recommendations can be converted into recovery actions with the rationale, trade-offs, source references, and investigation ID attached. A human approves each action, and the prototype records simulated execution, verification, and an audit trail.

Relay's Future of Work idea is not to replace project judgment. It is to give distributed teams a shared, evidence-backed view of consequences and make the next responsible action easier to coordinate.

## Problem and opportunity

- Teams often discover dependencies only after a change has already become a blocker.
- Context is fragmented across status updates, evidence, task owners, and release dates.
- AI-generated advice can be difficult to trust when sources, uncertainty, and approval steps are hidden.
- Recommendations lose value when they are not connected to accountable follow-through.

## What is distinctive

1. **Portfolio-aware reasoning:** a signal in one project can surface possible downstream project and shared-resource impacts.
2. **Evidence before confidence:** retrieved evidence, contradiction checks, assumptions, and missing information are surfaced instead of presenting every inference as fact.
3. **Compare futures, not just summaries:** a transparent, rule-based simulator compares options and trade-offs.
4. **Human control by design:** a recommendation becomes a pending-approval action, followed by simulated execution, verification, and a persistent audit trail.
5. **One workflow for understanding and doing:** Ripple Intelligence, evidence retrieval, Relay Studio, and Recovery Actions form a connected operational workflow.

## Three-minute demonstration

**0:00–0:20 — Start from the portfolio.** Show project risk, planned release, and the selected project. Explain that the example workspace uses synthetic project data.

**0:20–1:10 — Introduce a signal.** Open Ripple Intelligence, load the demo vendor update (API delivery moved from October 10 to October 15), and analyze it. Highlight the change interpretation, impacted projects, retrieved evidence, and assumptions or missing information.

**1:10–1:40 — Compare choices.** Show “Do nothing,” “Parallelize eligible work,” and “Reduce critical-path scope.” Emphasize that the risk index and release dates are illustrative estimates, not calibrated probabilities.

**1:40–2:40 — Go from advice to accountable work.** Choose “Send to Recovery Actions” on a recommendation. In Recovery Actions, show it begins in Pending approval, approve it, run the simulation, verify the result, and open the audit trail.

**2:40–3:00 — Close with the value.** Relay reduces the manual work of connecting a change to downstream impact and a reviewable recovery plan, while keeping evidence, assumptions, and human approval visible.

**Optional second showcase:** Relay Studio turns text, images, or audio into schema-validated structured previews for Jira, Confluence, or Slack. These destinations are previews, not live external writes.

## Responsible AI and prototype boundaries

- Gemini provides structured analysis; retrieval, project context, workflow transitions, and audit persistence are handled by application code.
- Scenario calculations are transparent and illustrative. They are not statistically calibrated forecasts.
- Jira/Confluence integrations and recovery execution are synthetic or simulated in this build.
- Gmail OAuth/sync is disabled in public-demo mode and should only be enabled on a private deployment.
- The guest screen is not server-side authentication. The public demo uses a shared synthetic workspace; confidential data must not be entered.
- A production rollout would require authenticated identities, authorization, tenant/data isolation, managed rate limiting, connector governance, retention controls, and evaluations against historical outcomes.

## Impact measures to validate next

No impact numbers are claimed yet. A pilot should measure:
- Time from receiving a change signal to producing a reviewed impact assessment.
- Time from identifying a risk to assigning an owner and approved recovery action.
- Share of recommendations with traceable evidence and explicit human decisions.
- Percentage of actions verified and whether recorded outcomes improve future recommendations.
- False-positive cross-project impacts and user override rates.

## Before submitting

- [ ] Paste the deployed demo URL and confirm the backend health endpoint is reachable.
- [ ] Attach a 2–3 minute screen recording following the script above.
- [ ] Add the participant/team details requested by the official form.
- [ ] Confirm the event's current submission format, rules, and deadline in the organizer portal.
- [ ] Ensure public-demo mode is enabled and Gmail remains disabled in the public deployment.
- [ ] Rehearse the approval/verification flow once against a fresh demo state.
