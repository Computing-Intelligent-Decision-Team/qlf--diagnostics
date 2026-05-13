#!/usr/bin/env bash
set -e

export PYTHONPATH="/usr/local/lib/python3.7/site-packages:/MAGICAL/flow/python:${PYTHONPATH:-}"

echo "Python executable:"
which python3.7 || which python

echo "Python version:"
python3.7 --version || python --version

echo "PYTHONPATH=$PYTHONPATH"

echo "Check magicalFlow import:"
python3.7 -c "import magicalFlow; print(magicalFlow)"

rm -rf *.gds *.ioPin gds
mkdir -p gds

python3.7 /MAGICAL/flow/python/Magical.py inverter.json
