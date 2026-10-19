# mc_ward — Minecraft pipeline for the ward project

Server (Minecraft 26.3, Sophie's `Hospital` world) → Mineflayer bot (Node) → HTTP bridge → Python.

```
mc_ward/
  server/        Paper 26.3 + ViaVersion/ViaBackwards, world in server/Hospital
  bot/bot.js     Mineflayer bot + HTTP bridge (:3000) + browser viewer (:3007)
  ward.py        Python client: Bot (bridge) and Rcon (server console)
  ward_map.json  coordinates of beds and containers in the ward
  tools/node     Node.js (no system install needed)
```

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
rc.cmd('tp WardBot -7 -59 30')          # put the bot in the ward
s = bot.state()                         # position, inventory, nearby beds/chests
bot.goto(-7, -59, 34, range=2)          # walk to a bed
bot.chest(-5, -59, 38)                  # walk to a chest and list its contents
rc.cmd('data get block -5 -59 38 Items')  # grader: read a container without the bot
```

Bridge endpoints: `GET /state`, `POST /goto {x,y,z,range}`, `POST /chest {x,y,z}`,
`POST /chat {message}`, `POST /tp {x,y,z}`, `POST /cmd {command}`, `POST /stop`.

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

## Ward layout (from ward_map.json)

16 beds on two floors (4 at y = -59, 12 at y = -54), a 2×2 stack of trapped chests at
(-5, -58/-59, 38/39) and a barrel at (-30, -60, 27). All containers are empty for now.
The server spawns players on top of the trees near (0, -50, 0); teleport the bot
to (-7, -59, 30) first, otherwise the pathfinder finds no way down.
