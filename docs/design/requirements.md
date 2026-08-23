# nr-csi-feedback — Requirements


| Field          | Value                                                                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Document       | Product requirements                                                                                                                                                     |
| Package        | `nr-csi-feedback`                                                                                                                                                        |
| Remote         | `git@github.com:BerkIGuler/nr-csi-feedback.git`                                                                                                                          |
| Status         | Draft                                                                                                                                                                    |
| Audience       | Maintainers of this research-oriented CSI-feedback exploration package                                                                                                   |
| Companion docs | Layers: `docs/design/layers.md`. Process: `.cursor/engineering-conventions.md`. Homes: `.cursor/rules/single-home.mdc`. This file is the product contract. |


The keywords **must**, **should**, and **may** are used as in RFC 2119.

---



## 1. Purpose

`nr-csi-feedback` is a small, research-oriented Python package that **computes a 5G NR CSI report** from a simulated downlink channel.

A CSI report in this project carries five quantities:


| Quantity | Name                       | Role in the report                                           |
| -------- | -------------------------- | ------------------------------------------------------------ |
| **CRI**  | CSI-RS Resource Indicator  | Which configured NZP-CSI-RS resource the UE prefers          |
| **RI**   | Rank Indicator             | How many transmission layers the UE recommends               |
| **PMI**  | Precoding Matrix Indicator | Which codebook precoder the UE recommends for those layers   |
| **CQI**  | Channel Quality Indicator  | Highest MCS the UE expects to decode at the target BLER      |
| **LI**   | Layer Indicator            | Which column of the reported precoder is the strongest layer |


The package exists to make these quantities **computable, inspectable, and statistically characterizable**. It is not a gNB, a UE stack, or a 3GPP conformance suite.

The design rule is: **start with the smallest scenario that still produces a complete five-field report, then grow one capability per milestone.**

---



## 2. Goals and non-goals



### 2.1 Goals

1. Provide a readable implementation of CSI selection algorithms for CRI, RI, PMI, CQI, and LI.
2. Provide a Monte Carlo simulation harness so empirical distributions of those quantities versus SNR, rank, and channel model can be collected.
3. Keep every algorithm's inputs, outputs, 3GPP clause, and documented simplifications explicit.
4. Grow the package behind a small, stable public CSI API (configuration, report, codebook, channel) so later milestones do not rewrite the first one. See `docs/design/layers.md` L4.
5. Follow ordinary software-engineering practice: tests, typed APIs, documented assumptions, reproducible RNG, versioned releases.



### 2.2 Non-goals (all currently planned releases)

The package **must not** attempt (at least for now):

- A full NR PHY (PDSCH, PDCCH, PUCCH, PUSCH, HARQ, UCI bit packing, CRC, polar/LDPC encoding).
- RRC / ASN.1 `CSI-ReportConfig` parsing, MAC CE triggering, or slot-accurate periodic / semi-persistent / aperiodic reporting.
- A production-grade 3GPP link-level simulator (Vienna, Sionna, MATLAB 5G Toolbox, ns-3). Those may be used later as *oracles*, not as dependencies.
- Multi-cell, multi-UE scheduling, MU-MIMO pairing, or beam management procedures beyond CRI selection among a configured resource set.
- SSB-based reports (`ssb-Index-RSRP`, `ssb-Index-SINR`) or L1-RSRP / L1-SINR report quantities. Those are related CSI quantities, not the five fields of this product.
- Real-time or on-device UE firmware constraints.

A later milestone **may** add a thin UCI payload view (bit widths from TS 38.212) as an optional overlay. That overlay is not required for a correct *numerical* CSI report.

---



## 3. Fidelity layers

3GPP does not prescribe a unique UE algorithm. It specifies:

- which quantities are reported,
- how they are conditioned on each other,
- which codebook matrices exist,
- and the CQI definition (highest index whose PDSCH would meet a BLER target on the CSI reference resource).

This package therefore has two fidelity layers. Every public algorithm **must** declare which layer it implements.


| Layer             | Meaning                                                                                            | Used when                                                                                                                                  |
| ----------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Exploratory**   | A documented, simplified estimator that produces the same *kind* of integer report a UE would send | Default for v0.x. Example: map post-equalization SINR to CQI through a published threshold table instead of running a PDSCH BLER campaign. |
| **Spec-faithful** | Matches a cited 3GPP table or procedure with no extra approximation beyond numerical precision     | Codebook matrices, CQI MCS tables, conditioning order, LI definition                                                                       |


Simplifications **must** be listed next to the algorithm, not hidden in comments. It **must** be possible to answer: *what did we compute, which clause is it from, and what did we skip?*

---



## 4. System context

```text
                    configured NZP-CSI-RS resource(s)
                                |
                                v
   gNB (simulated)  --CSI-RS-->  channel H  --y-->  UE CSI engine
                                                       |
                                                       |  CRI -> RI -> PMI -> CQI -> LI
                                                       v
                                                  CSI report
                                                       |
                                                       v
                                          Monte Carlo / notebooks / tests
```

There is no uplink in v0.x. The "UE" maps a channel (and noise / interference) to a CSI report. The "gNB" is a configuration plus, later, a set of CSI-RS resources (beams).

The report quantity for the product is:

```text
reportQuantity = cri-RI-LI-PMI-CQI
```

That is the 3GPP quantity that contains all five fields this package exists to compute (TS 38.214 / TS 38.331).

---



## 5. CSI quantities

Normative conditioning is from TS 38.214 clause 5.2.1.4. Implementations **must** compute fields in this order. A field **must not** be chosen using a later field.

```text
CRI  ->  RI | CRI  ->  PMI | (RI, CRI)  ->  CQI | (PMI, RI, CRI)  ->  LI | (CQI, PMI, RI, CRI)
```



### 5.1 CRI — CSI-RS Resource Indicator

CRI is the index of the preferred NZP-CSI-RS resource in the CSI-RS resource set used for channel measurement.

- When the resource set contains **one** resource, CRI is `0` and is still present in the report object.
- When the resource set contains **several** resources (typically analog / digital beams), CRI is the resource that maximizes a documented selection metric (received power or post-combining capacity). Remaining fields are then computed on the channel of that resource only.
- CRI is not reported in the spec when CSI-RS `repetition` is `'on'`. This package **must** still expose CRI on the report object; the configuration **may** mark it as `not_reported` in a later milestone. The first release treats it as always reported.



### 5.2 RI — Rank Indicator

RI is the recommended number of PDSCH layers \nu.

- For the first scenario (2 CSI-RS ports), \nu \in 1, 2.
- RI **must** be chosen from the ranks allowed by the codebook and by an optional rank restriction bitmap (default: all ranks allowed).
- The exploratory default metric is: pick the rank whose selected precoder yields the highest estimated spectral efficiency (sum of layer rates after CQI mapping, or a capacity proxy — the metric **must** be a named, swappable strategy).



### 5.3 PMI — Precoding Matrix Indicator

PMI is the codebook index (or index tuple) of the recommended precoder W of size P_{\text{CSI-RS}} \times \nu.

The first codebook **must** be **Type I Single-Panel, 2 antenna ports**, TS 38.214 Table 5.2.2.2.1-1:


| Codebook index | 1 layer \nu=1                                     | 2 layers \nu=2                                 |
| -------------- | ------------------------------------------------- | ---------------------------------------------- |
| 0              | \frac{1}{\sqrt{2}}\begin{bmatrix}11\end{bmatrix}  | \frac{1}{2}\begin{bmatrix}1&11&-1\end{bmatrix} |
| 1              | \frac{1}{\sqrt{2}}\begin{bmatrix}1-1\end{bmatrix} | \frac{1}{2}\begin{bmatrix}1&1j&-j\end{bmatrix} |
| 2              | \frac{1}{\sqrt{2}}\begin{bmatrix}1j\end{bmatrix}  | —                                              |
| 3              | \frac{1}{\sqrt{2}}\begin{bmatrix}1-j\end{bmatrix} | —                                              |


Exploratory PMI selection: exhaustive search over the allowed codebook entries for the candidate rank; pick the entry that maximizes a documented metric (default: mean post-equalization SINR or mutual information). For two ports this search is tiny and exact.

Later codebooks (4–32 ports, Type I Multi-Panel, Type II) **must** plug into the same PMI selection path and **must not** change the five report quantities. For P>2, PMI **should** be the 3GPP index tuple (i_1, i_2) plus the realized matrix W.

### 5.4 CQI — Channel Quality Indicator

CQI is a 4-bit index 0,\ldots,15. Index 0 means out of range.

The spec definition (TS 38.214 clause 5.2.2.1): the UE reports the **highest** CQI index such that a single PDSCH transport block on the CSI reference resource, using the modulation and target code rate of that index, would be received with transport-block error probability not exceeding:

- 0.1 for `cqi-Table = table1` or `table2`
- 10^{-5} for `cqi-Table = table3`

The first release **must** implement `table1` (TS 38.214 Table 5.2.2.1-2):


| CQI | Modulation   | Code rate × 1024 | Efficiency (bits/RE) |
| --- | ------------ | ---------------- | -------------------- |
| 0   | out of range | —                | —                    |
| 1   | QPSK         | 78               | 0.1523               |
| 2   | QPSK         | 120              | 0.2344               |
| 3   | QPSK         | 193              | 0.3770               |
| 4   | QPSK         | 308              | 0.6016               |
| 5   | QPSK         | 449              | 0.8770               |
| 6   | QPSK         | 602              | 1.1758               |
| 7   | 16QAM        | 378              | 1.4766               |
| 8   | 16QAM        | 490              | 1.9141               |
| 9   | 16QAM        | 616              | 2.4063               |
| 10  | 64QAM        | 466              | 2.7305               |
| 11  | 64QAM        | 567              | 3.3223               |
| 12  | 64QAM        | 666              | 3.9023               |
| 13  | 64QAM        | 772              | 4.5234               |
| 14  | 64QAM        | 873              | 5.1152               |
| 15  | 64QAM        | 948              | 5.5547               |


**Exploratory mapping (required for v0.1):** map the effective post-equalization SINR of the reported PMI/RI to the highest CQI whose documented SINR threshold is not exceeded. The threshold table is a versioned, cited L1 artifact. It is **not** claimed to be a measured NR BLER curve.

**Spec-faithful mapping (later, optional):** replace the lookup with a CSI-reference-resource BLER model. CQI mapping **must** be replaceable without changing how a caller requests CQI (FR-16).

Wideband CQI only in the first releases. One codeword only (\nu \le 4). Subband differential CQI is out of scope until the subband milestone.

### 5.5 LI — Layer Indicator

From TS 38.214 clause 5.2.1.4.2:

> The LI indicates which column of the precoder matrix of the reported PMI corresponds to the strongest layer of the codeword corresponding to the largest reported wideband CQI. If two wideband CQIs are reported and have equal value, the LI corresponds to the strongest layer of the first codeword.

Exploratory definition of "strongest": largest post-equalization SINR (or largest layer power) among the columns of W. For rank 1, LI is `0`. For the first scenario there is a single codeword, so the two-CQI tie rule does not apply yet; the implementation **must** still follow the spec wording so two-codeword reports later do not change what LI means.

---



## 6. Baseline scenario (first working CSI report)

This is the smallest complete product. Every later milestone is a controlled relaxation of one bullet.


| Axis                  | Baseline value                                               | Why it is first                              |
| --------------------- | ------------------------------------------------------------ | -------------------------------------------- |
| CSI-RS ports P        | 2                                                            | Smallest Type I codebook (Table 5.2.2.2.1-1) |
| Receive antennas N_r  | 2                                                            | 2×2 MIMO; rank 1 and 2 are both meaningful   |
| Codebook              | Type I Single-Panel, 2-port                                  | Finite, fully enumerable PMI                 |
| Frequency granularity | One wideband channel matrix                                  | No OFDM grid yet                             |
| Time                  | One snapshot                                                 | No Doppler, no slot timeline                 |
| Channel knowledge     | Perfect (true H)                                             | Algorithms before estimators                 |
| Channel law           | i.i.d. Rayleigh, single tap (H shape: `docs/design/layers.md` Numerics) | Closed-form, easy tests                      |
| Interference          | AWGN only                                                    | No CSI-IM                                    |
| CSI-RS resources      | 1                                                            | CRI is trivially 0, but the field exists     |
| Report quantity       | `cri-RI-LI-PMI-CQI`                                          | All five fields                              |
| CQI table             | `table1`                                                     | Standard 10% BLER table                      |
| CQI / PMI format      | widebandCQI, widebandPMI                                     | Matches the single-matrix model              |
| Equalizer model       | MMSE on HW, noise variance known                             | Standard baseline receiver                   |
| Users / cells         | 1 UE, 1 gNB, SU-MIMO                                         | No scheduler                                 |


Given a channel snapshot, a noise level, and a CSI configuration, the baseline **must** return a complete five-field report. The report **must** include CRI, RI, PMI, CQI, LI, the realized precoder used for CQI/LI, and optional diagnostics (per-layer SINR, selected metric values) that are not required to interpret the five quantities. The one-snapshot call is L4 (`docs/design/layers.md`); this document does not freeze its Python name.

A Monte Carlo driver **must** draw many independent channels, compute a report for each, and return sample statistics (histograms / PMFs of CQI, RI, PMI, CRI, LI versus SNR).

---



## 7. Functional requirements

Identifiers are stable. New work **should** add requirements rather than silently reuse these numbers.

These statements are capabilities. How to write them: `.cursor/rules/functional-requirements.mdc`.

### 7.1 Report and configuration


| ID   | Requirement                                                                                                                                                         |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-1 | The package **must** produce a CSI report containing CRI, RI, PMI, CQI, and LI for the configured report quantity.                                                  |
| FR-2 | The realized precoder used to obtain CQI and LI **must** be available alongside the PMI index, so the matrix can be inspected, not only the index.                  |
| FR-3 | The user **must** be able to choose codebook family, CQI table, allowed ranks, number of NZP-CSI-RS resources, and the selection metrics for CRI, RI, and PMI.      |
| FR-4 | Combinations that the codebook or CQI table forbid (rank above port count, PMI not in the codebook, CQI outside 0–15) **must** be rejected with an explicit error.  |
| FR-5 | Fields **must** be determined in the TS 38.214 order of §5: CRI, then RI, then PMI, then CQI, then LI. A later field **must not** be used to choose an earlier one. |




### 7.2 Algorithms


| ID    | Requirement                                                                                                                                                           |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-10 | The package **must** select CRI among the configured channel-measurement resources. With a single resource, the reported CRI **must** be that resource’s index.       |
| FR-11 | For the baseline codebook, PMI **must** be chosen by searching the allowed Type I 2-port entries at the selected rank.                                                |
| FR-12 | RI **must** be chosen among allowed ranks by comparing each rank’s selected precoder under a documented efficiency metric.                                            |
| FR-13 | CQI **must** be the highest index of TS 38.214 Table 5.2.2.1-2 whose documented SINR threshold is met by the effective post-equalization SINR of the reported PMI/RI. |
| FR-14 | LI **must** identify the strongest layer of the reported precoder, as defined in §5.5.                                                                                |
| FR-15 | CRI, RI, PMI, CQI, and LI selection **must** each be testable in isolation (no Monte Carlo required).                                                                 |
| FR-16 | The metrics used for CRI, RI, and PMI **must** be replaceable without changing the meaning or contents of the five report quantities.                                 |




### 7.3 Channel and simulation


| ID    | Requirement                                                                                                                                                       |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-20 | The baseline **must** draw i.i.d. Rayleigh (circularly symmetric complex Gaussian) channel snapshots under a seeded RNG.                                          |
| FR-21 | SNR **must** have a single documented definition, used everywhere statistics are reported.                                                                        |
| FR-22 | Monte Carlo results **must** be reproducible from a documented set of run controls (seed, number of draws, SNR points, and CSI configuration).                    |
| FR-23 | A campaign **must** record CRI, RI, PMI, CQI, and LI per realization so empirical PMFs and SNR sweeps can be produced from saved output.                          |
| FR-24 | The baseline **must** compute the report from perfect channel knowledge. A later release **must** be able to substitute a CSI-RS estimator without changing FR-1. |


Recommended SNR definition until an architecture note supersedes it: average SNR per receive antenna per RE, \mathbb{E}[|H F x|^2]/\sigma^2, with unit-power symbols and the CSI-RS / identity analog beam F.

### 7.4 Codebooks and tables


| ID    | Requirement                                                                                                                                           |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-30 | Type I 2-port precoders **must** match TS 38.214 Table 5.2.2.2.1-1 to numerical precision.                                                            |
| FR-31 | CQI modulation, code rate, and efficiency **must** match Table 5.2.2.1-2.                                                                             |
| FR-32 | The baseline **may** allow every codebook entry. Restricting the allowed subset **must** be possible later without replacing the codebook definition. |


---



## 8. Non-functional requirements


| ID     | Requirement                                                                                                                                                                                |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| NFR-1  | Implementation language is **Python 3.11+**. Core numerics use NumPy. No GPU requirement.                                                                                                  |
| NFR-2  | The installable distribution name is `nr-csi-feedback`. The import package is `nr_csi_feedback`.                                                                                           |
| NFR-3  | Public functions **must** have type hints and a docstring that states spec clause, fidelity layer, and simplifications.                                                                    |
| NFR-4  | Unit tests **must** exercise every public entry point and **must** include oracles for the M1 capabilities in §7, as listed in §8.1. Line coverage of private helpers is not the bar.     |
| NFR-5  | Continuous integration (CI) **must** run the unit tests and a tiny Monte Carlo SNR sweep (few realizations) so a broken statistics path fails the pull request.                            |
| NFR-6  | Releases use semantic versioning. `0.y.z` is the exploratory baseline lineage. `1.0.0` requires the milestone set in §10 to be complete and the public API to be documented as stable.     |
| NFR-7  | Randomness **must** go through an explicit generator (`numpy.random.Generator`). Global `numpy.random.`* **must not** be used in library code.                                             |
| NFR-8  | The repository **must** remain usable without MATLAB, Sionna, or a 3GPP spec PDF in the tree. Spec tables that we re-encode **must** cite the clause in comments or module docs.           |
| NFR-9  | Default examples **must** finish on a laptop in seconds, not minutes. Heavy campaigns belong in optional scripts.                                                                          |
| NFR-10 | Process conventions (branches, commits, PRs, M0 seed) live in `.cursor/engineering-conventions.md`. Code placement lives in `docs/design/layers.md`. This file does not replace them. |
| NFR-11 | Long Monte Carlo campaigns and qualitative SNR-curve shape **must not** be unit-test gates. Those belong in §11 acceptance or optional scripts.                                            |


### 8.1 Unit-test oracles (M1)

NFR-4 is satisfied when all of the following have tests. §11 may repeat a subset as product acceptance; this list is the completeness bar.

| Oracle class | What must fail if it is wrong |
| --- | --- |
| Public surface | Every public entry point is imported and called (report, configuration, CSI computation, codebook access, CQI table, channel draw, Monte Carlo runner). |
| Spec tables | Type I 2-port precoders match Table 5.2.2.2.1-1 (shape, scale, all six entries). CQI Table 5.2.2.1-2 matches modulation, code rate, and efficiency; index 0 is out of range. Exploratory SINR thresholds are monotonic and used by CQI mapping. |
| Isolated selectors | CRI, RI, PMI, CQI, and LI each have tests that do not run Monte Carlo (FR-15). Single-resource CRI is that resource’s index. Rank restriction is respected. Rank-1 LI is 0. Rank-2 LI is the stronger layer. CQI boundaries (low / threshold / high SINR) map to the expected index. |
| Conditioning | Fields are determined CRI → RI → PMI → CQI → LI. A later field is not used to choose an earlier one. The realized precoder is the codebook entry for the reported PMI and rank. |
| Forbidden inputs | Rank above port count, PMI not in the codebook, and CQI outside 0–15 are rejected with an explicit error. |
| Goldens | At least one documented 2×2 channel (fixed \(H\), fixed noise) produces a known PMI/RI/CQI (and consistent LI). Additional constructed channels **should** cover rank-1 alignment, high-SNR rank 2, and very low SINR. |
| Channel and harness | Seeded channel draws are reproducible. A campaign records CRI, RI, PMI, CQI, and LI per realization. The same run controls reproduce the same reports. |
| Contract | Public callables carry the NFR-3 docstring fields. NFR-7 holds (RNG home: NFR-7; threading: `docs/design/layers.md`). |

M2+ **must** add oracles for the new capability of that milestone (for example non-trivial CRI when the resource set grows) rather than weakening this list.


---



## 9. Architectural constraints (product-level)

Code **placement** (which layer, new module vs method) lives in `docs/design/layers.md`. This section only constrains **responsibilities**. It does not freeze a directory tree.

1. **One responsibility per CSI selector.** CRI, RI, PMI, CQI, and LI are separate algorithms. The report assembler (L4) calls them in spec order. Selectors **must not** reach into each other’s internals.
2. **Codebooks are data plus an enumerator** (L1), not a place for channel math.
3. **Channels produce \(H\)** (and later grids of \(H\)) at L2. They do not compute PMI.
4. **Simulation drivers (L5) consume** the public CSI API (L4). They do not reimplement selection.
5. **3GPP tables are fixtures** (L1), tested against literals from the spec, not regenerated ad hoc inside algorithms.
6. **Public API stays small** (L4). First public surface: configuration, report, one-snapshot CSI computation, codebook accessors, channel generators, Monte Carlo runner.

---



## 10. Milestones and releases

Each milestone **must** ship: code, tests, and a short changelog note of what became possible. A milestone **must not** expand two independent axes at once (for example: subband *and* Type II in the same release).


| Milestone                               | Version target | What becomes true                                                                                             | Still out                           |
| --------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| **M0 — Foundation**                     | `0.0.1`        | Installable package per M0 seed (`.cursor/engineering-conventions.md`); empty public types; this document in-tree | No algorithms                       |
| **M1 — Baseline report**                | `0.1.0`        | §6 scenario. All five fields. Type I 2-port. Rayleigh snapshot. SINR→CQI lookup. Monte Carlo PMFs vs SNR      | OFDM, estimation, multiple CSI-RS   |
| **M2 — CRI over a resource set**        | `0.2.0`        | K>1 CSI-RS resources (discrete analog beams). Non-trivial CRI. Other fields conditioned on the winner         | Time-varying beams, SSB             |
| **M3 — Frequency-selective wideband**   | `0.3.0`        | Multi-tap or per-RB H_f. Wideband PMI/CQI from a documented average (mean MI or mean MMSE-SINR over the band) | Subband reports                     |
| **M4 — Subband PMI/CQI**                | `0.4.0`        | Wideband i_1 + per-subband i_2 for P>2; for 2-port, per-subband PMI as in the spec. Subband CQI optional      | Type II                             |
| **M5 — Type I Single-Panel, P \in 4,8** | `0.5.0`        | n_1,n_2, codebook mode 1, PMI as (i_1,i_2). Rank up to \min(P,N_r,8) as allowed                               | Multi-panel, Type II                |
| **M6 — Imperfect CSI**                  | `0.6.0`        | LS or MMSE estimate from a simple NZP-CSI-RS model; reports run on \hat{H}                                    | Full TS 38.211 mapping              |
| **M7 — Interference**                   | `0.7.0`        | CSI-IM or noise+interference covariance in the MMSE SINR                                                      | Multi-cell geometry                 |
| **M8 — First stable public API**        | `1.0.0`        | M1–M5 documented as stable. Examples for the baseline and one P=8 Type I case. Fidelity notes complete        | Type II, UCI packing, BLER-true CQI |


M8 is the first **stable** release. Type II, enhanced Type II, two-codeword CQI (\nu>4), and UCI bit packing are **post-1.0**.

M0 is scaffolding only. M1 is the first release that computes a CSI report. **No feature work from M2+ may land before M1 is test-complete.**

---



## 11. Acceptance for M1 (`0.1.0`)

M1 is accepted when all of the following hold:

1. One-snapshot CSI computation (L4) returns all five fields on the baseline scenario.
2. With a single CSI-RS resource, `cri == 0` for every realization.
3. For a rank-1 reported PMI, `li == 0`.
4. Codebook unit tests compare `W` to the six matrices of Table 5.2.2.2.1-1.
5. A documented 2×2 channel (fixed H, fixed \sigma^2) produces a PMI/RI/CQI golden vector checked in CI.
6. An SNR sweep of Rayleigh snapshots shows the qualitative behaviour expected in a rich 2×2 channel: mean CQI non-decreasing in SNR; P(RI = 2) increasing with SNR.
7. README (or equivalent getting-started page) runs one snapshot and one tiny Monte Carlo from a copy-paste example.
8. Every public algorithm docstring names its 3GPP clause and its exploratory shortcut.

---



## 12. Open decisions (not blocking M1)

These are recorded so later design docs do not relitigate them accidentally. M1 **must not** wait on them.


| ID   | Question                                                                                                 | Default until decided                                                                             |
| ---- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| OD-1 | Exact numerical CQI SINR thresholds (literature table vs. generate-once from a mini AWGN Shannon offset) | Ship a *placeholder* L1 table, clearly labeled exploratory, with a cited starting point |
| OD-2 | Default RI metric: sum of CQI efficiencies vs. Gaussian mutual information of HW                         | Mutual information for RI/PMI search; CQI table applied after PMI is chosen                       |
| OD-3 | Channel estimator model for M6 (resource-element LS vs. port-level MMSE)                                 | Port-level MMSE on a P-port observation                                                           |
| OD-4 | Whether M1 stores `pmi` as a single integer (valid for 2-port) or always as a small struct               | Integer for 2-port, with a documented upgrade path to `(i1, i2)` in M5                            |
| OD-5 | Plotting library in examples (matplotlib vs. none)                                                       | matplotlib extra, not a hard dependency of the library                                            |


---



## 13. References

The package **must** cite these by clause, not by copying spec prose into source files.

1. 3GPP TS 38.214, *NR; Physical layer procedures for data* — CSI reporting, CQI tables, Type I codebook, LI, conditioning order (clauses 5.2.1, 5.2.2).
2. 3GPP TS 38.211, *NR; Physical channels and modulation* — CSI-RS (needed from M6).
3. 3GPP TS 38.212, *NR; Multiplexing and channel coding* — CSI UCI field widths (post-1.0 overlay).
4. 3GPP TS 38.331, *NR; RRC protocol* — `CSI-ReportConfig`, `reportQuantity` (configuration vocabulary only; no ASN.1 parser).

---



## 14. What this document is not

This file does not define branch names, commit messages, PR templates, or CI vendors. Process: `.cursor/engineering-conventions.md`. Placement: `docs/design/layers.md`. Homes: `.cursor/rules/single-home.mdc`.

This file **does** define what the software is, which CSI fields it computes, the smallest legal first scenario, and the order in which the product is allowed to grow.