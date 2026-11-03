"""The nurse model: reads what the memory kept of the doctor's messages and says
which orders are still in force.

    python3 llm_nurse.py                 # needs Ollama running with llama3.2 (no Minecraft needed)
    python3 llm_nurse.py --model qwen2.5  # any model you have pulled in Ollama

Run on its own it asks the model twice: once with the cancellation line in memory,
once with the memory rewritten so the cancelled order is gone. demo.py --llm uses
the same function inside the full episode.

The doctor's lines are fixed and written by us (see demo.SCRIPT); the model only
plays the nurse. Ollama's `format: "json"` makes it answer in JSON, so no ``` fences
and no missing words.
"""
import argparse
import json
import os
import sys
import urllib.request

OLLAMA = os.environ.get('OLLAMA_URL', 'http://localhost:11434') + '/api/generate'
PATIENTS = ['one', 'two', 'three', 'four']
DRUGS = ['strength', 'regeneration', 'fire_resistance']

PROMPT = """You are a nurse on a ward with patients one, two, three and four.
The pharmacy has these potions: {drugs}.
Below are the doctor's messages your memory has kept, oldest first.
List every order that is still in force right now. An order that the doctor
cancelled is not in force. Do not invent orders.

Doctor's messages:
{notes}

Answer with JSON only, in this exact shape:
{{"orders": [{{"patient": "one", "drug": "strength"}}]}}
Use an empty list if nothing is in force."""


def ask(notes, model='llama3.2', temperature=0.0):
    """notes: list of doctor messages as the memory kept them. Returns [(patient, drug), ...]."""
    prompt = PROMPT.format(drugs=', '.join(DRUGS),
                           notes='\n'.join(f'- {n}' for n in notes) or '- (nothing)')
    body = json.dumps({'model': model, 'prompt': prompt, 'format': 'json', 'stream': False,
                       'options': {'temperature': temperature}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return parse(json.loads(r.read())['response'])


def parse(text):
    """JSON text -> [(patient, drug), ...], keeping only names the ward knows."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print(f'[nurse] could not parse: {text!r}', file=sys.stderr)
        return []
    items = data.get('orders', []) if isinstance(data, dict) else data
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        p, d = str(it.get('patient', '')).lower().strip(), str(it.get('drug', '')).lower().strip()
        d = d.replace(' ', '_').replace('_potion', '')
        if p in PATIENTS and d in DRUGS and (p, d) not in out:
            out.append((p, d))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='llama3.2')
    ap.add_argument('--runs', type=int, default=3, help='ask each memory this many times')
    args = ap.parse_args()

    from demo import SCRIPT, Memory

    for name, rewrite in [('memory keeps everything (naive)', False),
                          ('memory rewritten on cancel', True)]:
        mem = Memory(rewrite)
        for kind, patient, drug, text in SCRIPT:
            mem.hear(kind, patient, drug, text)
        print(f'\n== {name} ==')
        for n in mem.notes:
            print('   memory:', n)
        for i in range(args.runs):
            print(f'   nurse says ({args.model}):', ask(mem.notes, args.model))
    print('\nexpected: patient three regeneration and patient four fire_resistance only; '
          'patient one strength was cancelled.')
