#!/bin/bash
# Privacy defenses on the item task (2026-11-22): decision stage, then the same decisions carried out in Minecraft.
#   stage 1: defense.py, 3 models x 4 defenses x 3 conditions x 20 secrets x 5 arrangements (text only)
#   stage 2: world_items.py, gemma-3-12b x 4 defenses x {fact, owner} x 20 secrets, carried out by the bot
# Stage 2 runs after stage 1 so that its decisions come from the same cache (arrangement 0) and match stage 1.
cd "$(dirname "$0")"
LOG=defense_run.log
echo "start $(date)" > $LOG
python3 defense.py >> $LOG 2>&1
echo "STAGE1_DONE $(date)" >> $LOG
python3 world_items.py --n 20 --conds fact,owner --models gemma-3-12b --defenses none,prompt,guard,instructor \
  --out world_defense_results.jsonl >> $LOG 2>&1
echo "ALL_DONE $(date)" >> $LOG
