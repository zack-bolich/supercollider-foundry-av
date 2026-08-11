const path = require('path');
const express = require('express');
const http = require('http');
const { WebSocketServer, WebSocket } = require('ws');
const dgram = require('dgram');

const HTTP_PORT = 8899;
const OSC_PORT = 57220;
const HOST = '127.0.0.1';
const ALLOWED = new Set(['/av/section', '/av/beat', '/av/hit', '/av/note', '/av/stop']);

const app = express();
app.use(express.static(path.join(__dirname, 'public')));
app.get('/health', (_req, res) => res.json({ ok: true, oscPort: OSC_PORT, clients: wss.clients.size, received }));

const server = http.createServer(app);
const wss = new WebSocketServer({ server });
let received = 0;
let lastEvent = null;

function readOscString(buffer, offset) {
  const end = buffer.indexOf(0, offset);
  if (end < 0) throw new Error('unterminated OSC string');
  return [buffer.toString('utf8', offset, end), (end + 4) & ~3];
}

function parseOsc(buffer) {
  let offset = 0;
  let address, tags;
  [address, offset] = readOscString(buffer, offset);
  [tags, offset] = readOscString(buffer, offset);
  if (!tags.startsWith(',')) throw new Error('invalid OSC type tag');
  const args = [];
  for (const tag of tags.slice(1)) {
    if (tag === 'i') { args.push(buffer.readInt32BE(offset)); offset += 4; }
    else if (tag === 'f') { args.push(buffer.readFloatBE(offset)); offset += 4; }
    else if (tag === 's') { let value; [value, offset] = readOscString(buffer, offset); args.push(value); }
    else throw new Error(`unsupported OSC type: ${tag}`);
  }
  return { address, args };
}

function broadcast(payload) {
  const body = JSON.stringify(payload);
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) client.send(body);
  }
}

wss.on('connection', client => {
  client.send(JSON.stringify({ type: 'relay', status: 'connected', oscPort: OSC_PORT, received, lastEvent }));
});

const udp = dgram.createSocket('udp4');
udp.on('message', packet => {
  try {
    const message = parseOsc(packet);
    if (!ALLOWED.has(message.address)) return;
    received += 1;
    lastEvent = Date.now();
    broadcast({ type: 'osc', address: message.address, args: message.args, received, at: lastEvent });
  } catch (error) {
    console.error('[OSC DROP]', error.message);
  }
});
udp.on('error', error => console.error('[OSC ERROR]', error.message));
udp.bind(OSC_PORT, HOST, () => console.log(`[OSC] udp://${HOST}:${OSC_PORT}`));

server.listen(HTTP_PORT, HOST, () => {
  console.log(`[WEB] http://${HOST}:${HTTP_PORT}`);
  console.log('[READY] SuperCollider → OSC → WebSocket → Three.js machine war');
});

function shutdown() {
  try { broadcast({ type: 'relay', status: 'stopping' }); } catch (_) {}
  try { udp.close(); } catch (_) {}
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 1000).unref();
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
