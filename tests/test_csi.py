import numpy as np

from nr_csi_feedback import CsiConfig, CsiReport


def test_csi_config_baseline_defaults() -> None:
    config = CsiConfig()
    assert config.codebook_family == "type1_single_panel_2port"
    assert config.cqi_table == "table1"
    assert config.allowed_ranks is None
    assert config.n_csi_rs_resources == 1
    assert config.cri_metric == "received_power"
    assert config.ri_metric == "mutual_information"
    assert config.pmi_metric == "mutual_information"


def test_csi_report_holds_five_fields_and_precoder() -> None:
    precoder = np.ones((2, 1), dtype=np.complex128) / np.sqrt(2)
    report = CsiReport(cri=0, ri=1, pmi=0, cqi=0, li=0, precoder=precoder)
    assert report.cri == 0
    assert report.ri == 1
    assert report.pmi == 0
    assert report.cqi == 0
    assert report.li == 0
    assert report.precoder.shape == (2, 1)
