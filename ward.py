"""Python side of the ward pipeline.

Two channels:
  * the bot bridge (bot/bot.js, HTTP on :3000): what the agent can do and see;
  * RCON to the server (:25575): what the grader can do (teleport, read any block,
    set up episodes) without going through the agent.

    from ward import Bot, Rcon
    bot = Bot(); print(bot.state()['beds'][:3])
    rc = Rcon(); print(rc.cmd('data get block -5 -58 38 Items'))
"""
import json
import socket
import struct
import urllib.request

BRIDGE = 'http://localhost:3000'


class Bot:
    def __init__(self, base=BRIDGE, timeout=90):
        self.base, self.timeout = base, timeout

    def _get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=self.timeout) as r:
            return json.load(r)['result']

    def _post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers={'content-type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                out = json.load(r)
        except urllib.error.HTTPError as e:
            out = json.load(e)  # the bridge answers 400 with {"ok": false, "error": ...}
        if not out.get('ok'):
            raise RuntimeError(out.get('error'))
        return out['result']

    def state(self):
        return self._get('/state')

    def goto(self, x, y, z, range=1):
        return self._post('/goto', {'x': x, 'y': y, 'z': z, 'range': range})

    def chest(self, x, y, z):
        return self._post('/chest', {'x': x, 'y': y, 'z': z})

    def take(self, x, y, z, item, count=1):
        """Walk to a container and take `count` of `item` (e.g. 'potion') into the inventory."""
        return self._post('/take', {'x': x, 'y': y, 'z': z, 'item': item, 'count': count})

    def put(self, x, y, z, item, count=1):
        """Walk to a container and put `count` of `item` from the inventory into it."""
        return self._post('/put', {'x': x, 'y': y, 'z': z, 'item': item, 'count': count})

    def chat(self, message):
        return self._post('/chat', {'message': message})

    def tp(self, x, y, z):
        return self._post('/tp', {'x': x, 'y': y, 'z': z})

    def cmd(self, command):
        return self._post('/cmd', {'command': command})

    def stop(self):
        return self._post('/stop', {})


class Rcon:
    """Minimal Minecraft RCON client (Source RCON protocol)."""

    def __init__(self, host='localhost', port=25575, password='wardlocal'):
        self.sock = socket.create_connection((host, port), timeout=10)
        self._id = 0
        self._send(3, password)
        rid, _, _ = self._recv()
        if rid == -1:
            raise RuntimeError('rcon auth failed')

    def _send(self, kind, payload):
        self._id += 1
        body = struct.pack('<ii', self._id, kind) + payload.encode() + b'\x00\x00'
        self.sock.sendall(struct.pack('<i', len(body)) + body)

    def _recv(self):
        (length,) = struct.unpack('<i', self._read(4))
        data = self._read(length)
        rid, kind = struct.unpack('<ii', data[:8])
        return rid, kind, data[8:-2].decode(errors='replace')

    def _read(self, n):
        buf = b''
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError('rcon closed')
            buf += chunk
        return buf

    def cmd(self, command):
        self._send(2, command)
        _, _, text = self._recv()
        return text


if __name__ == '__main__':
    b = Bot()
    s = b.state()
    print('bot at', s['position'])
    print(len(s['beds']), 'bed blocks,', len(s['chests']), 'chests')
    rc = Rcon()
    print('rcon:', rc.cmd('list'))
