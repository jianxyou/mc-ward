"""One scripted ward episode: a doctor gives three orders and withdraws one.

    python3 demo.py                  # memory rewrites the order on cancellation
    python3 demo.py --naive          # memory only appends; the cancelled order survives
    python3 demo.py --llm            # a language model (Ollama, llama3.2) plays the nurse
    python3 demo.py --llm --naive    # ... and has to notice the cancellation by itself

Server and bot must be running (see README). Without --llm the "agent" is a few lines
of Python standing in for the decision model. The point is the loop the benchmark will
use: doctor messages -> memory -> actions in the world -> grading from the world state,
never from what the agent says.
"""
import argparse
import json
import os
import re
import time

from ward import Bot, Rcon

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = json.load(open(os.path.join(HERE, 'ward_map.json'), encoding='utf-8'))
ENTRANCE = MAP['spawn_hint']
PATIENTS = ['one', 'two', 'three', 'four']

# drug -> (pharmacy chest in ward_map.json, potion type the grader can read back).
# placebo and damage are left out: the map gives both the same chest.
DRUGS = {
    'strength': ('strength_potion_chest', 'minecraft:strength'),
    'regeneration': ('regeneration_potion_chest', 'minecraft:regeneration'),
    'fire_resistance': ('fire_resistance_potion_chest', 'minecraft:fire_resistance'),
}

# what the doctor says, in order
SCRIPT = [
    ('order', 'one', 'strength', 'Give patient one a strength potion.'),
    ('order', 'three', 'regeneration', 'Patient three needs a regeneration potion.'),
    ('cancel', 'one', 'strength', 'Cancel the strength potion for patient one, blood pressure is up.'),
    ('order', 'four', 'fire_resistance', 'And a fire resistance potion for patient four, please.'),
]


def blocks(name):
    """All blocks of a named container (a double chest is two blocks)."""
    return [(c['x'], c['y'], c['z']) for c in MAP['containers'] if c['name'] == name]


# ---------------------------------------------------------------- world setup
def reset(rc):
    for p in PATIENTS:
        for pos in blocks(f'patient_{p}_chest'):
            rc.cmd('data modify block %d %d %d Items set value []' % pos)
    for chest, potion in DRUGS.values():
        halves = blocks(chest)
        for pos in halves:
            rc.cmd('data modify block %d %d %d Items set value []' % pos)
        rc.cmd('item replace block %d %d %d container.0 with '
               'minecraft:potion[potion_contents={potion:"%s"}] 1' % (*halves[0], potion))
    rc.cmd('clear WardBot')
    rc.cmd('tp WardBot %d %d %d' % (ENTRANCE['x'], ENTRANCE['y'], ENTRANCE['z']))
    rc.cmd('time set day')
    time.sleep(2)


# ---------------------------------------------------------------- the agent
class Memory:
    """What the agent kept of the doctor's messages.

    rewrite=True : a cancellation deletes the order's entry (the memory is rewritten).
    rewrite=False: a cancellation is just one more entry, the order's entry stays.
    """

    def __init__(self, rewrite):
        self.rewrite, self.entries = rewrite, []

    def hear(self, kind, patient, drug, text):
        if kind == 'cancel' and self.rewrite:
            self.entries = [e for e in self.entries
                            if not (e['kind'] == 'order' and (e['patient'], e['drug']) == (patient, drug))]
        else:
            self.entries.append({'kind': kind, 'patient': patient, 'drug': drug, 'text': text})

    @property
    def notes(self):
        """The messages as text, for a language model."""
        return [e['text'] for e in self.entries]

    @property
    def orders(self):
        """The rule-based nurse: every order entry still in memory is in force."""
        return [(e['patient'], e['drug']) for e in self.entries if e['kind'] == 'order']


def deliver(bot, patient, drug):
    chest, _ = DRUGS[drug]
    bot.gotoPlace(f'pos_{drug}_potion')
    bot.takeByName(chest, 'potion')
    bot.gotoContainer(f'patient_{patient}_chest')
    bot.putByName(f'patient_{patient}_chest', 'potion')


# ---------------------------------------------------------------- the grader
def chest_potions(rc, name):
    """Potion types in a named container, e.g. ['strength']. A plain potion is 'potion'."""
    found = []
    for pos in blocks(name):   # read both halves of the double chest
        listing = rc.cmd('data get block %d %d %d Items' % pos)
        ids = re.findall(r'id: "minecraft:([a-z_]+)"', listing)
        for k, item in enumerate(ids):
            # `data get ... Items` elides nested components as {...}, so ask slot by slot
            out = rc.cmd('data get block %d %d %d Items[%d].components."minecraft:potion_contents".potion' % (*pos, k))
            m = re.search(r'"minecraft:([a-z_]+)"', out)
            found.append(m.group(1) if m else item)
    return found


def grade(rc, expected):
    """expected: {patient: drug} for the orders still in force at the end."""
    counts = {'correct': 0, 'omission': 0, 'commission': 0, 'wrong drug': 0}
    for p in PATIENTS:
        got, want = chest_potions(rc, f'patient_{p}_chest'), expected.get(p)
        if want and got == [want]:
            verdict = 'correct'
        elif want and not got:
            verdict = 'omission'
        elif want:
            verdict = 'wrong drug'
        elif got:
            verdict = 'commission'
        else:
            verdict = 'nothing due'
        if verdict in counts:
            counts[verdict] += 1
        print(f'  patient {p:5s}  bedside chest: {", ".join(got) or "empty":<22}  expected: {want or "nothing":<16}  -> {verdict}')
    return counts


# ---------------------------------------------------------------- episode
def main(rewrite, llm=None):
    bot, rc = Bot(), Rcon()
    print('resetting the ward')
    reset(rc)
    memory = Memory(rewrite)
    expected = {}
    print('\n--- doctor speaks, agent listens ---')
    for kind, patient, drug, text in SCRIPT:
        rc.cmd(f'say [Doctor] {text}')
        print(f'doctor: {text}')
        memory.hear(kind, patient, drug, text)
        if kind == 'order':
            expected[patient] = drug
        else:
            expected.pop(patient, None)
        time.sleep(1)
    print('\nmemory now holds:')
    for n in memory.notes:
        print(f'  - {n}')
    if llm:
        import llm_nurse
        orders = llm_nurse.ask(memory.notes, model=llm)
        print(f'\nnurse model ({llm}) says these orders are in force: {orders}')
    else:
        orders = memory.orders
        print(f'\nrule-based nurse says these orders are in force: {orders}')
    print('\n--- agent acts ---')
    for patient, drug in orders:
        t = time.time()
        deliver(bot, patient, drug)
        print(f'  delivered {drug} to patient {patient}  ({time.time() - t:.0f}s)')
    print('\n--- grader reads the world ---')
    counts = grade(rc, expected)
    print(f'\nsummary: {counts}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--naive', action='store_true', help='memory only appends, never rewrites')
    ap.add_argument('--llm', nargs='?', const='llama3.2', default=None, metavar='MODEL',
                    help='let an Ollama model play the nurse (default model: llama3.2)')
    args = ap.parse_args()
    main(rewrite=not args.naive, llm=args.llm)
