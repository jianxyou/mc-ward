import json, os, sys, glob
from math import comb
P = os.path.dirname(os.path.abspath(__file__)) + '/'
MODELS = [('gemma-3-4b-it', 'gemma-4b'), ('gemma-3-12b-it', 'gemma-12b'), ('gemma-3-27b-it', 'gemma-27b'), ('mistral-small-3.2-24b-instruct', 'mistral-24b'),
          ('gemini-3.1-flash-lite', 'gemini-fl'), ('deepseek-v4.1-flash', 'deepseek'), ('claude-haiku-5.5', 'haiku-5.5')]
def mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
def load(m):
    D = {}
    fs = [P + 'shift_results_%s.jsonl' % m, P + ('shift_more_results.jsonl' if m == 'gemma-3-12b-it' else 'shift_more_results_%s.jsonl' % m), P + 'explore_results_%s.jsonl' % m]
    for f in fs:
        if not os.path.exists(f): continue
        for l in open(f):
            r = json.loads(l)
            if r.get('probe') not in ('A0', 'home') or 'gave' not in r: continue
            D[(r.get('style', 'chores'), r['mem'], r['world'], r['n'], r['probe'], r['id'], r['seed'])] = r
    return D
ALL = {short: load(m) for m, short in MODELS}
def cell(D, st, mem, world, n, probe, key='gave'):
    return {(k[5], k[6]): bool(r[key]) for k, r in D.items() if k[:5] == (st, mem, world, n, probe)}
def pc(d): return ' --' if not d else '%3.0f' % (100 * sum(d.values()) / len(d))
def inval(D, st, mem, world, n, probe): return sum(not r['valid'] for k, r in D.items() if k[:5] == (st, mem, world, n, probe))
def p(a, b):
    ids = set(a) & set(b)
    if not ids: return '   --'
    bb = sum(a[i] and not b[i] for i in ids); cc = sum(b[i] and not a[i] for i in ids)
    return '%.3f' % mcnemar(bb, cc)
def table(title, cols, key='gave', probe='A0'):
    print('\n' + title); print('%-12s' % '' + ''.join('%9s' % c[0] for c in cols))
    for _, s in MODELS:
        print('%-12s' % s + ''.join('%9s' % pc(cell(ALL[s], *c[1], probe, key)) for c in cols))
def tests(title, pairs, probe='A0', key='gave'):
    print('\n' + title + '  (paired exact test, p)'); print('%-12s' % '' + ''.join('%22s' % t for t, _, _ in pairs))
    for _, s in MODELS:
        print('%-12s' % s + ''.join('%22s' % ('%s>%s p=%s' % (pc(cell(ALL[s], *a, probe, key)).strip(), pc(cell(ALL[s], *b, probe, key)).strip(), p(cell(ALL[s], *a, probe, key), cell(ALL[s], *b, probe, key)))) for _, a, b in pairs))
C = lambda st, mem, w, n: (st, mem, w, n)
table('T1 visitor leak, NO secret told, doctor deliveries n', [(str(n), C('chores', 'nosecret', 'none', n)) for n in (0, 4, 8, 16, 32, 64, 128)])
table('T2 visitor leak, secret told, doctor deliveries n', [(str(n), C('chores', 'full', 'none', n)) for n in (0, 4, 8, 16, 32, 64, 128)])
table('T3 visitor leak at n=32, other records', [(a, C(st, mem, 'none', 32)) for st in ('talk', 'ambient', 'others') for mem, a in (('full', st[:5] + '+s'), ('nosecret', st[:5] + '-s'))])
tests('E1 no secret: 0 vs 32 deliveries; talk32; ambient32', [('n0 > n32', C('chores', 'nosecret', 'none', 0), C('chores', 'nosecret', 'none', 32)),
      ('n0 > talk32', C('chores', 'nosecret', 'none', 0), C('talk', 'nosecret', 'none', 32)), ('n0 > amb32', C('chores', 'nosecret', 'none', 0), C('ambient', 'nosecret', 'none', 32))])
tests('E2 secret vs no secret', [('n=0: secret > none', C('chores', 'full', 'none', 0), C('chores', 'nosecret', 'none', 0)), ('n=32: secret > none', C('chores', 'full', 'none', 32), C('chores', 'nosecret', 'none', 32)),
      ('secret: n0 > n32', C('chores', 'full', 'none', 0), C('chores', 'full', 'none', 32))])
table('T4 visitor errands (vgift), secret told: leak', [('n=0', C('chores', 'full', 'none', 0))] + [(str(n), C('vgift', 'full', 'none', n)) for n in (2, 4, 8, 16)] + [('-s ' + str(n), C('vgift', 'nosecret', 'none', n)) for n in (2, 8, 16)])
tests('E3 errands', [('secret: n0 > vgift8', C('chores', 'full', 'none', 0), C('vgift', 'full', 'none', 8)), ('secret: n0 > vgift16', C('chores', 'full', 'none', 0), C('vgift', 'full', 'none', 16)),
      ('vgift8 vs chores8', C('vgift', 'full', 'none', 8), C('chores', 'full', 'none', 8))])
table('T5 vborrow, leak', [('n=0', C('chores', 'full', 'none', 0))] + [(str(n), C('vborrow', 'full', 'none', n)) for n in (2, 4, 8, 16)] + [('-s ' + str(n), C('vborrow', 'nosecret', 'none', n)) for n in (2, 4, 8, 16)])
for st in ('vgift', 'chores'):
    table('T6 defenses after 8 %s: visitor leak' % st, [(w, C(st, 'full', w, 8)) for w in ('none', 'guard', 'ask', 'stash')])
    table('T6 defenses after 8 %s: visitor gets exactly the 4 everyday things' % st, [(w, C(st, 'full', w, 8)) for w in ('none', 'guard', 'ask', 'stash')], key='ok')
    table('T6 defenses after 8 %s: patient gets the object back (home)' % st, [(w, C(st, 'full', w, 8)) for w in ('none', 'guard', 'ask', 'stash')], probe='home')
    table('T6 defenses after 8 %s: patient gets all five (home, ok)' % st, [(w, C(st, 'full', w, 8)) for w in ('none', 'guard', 'ask', 'stash')], probe='home', key='ok')
table('T7 n=0: patient gets the object back (home)', [('secret', C('chores', 'full', 'none', 0)), ('no secr', C('chores', 'nosecret', 'none', 0)), ('guard', C('chores', 'full', 'guard', 0)), ('ask', C('chores', 'full', 'ask', 0)), ('stash', C('chores', 'full', 'stash', 0))], probe='home')
table('T7b home, secret told, deliveries n', [(str(n), C('chores', 'full', 'none', n)) for n in (0, 4, 8, 16, 32)], probe='home')
table('T7c home, NO secret, deliveries n', [(str(n), C('chores', 'nosecret', 'none', n)) for n in (0, 4, 8, 16, 32)], probe='home')
tests('E4 home', [('n0: secret vs none', C('chores', 'full', 'none', 0), C('chores', 'nosecret', 'none', 0)), ('secret: n0 > n32', C('chores', 'full', 'none', 0), C('chores', 'full', 'none', 32)), ('n0: none vs stash', C('chores', 'full', 'none', 0), C('chores', 'full', 'stash', 0))], probe='home')
table('T8 content (secret told): leak', [(a, C(st, 'full', 'none', n)) for st, a in (('chores', 'chor'), ('count', 'count'), ('todesk', 'desk'), ('out', 'out'), ('precedent', 'prec'), ('late', 'late')) for n in (8, 32)][:12])
print('   columns: chores 8,32 | count 8,32 | todesk 8,32 | out 8,32 | precedent 8,32 | late 8,32')
table('T8b content (no secret): leak', [(a, C(st, 'nosecret', 'none', n)) for st, a in (('chores', 'chor'), ('count', 'count'), ('todesk', 'desk'), ('out', 'out'), ('precedent', 'prec')) for n in (8, 32)])
tests('E5 content, secret told', [('chores32 vs count32', C('chores', 'full', 'none', 32), C('count', 'full', 'none', 32)), ('chores32 vs prec32', C('chores', 'full', 'none', 32), C('precedent', 'full', 'none', 32)), ('chores8 vs prec8', C('chores', 'full', 'none', 8), C('precedent', 'full', 'none', 8)), ('chores32 vs late32', C('chores', 'full', 'none', 32), C('late', 'full', 'none', 32))])
tests('E5b no secret', [('chores32 vs count32', C('chores', 'nosecret', 'none', 32), C('count', 'nosecret', 'none', 32)), ('chores32 vs desk32', C('chores', 'nosecret', 'none', 32), C('todesk', 'nosecret', 'none', 32)), ('chores32 vs out32', C('chores', 'nosecret', 'none', 32), C('out', 'nosecret', 'none', 32))])
tests('E6 defenses after 8 vgift, leak', [('none vs guard', C('vgift', 'full', 'none', 8), C('vgift', 'full', 'guard', 8)), ('none vs ask', C('vgift', 'full', 'none', 8), C('vgift', 'full', 'ask', 8)), ('none vs stash', C('vgift', 'full', 'none', 8), C('vgift', 'full', 'stash', 8))])
print('\nunreadable rows per model:', {s: sum(not r['valid'] for r in ALL[s].values()) for _, s in MODELS}, 'rows', {s: len(ALL[s]) for _, s in MODELS})
