"""Public CSI API: configuration, report, and one-snapshot computation (L4)."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True, kw_only=True)
class CsiConfig:
    """Knobs for one CSI report (FR-3). Defaults match the §6 baseline.

    Spec: TS 38.331 CSI-ReportConfig vocabulary only (no ASN.1).
    Fidelity: exploratory.
    Simplifications: Python fields, not RRC; CRI is always reported.
    ``allowed_ranks`` of None means every rank the codebook allows.
    """

    codebook_family: str = "type1_single_panel_2port"
    cqi_table: str = "table1"
    allowed_ranks: tuple[int, ...] | None = None
    n_csi_rs_resources: int = 1
    cri_metric: str = "received_power"
    ri_metric: str = "mutual_information"
    pmi_metric: str = "mutual_information"


@dataclass(frozen=True, slots=True, kw_only=True)
class CsiReport:
    """Five-field CSI report plus the realized precoder W (FR-1, FR-2).

    Spec: TS 38.214 clause 5.2.1.4 (quantities and conditioning order).
    Fidelity: exploratory.
    Simplifications: PMI is a single integer (OD-4 default for 2-port).
    Integers are 0-based; ``ri`` is the layer count; ``li`` is a column
    index of ``precoder``.
    """

    cri: int
    ri: int
    pmi: int
    cqi: int
    li: int
    precoder: NDArray[np.complex128]


def compute_csi_report(
    channel: NDArray[np.complex128],
    noise_variance: float,
    config: CsiConfig,
) -> CsiReport:
    """Compute a CSI report from one channel snapshot.

    Spec: TS 38.214 clause 5.2.1.4 (CRI, then RI, then PMI, then CQI, then LI).
    Fidelity: exploratory.
    Simplifications: M0 shell; does not select any field.

    ``channel`` is H with shape (N_r, P). ``noise_variance`` is sigma^2
    per receive antenna.
    """

    raise NotImplementedError(
        "CSI computation is not implemented in M0; this entry point is an empty L4 shell."
    )
