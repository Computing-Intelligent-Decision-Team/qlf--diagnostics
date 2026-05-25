subckt ota_core VINP VINM IB VDD VOUT GND
M6 (net1 VINP net2 GND) sky130_fd_pr__nfet_01v8 l=150n w=1.26u multi=1 nf=2
M7 (VOUT net1 VDD VDD) sky130_fd_pr__pfet_01v8 l=150n w=1.26u multi=1 nf=2
M8 (net1 net1 VDD VDD) sky130_fd_pr__pfet_01v8 l=150n w=1.26u multi=1 nf=2
M2 (VOUT VINM net2 GND) sky130_fd_pr__nfet_01v8 l=150n w=1.26u multi=1 nf=2
M1 (net2 IB GND GND) sky130_fd_pr__nfet_01v8 l=150n w=1.26u multi=1 nf=2
ends ota_core
