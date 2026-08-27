# Changelog

What became possible in each tagged release. Milestone list: [`docs/design/requirements.md`](docs/design/requirements.md) §10.

## 0.0.1 — M0 Foundation

The package is installable (`nr-csi-feedback` / `nr_csi_feedback`) with pytest, Ruff, and CI on pull requests into `dev` or `main`.

Empty L4 types (`CsiConfig`, `CsiReport`, `compute_csi_report`) are the public CSI surface. They do not compute a report. Product requirements and layer placement are in-tree.
