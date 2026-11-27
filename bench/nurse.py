"""The nurse model behind an OpenAI-style chat endpoint (OpenRouter by default).

    ask(notes, model) -> ([(patient, drug), ...], raw_text)
    complete(prompt, model) -> text          (used by the summary memory)

Key: file named by $OPENROUTER_KEY_FILE, default ../../.openrouter_key (never printed).
Responses are cached in cache.json keyed by model + prompt so re-runs are free.
"""
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get('LLM_URL', 'https://openrouter.ai/api/v1/chat/completions')
KEY_FILE = os.environ.get('OPENROUTER_KEY_FILE', os.path.join(HERE, '..', '..', '.openrouter_key'))
CACHE_FILE = os.environ.get('NURSE_CACHE') or os.path.join(HERE, 'cache.json')   # two runs at once: give one its own copy

PATIENTS = ['one', 'two', 'three', 'four']
DRUGS = ['strength', 'regeneration', 'fire_resistance']

PROMPT = """You are a nurse on a ward with patients one, two, three and four.
The pharmacy has these potions: {drugs}.
Below is what your memory has kept of the doctor's instructions, oldest first.
Decide which potions should be delivered now, and to which patients.

Doctor's instructions kept in memory:
{notes}

Answer with JSON only, in this exact shape:
{{"orders": [{{"patient": "one", "drug": "strength"}}]}}
Use an empty list if nothing should be delivered."""

# One provider per model so that results do not depend on where OpenRouter routes a call
# (DeepInfra's and NextBit's gemma-3-12b answered the same prompt differently).
PROVIDERS = {
    'google/gemma-3-4b-it': 'DeepInfra',
    'google/gemma-3-12b-it': 'DeepInfra',
    'qwen/qwen3.5-9b': 'DeepInfra',
    'mistralai/mistral-small-3.2-24b-instruct': 'DeepInfra',
    'meta-llama/llama-3.2-3b-instruct': 'Cloudflare',
}

_lock = threading.Lock()
_cache = None
usage = {'calls': 0, 'cost': 0.0}      # new (uncached) calls in this process


def _key():
    with open(os.path.expanduser(KEY_FILE)) as f:
        return f.read().strip()


def _load_cache():
    global _cache
    if _cache is None:
        try:
            _cache = json.load(open(CACHE_FILE))
        except (OSError, ValueError):
            _cache = {}
    return _cache


def _save_cache():
    tmp = CACHE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(_cache, f)
    os.replace(tmp, CACHE_FILE)


def complete(prompt, model, temperature=0.0, max_tokens=400, retries=4):
    """One chat completion, cached. Returns the text (empty string on failure)."""
    max_tokens = max(max_tokens, int(os.environ.get('NURSE_MIN_TOKENS', '0')))   # models that explain before they answer (claude-haiku-5.5)
    provider = PROVIDERS.get(model)
    h = hashlib.sha1(('nothink\n%s\n%s\n%s\n%s' % (model, provider, temperature, prompt)).encode()).hexdigest()
    with _lock:
        c = _load_cache()
        if h in c:
            return c[h]
    # reasoning off: thinking models (qwen3.5) otherwise spend the whole budget before answering
    req_body = {'model': model, 'temperature': temperature, 'max_tokens': max_tokens,
                'reasoning': {'enabled': False}, 'usage': {'include': True},
                'messages': [{'role': 'user', 'content': prompt}]}
    if provider:
        req_body['provider'] = {'order': [provider], 'allow_fallbacks': False}
    body = json.dumps(req_body).encode()
    req = urllib.request.Request(URL, data=body, headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + _key()})
    text = ''
    for attempt in range(int(os.environ.get('NURSE_RETRIES', retries))):     # long unattended runs set NURSE_RETRIES (rate limits)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
            text = data['choices'][0]['message'].get('content') or ''
            with _lock:
                usage['calls'] += 1
                usage['cost'] += (data.get('usage') or {}).get('cost') or 0.0
            break
        except urllib.error.HTTPError as e:
            msg = e.read()[:200]
            print('[nurse] HTTP %s from %s: %s' % (e.code, model, msg), file=sys.stderr)
            if e.code in (400, 401, 402, 404):
                break
        except Exception as e:  # timeouts, connection resets, odd payloads
            print('[nurse] %s: %r' % (model, e), file=sys.stderr)
        time.sleep(min(30, 2 * (attempt + 1)))
    if text:
        with _lock:
            _cache[h] = text
            _save_cache()
    return text


def parse(text):
    """Model text -> [(patient, drug), ...]; keeps only names the ward knows."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S)
    m = re.search(r'\{.*\}', text, flags=re.S)
    data = None
    if m:
        try:
            data = json.loads(m.group(0))
        except ValueError:
            data = None
    elif text.strip().startswith('['):          # a bare list, e.g. "[]" for nothing in force
        try:
            data = json.loads(text.strip())
        except ValueError:
            data = None
    out = []
    if data is not None:
        items = data.get('orders', []) if isinstance(data, dict) else data
        for it in items if isinstance(items, list) else []:
            if not isinstance(it, dict):
                continue
            p = str(it.get('patient', '')).lower().replace('patient', '').strip()
            p = {'1': 'one', '2': 'two', '3': 'three', '4': 'four'}.get(p, p)
            d = str(it.get('drug', '')).lower().strip().replace(' ', '_').replace('_potion', '')
            if p in PATIENTS and d in DRUGS and (p, d) not in out:
                out.append((p, d))
        return out, True
    # no JSON at all: scrape "patient X ... Y potion" pairs
    for p, d in re.findall(r'patient\s+(one|two|three|four)[^.\n]*?(strength|regeneration|fire[ _]resistance)', text, flags=re.I):
        pair = (p.lower(), d.lower().replace(' ', '_'))
        if pair not in out:
            out.append(pair)
    return out, False


def ask(notes, model):
    prompt = PROMPT.format(drugs=', '.join(d.replace('_', ' ') for d in DRUGS),
                           notes='\n'.join('- ' + n for n in notes) or '- (nothing)')
    raw = complete(prompt, model)
    orders, ok = parse(raw)
    return orders, raw, ok


if __name__ == '__main__':
    model = sys.argv[1] if len(sys.argv) > 1 else 'meta-llama/llama-3.2-3b-instruct'
    notes = ['Give patient one a strength potion.',
             'Patient three needs a regeneration potion.',
             'Cancel the strength potion for patient one, blood pressure is up.',
             'And a fire resistance potion for patient four, please.']
    orders, raw, ok = ask(notes, model)
    print('raw:', raw.strip()[:300])
    print('parsed:', orders, '(json)' if ok else '(scraped)')
    print('expected: [(three, regeneration), (four, fire_resistance)]')
