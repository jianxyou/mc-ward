"""Third round (night of 2026-11-24), decisions as text: what the records in the robot's memory do to the
hand-over at the end of the shift, and what a visitor can do with that. Builds on shift.py and shift_more.py.

  A  attack    can the visitor make the records himself? Harmless errands first, then the request:
                 vgift    presents the robot carries to other patients for the visitor
                 vborrow  one everyday thing of the patient at a time, handed to the visitor and given back
               and the defenses against it: privacy line (none), guard, ask, stash
  B  dose      64 and 128 deliveries; the same deliveries written as one line (count)
  C  content   which part of a record matters:
                 todesk     the potions go to the nurses' station, not into a bedside chest
                 out        other patients get a thing out of their own bedside chest
                 late       the secret is told after the deliveries, not before
                 precedent  one more record: the robot handled such a request the right way for another patient
  D  core      the table of shift_more.py (PLAN=core), for a model that has not run it yet
  E  core, small: deliveries only, 0 / 8 / 32, with and without the secret

    MODEL=gemma-3-12b PARTS=A,B,C python3 shift_explore.py
Writes explore_results_<model>.jsonl. Every run writes the whole file again; calls already made come from the cache.
"""
import concurrent.futures
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, '..', 'bench'))
import nurse        # noqa: E402
import episodes     # noqa: E402
import shift        # noqa: E402
import shift_more   # noqa: E402

shift.DELIVERIES = (0, 4, 8, 16, 32, 64, 128)      # the first deliveries of every shift stay the same ones
KINDS = ('A0', 'home')


def plan_for(parts):
    plan = []
    if 'A' in parts:
        plan += [('chores', 'full', w, n, KINDS) for w in ('none', 'guard', 'ask', 'stash') for n in (0, 8)]
        for st in ('vgift', 'vborrow'):
            plan += [(st, mem, 'none', n, KINDS) for mem in ('full', 'nosecret') for n in (2, 4, 8, 16)]
            plan += [(st, 'full', w, 8, KINDS) for w in ('guard', 'ask', 'stash')]
    if 'B' in parts:
        plan += [('chores', mem, 'none', n, KINDS) for mem in ('full', 'nosecret') for n in (32, 64, 128)]
        plan += [('count', mem, 'none', n, KINDS) for mem in ('full', 'nosecret') for n in (8, 32, 128)]
    if 'C' in parts:
        plan += [(st, mem, 'none', n, KINDS) for st in ('todesk', 'out', 'precedent') for mem in ('full', 'nosecret') for n in (8, 32)]
        plan += [('late', 'full', 'none', n, KINDS) for n in (0, 8, 32)]
    if 'D' in parts:
        plan += [('chores', mem, 'none', n, KINDS) for mem in ('full', 'nosecret') for n in (0, 4, 8, 16, 32)]
        plan += [(st, mem, 'none', 32, KINDS) for st in ('talk', 'ambient', 'others') for mem in ('full', 'nosecret')]
    if 'E' in parts:                               # the smallest version of D, for an expensive model
        plan += [('chores', mem, 'none', n, KINDS) for mem in ('full', 'nosecret') for n in (0, 8, 32)]
    seen, out = set(), []
    for row in plan:                               # the parts share some cells
        if row[:4] not in seen:
            seen.add(row[:4])
            out.append(row)
    return out


def main():
    model = shift.MODELS[os.environ.get('MODEL', 'gemma-3-12b')]
    parts = os.environ.get('PARTS', 'A,B,C').split(',')
    max_cost = float(os.environ.get('MAX_COST', '0.30'))
    seeds = (0, 1) if not os.environ.get('REDUCED') else (0,)
    eps = episodes.generate()
    plan = plan_for(parts)
    rows = []
    path = os.path.join(HERE, 'explore_results_%s.jsonl' % model.split('/')[-1])
    with open(path, 'w') as f, concurrent.futures.ThreadPoolExecutor(int(os.environ.get('THREADS', '8'))) as pool:
        for st, mem, world, n, kinds in plan:
            shift_more.style = st
            got = []
            for s in seeds:                        # one arrangement of the chest at a time: 'vborrow' names its things
                shift_more.cur_seed = s
                got += list(pool.map(lambda j: shift.probe(j[1], s, model, mem, world, n, j[0]), [(k, ep) for k in kinds for ep in eps]))
            for r in got:
                r['style'] = st
                f.write(json.dumps(r) + '\n')
            f.flush()
            rows += got
            bad = sum(not r['valid'] for r in got)
            print('  %-9s %-8s %-5s n=%-3d: %d rows, %d unreadable | %d new calls, $%.3f' % (
                st, mem, world, n, len(got), bad, nurse.usage['calls'], nurse.usage['cost']), flush=True)
            if bad > len(got) / 2:
                print('STOP: most answers are empty (API down or out of credit)', flush=True)
                break
            if nurse.usage['cost'] > max_cost:
                print('STOP: budget of $%.2f reached' % max_cost, flush=True)
                break
    print('\n%s. Percent of episodes. visitor: the revealing object is handed over / the visitor gets exactly the four everyday things; '
          'patient: gets the revealing object back / gets all five.' % model.split('/')[-1])
    print('%-9s %-8s %-5s %3s | %7s %7s | %7s %7s' % ('records', 'memory', 'world', 'n', 'v leak', 'v right', 'p evid', 'p all'))
    for st, mem, world, n, _ in plan:
        def cell(kind, key):
            return shift.pct([r for r in rows if (r['style'], r['mem'], r['world'], r['n'], r['probe']) == (st, mem, world, n, kind)], key)
        if any((r['style'], r['mem'], r['world'], r['n']) == (st, mem, world, n) for r in rows):
            print('%-9s %-8s %-5s %3d | %7s %7s | %7s %7s' % (st, mem, world, n, cell('A0', 'gave'), cell('A0', 'ok'), cell('home', 'gave'), cell('home', 'ok')))
    print('new API calls %d, reported cost $%.4f' % (nurse.usage['calls'], nurse.usage['cost']))


if __name__ == '__main__':
    main()
