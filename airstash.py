import os
import io
import socket
import secrets
import time
import zipfile
import logging
from flask import Flask, request, jsonify, send_from_directory, send_file, abort, render_template_string
from werkzeug.utils import secure_filename
import pyperclip
import qrcode

# Enable ANSI colors in Windows CMD / PowerShell
os.system("")

# --- CONFIGURATION ---
PORT = 5000
STASH_DIR = os.path.join(os.getcwd(), "AirStash_Drop")
SESSION_TOKEN = f"{secrets.randbelow(9000) + 1000}"  # 4-digit security PIN
os.makedirs(STASH_DIR, exist_ok=True)

app = Flask(__name__)

# Mute standard Flask logs for a clean terminal UI
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

def get_lan_ip():
    """Detects active local Wi-Fi IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def verify_auth():
    token = request.args.get("token") or request.headers.get("X-AirStash-Token")
    if token != SESSION_TOKEN:
        abort(403, description="Unauthorized: Invalid AirStash session token.")

def format_size(size_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

# --- EMBEDDED DARK NEO-BRUTALIST UI ---
HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>AIRSTASH // NEO-BRUTALIST LAN BRIDGE</title>
<style>
  :root {
    --bg: #090D16;
    --surface: #111827;
    --ink: #F8FAFC;
    --blue: #00F0FF;
    --green: #00FF66;
    --gold: #FFD600;
    --red: #FF3366;
    --border: 3px solid #F8FAFC;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background-color: var(--bg);
    background-image: radial-gradient(#334155 1.5px, transparent 1.5px);
    background-size: 20px 20px;
    color: var(--ink);
    font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
    padding: 16px;
    max-width: 540px;
    margin: 0 auto;
    min-height: 100vh;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 16px;
    margin-bottom: 22px;
    background: var(--gold);
    color: #000;
    border: 3px solid #000;
    box-shadow: 6px 6px 0px var(--blue);
  }
  .brand { font-weight: 900; font-size: 1.35rem; letter-spacing: -1px; text-transform: uppercase; }
  .badge { font-size: 0.8rem; font-weight: 800; padding: 4px 10px; background: #000; color: var(--green); border: 2px solid #000; }
  .card {
    background: var(--surface);
    border: var(--border);
    padding: 18px;
    margin-bottom: 24px;
    box-shadow: 6px 6px 0px var(--blue);
  }
  .card.green-shadow { box-shadow: 6px 6px 0px var(--green); }
  .card.gold-shadow { box-shadow: 6px 6px 0px var(--gold); }
  .card-title {
    font-size: 0.85rem;
    font-weight: 900;
    text-transform: uppercase;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 3px solid var(--ink);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .tag {
    background: var(--ink);
    color: #000;
    padding: 3px 8px;
    font-size: 0.72rem;
    font-weight: 900;
    text-decoration: none;
    border: 2px solid #000;
  }
  textarea {
    width: 100%;
    height: 115px;
    background: #000;
    border: 3px solid var(--ink);
    color: var(--green);
    padding: 12px;
    font-family: inherit;
    font-size: 0.9rem;
    resize: vertical;
    outline: none;
    margin-bottom: 14px;
  }
  textarea:focus { border-color: var(--blue); }
  .btn-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  button {
    padding: 12px 10px;
    border: 3px solid #000;
    font-family: inherit;
    font-weight: 900;
    font-size: 0.82rem;
    text-transform: uppercase;
    cursor: pointer;
    box-shadow: 4px 4px 0px #F8FAFC;
    transition: transform 0.08s, box-shadow 0.08s;
  }
  button:active { transform: translate(4px, 4px); box-shadow: 0px 0px 0px #F8FAFC; }
  .btn-blue { background: var(--blue); color: #000; }
  .btn-green { background: var(--green); color: #000; }
  .drop-zone {
    border: 3px dashed var(--green);
    padding: 28px 16px;
    text-align: center;
    cursor: pointer;
    background: #000;
  }
  .progress-wrap { margin-top: 14px; display: none; background: #000; border: 3px solid var(--ink); height: 22px; }
  .progress-bar { height: 100%; width: 0%; background: var(--green); transition: width 0.1s; }
  .file-list { list-style: none; }
  .file-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 10px;
    margin-bottom: 10px;
    background: #000;
    border: 2px solid var(--ink);
    gap: 8px;
  }
  .file-item:last-child { margin-bottom: 0; }
  .file-name { font-size: 0.85rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .file-meta { font-size: 0.72rem; color: var(--gold); margin-top: 4px; font-weight: 700; }
  .actions { display: flex; gap: 8px; flex-shrink: 0; }
  .dl-btn, .del-btn {
    text-decoration: none;
    font-size: 0.75rem;
    font-weight: 900;
    padding: 8px 10px;
    border: 2px solid #000;
    box-shadow: 3px 3px 0px var(--ink);
    text-transform: uppercase;
    cursor: pointer;
  }
  .dl-btn { background: var(--gold); color: #000; }
  .del-btn { background: var(--red); color: #000; }
  #toast {
    position: fixed;
    bottom: 22px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--gold);
    color: #000;
    border: 3px solid #000;
    box-shadow: 5px 5px 0px var(--ink);
    padding: 10px 18px;
    font-weight: 900;
    font-size: 0.82rem;
    text-transform: uppercase;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s;
    z-index: 999;
  }
</style>
</head>
<body>

<header>
  <div class="brand">AirStash</div>
  <div class="badge">PIN // {{ token }}</div>
</header>

<div class="card">
  <div class="card-title">
    <span>Send/Recieve On ClipBoard</span>
    <span class="tag">LIVE_SYNC</span>
  </div>
  <textarea id="clipText" placeholder=">> PASTE TEXT TO BEAM TO LAPTOP OR PULL..."></textarea>
  <div class="btn-row">
    <button class="btn-blue" onclick="pushClipboard()">⬆ PUSH TO PC</button>
    <button class="btn-green" onclick="pullClipboard()">⬇ PULL FROM PC</button>
  </div>
</div>

<div class="card green-shadow">
  <div class="card-title">
    <span>Send/Recieve Files</span>
    <span id="pctLabel" class="tag" style="background:var(--green)">READY</span>
  </div>
  <label class="drop-zone" for="fileInput" style="display:block">
    <div style="font-size:1.8rem; margin-bottom:6px">📂</div>
    <div style="font-weight:900; font-size:0.95rem; color:var(--green)">[ TAP TO SELECT OR DROP FILES ]</div>
    <div style="font-size:0.75rem; color:#94A3B8; margin-top:6px"></div>
    <input type="file" id="fileInput" multiple style="display:none" onchange="uploadFiles(this.files)">
  </label>
  <div class="progress-wrap" id="progWrap">
    <div class="progress-bar" id="progBar"></div>
  </div>
</div>

<div class="card gold-shadow">
  <div class="card-title">
    <span>Sent/Recieved Files</span>
    <div style="display:flex; gap:6px">
      <a class="tag" style="background:var(--blue)" href="/api/zip?token={{ token }}">📦 ZIP ALL</a>
      <span class="tag" style="background:var(--gold); cursor:pointer" onclick="loadFiles()">↻ RELOAD</span>
    </div>
  </div>
  <ul class="file-list" id="fileList"></ul>
</div>

<div id="toast"></div>

<script>
  const TOKEN = "{{ token }}";

  function toast(msg) {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.style.opacity = 1;
    setTimeout(() => t.style.opacity = 0, 2200);
  }

  async function pushClipboard() {
    const text = document.getElementById("clipText").value;
    if (!text) return toast("ERR: EMPTY BUFFER");
    const res = await fetch(`/api/clipboard?token=${TOKEN}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    if (res.ok) toast("COPIED TO LAPTOP!");
  }

  async function pullClipboard() {
    const res = await fetch(`/api/clipboard?token=${TOKEN}`);
    const data = await res.json();
    document.getElementById("clipText").value = data.text || "";
    if (navigator.clipboard && data.text) {
      navigator.clipboard.writeText(data.text).catch(() => {});
    }
    toast("PULLED FROM LAPTOP!");
  }

  function uploadFiles(files) {
    if (!files.length) return;
    const formData = new FormData();
    for (const f of files) formData.append("files", f);

    const xhr = new XMLHttpRequest();
    const wrap = document.getElementById("progWrap");
    const bar = document.getElementById("progBar");
    const pctLabel = document.getElementById("pctLabel");

    wrap.style.display = "block";
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        bar.style.width = pct + "%";
        pctLabel.textContent = pct + "%";
      }
    };
    xhr.onload = () => {
      if (xhr.status === 200) {
        toast(`STASHED ${files.length} FILE(S)!`);
        pctLabel.textContent = "100% OK";
        setTimeout(() => { wrap.style.display = "none"; bar.style.width = "0%"; pctLabel.textContent = "READY"; }, 1200);
        loadFiles();
      } else {
        toast("ERR: UPLOAD FAILED");
      }
    };
    xhr.open("POST", `/api/upload?token=${TOKEN}`);
    xhr.send(formData);
  }

  async function deleteFile(filename) {
    const res = await fetch(`/api/files/${encodeURIComponent(filename)}?token=${TOKEN}`, { method: "DELETE" });
    if (res.ok) {
      toast("DELETED: " + filename);
      loadFiles();
    }
  }

  async function loadFiles() {
    const res = await fetch(`/api/files?token=${TOKEN}`);
    const data = await res.json();
    const list = document.getElementById("fileList");
    if (!data.files.length) {
      list.innerHTML = `<li style="color:#94A3B8; font-size:0.82rem; padding:8px 0">[ EMPTY DIRECTORY: ./AirStash_Drop ]</li>`;
      return;
    }
    list.innerHTML = data.files.map(f => `
      <li class="file-item">
        <div style="overflow:hidden; flex:1">
          <div class="file-name">${f.name}</div>
          <div class="file-meta">SIZE: ${f.size}</div>
        </div>
        <div class="actions">
          <a class="dl-btn" href="/files/${encodeURIComponent(f.name)}?token=${TOKEN}" download>GET ⬇</a>
          <span class="del-btn" onclick="deleteFile('${f.name.replace(/'/g, "\\'")}')">✕</span>
        </div>
      </li>
    `).join("");
  }

  loadFiles();
</script>
</body>
</html>
"""

# --- ROUTES ---
@app.route("/")
def index():
    verify_auth()
    return render_template_string(HTML_UI, token=SESSION_TOKEN)

@app.route("/api/clipboard", methods=["GET", "POST"])
def handle_clipboard():
    verify_auth()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        pyperclip.copy(text)
        print(f"\033[96m[CLIPBOARD IN]\033[0m Received {len(text)} chars from phone.")
        return jsonify({"status": "copied"})
    else:
        text = pyperclip.paste()
        return jsonify({"status": "ok", "text": text})

@app.route("/api/upload", methods=["POST"])
def handle_upload():
    verify_auth()
    uploaded = request.files.getlist("files")
    saved = []
    for f in uploaded:
        if not f.filename:
            continue
        clean_name = secure_filename(f.filename)
        dest = os.path.join(STASH_DIR, clean_name)
        if os.path.exists(dest):
            base, ext = os.path.splitext(clean_name)
            clean_name = f"{base}_{int(time.time())}{ext}"
            dest = os.path.join(STASH_DIR, clean_name)
        f.save(dest)
        saved.append(clean_name)
        print(f"\033[92m[FILE STASHED]\033[0m {clean_name}")
    return jsonify({"saved": saved})

@app.route("/api/files", methods=["GET"])
def list_files():
    verify_auth()
    items = []
    for fname in sorted(os.listdir(STASH_DIR)):
        fpath = os.path.join(STASH_DIR, fname)
        if os.path.isfile(fpath):
            items.append({"name": fname, "size": format_size(os.path.getsize(fpath))})
    return jsonify({"files": items})

@app.route("/api/files/<path:filename>", methods=["DELETE"])
def remove_file(filename):
    verify_auth()
    clean_name = secure_filename(filename)
    fpath = os.path.join(STASH_DIR, clean_name)
    if os.path.isfile(fpath):
        os.remove(fpath)
        print(f"\033[91m[FILE DELETED]\033[0m {clean_name}")
        return jsonify({"status": "deleted"})
    abort(404)

@app.route("/api/zip", methods=["GET"])
def download_zip():
    verify_auth()
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(STASH_DIR):
            fpath = os.path.join(STASH_DIR, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, arcname=fname)
    memory_file.seek(0)
    return send_file(memory_file, download_name="AirStash_Bundle.zip", as_attachment=True)

@app.route("/files/<path:filename>", methods=["GET"])
def download_file(filename):
    verify_auth()
    return send_from_directory(STASH_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    lan_ip = get_lan_ip()
    url = f"http://{lan_ip}:{PORT}/?token={SESSION_TOKEN}"

    print("\n\033[96m==================================================\033[0m")
    print("  \033[1mAirStash-By Muaz Pathan\033[0m")
    print("\033[96m==================================================\033[0m")
    print(f"  \033[93m• Stash Folder:\033[0m {STASH_DIR}")
    print(f"  \033[92m• Direct URL  :\033[0m {url}")
    print(f"  \033[95m• Session PIN :\033[0m {SESSION_TOKEN}\n")

    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    print("\n  Scan QR on your phone (must be on same Wi-Fi/Hotspot).")
    print("  Press \033[91mCtrl+C\033[0m to shut down AirStash.\n")
    app.run(host="0.0.0.0", port=PORT, threaded=True)