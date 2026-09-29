# Hugging Face Space configuration

**This repository publishes no Hugging Face Space.** It holds no provider
credential, and `.github/workflows/hf-deploy.yml` is a read-only authority
verifier.

| Space | State | Writer |
| --- | --- | --- |
| `SZLHOLDINGS/lyte` | canonical Lyte Space | `szl-holdings/a11oy` `.github/workflows/hf-sync.yml` (`scripts/hf_publish_lyte_enterprise.py`, exact `lyte-services` revision) |
| `SZLHOLDINGS/lyte-lattice` | retired standalone target, absent on the Hub | none; do not recreate it |

`lyte-lattice.md` is the retired standalone card, kept as history. It is not
published anywhere. Lyte is **BIND_AS_A11OY_PACKAGE**: not a second flagship and
not a new product name. a-11-oy.com is not certified.
