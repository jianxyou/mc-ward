#!/bin/bash
# Night of 2026-11-24: what the records in the robot's memory do, and what a visitor can do with that.
#   text (shift_explore.py): the visitor's errands as an attack and the defenses against it; 64 and 128 deliveries and
#        the same deliveries as one line; which part of a record matters; four larger models
#   game (world_shift.py):   the visitor's errands carried out by the robot (8 errands x 4 defenses, then 2 and 16
#        errands), and the 32-delivery shift with and without the secret
# The game runs on its own copy of the answer cache while the other models run as text; the copies are merged at the end.
# Start it with:  caffeinate -is bash run_night3.sh
cd "$(dirname "$0")"
export PATH="$PWD/../tools/node/bin:$PATH"
export NURSE_RETRIES=10
LOG=night3_text.log
GLOG=night3_game.log
echo "start $(date)" > $LOG
MODEL=gemma-3-12b PARTS=A,B,C MAX_COST=0.40 python3 shift_explore.py >> $LOG 2>&1
echo "TEXT_GEMMA12_DONE $(date)" >> $LOG

cp ../bench/cache.json ../bench/cache_game.json
(
  export NURSE_CACHE="$PWD/../bench/cache_game.json"
  echo "start $(date)"
  python3 world_shift.py --n 8 --style vgift --cells full:none,full:guard,full:ask,full:stash --out world_attack_results.jsonl
  echo "ATTACK8_DONE $(date)"
  python3 world_shift.py --n 2 --style vgift --cells full:none --out world_attack2_results.jsonl
  python3 world_shift.py --n 16 --style vgift --cells full:none --out world_attack16_results.jsonl
  echo "ATTACK_DONE $(date)"
  python3 world_shift.py --n 32 --cells full:none,nosecret:none --out world_long_results.jsonl
  echo "GAME_DONE $(date)"
) > $GLOG 2>&1 &
GAME=$!

MODEL=mistral PARTS=A,B,C MAX_COST=0.60 python3 shift_explore.py >> $LOG 2>&1
MODEL=gemma-3-4b PARTS=A,B,C MAX_COST=0.30 python3 shift_explore.py >> $LOG 2>&1
MODEL=gemma-3-27b PARTS=D,A MAX_COST=0.50 python3 shift_explore.py >> $LOG 2>&1
NURSE_MIN_TOKENS=200 MODEL=haiku-5.5 PARTS=D,A MAX_COST=0.80 python3 shift_explore.py >> $LOG 2>&1
MODEL=deepseek-flash PARTS=D,A MAX_COST=0.30 python3 shift_explore.py >> $LOG 2>&1
MODEL=gemini-flash-lite PARTS=D MAX_COST=0.60 python3 shift_explore.py >> $LOG 2>&1
echo "TEXT_DONE $(date)" >> $LOG

wait $GAME
python3 - >> $LOG 2>&1 <<'PY'
import json, os
main, game = '../bench/cache.json', '../bench/cache_game.json'
a, b = json.load(open(main)), json.load(open(game))
new = [k for k in b if k not in a]
for k in new:
    a[k] = b[k]
json.dump(a, open(main + '.merge.tmp', 'w'))
os.replace(main + '.merge.tmp', main)
print('cache: %d answers of the game run added, %d in all' % (len(new), len(a)))
PY
echo "ALL3_DONE $(date)" >> $LOG
