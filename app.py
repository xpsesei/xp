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
    "token": "",  # 留空，通过后台面板安全配置
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

    log_message("Starting automated generation and sync cycle...")
    ad_header = config.get("ad_header", "")
    ad_sidebar = config.get("ad_sidebar", "")
    ad_footer = config.get("ad_footer", "")
    ai_key = config.get("ai_api_key", "")
    ai_status_text = "AI Powered Active" if ai_key else "Standard Mode"

    tools = [
        {"id": "color", "name": "Color Converter", "desc": "Convert HEX, RGB, HSL instantly."},
        {"id": "password", "name": "Secure Password Generator", "desc": "Generate cryptographic passwords."},
        {"id": "json", "name": "JSON Formatter", "desc": "Validate and format JSON data."},
        {"id": "uuid", "name": "UUID v4 Generator", "desc": "Generate random unique identifiers."},
        {"id": "base64", "name": "Base64 Encoder/Decoder", "desc": "Encode and decode text securely."},
        {"id": "hash", "name": "Hash Generator", "desc": "Compute MD5, SHA-256 hashes."},
        {"id": "timestamp", "name": "Epoch Timestamp Converter", "desc": "Convert Unix timestamps."},
        {"id": "url", "name": "URL Encoder/Decoder", "desc": "Encode and decode query strings."},
        {"id": "jwt", "name": "JWT Decoder", "desc": "Inspect JSON Web Tokens locally."},
        {"id": "lorem", "name": "Lorem Ipsum Generator", "desc": "Generate placeholder text."}
    ]

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
            <div class="text-xs text-slate-400">Multi-page Developer Utilities</div>
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
"""
    for t in tools:
        index_content += f'                <li><a href="#{t["id"]}" class="block px-3 py-2 rounded hover:bg-slate-700 transition">{t["name"]}</a></li>\n'

    index_content += f"""            </ul>
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
        const toolsData = {json.dumps(tools)};
        window.addEventListener('hashchange', renderTool);
        function renderTool() {{
            const hash = location.hash.replace('#', '') || 'color';
            const tool = toolsData.find(t => t.id === hash) || toolsData[0];
            document.getElementById('tool-title').innerText = tool.name;
            document.getElementById('tool-desc').innerText = tool.desc;
        }}
        if(location.hash) renderTool();
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
        subprocess.run(["git", "commit", "-m", "Auto-generated tools securely"], check=True)
        
        remote_url = f"https://{token}@github.com/{user}/{repo}.git"
        subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
        subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        subprocess.run(["git", "push", "-u", "origin", "main", "--force"], check=True)
        log_message("Success: Tools generated and synced with GitHub securely!")
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
                    <label class="block text-sm font-medium text-slate-300">GitHub Personal Access Token (安全保存在本地 config.json)</label>
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
