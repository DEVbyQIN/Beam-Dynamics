#!/bin/zsh
cd "$(dirname "$0")"
if [[ -x /opt/anaconda3/bin/python3 ]]; then
  /opt/anaconda3/bin/python3 run_gui.py --open
else
  python3 run_gui.py --open
fi
