# Codex Review: Claude AH-SMC-007

## Decision

Return for correction. The report successfully reproduces the direct Magic
short, substrate, equivalence, and device-mapping evidence. Its router-layer
interpretation and proposed repair are not technically acceptable.

## Findings

### 1. High: Router layer 6 is incorrectly treated as OD/diff

The report states at lines 97, 145, and 152 that
`psub_route_db_layer=6` maps to `diff.drawing 65/20`.

Direct artifacts contradict this:

- `fan_smc_pin_3.gr` uses route layer 6 for normal gnda and vdda routes.
- `run_fan_smc_pin_3_trial.log` records the synthetic psub shape on router
  shape layer 5, the zero-based form of the sixth routing layer.
- The corresponding horizontal geometry in `fan_smc_pin_3.route.gds` appears
  on MAGICAL routing layers 31 through 36.
- The remap contract maps layers 31 through 36 to Sky130 `li1` through `met5`.

Therefore the synthetic psub evidence is a multi-metal power stack, not an OD
or substrate-tap diffusion stripe. The report's primary hypothesis is built on
the wrong layer interpretation.

### 2. High: The proposed body-pin/label edit cannot create substrate contact

The proposed experiment at lines 260-279 adds a metal body-pin box or TEXT
labels. Neither operation creates the physical Sky130 p+ substrate stack
required for a psubstrate contact: `tap.drawing`, `psdm`, `licon1`, `li1`, and a
connection to the gnda route.

Changing the `.pin` sentinel may change router connectivity, but it is not a
valid physical-body repair unless the primitive also contains real tap
geometry. Adding TEXT only changes naming and must not be presented as an
electrical connection.

### 3. Medium: Static diffusion adjacency is promoted beyond its evidence

The report correctly says the static tracer over-approximates active
diffusion, but later claims the psub stripe is contiguous through NMOS and PMOS
channels. The tracer does not model transistor junction/channel isolation and
cannot prove that physical path. Keep this as a rejected or unproven static
hypothesis. The authoritative failure remains Magic's substrate/equiv/device
records.

### 4. Medium: `as=0 ps=0` is over-interpreted

Lines 187 and 250 infer that M11 source diffusion is physically absent or
merged. Zero source area in an ext2spice record is an extraction symptom and
can also result from source/drain area attribution or shared regions. It does
not independently prove missing primitive diffusion. Record it as a symptom
unless geometry-level evidence proves the cause.

### 5. Low: The requested unaffected control does not exist

M0 is labeled a control, but it also has a body mismatch and source/drain
collapse. The report should call it a comparison instance, not an unaffected
control, and explicitly state that no unaffected MOS exists in this globally
collapsed extraction.

## Accepted Evidence

- Magic reports vout shorted to vdda and gnda.
- `.ext` records substrate `vout` and both supply equivalences.
- Device mapping reports 23 mapped devices, one unmatched device, 23 body
  mismatches, and 88 terminal mismatches.
- Nwell diagnosis passes while psub diagnosis fails.
- Source NMOS bodies are `gnda`, but generated NMOS fourth pins are `-1` and
  primitive GDS has no explicit p+ substrate tap.

## Required Correction

Revise the report without rerunning P&R or editing geometry. The corrected
single-variable proposal must be a physical p+ substrate-tap experiment, or
must clearly defer physical design choice to Codex/user review. It must not
claim that a metal box or TEXT label alone connects the substrate.
