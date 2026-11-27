#!/bin/bash
# Follows run_night.sh (waits for it to finish), 2026-11-23:
#   1. shift_more.py: longer shifts (16 and 32 deliveries), and filler lines that are not deliveries (text only)
#   2. a second model in Minecraft: mistral, 20 secrets x 3 cells, 8 deliveries per shift
cd "$(dirname "$0")"
until grep -q ALL_DONE night_run.log; do sleep 60; done
LOG=night_run2.log
export NURSE_RETRIES=10
echo "start $(date)" > $LOG
MAX_COST=0.10 python3 shift_more.py >> $LOG 2>&1
echo "MORE_DONE $(date)" >> $LOG
python3 world_shift.py --model mistral --n 8 --cells full:none,window:stash,full:ask --out world_shift_results_mistral.jsonl >> $LOG 2>&1
echo "ALL2_DONE $(date)" >> $LOG
