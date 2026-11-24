# 0004. Repo locations and large-storage symlinks
- Status: Accepted for neumann; bare-repo clause and SDumont part superseded by
  [0012](0012-github-origin-and-sdumont-locations.md).
- Date: 2026-11-13. Decided by: owner (Eudes Fileti). Process: infrastructure (approval).

## Context
Data and run outputs must stay out of git and must be reachable from compute nodes.
neumann: `/home` is NFS-exported to the nodes and not purged; `/scratch` exists only on the
headnode. SDumont: `$HOME=/prj/acmes/eudes.fileti3` (NFS); `/scratch` is Lustre with an
unknown purge rule.

## Decision
- neumann: repos in `~/<repo>` (e.g. `~/lab-template`, `~/sandbox`); bare repos in `~/git/`.
- Project repos: `data`, `runs`, `logs` are gitignored symlinks to a store outside the repo.
  Sandbox store on neumann: `~/sandbox-store/`.
- SDumont: proposed store `/scratch/acmes/eudes.fileti3/projects/sandbox-store/`; repo
  location TODO(owner), decided after the purge rule is known.
- Machine facts (paths, partitions, modules, envs, cost unit) live in
  `configs/machines/<machine>.yaml`, validated with unknown keys rejected.

## Owner's approval and agent's check
Approved by the owner for neumann. Agent's justification: symlinks keep existing data in
place and keep the watcher and git away from large trees; `/home` on neumann is the only
filesystem the nodes see.

## Consequences
- The `.gitignore` uses `/data`, `/runs`, `/logs` without a trailing slash so symlinks are
  ignored too.
- TODO(owner): SDumont purge rule and repo location (helpdesk-sdumont@lncc.br if needed).
