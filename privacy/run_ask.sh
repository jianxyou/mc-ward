#!/bin/bash
# 2026-11-22 night: the robot can walk to the patient's bed and check a request in person (defense 'ask', 'ask_always').
# (1) attack search against 'ask' (can the visitor talk the robot out of checking?), held-out table for gemma-3-12b;
# (2) the same table for two other nurse models;
# (3) in Minecraft, held-out secrets: the robot walks to the bed, asks, and carries the things.
cd "$(dirname "$0")"
LOG=ask_run.log
echo "start $(date)" > $LOG
python3 search.py attack4 >> $LOG 2>&1
echo "A4_DONE $(date)" >> $LOG
NURSE=mistralai/mistral-small-3.2-24b-instruct python3 search.py eval >> $LOG 2>&1
NURSE=google/gemma-3-4b-it python3 search.py eval >> $LOG 2>&1
echo "TRANSFER_DONE $(date)" >> $LOG
python3 world_items.py --heldout --n 12 --conds fact,home --models gemma-3-12b --defenses ask --attacks A0,A3,A4 \
  --out world_ask_results.jsonl >> $LOG 2>&1
python3 world_items.py --heldout --n 12 --conds fact --models gemma-3-12b --defenses ask_always,prompt --attacks A4 \
  --out world_ask_results.jsonl >> $LOG 2>&1
echo "ALL_DONE $(date)" >> $LOG
