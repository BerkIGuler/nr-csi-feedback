---
status: draft
---

# Architecture layers

This document is the placement guide for new code. There is **no frozen directory tree**. Files and class names may change. **Import direction and responsibility** must follow the layers below.

When adding a feature, decide the layer first, then decide whether it is a new module, a type, a function, or a method. Do not put L3 selection logic in L5, or L1 tables inside L4 orchestration.

Product constraints (conditioning order, separate CRI/RI/PMI/CQI/LI, tables as fixtures) are in `docs/design/requirements.md` §9. This file is how those constraints sit in the codebase.

## Dependency rule

Layer \(N\) **may** use layers \(0 \ldots N-1\). It **must not** import or call layers \(> N\).

Siblings in the same layer **must not** reach into each other’s internals (especially L3 selectors). They may share L0–L2 only.

## Numerics and indices

These conventions are part of L0/L2. Do not transpose “to match a paper” inside a selector.

- **\(H\)** has shape \((N_r, P)\): rows = receive antennas, columns = CSI-RS ports. dtype `complex128` unless a caller documents otherwise.
- **\(W\)** has shape \((P, \nu)\): rows = ports, columns = layers. LI is the **0-based column** index of \(W\).
- **CSI integers** (CRI, RI, PMI, CQI, LI) are **0-based** in code. Spec prose that says “first resource” or “layer 1” maps to index `0`. Rank \(\nu\) is the integer layer count (1 or 2 in M1), not an index into a list of ranks.
- **\(\sigma^2\)** is a real scalar: noise variance per receive antenna (same SNR definition as `docs/design/requirements.md` FR-21). Not a covariance matrix until M7.
- A vector \(x\) of \(\nu\) unit-power symbols is a column of length \(\nu\). Do not silently conjugate-transpose \(H\) or \(W\) to make shapes multiply.

## RNG

The requirement is NFR-7 in `docs/design/requirements.md` (explicit `Generator`; no global `numpy.random.*`). This section is only **how it is threaded**:

- L5 (and notebooks) **construct** the generator (`np.random.default_rng(seed)`) and **pass it down**.
- L2 channel draws **accept** that generator; they do not create a hidden one.
- L0 may wrap construction so callers do not touch the global module.
- L3/L4 are deterministic given \(H\), \(\sigma^2\), and config. They **must not** draw random numbers.

## Layers

| Layer | Name | Owns | Does not own |
| --- | --- | --- | --- |
| **L0** | Primitives | CSI-agnostic helpers: errors, seeded RNG adapters, small numeric utilities, validation of shapes/dtypes | 3GPP tables, \(H\), CSI field selection, Monte Carlo |
| **L1** | Spec artifacts | Codebooks, CQI tables, SINR-threshold tables: data, lookup, enumeration, cited clause | Channel math, PMI search, report assembly |
| **L2** | Observation and metrics | Channel draws (and later grids / estimators), SNR definition, equalizer, post-eq SINR, MI / RSRP / capacity **metrics** | Choosing CRI/RI/PMI/CQI/LI, packing a CSI report, campaign loops |
| **L3** | CSI selection | One algorithm per quantity: CRI, RI, PMI, CQI, LI, in spec order when composed | Inventing codebook matrices, drawing \(H\), iterating SNR grids |
| **L4** | Public CSI API | Configuration, report object, orchestration that calls L3 in order and returns the five fields plus realized \(W\) | Reimplementing selectors, plotting, multi-realization loops |
| **L5** | Experiments | Monte Carlo, examples, notebooks, saved PMFs / sweeps | CSI algorithms, spec tables |

M1 uses all six layers in thin form: L2 is Rayleigh + AWGN + MMSE SINR; L3 CRI is the single-resource index; L5 is a small harness. Later milestones thicken a layer (M2: L3 CRI; M6: L2 estimator) without jumping logic upward or downward.

**Who imports L3.** Tests **may** import L3 selectors directly (FR-15: isolated oracles). Notebooks, examples, and L5 **must** go through L4. L3 is not a stability promise for 1.0; L4 is the caller API.

## Where does a change go?

Answer in order. Stop at the first yes.

1. **Is it a 3GPP literal or enumeration of literals?** → L1. New codebook family = new L1 module, not a method on the report type.
2. **Is it CSI-agnostic plumbing (RNG, errors, array checks)?** → L0. Prefer a function; a type only if callers need to pass a policy (e.g. a generator).
3. **Is it “given \(H, W, \sigma^2\), a number” (SINR, MI, RSRP)?** → L2 metric. New metric = new L2 callable (or strategy object) that L3 can select by name. Not a branch inside CQI.
4. **Is it “given observation + config, one CSI field”?** → L3. Same quantity = extend that selector (new strategy, extra rank). New quantity = new L3 module, then L4 orchestration.
5. **Is it wiring fields together or the objects a caller imports for one snapshot?** → L4. Keep this thin. New report fields at L4 only after L3 can compute them.
6. **Is it many realizations, plots, or a script a human runs?** → L5. L5 **must** call L4 for CSI, not reimplement L3.

**New module vs method**

- **Method / function on an existing type** if the behavior is a variation of that type’s job (another PMI metric, another rank in the same codebook enumerator).
- **New module in the same layer** if the job is a new artifact or quantity (Type I 8-port codebook at L1; CSI-IM covariance at L2; CRI over a resource set still L3 CRI, not a new L4 API unless the report shape changes).
- **Do not** add a sibling L3 selector that another L3 file imports. Compose only in L4.
- **Do not** grow L4 into a god module. If orchestration needs a helper that is not CSI selection, that helper is L0 or L2.

## Examples

| Change | Layer | Shape |
| --- | --- | --- |
| Type I 2-port matrices from Table 5.2.2.2.1-1 | L1 | Module (data + enumerator) |
| CQI table1 efficiencies | L1 | Module / fixture |
| i.i.d. Rayleigh snapshot | L2 | Channel generator |
| MMSE post-eq SINR | L2 | Function or small type |
| Swap RI metric (MI vs sum-rate) | L2 metric + L3 RI | Named strategy; RI stays L3 |
| Single-resource CRI | L3 | Function; later resource-set CRI extends this, still L3 |
| One-snapshot CSI computation | L4 | Orchestration only |
| SNR sweep PMFs | L5 | Harness consuming L4 |

## Out of scope here

- Branch / commit / PR process and M0 seed — `.cursor/engineering-conventions.md`
- FR/NFR text — `docs/design/requirements.md`
- One-home rule — `.cursor/rules/single-home.mdc`
