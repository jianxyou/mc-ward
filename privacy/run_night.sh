#!/bin/bash
# Night of 2026-11-23: the long shift (shift.py, world_shift.py). About five and a half hours.
#   1. decisions as text, gemma-3-12b: 4 memory designs x 3 world designs x 3 shift lengths x 4 requests, 20 secrets
#   2. the same shifts carried out by the robot in Minecraft: 20 secrets x 7 cells, 8 deliveries per shift,
#      three requests at the end of each shift (140 shifts, 1120 deliveries, 420 requests)
#   3. decisions as text for two other models (smaller table)
# Start it with:  caffeinate -is bash run_night.sh   (keeps the Mac awake)
cd "$(dirname "$0")"
LOG=night_run.log
export NURSE_RETRIES=10
echo "start $(date)" > $LOG
MODEL=gemma-3-12b MAX_COST=0.22 python3 shift.py >> $LOG 2>&1
echo "TEXT1_DONE $(date)" >> $LOG
python3 world_shift.py --n 8 --cells full:none,window:none,summary:none,pin:none,window:stash,window:ask,full:ask >> $LOG 2>&1
echo "GAME_DONE $(date)" >> $LOG
MODEL=mistral REDUCED=1 MAX_COST=0.07 python3 shift.py >> $LOG 2>&1
MODEL=gemma-3-4b REDUCED=1 MAX_COST=0.05 python3 shift.py >> $LOG 2>&1
echo "ALL_DONE $(date)" >> $LOG
