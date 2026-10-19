"""One scripted episode, end to end, without an LLM.

The "doctor" gives an order, the bot carries it out with hard-coded steps, and
the grader reads the world state over RCON. This is the skeleton the real
benchmark fills in: the hard-coded steps become LLM decisions, the order becomes
part of a longer conversation with cancellations and distractor chores.

    python3 example_episode.py
"""
import re
import time

from ward import Bot, Rcon

# The 2x2 stack of trapped chests near the beds: top one is the pharmacy for now,
# the two bottom ones stand for bedside tables. (The barrel at (-30,-60,27) is in a
# room the pathfinder cannot reach from the entrance; to be fixed in the build.)
PHARMACY = (-5, -58, 38)
BEDSIDE = {                   # bed label -> chest that stands for its bedside table
    'bed 1': (-5, -59, 39),
    'bed 2': (-5, -59, 38),
}
ENTRANCE = (-7, -59, 30)


def container_items(rc, pos):
    """Grader: read a container directly from the server, bypassing the bot."""
    out = rc.cmd('data get block %d %d %d Items' % pos)
    return re.findall(r'id: "minecraft:([a-z_]+)"', out)


def reset(rc):
    for pos in list(BEDSIDE.values()) + [PHARMACY]:
        rc.cmd('data modify block %d %d %d Items set value []' % pos)
    for slot in range(4):   # potions do not stack: one per slot
        rc.cmd('item replace block %d %d %d container.%d with '
               'minecraft:potion[potion_contents={potion:"minecraft:healing"}] 1' % (*PHARMACY, slot))
    rc.cmd('clear WardBot')
    rc.cmd('tp WardBot %d %d %d' % ENTRANCE)
    rc.cmd('time set day')
    time.sleep(2)


def main():
    bot, rc = Bot(), Rcon()
    reset(rc)
    print('pharmacy holds:', container_items(rc, PHARMACY))

    order = {'patient': 'bed 1', 'item': 'potion'}
    print(f"doctor: give {order['patient']} a healing potion")

    # --- what the agent does (hard-coded here, LLM-driven in the benchmark) ---
    inv = bot.take(*PHARMACY, item=order['item'], count=1)
    print('bot took the potion, inventory:', inv)
    inv = bot.put(*BEDSIDE[order['patient']], item=order['item'], count=1)
    print('bot delivered it, inventory:', inv)

    # --- grading from world state ---
    for label, pos in BEDSIDE.items():
        print(f'{label} bedside chest:', container_items(rc, pos))
    delivered = {label for label, pos in BEDSIDE.items() if 'potion' in container_items(rc, pos)}
    expected = {order['patient']}
    print('omission' if not delivered else 'wrong patient' if delivered != expected else 'correct')


if __name__ == '__main__':
    main()
