#!/usr/bin/env python3
"""
Stone to SGF — Go board photo converter
Hosted version for Render.com
"""

import http.server
import json
import urllib.request
import urllib.error
import os
import re
import sys

PORT = int(os.environ.get('PORT', 8080))
API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stone to SGF</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@200;300&family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #ffffff;
  color: #111111;
  font-family: 'Cormorant Garamond', Georgia, serif;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
}
body::before {
  content: '';
  display: block;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #6b4200 20%, #111 50%, #6b4200 80%, transparent);
  opacity: 0.4;
  flex-shrink: 0;
}
.wrap {
  width: 100%;
  max-width: 620px;
  padding: 60px 36px 90px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 48px;
  animation: rise 0.9s ease both;
}
.eyebrow {
  font-family: 'Noto Serif JP', serif;
  font-weight: 200;
  font-size: 11px;
  letter-spacing: 7px;
  color: #555555;
}
h1 { font-size: 38px; font-weight: 300; letter-spacing: 1.5px; color: #111111; }
.tagline { font-size: 15px; font-style: italic; color: #444444; }
.rule {
  width: 1px; height: 36px;
  background: linear-gradient(to bottom, transparent, #999, transparent);
  margin-bottom: 40px;
}
.panel {
  width: 100%;
  border: 1px solid #cccccc;
  background: #fafafa;
  padding: 32px 28px;
  position: relative;
}
.panel::after {
  content: '';
  position: absolute;
  inset: 6px;
  border: 1px solid #dddddd;
  pointer-events: none;
}
.panel-label {
  position: absolute;
  top: -11px; left: 22px;
  background: #ffffff;
  padding: 0 10px;
  font-family: 'Noto Serif JP', serif;
  font-weight: 200;
  font-size: 10px;
  letter-spacing: 4px;
  color: #555555;
  text-transform: uppercase;
}
.connector { width: 1px; height: 22px; background: #cccccc; margin: 0 auto; }
.drop-area {
  border: 1px dashed #cccccc;
  padding: 48px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}
.drop-area:hover, .drop-area.over {
  border-color: #6b4200;
  background: #fffaf5;
}
.stones { display: flex; justify-content: center; gap: 14px; margin-bottom: 20px; }
.st { border-radius: 50%; transition: transform 0.35s; }
.drop-area:hover .st, .drop-area.over .st { transform: translateY(-3px); }
.st.b { width: 28px; height: 28px; background: radial-gradient(circle at 34% 32%, #4a4a4a, #080808); box-shadow: 2px 4px 10px rgba(0,0,0,0.5); }
.st.w { width: 28px; height: 28px; background: radial-gradient(circle at 34% 32%, #ffffff, #ddd6ca); box-shadow: 2px 4px 8px rgba(0,0,0,0.18); border: 1px solid #cccccc; }
.drop-main { font-size: 18px; font-weight: 300; color: #444444; line-height: 1.55; }
.drop-main strong { color: #6b4200; font-weight: 400; }
.drop-sub { margin-top: 10px; font-size: 12px; color: #999999; letter-spacing: 1px; }
input[type=file] { display: none; }
#step-preview { display: none; width: 100%; }
#step-preview.show { display: block; animation: rise 0.5s ease both; }
.preview-frame { border: 1px solid #cccccc; padding: 10px; background: white; position: relative; margin-bottom: 18px; }
.preview-frame img { display: block; width: 100%; max-height: 380px; object-fit: contain; }
.frame-label { position: absolute; top: -10px; left: 18px; background: white; padding: 0 8px; font-size: 10px; letter-spacing: 3px; color: #666666; }
.btn-read {
  width: 100%; padding: 15px;
  background: #111111; color: #ffffff;
  border: none; font-family: 'Cormorant Garamond', serif;
  font-size: 16px; letter-spacing: 3px; cursor: pointer; transition: background 0.3s;
}
.btn-read:hover:not(:disabled) { background: #333333; }
.btn-read:disabled { opacity: 0.5; cursor: default; }
.btn-change {
  display: block; margin: 12px auto 0;
  background: none; border: none; color: #777777;
  font-family: 'Cormorant Garamond', serif; font-size: 13px;
  font-style: italic; cursor: pointer;
  text-decoration: underline; text-decoration-color: transparent; transition: all 0.3s;
}
.btn-change:hover { color: #6b4200; text-decoration-color: #cccccc; }
#step-loading { display: none; margin-top: 24px; text-align: center; }
#step-loading.show { display: flex; flex-direction: column; align-items: center; gap: 14px; }
.brush-loader { display: flex; gap: 5px; align-items: flex-end; height: 28px; }
.brush-loader span { width: 2px; border-radius: 1px; background: #333333; animation: ink 1.3s ease-in-out infinite; }
.brush-loader span:nth-child(1) { height: 10px; animation-delay: 0.00s; }
.brush-loader span:nth-child(2) { height: 18px; animation-delay: 0.10s; }
.brush-loader span:nth-child(3) { height: 28px; animation-delay: 0.20s; }
.brush-loader span:nth-child(4) { height: 20px; animation-delay: 0.30s; }
.brush-loader span:nth-child(5) { height: 12px; animation-delay: 0.40s; }
.brush-loader span:nth-child(6) { height: 22px; animation-delay: 0.50s; }
.brush-loader span:nth-child(7) { height: 10px; animation-delay: 0.60s; }
.loading-label { font-size: 14px; font-style: italic; color: #555555; letter-spacing: 1px; }
#step-error { display: none; margin-top: 20px; width: 100%; }
#step-error.show { display: block; }
.error-box {
  border: 1px solid #ffaaaa;
  background: #fff5f5;
  padding: 16px 18px;
  font-size: 14px; color: #cc0000; line-height: 1.6;
}
.error-box strong { display: block; margin-bottom: 4px; font-size: 15px; }
#step-result { display: none; margin-top: 24px; width: 100%; }
#step-result.show { display: block; animation: rise 0.5s ease both; }
.result-label { display: block; font-size: 10px; letter-spacing: 4px; color: #555555; margin-bottom: 10px; text-transform: uppercase; }
.sgf-box {
  background: #1a1a1a; color: #d4c4a0;
  font-family: 'Courier New', monospace; font-size: 12px;
  line-height: 1.8; padding: 20px;
  max-height: 200px; overflow-y: auto;
  white-space: pre-wrap; word-break: break-all;
}
.sgf-box::-webkit-scrollbar { width: 4px; }
.sgf-box::-webkit-scrollbar-thumb { background: #6b4200; }
.counts { display: flex; justify-content: center; gap: 32px; margin-top: 16px; font-size: 14px; color: #444444; }
.count-item { display: flex; align-items: center; gap: 8px; }
.dot { width: 13px; height: 13px; border-radius: 50%; }
.dot.b { background: radial-gradient(circle at 35% 35%, #4a4a4a, #080808); box-shadow: 1px 1px 4px rgba(0,0,0,0.5); }
.dot.w { background: radial-gradient(circle at 35% 35%, #fff, #d5cfc5); box-shadow: 1px 1px 3px rgba(0,0,0,0.2); border: 1px solid #cccccc; }
.btn-download {
  width: 100%; margin-top: 16px; padding: 14px;
  background: transparent; color: #6b4200;
  border: 1px solid #cccccc;
  font-family: 'Cormorant Garamond', serif; font-size: 15px; letter-spacing: 2px; cursor: pointer; transition: all 0.3s;
}
.btn-download:hover { background: #6b4200; color: #ffffff; border-color: #6b4200; }
.btn-again {
  display: block; margin: 18px auto 0;
  background: none; border: none; color: #777777;
  font-family: 'Cormorant Garamond', serif; font-size: 13px;
  font-style: italic; cursor: pointer;
  text-decoration: underline; text-decoration-color: transparent; transition: all 0.3s;
}
.btn-again:hover { color: #6b4200; text-decoration-color: #cccccc; }
.footer { margin-top: 56px; text-align: center; font-size: 12px; color: #999999; line-height: 1.8; }
@keyframes rise {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes ink {
  0%,100% { opacity: 0.2; transform: scaleY(0.4); }
  50%      { opacity: 1;   transform: scaleY(1); }
}
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
      <rect x="8" y="8" width="48" height="48" stroke="#cccccc" stroke-width="0.7" fill="none"/>
      <line x1="8" y1="24" x2="56" y2="24" stroke="#cccccc" stroke-width="0.5"/>
      <line x1="8" y1="40" x2="56" y2="40" stroke="#cccccc" stroke-width="0.5"/>
      <line x1="24" y1="8" x2="24" y2="56" stroke="#cccccc" stroke-width="0.5"/>
      <line x1="40" y1="8" x2="40" y2="56" stroke="#cccccc" stroke-width="0.5"/>
      <circle cx="24" cy="24" r="9" fill="url(#sb)"/>
      <circle cx="40" cy="40" r="9" fill="url(#sw)" stroke="#cccccc" stroke-width="0.5"/>
      <circle cx="40" cy="24" r="6" fill="url(#sb2)"/>
      <circle cx="24" cy="40" r="6" fill="url(#sw2)" stroke="#cccccc" stroke-width="0.4"/>
      <defs>
        <radialGradient id="sb"  cx="36%" cy="34%"><stop offset="0%" stop-color="#5a5a5a"/><stop offset="100%" stop-color="#080808"/></radialGradient>
        <radialGradient id="sw"  cx="36%" cy="34%"><stop offset="0%" stop-color="#ffffff"/><stop offset="100%" stop-color="#cec8be"/></radialGradient>
        <radialGradient id="sb2" cx="36%" cy="34%"><stop offset="0%" stop-color="#5a5a5a"/><stop offset="100%" stop-color="#080808"/></radialGradient>
        <radialGradient id="sw2" cx="36%" cy="34%"><stop offset="0%" stop-color="#ffffff"/><stop offset="100%" stop-color="#cec8be"/></radialGradient>
      </defs>
    </svg>
    <span class="eyebrow">囲碁 · 棋譜変換</span>
    <h1>Stone to SGF</h1>
    <p class="tagline">Convert board photographs to game records</p>
  </div>

  <div class="rule"></div>

  <div class="panel" id="step-upload">
    <span class="panel-label">Board Image</span>
    <div class="drop-area" id="dropArea" onclick="document.getElementById('fileInput').click()">
      <div class="stones">
        <div class="st w"></div><div class="st b"></div><div class="st w"></div>
        <div class="st b"></div><div class="st w"></div>
      </div>
      <p class="drop-main"><strong>Drop your photo here</strong><br>or tap to choose a file</p>
      <p class="drop-sub">JPG · PNG · WEBP</p>
    </div>
    <input type="file" id="fileInput" accept="image/*" onchange="handleFile(this.files[0])">
  </div>

  <div id="step-preview">
    <div class="preview-frame">
      <span class="frame-label">BOARD IMAGE</span>
      <img id="previewImg" src="" alt="Go board">
    </div>
    <button class="btn-read" id="btnRead" onclick="analyze()">READ THE STONES</button>
    <button class="btn-change" onclick="resetToUpload()">Choose a different image</button>
  </div>

  <div id="step-loading">
    <div class="brush-loader">
      <span></span><span></span><span></span><span></span>
      <span></span><span></span><span></span>
    </div>
    <p class="loading-label">Reading the board…</p>
  </div>

  <div id="step-error">
    <div class="error-box" id="errorBox">
      <strong id="errorTitle">Error</strong>
      <span id="errorDetail"></span>
    </div>
  </div>

  <div id="step-result">
    <span class="result-label">· SGF Record ·</span>
    <div class="sgf-box" id="sgfBox"></div>
    <div class="counts" id="counts"></div>
    <button class="btn-download" onclick="download()">↓ Download .sgf file</button>
    <button class="btn-again" onclick="resetAll()">Read another board</button>
  </div>

  <p class="footer">Powered by Claude Vision</p>
</div>

<script>
let imageData = null;
let currentSGF = null;

const drop = document.getElementById('dropArea');
drop.addEventListener('dragover',  e => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', e => {
  e.preventDefault(); drop.classList.remove('over');
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('image/')) handleFile(f);
});

function handleFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    imageData = e.target.result;
    document.getElementById('previewImg').src = imageData;
    document.getElementById('step-upload').style.display = 'none';
    document.getElementById('step-preview').classList.add('show');
    document.getElementById('step-result').classList.remove('show');
    hideError(); currentSGF = null;
  };
  reader.readAsDataURL(file);
}

async function analyze() {
  if (!imageData) return;
  const btn = document.getElementById('btnRead');
  btn.disabled = true; btn.textContent = 'READING…';
  document.getElementById('step-loading').classList.add('show');
  document.getElementById('step-result').classList.remove('show');
  hideError();

  const base64 = imageData.split(',')[1];
  const mediaType = imageData.match(/data:(.*?);/)[1];

  try {
    const res = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_b64: base64, media_type: mediaType })
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      const status = res.status;
      const msg = data.error?.message || 'Unknown error';
      if (status === 401) throw new Error('API key invalid — check your Render environment variable.');
      if (status === 429) throw new Error('Rate limit reached. Please wait a moment and try again.');
      throw new Error(`Error (${status}): ${msg}`);
    }
    const sgf = data.sgf || '';
    if (!sgf.includes('(;')) throw new Error('No valid SGF returned. Got: ' + sgf.slice(0, 200));
    currentSGF = sgf;
    showResult(sgf);
  } catch (err) {
    showError('Conversion failed', err.message);
  } finally {
    document.getElementById('step-loading').classList.remove('show');
    btn.disabled = false; btn.textContent = 'READ THE STONES';
  }
}

function showResult(sgf) {
  document.getElementById('sgfBox').textContent = sgf;
  const ab = sgf.match(/AB((?:\[[a-z]{2}\])+)/);
  const aw = sgf.match(/AW((?:\[[a-z]{2}\])+)/);
  const b = ab ? (ab[1].match(/\[[a-z]{2}\]/g)||[]).length : 0;
  const w = aw ? (aw[1].match(/\[[a-z]{2}\]/g)||[]).length : 0;
  document.getElementById('counts').innerHTML = `
    <div class="count-item"><div class="dot b"></div>${b} black stone${b!==1?'s':''}</div>
    <div class="count-item"><div class="dot w"></div>${w} white stone${w!==1?'s':''}</div>`;
  document.getElementById('step-result').classList.add('show');
}

function download() {
  if (!currentSGF) return;
  const blob = new Blob([currentSGF], {type:'application/x-go-sgf'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url;
  a.download = 'go-' + Date.now() + '.sgf'; a.click();
  URL.revokeObjectURL(url);
}

function showError(title, detail) {
  document.getElementById('errorTitle').textContent = title;
  document.getElementById('errorDetail').textContent = detail ? ' — ' + detail : '';
  document.getElementById('step-error').classList.add('show');
}
function hideError() { document.getElementById('step-error').classList.remove('show'); }
function resetToUpload() {
  imageData = null; currentSGF = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('step-preview').classList.remove('show');
  document.getElementById('step-result').classList.remove('show');
  document.getElementById('step-upload').style.display = '';
  hideError();
}
function resetAll() { resetToUpload(); }
</script>
</body>
</html>
"""

SYSTEM_PROMPT = """You are an expert Go (baduk/weiqi) board reader. Given an image of a Go board, output ONLY a valid SGF file. No explanations, no markdown fences, no preamble — just raw SGF starting with (;FF[4].

Rules:
- FF[4]GM[1]SZ[N] where N is 9, 13, or 19 — detect from the image
- Coordinates: columns left-to-right as a,b,c...s; rows top-to-bottom as a,b,c...s. Top-left = [aa]
- All black stones in AB[..][..]...
- All white stones in AW[..][..]...
- Start with (;FF[4] and end with )

Example:
(;FF[4]GM[1]SZ[19]CA[UTF-8]
;AB[dd][pd][dp][pp]AW[de][pe][ep][pe])"""


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Print simplified logs
        print(f"  {self.command} {self.path}")

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML.encode('utf-8'))

    def do_POST(self):
        if self.path != '/analyze':
            self.send_response(404)
            self.end_headers()
            return

        if not API_KEY:
            self._respond(500, {'error': {'message': 'ANTHROPIC_API_KEY environment variable is not set on the server.'}})
            return

        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length))

        image_b64  = body.get('image_b64', '')
        media_type = body.get('media_type', 'image/jpeg')

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_b64
                    }},
                    {"type": "text", "text": "Analyze this Go board and output the SGF."}
                ]
            }]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': API_KEY,
                'anthropic-version': '2023-06-01'
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())

            sgf = ''.join(b.get('text', '') for b in result.get('content', [])).strip()
            sgf = re.sub(r'^```[a-z]*\s*', '', sgf, flags=re.IGNORECASE)
            sgf = re.sub(r'\s*```$', '', sgf).strip()
            m = re.search(r'\(;[\s\S]*\)', sgf)
            if m:
                sgf = m.group(0)

            self._respond(200, {'sgf': sgf})

        except urllib.error.HTTPError as e:
            err_body = {}
            try:
                err_body = json.loads(e.read())
            except Exception:
                pass
            self._respond(e.code, {'error': err_body.get('error', {'message': str(e)})})
        except Exception as e:
            self._respond(500, {'error': {'message': str(e)}})

    def _respond(self, status, data):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'\n  石 Stone to SGF — listening on port {PORT}\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  Stopped.')
        server.shutdown()
