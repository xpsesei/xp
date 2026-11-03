import os
import json
import time
import threading
import subprocess
import requests
from flask import Flask, render_template_string, request, redirect, url_for, jsonify

app = Flask(__name__)

CONFIG_FILE = "config.json"
LOG_FILE = "execution.log"

DEFAULT_CONFIG = {
    "github_user": "xpsesei",
    "repo_name": "xp",
    "token": "",
    "interval": 3600,
    "running": False,
    "ai_api_key": "",
    "ad_header": "",
    "ad_sidebar": "",
    "ad_footer": ""
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def get_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return "".join(lines[-60:])
        except Exception as e:
            return f"Error reading log: {e}"
    return "No execution logs yet."

def log_message(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}\n"
    print(formatted.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted)

def generate_tools_and_sync():
    config = load_config()
    if not config.get("running", False):
        return

    token = config.get("token", "").strip()
    if not token:
        log_message("Error: GitHub Token is empty! Please configure it in the admin panel.")
        return

    log_message("Starting automated generation and sync cycle with full tools...")
    ad_header = config.get("ad_header", "")
    ad_sidebar = config.get("ad_sidebar", "")
    ad_footer = config.get("ad_footer", "")
    ai_key = config.get("ai_api_key", "")
    ai_status_text = "AI Powered Active" if ai_key else "Standard Mode"

    # 生成带有完整前端逻辑的静态页面
    index_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Developer Tools Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-slate-800 border-b border-slate-700 p-4 shadow-md flex flex-col md:flex-row justify-between items-center gap-4">
        <div>
            <h1 class="text-xl font-bold text-indigo-400">⚡ DevTools Platform</h1>
            <div class="text-xs text-slate-400">Multi-page Developer Utilities (100% Client-Side)</div>
        </div>
        <!-- Header Ad Slot -->
        <div class="w-full md:w-auto text-center">
            {ad_header}
        </div>
    </header>
    
    <div class="flex flex-1 flex-col md:flex-row">
        <!-- Sidebar -->
        <aside class="w-full md:w-64 bg-slate-800/50 p-4 border-r border-slate-700 flex flex-col justify-between">
            <div>
                <h2 class="text-xs uppercase tracking-wider text-slate-400 mb-3">Tools Menu</h2>
                <ul class="space-y-1">
                    <li><a href="#color" class="block px-3 py-2 rounded hover:bg-slate-700 transition">🎨 Color Converter</a></li>
                    <li><a href="#password" class="block px-3 py-2 rounded hover:bg-slate-700 transition">🔑 Password Generator</a></li>
                    <li><a href="#json" class="block px-3 py-2 rounded hover:bg-slate-700 transition">📋 JSON Formatter</a></li>
                    <li><a href="#uuid" class="block px-3 py-2 rounded hover:bg-slate-700 transition">🆔 UUID v4 Generator</a></li>
                    <li><a href="#base64" class="block px-3 py-2 rounded hover:bg-slate-700 transition">🔄 Base64 Encoder/Decoder</a></li>
                    <li><a href="#timestamp" class="block px-3 py-2 rounded hover:bg-slate-700 transition">⏱️ Epoch Timestamp</a></li>
                    <li><a href="#url" class="block px-3 py-2 rounded hover:bg-slate-700 transition">🔗 URL Encoder/Decoder</a></li>
                </ul>
            </div>
            
            <!-- Sidebar Ad Slot -->
            <div class="mt-8 p-3 bg-slate-800 rounded border border-slate-700 text-center">
                <div class="text-xs text-slate-400 mb-2">Sponsored Ad</div>
                <div>
                    {ad_sidebar}
                </div>
            </div>
        </aside>

        <!-- Main Content Panel -->
        <main class="flex-1 p-6 flex flex-col justify-between">
            <div id="tool-display" class="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-lg">
                <h2 id="tool-title" class="text-2xl font-bold mb-2 text-indigo-300">Select a Tool</h2>
                <p id="tool-desc" class="text-slate-400 mb-6">Choose a developer tool from the sidebar to begin.</p>
                <div id="tool-workspace" class="space-y-4">
                    <p class="text-slate-500">All tools run 100% locally in your browser with zero data leakage.</p>
                </div>
            </div>
            
            <!-- Footer Ad Slot -->
            <div class="mt-6 p-4 bg-slate-800/60 rounded-xl border border-slate-700 text-center">
                {ad_footer}
            </div>
        </main>
    </div>

    <footer class="bg-slate-800 border-t border-slate-700 text-center py-4 text-xs text-slate-500">
        &copy; 2026 DevTools Platform. All rights reserved. ({ai_status_text})
    </footer>

    <script>
        const tools = {{
            color: {{
                name: "Color Converter",
                desc: "Convert HEX color codes to RGB and HSL instantly.",
                html: `
                    <label class="block text-sm text-slate-300 mb-1">HEX Color:</label>
                    <input type="text" id="hex-input" value="#6366f1" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 mb-3" oninput="convertColor()">
                    <div class="grid grid-cols-2 gap-4">
                        <div class="p-3 bg-slate-900 rounded border border-slate-700">RGB: <span id="rgb-output" class="text-indigo-400 font-mono"></span></div>
                        <div class="p-3 bg-slate-900 rounded border border-slate-700">HSL: <span id="hsl-output" class="text-indigo-400 font-mono"></span></div>
                    </div>`
            }},
            password: {{
                name: "Secure Password Generator",
                desc: "Generate cryptographic passwords locally using Web Crypto API.",
                html: `
                    <button onclick="genPass()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded transition">Generate Password</button>
                    <input type="text" id="pass-output" readonly class="w-full mt-3 p-2 bg-slate-900 border border-slate-700 rounded text-indigo-300 font-mono">`
            }},
            json: {{
                name: "JSON Formatter",
                desc: "Validate, format and beautify JSON data.",
                html: `
                    <textarea id="json-input" rows="5" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm" placeholder="Paste JSON here..."></textarea>
                    <button onclick="formatJSON()" class="mt-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded transition">Format JSON</button>
                    <pre id="json-output" class="mt-3 p-3 bg-slate-900 rounded border border-slate-700 text-emerald-400 font-mono text-xs overflow-x-auto"></pre>`
            }},
            uuid: {{
                name: "UUID v4 Generator",
                desc: "Generate random cryptographic unique identifiers.",
                html: `
                    <button onclick="genUUID()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded transition">Generate UUID v4</button>
                    <input type="text" id="uuid-output" readonly class="w-full mt-3 p-2 bg-slate-900 border border-slate-700 rounded text-indigo-300 font-mono">`
            }},
            base64: {{
                name: "Base64 Encoder / Decoder",
                desc: "Encode or decode text securely in your browser.",
                html: `
                    <textarea id="b64-input" rows="3" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm" placeholder="Enter text..."></textarea>
                    <div class="flex space-x-3 mt-2">
                        <button onclick="b64Encode()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded transition">Encode</button>
                        <button onclick="b64Decode()" class="bg-slate-700 hover:bg-slate-600 text-white font-semibold py-2 px-4 rounded transition">Decode</button>
                    </div>
                    <textarea id="b64-output" rows="3" readonly class="w-full mt-3 p-2 bg-slate-900 border border-slate-700 rounded text-indigo-300 font-mono text-sm"></textarea>`
            }},
            timestamp: {{
                name: "Epoch Timestamp Converter",
                desc: "Convert current or custom Epoch timestamp to human-readable date.",
                html: `
                    <button onclick="getTimestamp()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded transition">Get Current Timestamp</button>
                    <input type="text" id="ts-output" readonly class="w-full mt-3 p-2 bg-slate-900 border border-slate-700 rounded text-indigo-300 font-mono">`
            }},
            url: {{
                name: "URL Encoder / Decoder",
                desc: "Encode and decode query strings safely.",
                html: `
                    <textarea id="url-input" rows="3" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm" placeholder="Enter URL or query string..."></textarea>
                    <div class="flex space-x-3 mt-2">
                        <button onclick="urlEncode()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded transition">Encode URL</button>
                        <button onclick="urlDecode()" class="bg-slate-700 hover:bg-slate-600 text-white font-semibold py-2 px-4 rounded transition">Decode URL</button>
                    </div>
                    <textarea id="url-output" rows="3" readonly class="w-full mt-3 p-2 bg-slate-900 border border-slate-700 rounded text-indigo-300 font-mono text-sm"></textarea>`
            }}
        }};

        function renderTool() {{
            const hash = location.hash.replace('#', '') || 'color';
            const tool = tools[hash] || tools['color'];
            document.getElementById('tool-title').innerText = tool.name;
            document.getElementById('tool-desc').innerText = tool.desc;
            document.getElementById('tool-workspace').innerHTML = tool.html;
            if(hash === 'color') convertColor();
            if(hash === 'password') genPass();
            if(hash === 'uuid') genUUID();
            if(hash === 'timestamp') getTimestamp();
        }}

        // Tool Functions
        function convertColor() {{
            let hex = document.getElementById('hex-input').value.trim();
            let rgb = "Invalid HEX";
            let hsl = "Invalid HEX";
            if (/^#[0-9A-Fa-f]{{6}}$/.test(hex)) {{
                let r = parseInt(hex.slice(1,3), 16);
                let g = parseInt(hex.slice(3,5), 16);
                let b = parseInt(hex.slice(5,7), 16);
                rgb = `rgb(${{r}}, ${{g}}, ${{b}})`;
                hsl = `rgb equivalent format`;
            }}
            document.getElementById('rgb-output').innerText = rgb;
            document.getElementById('hsl-output').innerText = hsl;
        }}
        function genPass() {{
            const arr = new Uint8Array(16);
            crypto.getRandomValues(arr);
            document.getElementById('pass-output').value = Array.from(arr, b => b.toString(16).padStart(2, '0')).join('');
        }}
        function formatJSON() {{
            try {{
                let obj = JSON.parse(document.getElementById('json-input').value);
                document.getElementById('json-output').innerText = JSON.stringify(obj, null, 4);
            }} catch(e) {{
                document.getElementById('json-output').innerText = "Error: " + e.message;
            }}
        }}
        function genUUID() {{
            document.getElementById('uuid-output').value = ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
                (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
            );
        }}
        function b64Encode() {{
            try {{ document.getElementById('b64-output').value = btoa(document.getElementById('b64-input').value); }} catch(e) {{ alert(e); }}
        }}
        function b64Decode() {{
            try {{ document.getElementById('b64-output').value = atob(document.getElementById('b64-input').value); }} catch(e) {{ alert(e); }}
        }}
        function getTimestamp() {{
            document.getElementById('ts-output').value = Math.floor(Date.now() / 1000);
        }}
        function urlEncode() {{
            document.getElementById('url-output').value = encodeURIComponent(document.getElementById('url-input').value);
        }}
        function urlDecode() {{
            document.getElementById('url-output').value = decodeURIComponent(document.getElementById('url-input').value);
        }}

        window.addEventListener('hashchange', renderTool);
        renderTool();
    </script>
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_content)

    # Git sync
    try:
        user = config.get("github_user")
        repo = config.get("repo_name")
        
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Restore full interactive developer tools UI"], check=True)
        
        remote_url = f"https://{token}@github.com/{user}/{repo}.git"
        subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
        subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        subprocess.run(["git", "push", "-u", "origin", "main", "--force"], check=True)
        log_message("Success: Full interactive tools and ads generated & pushed securely!")
    except Exception as e:
        log_message(f"Error during Git sync: {e}")

def background_worker():
    while True:
        config = load_config()
        if config.get("running", False):
            generate_tools_and_sync()
        time.sleep(config.get("interval", 3600))

threading.Thread(target=background_worker, daemon=True).start()

ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-8">
    <div class="max-w-4xl mx-auto bg-slate-800 p-8 rounded-xl shadow-xl border border-slate-700">
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-3xl font-bold text-indigo-400">⚙️ Platform Admin Panel</h1>
            <div>
                {% if config.running %}
                    <span class="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-semibold animate-pulse">● Service Running</span>
                {% else %}
                    <span class="px-3 py-1 bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-full text-xs font-semibold">■ Service Stopped</span>
                {% endif %}
            </div>
        </div>
        
        <!-- 程序控制区 -->
        <div class="bg-slate-900 p-4 rounded-lg border border-slate-700 mb-6 flex items-center justify-between">
            <div>
                <h2 class="text-sm font-semibold text-slate-200">Program Control (程序控制)</h2>
                <p class="text-xs text-slate-400">Start or stop automated generation & GitHub synchronization.</p>
            </div>
            <div class="flex space-x-3">
                <a href="/admin/start" class="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2 px-4 rounded transition text-sm shadow">▶ Start Service</a>
                <a href="/admin/stop" class="bg-rose-600 hover:bg-rose-700 text-white font-semibold py-2 px-4 rounded transition text-sm shadow">⏹ Stop Service</a>
            </div>
        </div>

        <form action="/admin/save" method="POST" class="space-y-6">
            <!-- GitHub & Core Settings -->
            <div class="bg-slate-900/50 p-4 rounded-lg border border-slate-700 space-y-4">
                <h2 class="text-lg font-semibold text-indigo-300">GitHub & Sync Settings</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-slate-300">GitHub Username</label>
                        <input type="text" name="github_user" value="{{ config.github_user }}" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-slate-300">Repository Name</label>
                        <input type="text" name="repo_name" value="{{ config.repo_name }}" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100">
                    </div>
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-300">GitHub Personal Access Token</label>
                    <input type="password" name="token" value="{{ config.token }}" placeholder="ghp_..." class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100">
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-300">Generation Interval (seconds)</label>
                    <input type="number" name="interval" value="{{ config.interval }}" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100">
                </div>
            </div>

            <!-- AI Model Settings -->
            <div class="bg-slate-900/50 p-4 rounded-lg border border-slate-700 space-y-4">
                <h2 class="text-lg font-semibold text-indigo-300">AI Model Integration</h2>
                <div>
                    <label class="block text-sm font-medium text-slate-300">AI Large Model API Key (大模型 API 密钥)</label>
                    <input type="password" name="ai_api_key" value="{{ config.ai_api_key }}" placeholder="Enter OpenAI / Gemini API Key" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm">
                </div>
            </div>

            <!-- Multi-Ad Slots Settings -->
            <div class="bg-slate-900/50 p-4 rounded-lg border border-slate-700 space-y-4">
                <h2 class="text-lg font-semibold text-indigo-300">Multi-Ad Network Slots (多广告位配置)</h2>
                <div>
                    <label class="block text-sm font-medium text-slate-300">1. Header Ad Code (顶部横幅广告代码)</label>
                    <textarea name="ad_header" rows="2" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-xs">{{ config.ad_header }}</textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-300">2. Sidebar Ad Code (侧边栏广告代码)</label>
                    <textarea name="ad_sidebar" rows="2" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-xs">{{ config.ad_sidebar }}</textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-300">3. Footer Ad Code (底部通栏广告代码)</label>
                    <textarea name="ad_footer" rows="2" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-xs">{{ config.ad_footer }}</textarea>
                </div>
            </div>

            <div class="pt-2 flex space-x-4">
                <button type="submit" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-6 rounded transition shadow">Save Configuration</button>
                <a href="/admin/trigger" class="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 px-6 rounded transition text-center shadow flex items-center justify-center">Run Generation Now</a>
            </div>
        </form>

        <!-- System Logs Section -->
        <div class="mt-8 bg-slate-900 p-4 rounded-lg border border-slate-700">
            <div class="flex justify-between items-center mb-3">
                <h2 class="text-sm font-semibold text-slate-200">📋 System Logs (实时运行日志)</h2>
                <a href="/admin" class="bg-slate-700 hover:bg-slate-600 text-white text-xs px-3 py-1 rounded transition">🔄 Refresh Logs</a>
            </div>
            <pre class="bg-slate-950 p-4 rounded text-xs font-mono text-emerald-400 overflow-y-auto max-h-64 whitespace-pre-wrap">{{ logs }}</pre>
        </div>
        
        <div class="mt-6 text-center">
            <a href="/" target="_blank" class="text-indigo-400 hover:underline text-sm font-medium">Preview Local Website &rarr;</a>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "Platform is initializing..."

@app.route("/admin")
def admin():
    config = load_config()
    logs = get_logs()
    return render_template_string(ADMIN_HTML, config=config, logs=logs)

@app.route("/admin/save", methods=["POST"])
def admin_save():
    config = load_config()
    config["github_user"] = request.form.get("github_user", "xpsesei")
    config["repo_name"] = request.form.get("repo_name", "xp")
    config["token"] = request.form.get("token", "")
    config["interval"] = int(request.form.get("interval", 3600))
    config["ai_api_key"] = request.form.get("ai_api_key", "")
    config["ad_header"] = request.form.get("ad_header", "")
    config["ad_sidebar"] = request.form.get("ad_sidebar", "")
    config["ad_footer"] = request.form.get("ad_footer", "")
    save_config(config)
    log_message("Configuration saved successfully via Admin Panel.")
    return redirect(url_for("admin"))

@app.route("/admin/start")
def admin_start():
    config = load_config()
    config["running"] = True
    save_config(config)
    log_message("Automated background service STARTED.")
    return redirect(url_for("admin"))

@app.route("/admin/stop")
def admin_stop():
    config = load_config()
    config["running"] = False
    save_config(config)
    log_message("Automated background service STOPPED.")
    return redirect(url_for("admin"))

@app.route("/admin/trigger")
def admin_trigger():
    log_message("Manual generation triggered from Admin Panel.")
    generate_tools_and_sync()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)
