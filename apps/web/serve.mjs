// Serve the exported Next app for a local two-process production preview.
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = fileURLToPath(new URL('./out/', import.meta.url));
const types = {'.html':'text/html', '.css':'text/css', '.js':'application/javascript', '.woff2':'font/woff2', '.json':'application/json'};
http.createServer(async (req, res) => {
  try {
    const name = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const file = path.resolve(root, '.' + (name === '/' ? '/index.html' : name));
    if (!file.startsWith(root)) throw new Error();
    const body = await readFile(file);
    res.writeHead(200, {'Content-Type': types[path.extname(file)] || 'application/octet-stream'});
    res.end(body);
  } catch { res.writeHead(404); res.end(); }
}).listen(Number(process.env.PORT || 3000), '0.0.0.0');
