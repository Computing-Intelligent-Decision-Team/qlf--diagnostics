# AH-SMC-025: Substrate-Abstracted MOS-Only LVS Diagnostic Probe

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-025 |
| Date | 2026-06-22 |
| Type | Diagnostic LVS policy probe |
| MAGICAL files modified | **None** |
| Trust status | Failure-case only (`usable_for_mos_only_lvs_diagnostic: true`) |

## Executive Summary

**Stripping the NMOS body terminal from LVS comparison does not resolve the
Fan_SMC mismatch.** The substrate collapse (`equiv "vout" "vdda"`,
`equiv "vout" "gnda"`) restructures the entire extracted connectivity, not
just the body terminals. Internal nets are merged and reorganized — source
net names (dm_1, net043, vb3, net050...) no longer correspond to any
extracted internal node.

Fan_SMC's problem is deeper than body terminal collapse: **the entire
internal net topology is affected by Magic's substrate merge.** A 3-terminal
LVS does not fix this; it only removes one symptom (body mismatch) while
the underlying topology restructuring persists.

**Fan_SMC is classified as: topology restructured by substrate collapse,
MOS-only LVS insufficient for pass.** This is a stronger negative result
than anticipated, but it accurately reflects the extraction evidence.

---

## 1. Experiment Design

Three LVS variants were compared:

| Variant | NMOS body | PMOS body | Ports | Description |
| --- | --- | --- | --- | --- |
| Full (baseline) | 4 terminals | 4 terminals | 5 vs 3 | Original full LVS |
| 3term (NMOS body stripped) | 3 terminals | 4 terminals | 5 vs 3 | Ignore NMOS body |
| 3term+portmatch | 3 terminals | 4 terminals | 5 vs 5 | Port aliasing added |

### 3term+portmatch Method

1. Source: NMOS `D G S B` → `D G S` (body stripped)
2. Extracted: NMOS `D G S B` → `D G S` (body stripped)
3. Extracted ports: `gnda` and `vdda` added as port aliases to `vout`
   (per `.ext` equiv records), with 0V voltage sources

---

## 2. Results

### Full LVS (Baseline)

```
Result: Netlists do not match.
Devices: 24 vs 24
Nets: 18 vs 19 (MISMATCH)
```

### 3term (NMOS Body Stripped, no port matching)

```
Result: Netlists do not match.
Devices: 24 vs 24
Nets: 18 vs 19 (MISMATCH)
```

**Body stripping alone had zero effect** — the same 18 vs 19 net mismatch
persists because the port mismatch (5 vs 3) dominates.

### 3term+portmatch (NMOS Body Stripped, Ports Matched)

```
Result: Netlists do not match.
Devices: 24 vs 26 (MISMATCH — 2 extra vsrc elements)
Nets: 18 vs 21 (MISMATCH)
```

### Net Mismatch Analysis (3term+portmatch)

| Source net | Matched to | Fanout | Issue |
| --- | --- | --- | --- |
| `dm_1` | `a_1220_2750#` | 1 PFET vs 1 NFET+2 PFET | **Topology mismatch** |
| `net043` | `a_1500_2270#` | 1 PFET+2 NFET vs 2 NFET+1 PFET | **Topology mismatch** |
| `vdda` | `a_220_2930#` | 10 PFET+10 PFET B vs 1 NFET+1 PFET+1 NFET | **Collapsed to internal** |
| `vb3` | `a_700_3870#` | various | **Collapsed to internal** |
| `gnda` | (no matching net) | 8 NFET S + 12 NFET B | **Lost entirely** |

---

## 3. Why Body Stripping Doesn't Fix This

The substrate collapse (`equiv "vout" "vdda"`, `equiv "vout" "gnda"`) causes
Magic's extractor to restructure the internal connectivity:

1. **NMOS source (should be gnda) → vout**: Source terminals that were `gnda`
   become `vout` because the substrate shorts gnda to vout.

2. **PMOS source (should be vdda) → vout**: Source terminals that were `vdda`
   become `vout` because the substrate shorts vdda to vout.

3. **Internal nodes are merged**: `a_20_2910#` (fanout 6) represents a merged
   node combining net013, vb3, vdda connections that should be separate.

4. **Gate terminals are preserved but misrouted**: NMOS gates (vb3, vb4,
   net043) are assigned to internal nodes that don't correspond to source
   net names.

The body terminal is just one of many terminals affected. Stripping it does
not restore the correct source/drain/gate assignments.

---

## 4. What This Tells Us

### Fan_SMC's Problem Is Not "Body Mismatch" — It's "Topology Restructuring"

| Symptom | Cause | Fixable by 3-term LVS? |
| --- | --- | --- |
| NMOS body = vout | Substrate names vout | Yes (body stripped) |
| NMOS source = vout | Substrate shorts gnda→vout | **No** |
| PMOS source = vout | Substrate shorts vdda→vout | **No** |
| Internal nets merged | Device channel bridges | **No** |
| Gate terminals misassigned | Topology restructuring | **No** |
| Port count mismatch | ext2spice drops equated ports | Partially (aliasing possible) |

### Three-Terminal LVS Is Insufficient As A Diagnostic

The extracted connectivity has been fundamentally restructured by the
substrate collapse. A 3-terminal comparison does not recover the original
topology — it only hides one symptom (body mismatch) while the underlying
topology restructuring persists.

---

## 5. Classification

Fan_SMC is classified as:

```json
{
  "full_lvs": "FAIL — substrate collapse restructures extracted connectivity",
  "mos_only_3term_lvs": "FAIL — topology restructuring persists beyond body terminals",
  "topology_status": "RESTRUCTURED_BY_SUBSTRATE_COLLAPSE",
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true,
  "usable_for_mos_only_lvs_diagnostic": false
}
```

**Even `usable_for_mos_only_lvs_diagnostic` is false** because the topology
restructuring affects more than just the body terminals.

---

## 6. Hypothesis Assessment (Final)

| H | Claim | Status | Confidence |
| --- | --- | --- | --- |
| H1 | `.pin=-1` sole cause | DISPROVEN | High |
| H2 | Diffusion/psub geometry dominates | PRIMARY CANDIDATE | High |
| H6 | Layout complexity is differentiator | CANDIDATE_STRONG | Medium |
| H7 | Collapse is port-level, device-global | SUPPORTED | High |
| **H8** | **Topology restructuring beyond body terminals** | **CONFIRMED** | **High** |

### H8 (New, from this experiment)

Fan_SMC's extracted connectivity has been fundamentally restructured by
the substrate collapse. The restructuring affects source, drain, gate, and
body terminals; internal node merging; and port assignment. A 3-terminal
(body-abstracted) LVS does not resolve the mismatch because the topology
change is broader than the body terminal alone.

---

## 7. Trust Boundary

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true,
  "usable_for_mos_only_lvs_diagnostic": false,
  "topology_status": "RESTRUCTURED_BY_SUBSTRATE_COLLAPSE"
}
```

---

## 8. Artifacts

| # | Artifact | Path |
| --- | --- | --- |
| 1 | Full LVS log | `.../ah_smc_025/full_lvs.log` |
| 2 | 3term LVS log | `.../ah_smc_025/3term_lvs.log` |
| 3 | 3term portmatched LVS log | `.../ah_smc_025/3term_portmatched_lvs.log` |
| 4 | Source 3term SPICE | `.../ah_smc_025/src_3term.spice` |
| 5 | Extracted 3term portmatched SPICE | `.../ah_smc_025/ext_3term_portmatched.spice` |
