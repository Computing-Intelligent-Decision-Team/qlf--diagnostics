subckt inverter_core A Y VPWR VGND
M0 (Y A VGND VGND) nch_lvt_mac l=150n w=1u multi=1 nf=1
M1 (Y A VPWR VPWR) pch_lvt_mac l=150n w=2u multi=1 nf=1
ends inverter_core
