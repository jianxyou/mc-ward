// Minimal Mineflayer bot + HTTP bridge for the ward project.
// The server runs Minecraft 26.3 (Paper + ViaBackwards); the bot speaks 26.1,
// the newest protocol Mineflayer supports, and ViaBackwards translates.
//
//   node bot.js                      # joins localhost:25565 as WardBot
//   open http://localhost:3007       # first-person view of the bot
//   curl localhost:3000/state        # position, health, inventory, nearby chests/beds
//   curl -X POST localhost:3000/gotoCoord -H 'content-type: application/json' -d '{"x":0,"y":64,"z":0}'
//   curl -X POST localhost:3000/gotoPlace -H 'content-type: application/json' -d '{"placeName":"pharmacy"}'
//   curl -X POST localhost:3000/takeByName -H 'content-type: application/json' -d '{"containerName":"strength_potion_chest","item":"potion"}'
//
// Named places and containers come from ../ward_map.json (Sophie's layout). The file
// is re-read on every request, so editing it needs no bot restart.

const fs = require('fs')
const path = require('path')
const mineflayer = require('mineflayer')
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder')
const express = require('express')

const HOST = process.env.MC_HOST || 'localhost'
const PORT = parseInt(process.env.MC_PORT || '25565')
const BRIDGE_PORT = parseInt(process.env.BRIDGE_PORT || '3000')
const VIEWER_PORT = parseInt(process.env.VIEWER_PORT || '3007')
const MAP_PATH = process.env.WARD_MAP || path.join(__dirname, '..', 'ward_map.json')

const bot = mineflayer.createBot({
  host: HOST,
  port: PORT,
  username: process.env.BOT_NAME || 'WardBot',
  version: process.env.MC_VERSION || '1.21.4',
  auth: 'offline'
})
bot.loadPlugin(pathfinder)

// Workaround for 26.3 servers: they kick a client that sends two position updates
// without a tick_end packet in between. Mineflayer never sends tick_end and
// ViaBackwards does not add it, so we send one after every movement packet.
{
  const origWrite = bot._client.write.bind(bot._client)
  const movePackets = new Set(['position', 'position_look', 'look', 'flying'])
  bot._client.write = (name, params) => {
    origWrite(name, params)
    if (movePackets.has(name)) origWrite('tick_end', {})
  }
}

bot.on('error', e => console.error('[bot] error', e.message))
bot.on('kicked', r => console.error('[bot] kicked', JSON.stringify(r)))
bot.on('end', r => console.error('[bot] disconnected', r))

bot.once('spawn', () => {
  console.log('[bot] spawned at', bot.entity.position.toString(), 'version', bot.version)
  const moves = new Movements(bot)
  moves.canDig = false            // never break the ward
  moves.allow1by1towers = false   // never place scaffolding blocks
  moves.scafoldingBlocks = []
  moves.canOpenDoors = true
  bot.pathfinder.setMovements(moves)
  try {
    require('prismarine-viewer').mineflayer(bot, { port: VIEWER_PORT, firstPerson: true })
    console.log(`[bot] viewer on http://localhost:${VIEWER_PORT}`)
  } catch (e) {
    console.error('[bot] viewer unavailable:', e.message)
  }
})

// ---- ward map: named places and containers ----
function loadMap() {
  return JSON.parse(fs.readFileSync(MAP_PATH, 'utf8'))
}

function place(name) {
  const p = loadMap()[name]
  if (!p || typeof p.x !== 'number') throw new Error(`unknown place "${name}" (not a named spot in ward_map.json)`)
  return p
}

// A double chest is listed twice under one name; either block opens the whole inventory.
function container(name) {
  const c = (loadMap().containers || []).find(c => c.name === name)
  if (!c) throw new Error(`unknown container "${name}" (not in ward_map.json containers)`)
  return c
}

const CONTAINER_BLOCKS = new Set(['chest', 'trapped_chest', 'barrel'])
function containerBlockAt(x, y, z) {
  const block = bot.blockAt(require('vec3')(x, y, z))
  if (!block) throw new Error('no block loaded at that position')
  if (!CONTAINER_BLOCKS.has(block.name)) throw new Error(`no container at (${x},${y},${z}): the block there is ${block.name}`)
  return block
}

// ---- helpers ----
function nearbyBlocks(names, maxDistance = 96) {
  const ids = names.map(n => bot.registry.blocksByName[n]?.id).filter(x => x !== undefined)
  return bot.findBlocks({ matching: ids, maxDistance, count: 64 })
    .map(p => ({ name: bot.blockAt(p).name, x: p.x, y: p.y, z: p.z }))
}

function state() {
  const p = bot.entity.position
  return {
    position: { x: +p.x.toFixed(1), y: +p.y.toFixed(1), z: +p.z.toFixed(1) },
    health: bot.health,
    food: bot.food,
    time: bot.time.timeOfDay,
    held: bot.heldItem ? { name: bot.heldItem.name, count: bot.heldItem.count } : null,
    inventory: bot.inventory.items().map(i => ({ name: i.name, count: i.count })),
    chests: nearbyBlocks([...CONTAINER_BLOCKS]),
    beds: nearbyBlocks(Object.keys(bot.registry.blocksByName).filter(n => n.endsWith('_bed')))
  }
}

async function goto(x, y, z, range = 1) {
  await bot.pathfinder.goto(new goals.GoalNear(x, y, z, range))
  return state().position
}

async function chestContents(x, y, z) {
  const block = containerBlockAt(x, y, z)
  await goto(x, y, z, 3)   // within reach (4.5 blocks) even when the chest sits behind a counter
  const chest = await bot.openContainer(block)
  const items = chest.containerItems().map(i => ({ name: i.name, count: i.count, slot: i.slot }))
  chest.close()
  return items
}

async function moveItems(x, y, z, itemName, count, direction) {
  const block = containerBlockAt(x, y, z)
  const item = bot.registry.itemsByName[itemName]
  if (!item) throw new Error(`unknown item ${itemName}`)
  await goto(x, y, z, 3)
  const chest = await bot.openContainer(block)
  try {
    if (direction === 'take') await chest.withdraw(item.id, null, count)
    else await chest.deposit(item.id, null, count)
  } finally { chest.close() }
  return bot.inventory.items().map(i => ({ name: i.name, count: i.count }))
}

async function changeHandItem(itemName) {
  const it = bot.inventory.items().find(i => i.name === itemName)
  if (!it) throw new Error(`no ${itemName} in the inventory`)
  await bot.equip(it, 'hand')
  return bot.heldItem ? { name: bot.heldItem.name, count: bot.heldItem.count } : null
}

// ---- HTTP bridge for Python ----
const app = express()
app.use(express.json())
const wrap = fn => async (req, res) => {
  try { res.json({ ok: true, result: await fn(req.body || {}) }) }
  catch (e) { res.status(400).json({ ok: false, error: e.message }) }
}
app.get('/state', (req, res) => res.json({ ok: true, result: state() }))

// movement: by coordinate, by named place, by named container
const gotoCoord = b => goto(b.x, b.y, b.z, b.range ?? 1)
app.post('/goto', wrap(gotoCoord))            // old name, kept for compatibility
app.post('/gotoCoord', wrap(gotoCoord))
app.post('/gotoPlace', wrap(b => { const p = place(b.placeName); return goto(p.x, p.y, p.z, b.range ?? 1) }))
app.post('/gotoContainer', wrap(b => { const c = container(b.containerName); return goto(c.x, c.y, c.z, b.range ?? 2) }))

// containers: by coordinate, by name
const take = b => moveItems(b.x, b.y, b.z, b.item, b.count ?? 1, 'take')
const put = b => moveItems(b.x, b.y, b.z, b.item, b.count ?? 1, 'put')
app.post('/chest', wrap(b => chestContents(b.x, b.y, b.z)))
app.post('/take', wrap(take))                 // old name, kept for compatibility
app.post('/put', wrap(put))                   // old name, kept for compatibility
app.post('/takeByCoord', wrap(take))
app.post('/putByCoord', wrap(put))
app.post('/takeByName', wrap(b => { const c = container(b.containerName); return moveItems(c.x, c.y, c.z, b.item, b.count ?? 1, 'take') }))
app.post('/putByName', wrap(b => { const c = container(b.containerName); return moveItems(c.x, c.y, c.z, b.item, b.count ?? 1, 'put') }))
app.post('/changeHandItem', wrap(b => changeHandItem(b.itemName)))

app.post('/chat', wrap(b => { bot.chat(String(b.message)); return 'sent' }))
// Needs the bot to be an operator (server/ops.json). Teleport is the easy way
// to put the bot at the ward entrance instead of wherever the server spawns it.
app.post('/tp', wrap(b => { bot.chat(`/tp ${bot.username} ${b.x} ${b.y} ${b.z}`); return 'sent' }))
app.post('/cmd', wrap(b => { bot.chat('/' + String(b.command).replace(/^\//, '')); return 'sent' }))
app.post('/stop', wrap(() => { bot.pathfinder.stop(); bot.clearControlStates(); return 'stopped' }))
app.listen(BRIDGE_PORT, () => console.log(`[bridge] http://localhost:${BRIDGE_PORT}`))
