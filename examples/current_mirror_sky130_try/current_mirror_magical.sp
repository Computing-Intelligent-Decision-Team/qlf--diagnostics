subckt current_mirror_core IBIAS IOUT VDD GND
M0 (NREF NREF GND GND) sky130_fd_pr__nfet_01v8 l=150n w=1.26u multi=1 nf=2
M1 (IOUT NREF GND GND) sky130_fd_pr__nfet_01v8 l=150n w=1.26u multi=1 nf=2
M2 (NREF IBIAS VDD VDD) sky130_fd_pr__pfet_01v8 l=150n w=1.26u multi=1 nf=2
M3 (IOUT IBIAS VDD VDD) sky130_fd_pr__pfet_01v8 l=150n w=1.26u multi=1 nf=2
ends current_mirror_core
