# mc_ward — Minecraft pipeline for the ward project

Server (Minecraft 26.3, Sophie's `Hospital` world) → Mineflayer bot (Node) → HTTP bridge → Python.

```
mc_ward/
  server/        Paper 26.3 + ViaVersion/ViaBackwards, world in server/Hospital
  bot/bot.js     Mineflayer bot + HTTP bridge (:3000) + browser viewer (:3007)
  ward.py        Python client: Bot (bridge) and Rcon (server console)
  ward_map.json  named places, beds and containers of the ward (Sophie, 29 Oct)
  example_episode.py  Sophie's walk-through of the named API (needs her world, see below)
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
23 bed blocks on the second floor.

**Status of our copy of the world (checked over RCON on 30 Oct):** all 23 bed blocks are
there, the spots `in_hospital`, `first_floor` and `second_floor` are reachable, but none of
the 18 named container blocks exist (the blocks are air) and the `unit_patient_*` /
`pos_*_potion` spots are inside blocks, so `takeByName`, `putByName` and
`example_episode.py` cannot run here yet. Sophie built those in her own copy of the world;
we need her updated `Hospital` world folder (zip of `saves/Hospital`) to replace
`server/Hospital`. Two things to check with her in the map: `placebo_potion_chest` and
`damage_potion_chest` have the same coordinates (8 -54 34/35), and the white bed block
at (-15 -54 37) that exists in the world is missing from the list.

The old 2×2 stack of trapped chests at (-5, -58/-59, 38/39) is still in our copy and still
works with the coordinate API. The server spawns players on top of the trees near
(0, -50, 0); teleport the bot to (-7, -59, 30) first, otherwise the pathfinder finds no way
in.

## Patient NPCs (npc/patient_script.dsc)

Four Denizen assignment + interact scripts (burn, senior, accident, sick patient): greeting
within 2 blocks triggers a complaint, a handover phrase triggers thanks. Needs the Citizens
and Denizen plugins in `server/plugins/` (not installed yet). Known issue: all four greeting
triggers end with `patient one!`, so patients two to four would answer to "patient one".
