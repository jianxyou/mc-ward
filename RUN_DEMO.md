# Running the ward demo

What you will see: a doctor gives three orders and cancels one, the bot walks to the
pharmacy, takes potions and puts them in the patients' bedside chests, and a grader checks
the chests and prints a verdict per patient. One run takes about 40 seconds.

You need three programs installed first:

| Program | Where | How to check |
|---|---|---|
| Java 25 | the Minecraft launcher installs it when you run version 26.3 once | the setup script finds it for you |
| Node.js (LTS) | https://nodejs.org | `node -v` prints `v22` or newer |
| Python 3 | https://www.python.org/downloads (tick "Add python to PATH") | `python --version` |

Then get the code: on GitHub click the green **Code** button → **Download ZIP** and unzip
it, or if you have Git:

```
git clone https://github.com/jianxyou/mc-ward.git
```

All commands below are typed inside the `mc-ward` folder.

## Windows

Open PowerShell in the `mc-ward` folder (in Explorer: right click → "Open in Terminal").

**1. One-time setup** (downloads the server and unpacks the world, about a minute)

```
powershell -ExecutionPolicy Bypass -File server\setup_server.ps1
cd bot
npm install
python patch_viewer.py
cd ..
```

**2. Start the server.** Double-click `server\start_server.bat`, or run it from the
terminal. Wait until it prints a line containing `Done`. Leave this window open.

**3. Start the bot.** Open a second terminal in the `mc-ward` folder:

```
cd bot
node bot.js
```

Wait for `[bot] spawned`. Leave this window open too.

**4. Run the demo.** Open a third terminal in the `mc-ward` folder:

```
python demo.py
python demo.py --naive
```

## macOS

Same steps, with these commands instead:

```
./server/setup_server.sh                                   # step 1
cd bot && npm install && python3 patch_viewer.py && cd ..   # step 1, bot
./server/start_server.sh                                   # step 2
cd bot && node bot.js                                      # step 3, second terminal
python3 demo.py                                            # step 4, third terminal
python3 demo.py --naive
```

## What the two runs should print

`demo.py` uses a memory that deletes an order when the doctor cancels it:

```
  patient one    bedside chest: empty             expected: nothing           -> nothing due
  patient three  bedside chest: regeneration      expected: regeneration      -> correct
  patient four   bedside chest: fire_resistance   expected: fire_resistance   -> correct
summary: {'correct': 2, 'omission': 0, 'commission': 0, 'wrong drug': 0}
```

`demo.py --naive` uses a memory that only appends, so the cancelled order survives:

```
  patient one    bedside chest: strength          expected: nothing           -> commission
  ...
summary: {'correct': 2, 'omission': 0, 'commission': 1, 'wrong drug': 0}
```

## Watching the bot

* Browser: open http://localhost:3007 while the demo runs (first-person view of the bot).
  If the page is blank, hard-refresh it (Ctrl+Shift+R).
* In the game: start Minecraft 26.3, Multiplayer → Direct Connection → `localhost`. You
  spawn on the trees; to get to the ward run this in a terminal in the `mc-ward` folder,
  with your own player name:

  ```
  python -c "from ward import Rcon; rc=Rcon(); print(rc.cmd('tp YourName -7 -59 30')); print(rc.cmd('gamemode spectator YourName'))"
  ```

  Spectator mode lets you fly through walls and follow the bot. The ward is on the second
  floor (y = -54): the four beds are along z = 33 from x = -15 to 2, the pharmacy is around
  (10, -54, 37).

## If something goes wrong

* `setup_server.ps1` says no Java: run Minecraft 26.3 once from the launcher, then run the
  script again.
* `npm install` fails on `canvas`: install the Node.js LTS (not the "Current" version) and
  try again.
* The bot prints `kicked` or `disconnected`: start the server first and wait for `Done`,
  then start the bot. If the server has been running a long time, restart the bot.
* `demo.py` says `No path to the goal!`: the bot is outside the ward. Run
  `python -c "from ward import Rcon; print(Rcon().cmd('tp WardBot -7 -59 30'))"` and try again.
* Anything else: copy the error message and send it over.
