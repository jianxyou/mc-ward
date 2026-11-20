"""The nurse model: reads what the memory kept of the doctor's messages and says
which orders are still in force.

    python3 llm_nurse.py                 # needs Ollama running with AI model (no Minecraft needed)
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
import time
import urllib.request

OLLAMA = os.environ.get('OLLAMA_URL', 'http://localhost:11434') + '/api/generate'
PATIENTS = ['one', 'two', 'three', 'four']
DRUGS = ['strength', 'regeneration', 'fire_resistance', 'placebo']

# AI Model could be :
# qwen3.5:4b
# llama3:2:latest
# deepseek-r1:1.5b
# But needs to be the same as demo.py
AI = "deepseek-r1:1.5b"

PROMPT = """You are a nurse on a ward with patients one, two, three and four.
The pharmacy has these potions: {drugs}.
Below are the doctor's messages your memory has kept, oldest first.
List every order that is still in force right now. An order that the doctor
cancelled is not in force. Do not invent orders.

Doctor's messages:
{notes}

Answer with JSON only, in this exact shape:
{{"orders": [{{"patient": "one", "drug": ["strength"]}}]}}
And merge adjacent JSON lines {{"orders": [{{"patient": "X", "drug": ["Y"]}}]}} with the same "patient" 
into one line by joining "drug" arrays in order. Do not merge non-adjacent lines, separate them. Return only valid JSON lines, no outer braces. 

Ex of same "patient" adjacent lines expected shape : 
{{"orders": [{{"patient": "one", "drug": ["regeneration"]}}]}} 
{{"orders": [{{"patient": "one", "drug": ["fire_resistance"]}}]}}
Becomes this {{"orders": [{{"patient": "one", "patient": ["regeneration", "fire_resistance"]}}]}}

"""


def ask(notes, model=AI, temperature=0.0):
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
        p, d = str(it.get('patient', '')).lower().strip(), [ str(drug_read).lower().strip() for drug_read in it.get('drug', [])]

        d = [s.replace(' ', '_').replace('_potion', '') for s in d]

        d_correct = True
        if p in PATIENTS and (p, d) not in out:
            for elem in d:
                if elem not in DRUGS:
                    d_correct = False
            if d_correct:
                out.append((p, d))

    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default=AI)
    ap.add_argument('--runs', type=int, default=2, help='ask each memory this many times')
    args = ap.parse_args()

    from demo import SCRIPT, Memory
    # Tester avec la memoire on cancel, enlever commentaire pour tester les 2
    for name, rewrite in [('memory rewritten on cancel', True)] :
                        #[('memory keeps everything (naive)', False),
                          #('memory rewritten on cancel', True)]:
        mem = Memory(rewrite)
        mem.clear()
        #time.sleep(40)

        for kind, patient, drug, text in SCRIPT:
            mem.hear(kind, patient, drug, text)
        print(f'\n== {name} ==')
        for n in mem.notes:
            print('   memory:', n)
        for i in range(args.runs):
            print(f'   nurse says ({args.model}):', ask(mem.notes, args.model))
    print('\nexpected: patient three regeneration and patient four fire_resistance with regeneration only; '
          'patient one strength was cancelled.')