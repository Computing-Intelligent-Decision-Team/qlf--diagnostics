subckt inverter_core A Y VPWR VGND
M0 (Y A VGND VGND) sky130_fd_pr__nfet_01v8 l=150n w=1u multi=1 nf=1
M1 (Y A VPWR VPWR) sky130_fd_pr__pfet_01v8 l=150n w=2u multi=1 nf=1
ends inverter_core
