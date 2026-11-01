# mc_ward — Minecraft pipeline for the ward project

Server (Minecraft 26.3, Sophie's `Hospital` world) → Mineflayer bot (Node) → HTTP bridge → Python.

```
mc_ward/
  server/        Paper 26.3 + ViaVersion/ViaBackwards, world in server/Hospital
  bot/bot.js     Mineflayer bot + HTTP bridge (:3000) + browser viewer (:3007)
  ward.py        Python client: Bot (bridge) and Rcon (server console)
  ward_map.json  named places, beds and containers of the ward (Sophie, 29 Oct)
  demo.py        one scripted episode: doctor orders, one cancellation, bot acts, grader reads the world
  example_episode.py  Sophie's walk-through of the named API (runs on the 29 Oct world)
  npc/patient_script.dsc  Denizen dialogue for the four patient NPCs (Sophie; plugin not installed yet)
  tools/node     Node.js (no system install needed)
```

## Prerequisites

* **Java 25**: the Minecraft launcher installs one when you run version 26.3 (the setup
  script finds it on macOS); otherwise install Temurin 25 and make sure `java -version` says 25.
* **Node.js 20 or newer** from https://nodejs.org (the `canvas` package needs a prebuilt
  binary, available for macOS and Windows).
* **Python 3.9+**, no extra packages.
* Tested on macOS (Apple Silicon) only so far. On Windows, run the commands in
  `server/setup_server.sh` by hand and start the server with
  `java -Xmx4G -jar paper.jar nogui`.

## First-time setup

```
./server/setup_server.sh          # downloads Paper + Via plugins, unpacks the world (needs Java 25)
cd bot && npm install && python3 patch_viewer.py && cd ..   # needs Node >= 20
```

## Run (two terminals)

```
# 1. server (wait for "Done")
./server/start_server.sh

# 2. bot
cd bot && node bot.js
```

Then open http://localhost:3007 to watch the bot, and from Python:

```python
from ward import Bot, Rcon
bot = Bot(); rc = Rcon()
rc.cmd('tp WardBot -7 -59 30')          # put the bot at the ward entrance (see below)
s = bot.state()                         # position, held item, inventory, nearby beds/chests
bot.gotoPlace('second_floor')           # named spots and containers come from ward_map.json
bot.gotoContainer('patient_one_chest')
bot.takeByName('strength_potion_chest', 'potion')
bot.putByName('patient_one_chest', 'potion')
bot.changeHandItem('potion')            # hold it
bot.gotoCoord(-7, -59, 34, range=2)     # coordinate versions still exist
bot.chest(-5, -59, 38)                  # walk to a chest and list its contents
rc.cmd('data get block -5 -59 38 Items')  # grader: read a container without the bot
```

Bridge endpoints (`POST` unless noted):

| movement | containers | misc |
|---|---|---|
| `/gotoCoord {x,y,z,range}` (alias `/goto`) | `/chest {x,y,z}` | `GET /state` |
| `/gotoPlace {placeName}` | `/takeByCoord`, `/putByCoord {x,y,z,item,count}` (aliases `/take`, `/put`) | `/chat {message}` |
| `/gotoContainer {containerName}` | `/takeByName`, `/putByName {containerName,item,count}` | `/tp {x,y,z}`, `/cmd {command}`, `/stop` |
| | `/changeHandItem {itemName}` | |

`placeName` is any top-level key of `ward_map.json` with x/y/z; `containerName` is a `name`
in its `containers` list (a double chest is listed twice, either block works). The bot
re-reads the file on every request, so edits need no restart. Unknown names and
non-container blocks come back as a 400 with a readable error.

## Demo (no language model)

```
python3 demo.py            # memory rewrites the order on cancellation
python3 demo.py --naive    # memory only appends; the cancelled order is still carried out
```

The doctor gives three orders and withdraws one. `reset()` empties the patients' bedside
chests and stocks three pharmacy chests with one typed potion each (strength,
regeneration, fire resistance, via `potion_contents`, so the grader can tell them apart).
The agent is a few lines of Python standing in for the decision model; it walks to the
pharmacy, takes the potion, walks to the patient and puts it in the bedside chest. The
grader never asks the agent anything: it reads every bedside chest over RCON and reports
correct / omission / commission / wrong drug per patient. Run on 1 Nov: the rewriting
memory scores 2 correct, the appending memory adds one commission (patient one gets the
cancelled strength potion). About 40 s per episode.

Grader detail: `data get block … Items` prints nested components as `{...}`, so the potion
type has to be asked slot by slot with
`data get block x y z Items[k].components."minecraft:potion_contents".potion`.

## Setup notes (already done on this machine)

* Java: the Minecraft launcher's bundled JRE (Java 25) is used; see `start_server.sh`.
* Node: `tools/node` (v24 LTS, downloaded binary). Packages: mineflayer, mineflayer-pathfinder,
  express, prismarine-viewer, canvas.
* `server.properties`: `online-mode=false` (bot needs no account), `white-list=false`,
  `difficulty=peaceful`, `force-gamemode=true`, RCON on 25575 (password in the file).
* `ops.json` makes WardBot an operator so it can `/tp` itself.

## Version mismatch and the two workarounds

The world was built in **26.3**; upstream Mineflayer supports up to **26.1**.

1. The server is Paper 26.3 with ViaVersion + ViaBackwards, so the bot can connect
   with protocol `1.21.11` and be translated.
2. 26.3 servers kick a client that sends two position updates without a `tick_end`
   packet in between. Mineflayer never sends it, so `bot.js` sends one after every
   movement packet (see the wrapper near the top). Without this the bot is kicked
   two seconds after joining with "Invalid move player packet received".

3. prismarine-viewer 1.33 only renders blocks with 0 <= y < 256, and every modern
   superflat world (this one included) sits around y = -60, so the browser view was
   empty. `bot/patch_viewer.py` patches the viewer's bundles; run it once after every
   `npm install`. Hard-refresh the browser (Cmd+Shift+R) after patching.

Pathfinder is configured never to dig or place blocks, so the bot cannot damage the ward.

## Ward layout (ward_map.json, Sophie's version of 29 Oct)

Named spots: `spawn_hint` (entrance, -7 -59 30), `in_hospital`, `first_floor` (y = -59),
`second_floor` (y = -54), `pharmacy` (10 -54 34), `unit_patient_one` … `unit_patient_four`
(second floor, z = 33) and `pos_<potion>_potion` standing spots in the pharmacy.
Containers: a double chest per patient (`patient_<n>_chest`, z = 33/34) and one per potion
in the pharmacy (`strength`, `placebo`, `regeneration`, `fire_resistance`, `damage`).
19 bed blocks on the second floor (the map still lists 23, see below).

**World status (30 Oct):** `server/Hospital` and `Hospital.zip` are Sophie's save of 29 Oct
(the 19 Oct world is kept locally in `server/Hospital_old_1019/`, ignored by git). Checked
over RCON on that world: all 18 named container blocks are chests, every named spot is
reachable (the `pos_*` spots are the sign blocks, so the bot stops next to them), and the
whole flow runs: `gotoPlace` → `takeByName` from the strength chest → `changeHandItem` →
`gotoContainer` → `putByName` into `patient_one_chest`, with the grader reading the potion
back over RCON.

To settle with Sophie:

* Each pharmacy chest holds one plain `minecraft:potion` with no `potion_contents`, so the
  five drugs differ only by which chest they sit in. If grading needs to tell them apart in
  the inventory, give each a `potion_contents` or a `custom_name`.
* The pharmacy has five double chests but the map names four: `placebo_potion_chest` and
  `damage_potion_chest` both point at (8 -54 34/35), and the chest at (11 -54 37/38), next
  to the "Placebo" sign at (10 -54 37), is not listed. The sign at (9 -54 34) also reads
  Placebo instead of Damage.
* The orange beds at (10/11 -54 37/38) were removed for the pharmacy but are still listed.
* A newer map (not in the repo yet) adds `pos_give_patient_one` … `four`: `three` is
  (1 -54 33), next to patient four's chest, and `four` repeats `one`; by the pattern they
  should be x = -14, -9, -4, 1.

Grader note: a double chest has 54 slots split over its two blocks and `data get block` on
one block shows only that half (a deposit lands in whichever half has the first free slot),
so read both blocks.

The old 2×2 stack of trapped chests at (-5, -58/-59, 38/39) and the barrel at (-30, -60, 27)
are still in this world and work with the coordinate API; `reset()` in `example_episode.py`
still fills the trapped chest. The server spawns players on top of the trees near
(0, -50, 0); teleport the bot to (-7, -59, 30) first, otherwise the pathfinder finds no way
in.

## Patient NPCs (npc/patient_script.dsc)

Four Denizen assignment + interact scripts (burn, senior, accident, sick patient): greeting
within 2 blocks triggers a complaint, a handover phrase triggers thanks. Needs the Citizens
and Denizen plugins in `server/plugins/` (not installed yet). Known issue: all four greeting
triggers end with `patient one!`, so patients two to four would answer to "patient one".
