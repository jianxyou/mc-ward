#!/bin/bash
# 2026-11-22 night: (1) owner control with the same wording as the visitor ("going home"), all models and defenses;
# (2) attack/defense search after Zhang & Yang (search.py), with held-out evaluation;
# (3) the found attacks and defenses carried out by the bot in Minecraft, held-out secrets, gemma-3-12b.
cd "$(dirname "$0")"
LOG=search_run.log
echo "start $(date)" > $LOG
CONDS=home python3 defense.py >> $LOG 2>&1
echo "HOME_DONE $(date)" >> $LOG
python3 search.py >> $LOG 2>&1
echo "SEARCH_DONE $(date)" >> $LOG
ATT=$(python3 -c "import json;f=json.load(open('search_out.json'))['found'];print(','.join(['A0']+[k for k in sorted(f) if k.startswith('A') and f[k]]))")
DEF=$(python3 -c "import json;f=json.load(open('search_out.json'))['found'];d=[k for k in sorted(f) if k.startswith('D') and f[k]];print(','.join(['guard']+d[-1:]))")
echo "game: attacks $ATT, defenses $DEF" >> $LOG
python3 world_items.py --heldout --n 12 --conds fact,home --models gemma-3-12b --defenses "$DEF" --attacks "$ATT" \
  --out world_search_results.jsonl >> $LOG 2>&1
echo "ALL_DONE $(date)" >> $LOG
