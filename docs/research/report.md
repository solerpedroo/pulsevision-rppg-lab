# PulseVision — engineering and research status report

2026-11-08 · v1.0.0 local preparation · PV-1107.

## Question and scope

Can a local, inspectable pipeline extract facial RGB, estimate periodicity with
classical methods and abstain with reproducible reasons? Engineering feasibility
is implemented. Accuracy, robustness and physiological validity in people remain
unmeasured in this project. This document is not a completed human experiment.

## Method

PyAV decodes real presentation timestamps; ROI extraction uses MediaPipe landmarks
and explicit masks. Python DSP applies timestamp/gap checks, normalization,
resampling, detrending, GREEN/CHROM/POS, Butterworth filtering and Welch spectral
estimation. Instrumental quality gates can reject windows without erasing their
cause, duration or timestamps. Equations, support trimming and thresholds are
specified in ADRs 0003–0007; browser parity has a bounded artificial test domain,
not a claim that browser acquisition equals offline acquisition.

The offline protocol freezes access/alignment records, manifest, splits, parameters,
seeds, code state and hashes before evaluation. It reports accepted error alongside
eligible-window coverage, exclusions and session failures, with aggregation by
participant. Reference absent or unsupported means no error pair, not zero error.
See [protocol v1](../evaluation/protocol-v1.md) and ADRs 0008/0012. Protocols A–E
are draft experiment specifications, not completed robustness studies.

## Evidence obtained

Synthetic tests exercise known frequencies, degeneracy, gaps, harmonics and invalid
inputs. Independent numerical fixtures check method composition and limited
Python/TypeScript parity. API/browser tests exercise actual job processing,
abstention, deletion, exports and face-free camera lifecycle. A synthetic study
runs three artificial participants, GREEN/CHROM/POS and 10/20/30-second windows.
Its numbers demonstrate pipeline/report behavior only; none is a human MAE, RMSE,
clinical confidence interval or real sensor-to-screen latency measurement.

Risk-oriented coverage, exact release checks and audit results are recorded in
[state.md](../../state.md) and the [release dossier](../release/v1.0.0.md).
Automated accessibility checks and synthetic UI screenshots do not establish
usability for every user/device. No physiological result is supplied here because
no authorized dataset was evaluated.

## Literature and datasets

- Verkruysse, W.; Svaasand, L. O.; Nelson, J. S. (2008). Remote plethysmographic
  imaging using ambient light. _Optics Express_, 16(26), 21434–21445.
  [DOI 10.1364/OE.16.021434](https://doi.org/10.1364/OE.16.021434).
- de Haan, G.; Jeanne, V. (2013). Robust pulse rate from chrominance-based rPPG.
  _IEEE Transactions on Biomedical Engineering_, 60(10), 2878–2886.
  [PubMed / DOI 10.1109/TBME.2013.2266196](https://pubmed.ncbi.nlm.nih.gov/23744659/).
- Wang, W.; den Brinker, A. C.; Stuijk, S.; de Haan, G. (2017). Algorithmic
  Principles of Remote PPG. _IEEE Transactions on Biomedical Engineering_, 64(7),
  1479–1491. [PubMed / DOI 10.1109/TBME.2016.2609282](https://pubmed.ncbi.nlm.nih.gov/28113245/).
- UBFC-rPPG: [official dataset page](https://sites.google.com/view/ybenezeth/ubfcrppg).
  The maintainers request citation of Bobbia, S.; Macwan, R.; Benezeth, Y.; Mansouri,
  A.; Dubois, J., _Unsupervised skin tissue segmentation for remote
  photoplethysmography_, online 2017, later volume publication in _Pattern
  Recognition Letters_ 124. [DOI 10.1016/j.patrec.2017.10.017](https://doi.org/10.1016/j.patrec.2017.10.017).
- PURE: official source and current access record in
  [dataset-access.md](dataset-access.md). Neither PURE nor UBFC-rPPG was downloaded
  or used for accuracy claims. Adapters prepared from published organization still
  need validation against authorized original packages and synchronization evidence.

Implementing these methods does not inherit published performance. Model licenses
and consulted reference implementations are documented in
[face-model.md](face-model.md) and [classical-references.md](classical-references.md).

## Limitations and next scientific work

Obtain authorized data and terms, verify video/reference alignment and inspect
positive ROIs on authorized faces. Freeze a subject-disjoint protocol before
running experiments. Evaluate error with coverage, rejected windows and failure
rates; compare ROI/window/motion/light/compression conditions using actual verified
video transformations. Test physical cameras and mobile hardware separately.
Threshold tuning must not consume the final test split. Do not infer fairness,
clinical utility, SpO2, diagnosis or facial identity from synthetic results.
