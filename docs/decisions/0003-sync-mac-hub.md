# 0003. Sync through the Mac hub with bare repos
- Status: Superseded by [0012](0012-github-origin-and-sdumont-locations.md)
- Date: 2026-11-13. Decided by: owner (Eudes Fileti). Process: infrastructure (approval).

## Context
The neumann and SDumont VPNs are mutually exclusive, so the servers never see each other.
The owner's GitHub account is currently inaccessible. Both servers reach github.com over
HTTPS and ssh (ports 22 and 443), so a private remote stays possible later.

## Decision
- On each server: a bare repo `~/git/<repo>.git` (the clone's `origin`) plus a work clone.
- On the Mac: a clone with remotes `neumann` and `sdumont` over ssh. The Mac moves commits
  between them: connect VPN A, `git pull A main`; switch to VPN B, `git push B main`.
- Bare repos refuse history rewrites and branch deletion:
  `receive.denyNonFastForwards true`, `receive.denyDeletes true`.
- `/start-session` pulls; `/end-session` pushes to `origin`.
- A private GitHub remote may be added later via a new ADR.

## Owner's approval and agent's check
Approved by the owner. Agent's justification: does not depend on the GitHub account; a bare
repo means a push never touches files being edited (`receive.denyCurrentBranch updateInstead`
fails when the target clone is dirty).

## Consequences
- Cross-machine divergence is only visible on the Mac; the status block's per-machine
  "last sync" lines are what a server session can check.
- If both servers commit between syncs, the Mac merges and pushes the merge to both.
- Pushing to a server's `origin` and syncing through the Mac are separate steps; the
  journal records which machine a sync came from.
