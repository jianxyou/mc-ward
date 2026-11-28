# To test just one script

import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm_nurse import ask, AI

# ------------------ START Script ------------------

# Cas de base
# 1234
SCRIPT1 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "two", "regeneration", "Patient two needs a regeneration potion."),
    ("order", "three", "fire_resistance", "Patient three needs a fire_resistance potion."),
    ("order", "four", "placebo", "Patient four needs a placebo potion."),
]

# 1122
SCRIPT2 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "one", "regeneration", "Patient one needs a regeneration potion."),
    ("order", "two", "fire_resistance", "Patient two needs a fire_resistance potion."),
    ("order", "two", "placebo", "Patient two needs a placebo potion."),
]

# 111
SCRIPT3 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "one", "regeneration", "Patient one needs a regeneration potion."),
    ("order", "one", "fire_resistance", "Patient one needs a fire_resistance potion."),
]

# 1111
SCRIPT4 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "one", "regeneration", "Patient one needs a regeneration potion."),
    ("order", "one", "fire_resistance", "Patient one needs a fire_resistance potion."),
    ("order", "one", "placebo", "Patient one needs a placebo potion."),
]

# Same drug, OK but empty list []
SCRIPT5 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "one", "strength", "Patient one needs a strength potion.")
]

# Alternance devrait pas merge du tout 121
SCRIPT6 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "two", "regeneration", "Patient two needs a regeneration potion."),
    ("order", "one", "placebo", "Patient one needs a placebo potion.")
]

# Alternance devrait merge a moitie 121
SCRIPT7 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "one", "fire_resistance", "Patient one needs a fire_resistance potion."),
    ("order", "two", "regeneration", "Patient two needs a regeneration potion."),
    ("order", "one", "placebo", "Patient one needs a placebo potion.")
]

# Alternance strict
SCRIPT8 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "two", "regeneration", "Patient two needs a regeneration potion."),
    ("order", "one", "placebo", "Patient one needs a placebo potion."),
    ("order", "two", "fire_resistance", "Patient two needs a fire_resistance potion."),
    ("order", "one", "fire_resistance", "Patient one needs a fire_resistance potion."),
    ("order", "two", "placebo", "Patient two needs a placebo potion."),
]

# Longueur 
SCRIPT9 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "two", "regeneration", "Patient two needs a regeneration potion."),
    ("order", "one", "placebo", "Patient one needs a placebo potion."),
    ("order", "two", "fire_resistance", "Patient two needs a fire_resistance potion."),
    ("order", "one", "fire_resistance", "Patient one needs a fire_resistance potion."),
    ("order", "two", "placebo", "Patient two needs a placebo potion."),
    ("order", "four", "placebo", "Patient four needs a placebo potion."),
    ("order", "two", "fire_resistance", "Patient two needs a fire_resistance potion."),
    ("order", "three", "regeneration", "Patient three needs a regeneration potion."),
    ("order", "two", "strength", "Patient two needs a strength potion."),
]

# Incoherence - Drug ecrit =/ drug demande - (1)
SCRIPT10 = [
    ("order", "one", "strength", "Patient one needs a regeneration potion."),
]


# Incoherence - Drug ecrit =/ drug demande - (2)
SCRIPT11 = [
    ("order", "one", "strength", "Patient one needs a regeneration potion."),
    ("order", "two", "fire_resistance", "Patient two needs a strength potion."),
]


# Incoherence dans message - FR/EN - (1) 
SCRIPT12 = [
    ("order", "one", "strength", "Patient un a besoin a strength potion."),
    ("order", "two", "fire_resistance", "Patient two needs de la potion de resistance au feux."),
]


# Incoherence dans message - Infos non coherent - (2)
SCRIPT13 = [
    ("order", "one", "strength", "Take it yourself!"),
    ("order", "two", "strength", "Patient two needs a strength potion"),
]

# Cancel (1)
SCRIPT14 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "two", "regeneration", "Patient two needs a regeneration potion."),
    ("cancel", "two", "regeneration", "Patient two needs a regeneration potion."),
    ("order", "one", "placebo", "Patient one needs a placebo potion.")
]

# Cancel (2)
SCRIPT15 = [
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "two", "regeneration", "Patient two needs a regeneration potion."),
    ("order", "one", "strength", "Patient one needs a strength potion."),
    ("order", "three", "placebo", "Patient three needs a placebo potion."),
    ("cancel", "one", "strength", "Patient one needs a strength potion."),
]

# ------------------ END Script ------------------



if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=AI)
    ap.add_argument("--runs", type=int, default=1, help="ask each memory this many times")
    args = ap.parse_args()

    from demo import Memory
    for name, rewrite in [("memory rewritten on cancel", True)] :
        mem = Memory(rewrite)
        mem.clear()
        
        for kind, patient, drug, text in SCRIPT5: # Change here
            mem.hear(kind, patient, drug, text)
        print(f"\n== {name} ==")
        for n in mem.notes:
            print("   memory:", n)
        for i in range(args.runs):
            pred =  ask(mem.notes, args.model)
            # Remove empty list (if there is any)
            pred = [(patient, drug) for patient, drug in pred if drug]
            
            print(f"   nurse says ({args.model}):", pred)
