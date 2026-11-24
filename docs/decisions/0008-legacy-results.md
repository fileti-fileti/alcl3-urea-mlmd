# 0008. Legacy work stays in place; registered as legacy-*
- Status: Accepted
- Date: 2026-11-13. Decided by: owner (Eudes Fileti). Process: infrastructure (approval).

## Decision
Existing work directories stay where they are, read-only. Results the owner selects enter a
project repo through `scripts/register_result.py` under a `legacy-*` name, with provenance,
without rewriting anything. No new claim from them without a reading rule fixed first. The
template ships the mechanism only; no legacy data.

## Owner's approval and agent's check
Approved by the owner. Agent's justification: registration gives checksums and provenance
without moving or editing the originals.

## Consequences
None in the template beyond the `legacy-*` naming rule.
