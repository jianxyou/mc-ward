"""Run models x memories x episodes at the text level and grade the orders the nurse
model says are in force against the state the ward should end in.

    python3 run.py --episodes episodes.json --out results.jsonl
    python3 run.py --models meta-llama/llama-3.2-3b-instruct --memories append,rewrite --n 10

Grading per patient (same categories as demo.py's grader, which reads the chests):
  correct     expected drug, delivered
  omission    expected drug, nothing delivered
  wrong drug  expected drug, another one delivered
  commission  no order in force, something delivered
Commission is split into 'cancelled' (the patient had an order that was cancelled)
and 'hallucinated' (nothing was ever ordered, or the patient was never mentioned).
"""
import argparse
import collections
import concurrent.futures as cf
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import memory as memlib   # noqa: E402
import nurse               # noqa: E402

MODELS = ['google/gemma-3-4b-it', 'qwen/qwen3.5-9b', 'google/gemma-3-12b-it',
          'mistralai/mistral-small-3.2-24b-instruct']


def grade(expected, cancelled, orders):
    got = {}
    for p, d in orders:
        got.setdefault(p, d)         # first drug named for a patient wins, as the bot would deliver it
    c = collections.Counter()
    for p, d in expected.items():
        if p not in got:
            c['omission'] += 1
        elif got[p] == d:
            c['correct'] += 1
        else:
            c['wrong_drug'] += 1
    for p in got:
        if p not in expected:
            c['commission_cancelled' if p in cancelled else 'commission_hallucinated'] += 1
    c['n_expected'] = len(expected)
    c['n_cancelled'] = len(cancelled)
    return dict(c)


def run_one(ep, model, mem_name):
    llm = lambda prompt: nurse.complete(prompt, model)   # noqa: E731
    mem = memlib.MEMORIES[mem_name](llm)
    for m in ep['messages']:
        mem.hear(m)
    orders, raw, ok = nurse.ask(mem.notes, model)
    g = grade(ep['expected'], ep['cancelled'], orders)
    return {'episode': ep['id'], 'twin_of': ep['twin_of'], 'model': model, 'memory': mem_name,
            'notes': mem.notes, 'orders': orders, 'json_ok': ok, 'raw': raw[:500], **g}


def summarise(rows):
    by = collections.defaultdict(list)
    for r in rows:
        by[(r['model'], r['memory'])].append(r)
    hdr = '%-36s %-8s %4s  %6s %6s %6s  %7s %7s  %5s' % (
        'model', 'memory', 'eps', 'corr%', 'omis%', 'wrong%', 'cancDl%', 'halluc', 'json%')
    lines = [hdr, '-' * len(hdr)]
    for (model, mem), rs in sorted(by.items()):
        n_exp = sum(r['n_expected'] for r in rs) or 1
        n_can = sum(r['n_cancelled'] for r in rs) or 1
        s = lambda k: sum(r.get(k, 0) for r in rs)  # noqa: E731
        lines.append('%-36s %-8s %4d  %5.0f%% %5.0f%% %5.0f%%  %6.0f%% %7d  %4.0f%%' % (
            model, mem, len(rs), 100.0 * s('correct') / n_exp, 100.0 * s('omission') / n_exp,
            100.0 * s('wrong_drug') / n_exp, 100.0 * s('commission_cancelled') / n_can,
            s('commission_hallucinated'), 100.0 * sum(r['json_ok'] for r in rs) / len(rs)))
    lines.append('corr/omis/wrong: share of orders in force. cancDl: share of cancelled orders that '
                 'were still delivered. halluc: deliveries to patients with no order ever.')
    return '\n'.join(lines)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', default=os.path.join(HERE, 'episodes.json'))
    ap.add_argument('--models', default=','.join(MODELS))
    ap.add_argument('--memories', default='append,window3,rewrite,summary')
    ap.add_argument('--n', type=int, default=0, help='only the first n episodes (0 = all)')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--out', default=os.path.join(HERE, 'results.jsonl'))
    a = ap.parse_args()

    eps = json.load(open(a.episodes))
    if a.n:
        eps = eps[:a.n]
    models = a.models.split(',')
    mems = a.memories.split(',')
    jobs = [(ep, m, mem) for m in models for mem in mems for ep in eps]
    print('%d episodes x %d models x %d memories = %d runs' % (len(eps), len(models), len(mems), len(jobs)))

    rows = []
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(run_one, *j) for j in jobs]
        for i, f in enumerate(cf.as_completed(futs), 1):
            try:
                rows.append(f.result())
            except Exception as e:
                print('[run] failed: %r' % e, file=sys.stderr)
            if i % 25 == 0 or i == len(jobs):
                print('  %d/%d done' % (i, len(jobs)), file=sys.stderr)
    with open(a.out, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    print(summarise(rows))
    print('rows -> %s' % a.out)
