#!/usr/bin/env python3
"""
LocalDrop - Fast LAN File Transfer
Run: python3 transfer.py
Then open browser on phone: http://<laptop-ip>:8080
"""

import http.server
import os
import sys
import socket
import threading
import urllib.parse
import html
import json
import mimetypes
from pathlib import Path
from datetime import datetime

UPLOAD_DIR = Path("./received_files")
PORT = 8080

UPLOAD_DIR.mkdir(exist_ok=True)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LocalDrop</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --accent: #00d4aa;
    --accent-dim: rgba(0, 212, 170, 0.12);
    --text: #e8eaf0;
    --muted: #6b7280;
    --danger: #ff4d6d;
    --success: #00d4aa;
    --warn: #f59e0b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    min-height: 100vh;
    padding: 24px 16px;
  }
  .header {
    text-align: center;
    margin-bottom: 32px;
  }
  .logo {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 8px;
  }
  h1 {
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: var(--text);
  }
  .subtitle {
    font-size: 14px;
    color: var(--muted);
    margin-top: 6px;
  }
  .ip-badge {
    display: inline-block;
    background: var(--accent-dim);
    border: 1px solid var(--accent);
    color: var(--accent);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    margin-top: 12px;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    max-width: 640px;
    margin-left: auto;
    margin-right: auto;
  }
  .card h2 {
    font-size: 15px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 16px;
  }
  .drop-zone {
    border: 2px dashed var(--border);
    border-radius: 12px;
    padding: 48px 24px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
  }
  .drop-zone:hover, .drop-zone.dragover {
    border-color: var(--accent);
    background: var(--accent-dim);
  }
  .drop-icon {
    font-size: 40px;
    margin-bottom: 12px;
  }
  .drop-text {
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 6px;
  }
  .drop-sub {
    font-size: 13px;
    color: var(--muted);
  }
  #file-input {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
    width: 100%;
    height: 100%;
  }
  .btn {
    background: var(--accent);
    color: #0f1117;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    width: 100%;
    margin-top: 16px;
    transition: opacity 0.2s;
    letter-spacing: 0.02em;
  }
  .btn:hover { opacity: 0.88; }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .progress-wrap {
    display: none;
    margin-top: 16px;
  }
  .progress-bar {
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 8px;
  }
  .progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 3px;
    transition: width 0.15s ease;
    width: 0%;
  }
  .progress-label {
    font-size: 13px;
    color: var(--muted);
    display: flex;
    justify-content: space-between;
  }
  .file-queue {
    margin-top: 14px;
    display: none;
  }
  .file-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: var(--bg);
    border-radius: 8px;
    margin-bottom: 6px;
    font-size: 13px;
  }
  .file-item .fname {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text);
  }
  .file-item .fsize {
    color: var(--muted);
    font-family: monospace;
    font-size: 12px;
  }
  .file-item .fstatus {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--border);
    flex-shrink: 0;
  }
  .file-item .fstatus.done { background: var(--success); }
  .file-item .fstatus.uploading {
    background: transparent;
    border: 2px solid var(--accent);
    animation: spin 0.8s linear infinite;
  }
  .file-item .fstatus.error { background: var(--danger); }
  @keyframes spin { to { transform: rotate(360deg); } }
  .toast {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%) translateY(80px);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 500;
    transition: transform 0.3s ease;
    z-index: 99;
    white-space: nowrap;
  }
  .toast.show { transform: translateX(-50%) translateY(0); }
  .toast.success { border-color: var(--success); color: var(--success); }
  .toast.error { border-color: var(--danger); color: var(--danger); }
  .files-list { list-style: none; }
  .files-list li {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 0;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
  }
  .files-list li:last-child { border-bottom: none; }
  .files-list a {
    color: var(--accent);
    text-decoration: none;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .files-list a:hover { text-decoration: underline; }
  .files-list .meta {
    color: var(--muted);
    font-size: 12px;
    font-family: monospace;
    flex-shrink: 0;
  }
  .empty { color: var(--muted); font-size: 14px; text-align: center; padding: 20px 0; }
  .speed-display {
    font-family: 'SF Mono', monospace;
    font-size: 12px;
    color: var(--accent);
    text-align: right;
  }
</style>
</head>
<body>
<div class="header">
  <div class="logo">⚡ LocalDrop</div>
  <h1>File Transfer</h1>
  <div class="subtitle">LAN only · No internet · Max speed</div>
  <div class="ip-badge" id="ip-display">Loading...</div>
</div>

<div class="card">
  <h2>Upload Files</h2>
  <div class="drop-zone" id="drop-zone">
    <input type="file" id="file-input" multiple>
    <div class="drop-icon">📂</div>
    <div class="drop-text">Tap to select files</div>
    <div class="drop-sub">or drag & drop here</div>
  </div>
  <div class="file-queue" id="file-queue"></div>
  <button class="btn" id="upload-btn" disabled>Select files first</button>
  <div class="progress-wrap" id="progress-wrap">
    <div class="progress-bar">
      <div class="progress-fill" id="progress-fill"></div>
    </div>
    <div class="progress-label">
      <span id="progress-text">Uploading...</span>
      <span class="speed-display" id="speed-text"></span>
    </div>
  </div>
</div>

<div class="card">
  <h2>Received Files</h2>
  <div id="files-container"><div class="empty">No files yet</div></div>
</div>

<div class="toast" id="toast"></div>

<script>
let selectedFiles = [];

// Get server IP
fetch('/api/info').then(r=>r.json()).then(d=>{
  document.getElementById('ip-display').textContent = d.ip + ':' + d.port;
}).catch(()=>{
  document.getElementById('ip-display').textContent = window.location.host;
});

// Load file list
function loadFiles() {
  fetch('/api/files').then(r=>r.json()).then(files=>{
    const c = document.getElementById('files-container');
    if (!files.length) { c.innerHTML='<div class="empty">No files yet</div>'; return; }
    c.innerHTML = '<ul class="files-list">' + files.map(f=>`
      <li>
        <a href="/files/${encodeURIComponent(f.name)}" download="${f.name}">${f.name}</a>
        <span class="meta">${f.size}</span>
      </li>`).join('') + '</ul>';
  });
}
loadFiles();
setInterval(loadFiles, 3000);

// File select
const input = document.getElementById('file-input');
const dropZone = document.getElementById('drop-zone');
const btn = document.getElementById('upload-btn');

function setFiles(files) {
  selectedFiles = Array.from(files);
  const q = document.getElementById('file-queue');
  if (!selectedFiles.length) { q.style.display='none'; btn.disabled=true; btn.textContent='Select files first'; return; }
  q.style.display = 'block';
  q.innerHTML = selectedFiles.map((f,i)=>`
    <div class="file-item" id="fitem-${i}">
      <div class="fstatus" id="fstatus-${i}"></div>
      <span class="fname">${f.name}</span>
      <span class="fsize">${fmtSize(f.size)}</span>
    </div>`).join('');
  btn.disabled = false;
  btn.textContent = `Upload ${selectedFiles.length} file${selectedFiles.length>1?'s':''}`;
}

input.addEventListener('change', ()=>setFiles(input.files));
dropZone.addEventListener('dragover', e=>{e.preventDefault();dropZone.classList.add('dragover');});
dropZone.addEventListener('dragleave', ()=>dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e=>{e.preventDefault();dropZone.classList.remove('dragover');setFiles(e.dataTransfer.files);});

function fmtSize(b) {
  if(b<1024) return b+'B';
  if(b<1048576) return (b/1024).toFixed(1)+'KB';
  if(b<1073741824) return (b/1048576).toFixed(1)+'MB';
  return (b/1073741824).toFixed(2)+'GB';
}

function fmtSpeed(bps) {
  if(bps<1024) return bps.toFixed(0)+' B/s';
  if(bps<1048576) return (bps/1024).toFixed(0)+' KB/s';
  return (bps/1048576).toFixed(1)+' MB/s';
}

function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + type;
  setTimeout(()=>t.className='toast', 3000);
}

// Upload
btn.addEventListener('click', async ()=>{
  if(!selectedFiles.length) return;
  btn.disabled = true;
  const pw = document.getElementById('progress-wrap');
  const pf = document.getElementById('progress-fill');
  const pt = document.getElementById('progress-text');
  const sp = document.getElementById('speed-text');
  pw.style.display = 'block';

  let done=0, errors=0;
  for(let i=0;i<selectedFiles.length;i++) {
    const f = selectedFiles[i];
    const statusEl = document.getElementById('fstatus-'+i);
    statusEl.className = 'fstatus uploading';
    pt.textContent = `Uploading ${f.name}...`;

    try {
      const startT = Date.now();
      let lastLoaded = 0;
      let lastTime = startT;

      await new Promise((resolve,reject)=>{
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = e=>{
          if(!e.lengthComputable) return;
          const now = Date.now();
          const dt = (now-lastTime)/1000;
          if(dt>0.2) {
            const bps = (e.loaded-lastLoaded)/dt;
            sp.textContent = fmtSpeed(bps);
            lastLoaded = e.loaded;
            lastTime = now;
          }
          const pct = (i/selectedFiles.length + e.loaded/e.total/selectedFiles.length)*100;
          pf.style.width = pct+'%';
        };
        xhr.onload = ()=>{ if(xhr.status===200) resolve(); else reject(xhr.responseText); };
        xhr.onerror = ()=>reject('Network error');
        const fd = new FormData();
        fd.append('file', f);
        xhr.open('POST', '/upload');
        xhr.send(fd);
      });
      statusEl.className = 'fstatus done';
      done++;
    } catch(e) {
      statusEl.className = 'fstatus error';
      errors++;
    }
    pf.style.width = ((i+1)/selectedFiles.length*100)+'%';
  }

  sp.textContent = '';
  pt.textContent = `Done: ${done} uploaded${errors?' · '+errors+' failed':''}`;
  loadFiles();
  selectedFiles = [];
  input.value='';
  btn.disabled=false;
  btn.textContent='Select files first';
  document.getElementById('file-queue').style.display='none';
  if(errors===0) showToast(`✓ ${done} file${done>1?'s':''} uploaded`,'success');
  else showToast(`${errors} file${errors>1?'s':''} failed`,'error');
  setTimeout(()=>pw.style.display='none', 3000);
});
</script>
</body>
</html>
"""

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

def fmt_size(b):
    for u in ['B','KB','MB','GB']:
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.2f} TB"

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # Suppress default logs

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())

        elif path == '/api/info':
            data = json.dumps({"ip": get_local_ip(), "port": PORT}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)

        elif path == '/api/files':
            files = []
            for f in sorted(UPLOAD_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file():
                    files.append({"name": f.name, "size": fmt_size(f.stat().st_size)})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(files).encode())

        elif path.startswith('/files/'):
            fname = urllib.parse.unquote(path[7:])
            fpath = UPLOAD_DIR / fname
            if fpath.exists() and fpath.is_file():
                mime = mimetypes.guess_type(fname)[0] or 'application/octet-stream'
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(fpath.stat().st_size))
                self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
                self.end_headers()
                with open(fpath, 'rb') as f:
                    while chunk := f.read(1024*1024):
                        self.wfile.write(chunk)
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != '/upload':
            self.send_response(404)
            self.end_headers()
            return

        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            self.send_response(400)
            self.end_headers()
            return

        boundary = content_type.split('boundary=')[-1].encode()
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length)

        # Parse multipart
        parts = data.split(b'--' + boundary)
        for part in parts[1:-1]:
            if b'\r\n\r\n' not in part:
                continue
            headers_raw, body = part.split(b'\r\n\r\n', 1)
            body = body.rstrip(b'\r\n')
            headers_str = headers_raw.decode('utf-8', errors='replace')

            fname = None
            for line in headers_str.split('\r\n'):
                if 'filename=' in line:
                    fname = line.split('filename=')[-1].strip().strip('"')
                    break
            if not fname:
                continue

            # Safe filename
            fname = Path(fname).name
            dest = UPLOAD_DIR / fname
            # Avoid overwrite
            if dest.exists():
                stem = dest.stem
                suffix = dest.suffix
                i = 1
                while dest.exists():
                    dest = UPLOAD_DIR / f"{stem}_{i}{suffix}"
                    i += 1

            with open(dest, 'wb') as f:
                f.write(body)
            print(f"  ✓ Received: {dest.name} ({fmt_size(dest.stat().st_size)})")

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')


class ThreadedServer(http.server.ThreadingHTTPServer):
    pass

if __name__ == '__main__':
    ip = get_local_ip()
    server = ThreadedServer(('0.0.0.0', PORT), Handler)

    print(f"""
╔══════════════════════════════════════╗
║         ⚡ LocalDrop Running         ║
╠══════════════════════════════════════╣
║  Open on phone:                      ║
║  http://{ip}:{PORT}          ║
║                                      ║
║  Files saved to: ./received_files/   ║
║  Press Ctrl+C to stop                ║
╚══════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
