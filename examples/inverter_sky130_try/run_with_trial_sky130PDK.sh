#!/usr/bin/env bash
set -e

export PYTHONPATH=/usr/local/lib/python3.7/site-packages:/MAGICAL/flow/python:${PYTHONPATH:-}

echo "Python executable:"
which python3.7

echo "Python version:"
python3.7 --version

echo "PYTHONPATH=$PYTHONPATH"

echo "Check magicalFlow import:"
python3.7 -c "import magicalFlow; print(magicalFlow)"

cat > inverter_trial.json <<'JSON'
{
    "spectre_netlist" : "inverter_sky130_name_test.sp",
    "resultDir" : "./",
    "techfile" : "../../generated/sky130PDK_trial/sky130.techfile",
    "simple_tech_file" : "../../generated/sky130PDK_trial/sky130.techfile.simple",
    "lef" : "../../generated/sky130PDK_trial/sky130.lef",
    "vddNetNames" : ["VPWR"],
    "vssNetNames" : ["VGND"]
}
JSON

rm -rf inverter_core.route.gds inverter_core.place.gds inverter_core.ioPin gds
mkdir -p gds

python3.7 /MAGICAL/flow/python/Magical.py inverter_trial.json > run_trial_sky130PDK.log 2>&1

echo "Trial PDK run finished."
ls -lh inverter_core.route.gds inverter_core.ioPin
