#!/usr/bin/env python3
"""
Stone to SGF — Go board photo to SGF converter
Render.com deployment — single file, no API key needed.
pip install opencv-python-headless numpy
"""

import http.server, json, os, base64, traceback
import cv2
import numpy as np

PORT = int(os.environ.get('PORT', 8080))

# ---------------------------------------------------------------------------
# Computer Vision Pipeline
# ---------------------------------------------------------------------------

def cluster_lines(positions, min_gap=8):
    if not positions:
        return []
    positions = sorted(positions)
    clusters = [[positions[0]]]
    for p in positions[1:]:
        if p - clusters[-1][-1] < min_gap:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return [int(np.mean(c)) for c in clusters]


def detect_board_region(gray):
    """Find the board bounding box. Falls back to a tight crop."""
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    h_img, w_img = gray.shape
    for contour in contours[:5]:
        if cv2.contourArea(contour) < w_img * h_img * 0.1:
            continue
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(contour)
            if 0.7 < w / h < 1.3:
                return x, y, w, h
    m = int(min(w_img, h_img) * 0.03)
    return m, m, w_img - 2*m, h_img - 2*m


def detect_grid(board_gray):
    """Return 19-element h_grid and v_grid (pixel positions of each line)."""
    h, w = board_gray.shape
    edges = cv2.Canny(board_gray, 40, 120)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180,
                             threshold=80,
                             minLineLength=int(min(h, w) * 0.4),
                             maxLineGap=5)
    h_pos, v_pos = [], []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 5:
                h_pos.append((y1 + y2) // 2)
            elif angle > 85:
                v_pos.append((x1 + x2) // 2)
    margin = int(min(h, w) * 0.02)
    h_inner = [x for x in cluster_lines(h_pos) if margin < x < h - margin]
    v_inner = [x for x in cluster_lines(v_pos) if margin < x < w - margin]

    def make_grid(inner, size):
        if len(inner) >= 2:
            first, last = inner[0], inner[-1]
        else:
            first, last = int(size * 0.05), int(size * 0.95)
        return [int(first + i * (last - first) / 18) for i in range(19)]

    return make_grid(h_inner, h), make_grid(v_inner, w)


def classify_intersection(board_gray, ry, cx, window,
                           dark_thresh=120, bright_thresh=195, stone_frac=0.5):
    """
    Black stone:  >50% of window pixels are dark  (< dark_thresh)
    White stone:  >50% of window pixels are bright (> bright_thresh)
    Empty:        neither — only the thin grid-line cross is dark (~10%)
    """
    bh, bw = board_gray.shape
    y1, y2 = max(0, ry - window), min(bh, ry + window + 1)
    x1, x2 = max(0, cx - window), min(bw, cx + window + 1)
    region = board_gray[y1:y2, x1:x2]
    total = region.size
    if total == 0:
        return 'empty'
    if np.sum(region < dark_thresh) / total > stone_frac:
        return 'black'
    if np.sum(region > bright_thresh) / total > stone_frac:
        return 'white'
    return 'empty'


def image_to_sgf(img_bytes):
    COORDS = 'abcdefghijklmnopqrs'
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image. Please use JPEG, PNG, or WEBP.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bx, by, bw, bh = detect_board_region(gray)
    board_gray = gray[by:by + bh, bx:bx + bw]
    h_grid, v_grid = detect_grid(board_gray)

    # Adaptive window: ~35% of cell size, minimum 4px
    cell_size = (h_grid[-1] - h_grid[0]) / 18
    window = max(4, int(cell_size * 0.35))

    black_stones, white_stones = [], []
    for row_i in range(19):
        for col_i in range(19):
            result = classify_intersection(
                board_gray, h_grid[row_i], v_grid[col_i], window)
            coord = f'[{COORDS[col_i]}{COORDS[row_i]}]'
            if result == 'black':
                black_stones.append(coord)
            elif result == 'white':
                white_stones.append(coord)

    if not black_stones and not white_stones:
        raise ValueError(
            "No stones detected. Make sure the image shows a clear "
            "top-down view of a Go board with good contrast.")

    sgf = (f"(;FF[4]GM[1]SZ[19]CA[UTF-8]AP[Stone-to-SGF-CV:1.0]\n"
           f";AB{''.join(black_stones)}AW{''.join(white_stones)})")
    return sgf, len(black_stones), len(white_stones)


# ---------------------------------------------------------------------------
# Inline HTML
# ---------------------------------------------------------------------------

HTML_STR = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stone to SGF</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@200;300&family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fff;color:#111;font-family:'Cormorant Garamond',Georgia,serif;min-height:100vh;display:flex;flex-direction:column;align-items:center}
body::before{content:'';display:block;width:100%;height:2px;background:linear-gradient(90deg,transparent,#6b4200 20%,#111 50%,#6b4200 80%,transparent);opacity:.4;flex-shrink:0}
.wrap{width:100%;max-width:620px;padding:60px 36px 90px;display:flex;flex-direction:column;align-items:center}
.header{display:flex;flex-direction:column;align-items:center;gap:12px;margin-bottom:48px;animation:rise .9s ease both}
.eyebrow{font-family:'Noto Serif JP',serif;font-weight:200;font-size:11px;letter-spacing:7px;color:#555}
h1{font-size:38px;font-weight:300;letter-spacing:1.5px;color:#111}
.tagline{font-size:15px;font-style:italic;color:#444}
.rule{width:1px;height:36px;background:linear-gradient(to bottom,transparent,#999,transparent);margin-bottom:40px}
.panel{width:100%;border:1px solid #ccc;background:#fafafa;padding:32px 28px;position:relative}
.panel::after{content:'';position:absolute;inset:6px;border:1px solid #ddd;pointer-events:none}
.panel-label{position:absolute;top:-11px;left:22px;background:#fff;padding:0 10px;font-family:'Noto Serif JP',serif;font-weight:200;font-size:10px;letter-spacing:4px;color:#555;text-transform:uppercase}
.drop-area{border:1px dashed #ccc;padding:48px 24px;text-align:center;cursor:pointer;transition:all .3s}
.drop-area:hover,.drop-area.over{border-color:#6b4200;background:#fffaf5}
.stones{display:flex;justify-content:center;gap:14px;margin-bottom:20px}
.st{border-radius:50%;transition:transform .35s}
.drop-area:hover .st,.drop-area.over .st{transform:translateY(-3px)}
.st.b{width:28px;height:28px;background:radial-gradient(circle at 34% 32%,#4a4a4a,#080808);box-shadow:2px 4px 10px rgba(0,0,0,.5)}
.st.w{width:28px;height:28px;background:radial-gradient(circle at 34% 32%,#fff,#ddd6ca);box-shadow:2px 4px 8px rgba(0,0,0,.18);border:1px solid #ccc}
.drop-main{font-size:18px;font-weight:300;color:#444;line-height:1.55}
.drop-main strong{color:#6b4200;font-weight:400}
.drop-sub{margin-top:10px;font-size:12px;color:#999;letter-spacing:1px}
input[type=file]{display:none}
#step-preview{display:none;width:100%}
#step-preview.show{display:block;animation:rise .5s ease both}
.preview-frame{border:1px solid #ccc;padding:10px;background:#fff;position:relative;margin-bottom:18px}
.preview-frame img{display:block;width:100%;max-height:380px;object-fit:contain}
.frame-label{position:absolute;top:-10px;left:18px;background:#fff;padding:0 8px;font-size:10px;letter-spacing:3px;color:#666}
.btn-read{width:100%;padding:15px;background:#111;color:#fff;border:none;font-family:'Cormorant Garamond',serif;font-size:16px;letter-spacing:3px;cursor:pointer;transition:background .3s}
.btn-read:hover:not(:disabled){background:#333}
.btn-read:disabled{opacity:.5;cursor:default}
.btn-change{display:block;margin:12px auto 0;background:none;border:none;color:#777;font-family:'Cormorant Garamond',serif;font-size:13px;font-style:italic;cursor:pointer;text-decoration:underline;text-decoration-color:transparent;transition:all .3s}
.btn-change:hover{color:#6b4200;text-decoration-color:#ccc}
#step-loading{display:none;margin-top:24px;text-align:center}
#step-loading.show{display:flex;flex-direction:column;align-items:center;gap:14px}
.brush-loader{display:flex;gap:5px;align-items:flex-end;height:28px}
.brush-loader span{width:2px;border-radius:1px;background:#333;animation:ink 1.3s ease-in-out infinite}
.brush-loader span:nth-child(1){height:10px;animation-delay:.00s}
.brush-loader span:nth-child(2){height:18px;animation-delay:.10s}
.brush-loader span:nth-child(3){height:28px;animation-delay:.20s}
.brush-loader span:nth-child(4){height:20px;animation-delay:.30s}
.brush-loader span:nth-child(5){height:12px;animation-delay:.40s}
.brush-loader span:nth-child(6){height:22px;animation-delay:.50s}
.brush-loader span:nth-child(7){height:10px;animation-delay:.60s}
.loading-label{font-size:14px;font-style:italic;color:#555;letter-spacing:1px}
#step-error{display:none;margin-top:20px;width:100%}
#step-error.show{display:block}
.error-box{border:1px solid #faa;background:#fff5f5;padding:16px 18px;font-size:14px;color:#c00;line-height:1.6}
.error-box strong{display:block;margin-bottom:4px;font-size:15px}
#step-result{display:none;margin-top:24px;width:100%}
#step-result.show{display:block;animation:rise .5s ease both}
.result-label{display:block;font-size:10px;letter-spacing:4px;color:#555;margin-bottom:10px;text-transform:uppercase}
.sgf-box{background:#1a1a1a;color:#d4c4a0;font-family:'Courier New',monospace;font-size:12px;line-height:1.8;padding:20px;max-height:200px;overflow-y:auto;white-space:pre-wrap;word-break:break-all}
.sgf-box::-webkit-scrollbar{width:4px}
.sgf-box::-webkit-scrollbar-thumb{background:#6b4200}
.counts{display:flex;justify-content:center;gap:32px;margin-top:16px;font-size:14px;color:#444}
.count-item{display:flex;align-items:center;gap:8px}
.dot{width:13px;height:13px;border-radius:50%}
.dot.b{background:radial-gradient(circle at 35% 35%,#4a4a4a,#080808);box-shadow:1px 1px 4px rgba(0,0,0,.5)}
.dot.w{background:radial-gradient(circle at 35% 35%,#fff,#d5cfc5);box-shadow:1px 1px 3px rgba(0,0,0,.2);border:1px solid #ccc}
.btn-download{width:100%;margin-top:16px;padding:14px;background:transparent;color:#6b4200;border:1px solid #ccc;font-family:'Cormorant Garamond',serif;font-size:15px;letter-spacing:2px;cursor:pointer;transition:all .3s}
.btn-download:hover{background:#6b4200;color:#fff;border-color:#6b4200}
.btn-again{display:block;margin:18px auto 0;background:none;border:none;color:#777;font-family:'Cormorant Garamond',serif;font-size:13px;font-style:italic;cursor:pointer;text-decoration:underline;text-decoration-color:transparent;transition:all .3s}
.btn-again:hover{color:#6b4200;text-decoration-color:#ccc}
.tips{margin-top:40px;width:100%;border-top:1px solid #eee;padding-top:28px}
.tips-title{font-size:11px;letter-spacing:3px;color:#999;margin-bottom:14px;display:block}
.tips p{font-size:14px;color:#666;line-height:1.7;font-style:italic;margin-bottom:6px}
.footer{margin-top:56px;text-align:center;font-size:12px;color:#999;line-height:1.8}
@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
@keyframes ink{0%,100%{opacity:.2;transform:scaleY(.4)}50%{opacity:1;transform:scaleY(1)}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
      <rect x="8" y="8" width="48" height="48" stroke="#ccc" stroke-width=".7" fill="none"/>
      <line x1="8" y1="24" x2="56" y2="24" stroke="#ccc" stroke-width=".5"/>
      <line x1="8" y1="40" x2="56" y2="40" stroke="#ccc" stroke-width=".5"/>
      <line x1="24" y1="8" x2="24" y2="56" stroke="#ccc" stroke-width=".5"/>
      <line x1="40" y1="8" x2="40" y2="56" stroke="#ccc" stroke-width=".5"/>
      <circle cx="24" cy="24" r="9" fill="url(#sb)"/>
      <circle cx="40" cy="40" r="9" fill="url(#sw)" stroke="#ccc" stroke-width=".5"/>
      <circle cx="40" cy="24" r="6" fill="url(#sb2)"/>
      <circle cx="24" cy="40" r="6" fill="url(#sw2)" stroke="#ccc" stroke-width=".4"/>
      <defs>
        <radialGradient id="sb" cx="36%" cy="34%"><stop offset="0%" stop-color="#5a5a5a"/><stop offset="100%" stop-color="#080808"/></radialGradient>
        <radialGradient id="sw" cx="36%" cy="34%"><stop offset="0%" stop-color="#fff"/><stop offset="100%" stop-color="#cec8be"/></radialGradient>
        <radialGradient id="sb2" cx="36%" cy="34%"><stop offset="0%" stop-color="#5a5a5a"/><stop offset="100%" stop-color="#080808"/></radialGradient>
        <radialGradient id="sw2" cx="36%" cy="34%"><stop offset="0%" stop-color="#fff"/><stop offset="100%" stop-color="#cec8be"/></radialGradient>
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
    <p class="loading-label">Reading the board\u2026</p>
  </div>
  <div id="step-error">
    <div class="error-box">
      <strong id="errorTitle">Error</strong>
      <span id="errorDetail"></span>
    </div>
  </div>
  <div id="step-result">
    <span class="result-label">\u00b7 SGF Record \u00b7</span>
    <div class="sgf-box" id="sgfBox"></div>
    <div class="counts" id="counts"></div>
    <button class="btn-download" onclick="download()">\u2193 Download .sgf file</button>
    <button class="btn-again" onclick="resetAll()">Read another board</button>
  </div>
  <div class="tips">
    <span class="tips-title">\u00b7 TIPS FOR BEST RESULTS \u00b7</span>
    <p>Photograph straight-on \u2014 avoid steep angles</p>
    <p>Good even lighting with no glare on stones</p>
    <p>Crop tightly to the board before uploading</p>
    <p>Screenshots from digital Go apps work perfectly</p>
    <p>iPhone users: Settings \u2192 Camera \u2192 Formats \u2192 Most Compatible (saves as JPG)</p>
  </div>
  <p class="footer">Computer vision \u00b7 No AI credits required \u00b7 Runs on your server</p>
</div>
<script>
let imageData=null,currentSGF=null;
const drop=document.getElementById('dropArea');
drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('over')});
drop.addEventListener('dragleave',()=>drop.classList.remove('over'));
drop.addEventListener('drop',e=>{
  e.preventDefault();drop.classList.remove('over');
  const f=e.dataTransfer.files[0];
  if(f&&f.type.startsWith('image/'))handleFile(f);
});
function handleFile(file){
  if(!file)return;
  const reader=new FileReader();
  reader.onload=e=>{
    imageData=e.target.result;
    document.getElementById('previewImg').src=imageData;
    document.getElementById('step-upload').style.display='none';
    document.getElementById('step-preview').classList.add('show');
    document.getElementById('step-result').classList.remove('show');
    hideError();currentSGF=null;
  };
  reader.readAsDataURL(file);
}
async function analyze(){
  if(!imageData)return;
  const btn=document.getElementById('btnRead');
  btn.disabled=true;btn.textContent='READING\u2026';
  document.getElementById('step-loading').classList.add('show');
  document.getElementById('step-result').classList.remove('show');
  hideError();
  try{
    const res=await fetch('/analyze',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({image_b64:imageData.split(',')[1],media_type:imageData.match(/data:(.*?);/)[1]})
    });
    const data=await res.json();
    if(!res.ok||data.error)throw new Error(data.error||`Server error (${res.status})`);
    currentSGF=data.sgf;
    document.getElementById('sgfBox').textContent=data.sgf;
    document.getElementById('counts').innerHTML=`
      <div class="count-item"><div class="dot b"></div>${data.black} black stone${data.black!==1?'s':''}</div>
      <div class="count-item"><div class="dot w"></div>${data.white} white stone${data.white!==1?'s':''}</div>`;
    document.getElementById('step-result').classList.add('show');
  }catch(err){
    showError('Could not read board',err.message);
  }finally{
    document.getElementById('step-loading').classList.remove('show');
    btn.disabled=false;btn.textContent='READ THE STONES';
  }
}
function download(){
  if(!currentSGF)return;
  const blob=new Blob([currentSGF],{type:'application/x-go-sgf'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;a.download='go-'+Date.now()+'.sgf';a.click();
  URL.revokeObjectURL(url);
}
function showError(title,detail){
  document.getElementById('errorTitle').textContent=title;
  document.getElementById('errorDetail').textContent=detail?' \u2014 '+detail:'';
  document.getElementById('step-error').classList.add('show');
}
function hideError(){document.getElementById('step-error').classList.remove('show')}
function resetToUpload(){
  imageData=null;currentSGF=null;
  document.getElementById('fileInput').value='';
  document.getElementById('step-preview').classList.remove('show');
  document.getElementById('step-result').classList.remove('show');
  document.getElementById('step-upload').style.display='';
  hideError();
}
function resetAll(){resetToUpload()}
</script>
</body>
</html>"""
HTML = HTML_STR.encode("utf-8")

# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}")

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML)

    def do_POST(self):
        if self.path != '/analyze':
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length))
            img_bytes = base64.b64decode(body.get('image_b64', ''))
            sgf, black, white = image_to_sgf(img_bytes)
            self._respond(200, {'sgf': sgf, 'black': black, 'white': white})
        except ValueError as e:
            self._respond(400, {'error': str(e)})
        except Exception as e:
            traceback.print_exc()
            self._respond(500, {'error': f'Server error: {str(e)}'})

    def _respond(self, status, data):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'\n  Stone to SGF  \u2014  port {PORT}\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  Stopped.')
        server.shutdown()
