.subckt SMCNR_SE_2st_AMP vdda gnda vin vip ibias vout
xm1 outp outp gnda gnda nch_mac l=10u w=1.5u multi=1 nf=1
xm3 outn outp gnda gnda nch_mac l=10u w=1.5u multi=1 nf=1
xm7 ibias ibias vdda vdda pch_mac l=10u w=0.22u multi=1 nf=1
xm6 net53 ibias vdda vdda pch_mac l=10u w=0.22u multi=2 nf=1
xm5 vout ibias vdda vdda pch_mac l=10u w=0.22u multi=10 nf=1
xm2 outn vip net53 vdda pch_mac l=8.24u w=7.52u multi=1 nf=1
xm0 outp vin net53 vdda pch_mac l=8.24u w=7.52u multi=1 nf=1
xm4 vout outn gnda gnda nch_mac l=10u w=1.48u multi=10 nf=1
xr0 net027 vout gnda rppolywo_m lr=4e-6 wr=400e-9 multi=1 m=1 series=31 segspace=250e-9
xc0 outn net027 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
.ends SMCNR_SE_2st_AMP
