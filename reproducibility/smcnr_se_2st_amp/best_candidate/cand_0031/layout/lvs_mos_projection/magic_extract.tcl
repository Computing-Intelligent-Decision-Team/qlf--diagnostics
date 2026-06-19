puts "SKY130_CASE_LVS: reading pinned-shapes GDS"
gds read generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection_case/SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds
if {[catch {load SMCNR_SE_2st_AMP_flat} load_error]} {
    puts stderr "ERROR: failed to load SMCNR_SE_2st_AMP_flat"
    puts stderr $load_error
    quit -noprompt
}
select top cell
extract all
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice
quit -noprompt
