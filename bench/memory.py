"""Memory designs. Each one hears the doctor's messages in order and then exposes
`notes`: the list of lines the nurse model gets to read.

append   every message verbatim, oldest first (the naive memory of demo.py)
window3  only the last three messages
rewrite  one entry per patient, rewritten on cancel / change (rule-based, demo.py --rewrite)
summary  a running note the model itself rewrites after every message
"""
import re

PATIENTS = ['one', 'two', 'three', 'four']


class Append:
    name = 'append'

    def __init__(self, llm=None):
        self.notes = []

    def hear(self, m):
        self.notes.append(m['text'])


class Window(Append):
    name = 'window3'
    K = 3

    def hear(self, m):
        self.notes.append(m['text'])
        self.notes = self.notes[-self.K:]


class Rewrite:
    """One entry per patient holding the doctor's latest order sentence verbatim;
    a cancellation deletes the entry, a change replaces it."""
    name = 'rewrite'

    def __init__(self, llm=None):
        self.entries = {}

    def hear(self, m):
        if m['kind'] == 'cancel':
            self.entries.pop(m['patient'], None)
        else:
            self.entries[m['patient']] = canonical(m['patient'], m['drug'])

    @property
    def notes(self):
        return list(self.entries.values()) or ['(no orders in force)']


def canonical(patient, drug):
    """The order as the doctor would state it, context-free (a 'change' or 'actually, go
    ahead' sentence on its own reads as nothing to models that never saw the earlier line)."""
    return 'Give patient %s a %s potion.' % (patient, drug.replace('_', ' '))


SUMMARY_PROMPT = """You keep the nurse's note of the doctor's standing orders on a ward with patients one, two, three and four.

Current note:
{note}

New message from the doctor:
"{msg}"

Update the note: if the message gives a new order, add it; if it cancels an order, drop that
patient's line; if it changes an order, replace that patient's line. Write one line per order in
force, in the form "Give patient X a Y potion." If nothing is in force, write "(no orders in force)".
Reply with the updated note only."""


class Summary:
    """The model maintains the note; the nurse later reads only that note."""
    name = 'summary'

    def __init__(self, llm):
        self.llm = llm            # callable(prompt) -> text
        self.note = '(no orders in force)'
        self.calls = 0

    def hear(self, m):
        out = self.llm(SUMMARY_PROMPT.format(note=self.note, msg=m['text']))
        self.calls += 1
        out = re.sub(r'<think>.*?</think>', '', out, flags=re.S).strip()
        if out:
            self.note = out[:800]

    @property
    def notes(self):
        return [ln for ln in self.note.splitlines() if ln.strip()] or ['(no orders in force)']


MEMORIES = {c.name: c for c in (Append, Window, Rewrite, Summary)}
