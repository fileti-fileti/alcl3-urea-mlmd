# 0017. SDumont cost unit: UA from sacct
- Status: Accepted. Supersedes the SDumont cost unit of [0005](0005-cost-and-ask-first.md)
  (its ask-first limits stay as they are).
- Date: 2026-11-24. Decided by: owner (Eudes Fileti), proposed by the agent. Process: ADR-0013.

## Context
ADR-0005 left the SDumont cost unit as a TODO, so `cost_ledger.py` wrote `unknown` for
every SDumont job. LNCC bills an allocation in UA: 1 UA per CPU core-hour, 100 UA per
GPU-hour (LNCC manual §06, as quoted in Davi's HPC guide, 2026-10). `sacct` gives the
allocated CPUs (`AllocCPUS`) and GPUs (`AllocTRES`, e.g. `billing=12,cpu=12,gres/gpu=1,...`,
seen on this account's GPU jobs, 2026-11-24). The rule as quoted does not say whether the
CPU cores of a GPU job are billed on top of the GPU.

## Decision
- SDumont ledger unit: `UA` (`configs/machines/sdumont.yaml`, `cost.unit`).
- Cost = ElapsedRaw × (AllocCPUS + 100 × GPUs) / 3600, GPUs from the untyped `gres/gpu=N`
  entry of `AllocTRES` (typed `gres/gpu:<type>` entries ignored, so no double count).
- GPU jobs count cores and GPUs: an upper bound. With the project's GPU scheme (1 V100,
  `-c 6`) one day is 24 × 106 = 2544 UA, against 2400 if only the GPU is billed (+6 %).
  TODO(owner): does LNCC bill the CPU cores of a GPU job? (LNCC helpdesk or Davi.)
- A job that ran (ElapsedRaw > 0) with an empty `AllocTRES` gets `unknown`.
- The ledger columns do not change; the GPU count follows from cost, elapsed_s and
  alloc_cpus.

## Owner's approval and agent's check
- Owner, 2026-11-24: "Ok para A e B. Prossiga." (A = this decision.)
- Agent's justification: both rates come from the LNCC rule as quoted; counting cores and
  GPUs never under-states the cost of a job; the GPU count comes from accounting, not
  from the partition name.
- Check: `tests/test_cost_ledger.py` (CPU job = core-hours; GPU job = cores + 100 × GPUs;
  typed gres not double counted; empty `AllocTRES` → `unknown`); a dry run on a real GPU
  job of this account (11613155, outside the project) gives 165 s × 112 / 3600.

## Consequences
- New SDumont rows carry a cost in UA. Rows written before this ADR keep `unknown`
  (11758413): the ledger is append-only and `results/` is never hand-edited.
- `cost_ledger.py sum` reports UA and `unknown` separately; it never adds them.
- If LNCC bills only the GPU of a GPU job, a new ADR changes the formula; old rows keep
  the upper bound.
