#!/bin/bash
# 2026-11-22 night, after run_search.sh:
# (1) the found attacks and defenses on two other nurse models (transfer), held-out secrets;
# (2) one more attack search, against D2 (does the found defense hold?), then the held-out table again;
# (3) once the game stage of run_search.sh is done: the A1 attack against no defense and the privacy reminder, in Minecraft.
cd "$(dirname "$0")"
LOG=more_run.log
echo "start $(date)" > $LOG
NURSE=google/gemma-3-4b-it python3 search.py eval >> $LOG 2>&1
NURSE=mistralai/mistral-small-3.2-24b-instruct python3 search.py eval >> $LOG 2>&1
echo "TRANSFER_DONE $(date)" >> $LOG
python3 search.py attack3 >> $LOG 2>&1
echo "A3_DONE $(date)" >> $LOG
NURSE=google/gemma-3-4b-it python3 search.py eval >> $LOG 2>&1
NURSE=mistralai/mistral-small-3.2-24b-instruct python3 search.py eval >> $LOG 2>&1
echo "TRANSFER2_DONE $(date)" >> $LOG
until grep -q ALL_DONE search_run.log; do sleep 30; done
python3 world_items.py --heldout --n 12 --conds fact --models gemma-3-12b --defenses none,prompt --attacks A1 \
  --out world_search_results.jsonl >> $LOG 2>&1
echo "ALL_DONE $(date)" >> $LOG
