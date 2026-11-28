import json, time
import pandas as pd
from itertools import groupby
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm_nurse import ask

N_RUNS = 2
rows = []
def parse_expected(expected):
    return [(patient, list(drugs)) for patient, drugs in expected or []]

for sc in json.load(open("performance/scenarios.json", encoding="utf-8")):
    notes = [e[3] for e in sc["orders"]]
    expected =  parse_expected(sc["expected"])
    for run in range(N_RUNS):
        start, pred, error = time.time(), None, None
        try:
            pred = ask(notes)
            # Remove empty list (if there is any)
            pred = [(patient, drug) for patient, drug in pred if drug]
        except Exception as e:
            error = type(e).__name__

        got = [(b[0], i) for b in pred or [] for i in b[1]]
        want = [(b[0], i) for b in expected for i in b[1]]
        ok = sum(p in want for p in got)
        rows.append({"id": sc["id"], "run": run, "exact": pred == expected,
                     "error": error,
                     "precision": ok / len(got) if got else 0,
                     "recall": ok / len(want),
                     "latency": round(time.time() - start, 2), "pred": pred,})

df = pd.DataFrame(rows)
df.to_json("performance/results.jsonl", orient="records", lines=True, force_ascii=False)
print(df.groupby("id")[["exact", "precision", "recall", "latency"]].mean().round(2))
print("\nErrors:", df.error.value_counts().to_dict())
