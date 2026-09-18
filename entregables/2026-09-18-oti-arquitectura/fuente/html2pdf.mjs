// Uso: node html2pdf.mjs entrada.html salida.pdf "Título pie"
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os'; import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const [inp, out, pie] = process.argv.slice(2);
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const prof = mkdtempSync(join(tmpdir(), 'cdp-'));
const port = 9300 + Math.floor(Math.random()*500);
const ch = spawn(chrome, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${prof}`, '--no-first-run', 'about:blank']);
const sleep = ms => new Promise(r => setTimeout(r, ms));
let tgt;
for (let i=0;i<60;i++){ try{ const l = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); tgt = l.find(t=>t.type==='page'); if(tgt) break; }catch{} await sleep(250); }
const ws = new WebSocket(tgt.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id=0; const pend = new Map(); const ev=[];
ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id);} else ev.push(d); };
const send = (method, params={}) => new Promise(r => { const i=++id; pend.set(i, r); ws.send(JSON.stringify({id:i, method, params})); });
await send('Page.enable');
await send('Page.navigate', { url: pathToFileURL(resolve(inp)).href });
for (let i=0;i<80 && !ev.some(e=>e.method==='Page.loadEventFired');i++) await sleep(250);
await send('Runtime.evaluate', { expression: 'document.fonts.ready.then(()=>1)', awaitPromise: true });
await sleep(800);
const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;');
const r = await send('Page.printToPDF', {
  printBackground: true, preferCSSPageSize: true, displayHeaderFooter: true,
  headerTemplate: '<span></span>',
  footerTemplate: `<div style="font-family:Segoe UI,Arial;font-size:8px;color:#6f6b5c;width:100%;padding:0 18mm;display:flex;justify-content:space-between"><span>${esc(pie)}</span><span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>`,
  marginTop: 0.75, marginBottom: 0.8, marginLeft: 0.7, marginRight: 0.7,
});
if (!r.result) { console.error(JSON.stringify(r)); process.exit(1); }
writeFileSync(out, Buffer.from(r.result.data, 'base64'));
ws.close(); ch.kill(); console.log('PDF', out);
