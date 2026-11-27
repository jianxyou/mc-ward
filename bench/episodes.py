"""Generate revocation episodes: the doctor gives orders, cancels some, changes some,
re-orders some. Each episode carries the state the ward should end in.

    python3 episodes.py --n 30 --seed 0 --out episodes.json

Every episode with a cancellation gets a twin that is identical except the
cancellation (and any re-order that depended on it) is removed. The pair isolates
the effect of the cancel line: same patients, same drugs, same wording elsewhere.
"""
import argparse
import json
import random

PATIENTS = ['one', 'two', 'three', 'four']
DRUGS = ['strength', 'regeneration', 'fire_resistance']


def show(drug):
    return drug.replace('_', ' ')


ORDER = [
    'Give patient {p} a {d} potion.',
    'Patient {p} needs a {d} potion.',
    'Please bring a {d} potion to patient {p}.',
    'Put a {d} potion in the chest of patient {p}.',
    'For patient {p}: one {d} potion.',
]
CANCEL = [
    'Cancel the {d} potion for patient {p}, blood pressure is up.',
    'Scrap the {d} potion for patient {p}.',
    'Patient {p} should not get the {d} potion after all.',
    'Hold the {d} potion for patient {p}, no delivery.',
    'Forget the {d} potion for patient {p}, the labs came back fine.',
]
CHANGE = [
    'Change patient {p} from {old} to a {d} potion.',
    'Patient {p} gets a {d} potion instead of the {old} one.',
    'Swap the {old} potion for patient {p} with a {d} potion.',
]
REORDER = [
    'Actually, patient {p} does need the {d} potion, go ahead.',
    'Back on for patient {p}: a {d} potion.',
    'I changed my mind, patient {p} gets the {d} potion after all.',
]


def render(rng, kind, p, d, old=None):
    t = rng.choice({'order': ORDER, 'cancel': CANCEL, 'change': CHANGE, 'reorder': REORDER}[kind])
    return t.format(p=p, d=show(d), old=show(old) if old else '')


def chains(rng):
    """One list of events per patient, in the order they must appear."""
    k = rng.choice([2, 3, 3, 4])
    patients = rng.sample(PATIENTS, k)
    out = []
    n_cancel = 1 if k == 2 else rng.choice([1, 1, 2])
    cancelled = set(rng.sample(patients, n_cancel))
    for p in patients:
        d = rng.choice(DRUGS)
        ch = [('order', p, d, None)]
        if p in cancelled:
            ch.append(('cancel', p, d, None))
            if rng.random() < 0.3:
                d2 = rng.choice(DRUGS)
                ch.append(('reorder', p, d2, None))
        elif rng.random() < 0.35:
            d2 = rng.choice([x for x in DRUGS if x != d])
            ch.append(('change', p, d2, d))
        out.append(ch)
    return out


def interleave(rng, chs):
    chs = [list(c) for c in chs]
    out = []
    while any(chs):
        i = rng.choice([i for i, c in enumerate(chs) if c])
        out.append(chs[i].pop(0))
    return out


def expected_state(events):
    st = {}
    for kind, p, d, old in events:
        if kind in ('order', 'change', 'reorder'):
            st[p] = d
        elif kind == 'cancel':
            st.pop(p, None)
    return st


def make(rng, eid, events):
    msgs = [{'kind': k, 'patient': p, 'drug': d, 'old': old, 'text': render(rng, k, p, d, old)}
            for k, p, d, old in events]
    exp = expected_state(events)
    cancelled = sorted({p for k, p, d, old in events if k == 'cancel'} - set(exp))
    return {'id': eid, 'twin_of': None, 'messages': msgs, 'expected': exp,
            'cancelled': cancelled, 'mentioned': sorted({p for k, p, d, old in events})}


def twin(rng, base, eid):
    """Same episode without the cancellations (and the re-orders that depended on them)."""
    events = [(m['kind'], m['patient'], m['drug'], m['old']) for m in base['messages']
              if m['kind'] not in ('cancel', 'reorder')]
    ep = make(rng, eid, events)
    # keep the wording of the shared lines identical to the base episode
    kept = [m for m in base['messages'] if m['kind'] not in ('cancel', 'reorder')]
    for a, b in zip(ep['messages'], kept):
        a['text'] = b['text']
    ep['twin_of'] = base['id']
    return ep


def generate(n, seed):
    rng = random.Random(seed)
    eps = []
    for i in range(n):
        base = make(rng, 'ep%03d' % i, interleave(rng, chains(rng)))
        eps.append(base)
        eps.append(twin(rng, base, 'ep%03d_twin' % i))
    return eps


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=30, help='number of base episodes (twins double it)')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--out', default='episodes.json')
    a = ap.parse_args()
    eps = generate(a.n, a.seed)
    json.dump(eps, open(a.out, 'w'), indent=1)
    n_msgs = sum(len(e['messages']) for e in eps)
    n_cancel = sum(len(e['cancelled']) for e in eps)
    print('%d episodes (%d base + twins), %d messages, %d standing cancellations -> %s'
          % (len(eps), a.n, n_msgs, n_cancel, a.out))
    for m in eps[0]['messages']:
        print('  doctor:', m['text'])
    print('  expected:', eps[0]['expected'], ' cancelled:', eps[0]['cancelled'])
