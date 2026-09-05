---
title: LYTE Lattice
emoji: ⚖️
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
suggested_hardware: cpu-basic
short_description: "Lyte presentation package; canonical runtime is SZLHOLDINGS/lyte"
tags:
  - governed-ai
  - a11oy
  - lyte
  - lattice
  - hologram
  - szl-holdings
---

<!-- SZL-ESTATE-CARD:v2:START -->
<p align="center"><a href="https://a-11-oy.com/"><img src="https://huggingface.co/spaces/SZLHOLDINGS/README/resolve/main/assets/estate-banner-v2.svg" alt="SZL Holdings — governed, receipted, verifiable" width="100%"></a></p>
<p align="center">
  <a href="https://github.com/szl-holdings/.github/tree/main/doctrine"><img src="https://img.shields.io/badge/doctrine-v11%20LOCKED-0B1F3A?style=flat-square" alt="doctrine v11"></a>
  <a href="https://github.com/szl-holdings/lyte-lattice"><img src="https://img.shields.io/badge/source-szl--holdings%2Flyte--lattice-3A414C?style=flat-square" alt="GitHub source"></a>
  <a href="https://a11oy.net"><img src="https://img.shields.io/badge/proof-a11oy.net-3AF4C8?style=flat-square" alt="proof a11oy.net"></a>
</p>
<p align="center"><sub>Part of the <a href="https://huggingface.co/SZLHOLDINGS">SZL Holdings</a> governed estate. Verification proves integrity and origin, never accuracy or performance.</sub></p>
<!-- SZL-ESTATE-CARD:v2:END -->

# LYTE Lattice

**Presentation package. One canonical Lyte runtime.**

BIND_AS_A11OY_PACKAGE. This repository contains the named-frontier hologram and
presentation work. It is not a second flagship, a production certificate, a
broker, a GPU cluster, or a Hub-certified trainer.

| Role | Source or surface |
| --- | --- |
| Presentation package | [szl-holdings/lyte-lattice](https://github.com/szl-holdings/lyte-lattice) |
| Canonical Python backend | [szl-holdings/lyte-services](https://github.com/szl-holdings/lyte-services) |
| Current Hub runtime | [SZLHOLDINGS/lyte](https://huggingface.co/spaces/SZLHOLDINGS/lyte) |
| Product window | [a-11-oy.com/lyte](https://a-11-oy.com/lyte) |
| Canonical publisher | [A11oy hf-sync](https://github.com/szl-holdings/a11oy/blob/main/.github/workflows/hf-sync.yml) |
| Proof origin | [a11oy.net](https://a11oy.net) |
| Authority manifest | [estate/alignment.v1.json](https://github.com/szl-holdings/.github/blob/main/estate/alignment.v1.json) |

## Source → runtime

A11oy's `scripts/hf_publish_vertical_flagships_v4.py` delegates Lyte to
`scripts/hf_publish_lyte_enterprise.py`. That publisher binds an exact
`lyte-services` revision and publishes the existing `SZLHOLDINGS/lyte` Space.
The source-owned Python runtime must not be replaced by a generic generated shell.

The older `SZLHOLDINGS/lyte-lattice` standalone target and central
`publish-operator-spaces.yml` lane are retired. Do not recreate them.
The historical `.github/workflows/hf-deploy.yml` filename now holds a **read-only
authority verifier**, not a provider writer. It checks the estate manifest,
backend/Space ownership, and matching immutable publisher pins, then records the
exact inspected commits. A passing authority check is **not** a runtime uptime
or byte-parity claim; those require the canonical publisher's live evidence.

## Named frontiers

The package retains the N1–N27 frontier interfaces: serving, graph orchestration,
guards, memory, retrieval, evaluation, energy, tools, policy, voice, identity,
and research/training views. Their holographic interfaces do not grant execution
or promotion authority. Optional integrations must report unavailable rather
than simulate a working provider.

N26 inference is REPORTED; do not invent measured joules. N27 GPU training is
UNAVAILABLE without admitted CUDA execution. The gpu-bridge remains
NEVER_DISPATCH. Energy stays UNAVAILABLE unless a real RAPL `energy_uj` sample
is read; watts are not a substitute for integrated energy. Occupancy is
UNAVAILABLE without observations; this is not an MLS.

Hash receipts are not independent signatures. Λ remains **Conjecture 1**.
Owner order `AO-2026-08-29-001` admits this as an A11oy package, not a second flagship.
`a11oy.com` is not an SZL product origin.

## Develop

```bash
npm ci
npm run dev
# Compile the presentation without a database migration:
npm run build:dev
# Offline authority regression tests:
python scripts/test_hf_ownership.py
```

Optional completion integrations use server-side configuration. An absent key
is an unavailable capability, never a mock success. Keep credentials out of
source, browser bundles, and evidence receipts.

Apache-2.0 · Doctrine v11 LOCKED · Copyright 2026 SZL Holdings.
