# INC-YYYY-NNN: <Title>

| Field | Value |
|-------|-------|
| **Status** | Resolved |
| **Severity** | SEV-1 / SEV-2 / SEV-3 |
| **Date** | YYYY-MM-DD |
| **Duration** | <detection → resolution> |
| **Services** | api / auth / worker |
| **Authors** | <name> |
| **Reproduce** | `<chaos command(s)>` |

## Summary
One paragraph: what happened, the impact, and how it was resolved. Written so
someone unfamiliar with the incident understands it in 30 seconds.

## Timeline
All times UTC. Reference the concrete signal at each step (alert, metric, log).

| Time | Event |
|------|-------|
| HH:MM | ... |

## Customer impact
What users experienced and the rough scope/duration.

## Root cause
The single underlying cause. Blameless: describe the system condition.

## Contributing factors
Conditions that made the incident more likely, larger, or longer.

## Detection
Which alert/dashboard surfaced it, and how long detection took.

## Resolution
The manual operator steps taken to mitigate and resolve. No automated
remediation.

## Lessons learned
What went well, what went poorly, where we got lucky.

## Preventive actions
| Action | Type | Owner | Status |
|--------|------|-------|--------|
| ... | prevent / detect / mitigate | <team> | TODO |
