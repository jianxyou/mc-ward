import json, collections
from math import comb
def mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
def load(f): return [json.loads(l) for l in open(f)]
files = dict(att8='world_attack_results.jsonl', att2='world_attack2_results.jsonl', att16='world_attack16_results.jsonl', long='world_long_results.jsonl', base='world_shift_results.jsonl')
R = {k: load(v) for k, v in files.items()}
for k, f in files.items():
    lg = load(f.replace('results', 'log'))
    lg = [x for x in lg if not x.get('failed')]
    tot = sum(x['n'] for x in lg); done = sum(x['deliveries_done'] for x in lg)
    notes = [n for x in lg for n in (x.get('delivery_notes') or [])]
    errs = [e for x in lg for e in (x.get('errors') or [])]
    rows = R[k]
    print('%-6s shifts %3d | errands/deliveries %d/%d | notes %d | errors %d | requests %d, world matches decision %d | styles %s' % (
        k, len(lg), done, tot, len(notes), len(errs), len(rows), sum(bool(r['matches_decision']) for r in rows), collections.Counter(r.get('style') for r in rows)))
    if notes: print('   e.g.', notes[:2])
def cell(rows, **kw):
    return {r['id']: bool(r['gave_world']) for r in rows if all(r.get(a) == b for a, b in kw.items())}
def show(name, d): print('  %-34s %2d/%d' % (name, sum(d.values()), len(d)))
def pair(a, b, na, nb):
    ids = sorted(set(a) & set(b)); bb = sum(a[i] and not b[i] for i in ids); cc = sum(b[i] and not a[i] for i in ids)
    print('  paired %s vs %s: %d only-first, %d only-second, p=%.4f (n=%d)' % (na, nb, bb, cc, mcnemar(bb, cc), len(ids)))
print('\nvisitor errands in the game (gemma-12b, full memory, privacy line only)')
for p in ('A0', 'A1', 'home'):
    print(' probe', p)
    c2 = cell(R['att2'], probe=p); c8 = cell(R['att8'], probe=p, world='none'); c16 = cell(R['att16'], probe=p)
    show('2 errands', c2); show('8 errands', c8); show('16 errands', c16)
    b8 = cell(R['base'], probe=p, mem='full', world='none'); show('8 doctor deliveries (11/23 night)', b8)
    for w in ('guard', 'ask', 'stash'):
        cw = cell(R['att8'], probe=p, world=w); show('8 errands + ' + w, cw); pair(c8, cw, 'none', w)
print('\n32 deliveries in the game')
for p in ('A0', 'A1', 'home'):
    f = cell(R['long'], probe=p, mem='full'); ns = cell(R['long'], probe=p, mem='nosecret')
    b8 = cell(R['base'], probe=p, mem='full', world='none')
    print(' probe', p); show('secret, 32', f); show('no secret, 32', ns); show('secret, 8 (11/23)', b8); pair(f, ns, 'secret32', 'nosecret32'); pair(f, b8, 'secret32', 'secret8')
# ordinary things for the visitor / patient gets all
print('\nvisitor gets exactly the four everyday things (ok), 8 errands, by defense')
for w in ('none', 'guard', 'ask', 'stash'):
    for p in ('A0', 'home'):
        rs = [r for r in R['att8'] if r['world'] == w and r['probe'] == p]
        print('  %-6s %-5s ok %2d/%d  ordinary in world avg %.1f' % (w, p, sum(bool(r['ok']) for r in rs), len(rs), sum(r['ordinary_world'] for r in rs) / len(rs)))
