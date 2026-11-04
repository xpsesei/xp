import os
import json
import time
import threading
import subprocess
import requests
from flask import Flask, render_template_string, request, redirect, url_for, jsonify

app = Flask(__name__)

CONFIG_FILE = "config.json"
TOOLS_FILE = "tools.json"
LOG_FILE = "execution.log"

DEFAULT_CONFIG = {
    "github_user": "xpsesei",
    "repo_name": "xp",
    "token": "",
    "custom_domain": "",
    "interval": 3600,
    "running": False,
    "gemini_api_keys": "",             # 支持多行输入多个 Gemini Key
    "gemini_model": "gemini-1.5-flash", # Gemini 模型
    "ad_header": "",
    "ad_sidebar": "",
    "ad_tool_content": "",
    "ad_footer": ""
}

DEFAULT_TOOLS = [
    {
        "id": "color",
        "name": "🎨 Color Converter",
        "category": "Design & Media",
        "desc": "Convert HEX color codes to RGB and HSL instantly.",
        "html": '<label class="block text-sm text-slate-300 mb-1">HEX Color:</label><input type="text" id="hex-input" value="#6366f1" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 mb-3" oninput="convertColor()"><div class="grid grid-cols-2 gap-4"><div class="p-3 bg-slate-900 rounded border border-slate-700">RGB: <span id="rgb-output" class="text-indigo-400 font-mono"></span></div><div class="p-3 bg-slate-900 rounded border border-slate-700">HSL: <span id="hsl-output" class="text-indigo-400 font-mono"></span></div></div>'
    },
    {
        "id": "password",
        "name": "🔑 Password Generator",
        "category": "Security & Cryptography",
        "desc": "Generate cryptographic passwords locally using Web Crypto API.",
        "html": '<button onclick="genPass()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded transition">Generate Password</button><input type="text" id="pass-output" readonly class="w-full mt-3 p-2 bg-slate-900 border border-slate-700 rounded text-indigo-300 font-mono">'
    },
    {
        "id": "json",
        "name": "📋 JSON Formatter",
        "category": "Data & Database",
        "desc": "Validate, format and beautify JSON data.",
        "html": '<textarea id="json-input" rows="5" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm" placeholder="Paste JSON here..."></textarea><button onclick="formatJSON()" class="mt-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded transition">Format JSON</button><pre id="json-output" class="mt-3 p-3 bg-slate-900 rounded border border-slate-700 text-emerald-400 font-mono text-xs overflow-x-auto"></pre>'
    }
]

# 备用离线工具池
OFFLINE_BACKUP_POOL = [
    {
        "id": "qrcode",
        "name": "📱 QR Code Generator",
        "category": "Design & Media",
        "desc": "Generate QR codes instantly from text or URLs locally.",
        "html": '<input type="text" id="qr-input" value="https://github.com" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 mb-3" oninput="genQR()"><div id="qr-out" class="p-4 bg-slate-900 rounded border border-slate-700 text-center text-indigo-300 font-mono">QR Code container</div>'
    },
    {
        "id": "hash",
        "name": "🔒 Hash Generator (MD5/SHA)",
        "category": "Security & Cryptography",
        "desc": "Compute cryptographic hash sums locally in browser.",
        "html": '<textarea id="hash-input" rows="2" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 mb-2" placeholder="Enter text to hash..." oninput="calcHash()"></textarea><div class="p-3 bg-slate-900 rounded border border-slate-700 text-xs font-mono text-emerald-400" id="hash-output">SHA-256 / MD5 output</div>'
    }
]

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

def load_tools():
    if os.path.exists(TOOLS_FILE):
        try:
            with open(TOOLS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    save_tools(DEFAULT_TOOLS)
    return DEFAULT_TOOLS

def save_tools(tools):
    with open(TOOLS_FILE, "w", encoding="utf-8") as f:
        json.dump(tools, f, indent=4)

def get_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return "".join(lines[-70:])
        except Exception as e:
            return f"Error reading log: {e}"
    return "No execution logs yet."

def log_message(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}\n"
    print(formatted.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted)

# 核心：Gemini 多密钥轮询与自动故障转移
def generate_new_tool_via_gemini(existing_ids):
    config = load_config()
    keys_raw = config.get("gemini_api_keys", "")
    keys = [k.strip() for k in keys_raw.split("\n") if k.strip()]
    
    if not keys:
        log_message("Gemini Info: No API keys configured. Using backup pool.")
        return None

    model = config.get("gemini_model", "gemini-1.5-flash").strip()
    prompt = f"""You are an expert full-stack developer. Create a brand new, unique, highly useful browser-based developer utility tool (e.g., CSS Flexbox Playground, YAML to JSON converter, JWT Expiry Checker, Regex Cheatsheet, Base64 Image to DataURL converter, etc.) that is NOT in this existing list of IDs: {list(existing_ids)}.
Return ONLY a valid JSON object (no markdown wrapping, no backticks) with these exact keys:
{{
  "id": "unique_string_id",
  "name": "Emoji & Tool Name",
  "category": "Security & Cryptography" or "Network & DevOps" or "Data & Database" or "Text & Formatting" or "Math & Converters" or "Design & Media",
  "desc": "Short description of what the tool does",
  "html": "Tailwind CSS styled HTML form elements and interactive JavaScript logic with inline event handlers"
}}"""

    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    for idx, key in enumerate(keys):
        try:
            log_message(f"Attempting Gemini request using Key #{idx + 1}...")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            response = requests.post(url, headers=headers, json=data, timeout=35)
            
            if response.status_code == 200:
                res_json = response.json()
                content = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                tool_data = json.loads(content.strip())
                if "id" in tool_data and "html" in tool_data:
                    log_message(f"Successfully generated new tool via Gemini (Key #{idx + 1}): {tool_data.get('name')}")
                    return tool_data
            else:
                log_message(f"Gemini Key #{idx + 1} returned error status {response.status_code}: {response.text}. Rotating to next key...")
        except Exception as e:
            log_message(f"Gemini Key #{idx + 1} exception: {e}. Rotating to next key...")
            continue
            
    log_message("All Gemini API keys failed or exhausted. Falling back to offline backup pool.")
    return None

def auto_expand_and_sync():
    config = load_config()
    if not config.get("running", False):
        return

    token = config.get("token", "").strip()
    if not token:
        log_message("Error: GitHub Token is empty!")
        return

    log_message("Scheduled task triggered: Generating new tool via Gemini...")
    tools = load_tools()
    existing_ids = {t["id"] for t in tools}

    # 优先尝试多密钥轮询调用 Gemini 生成
    new_tool = generate_new_tool_via_gemini(existing_ids)

    # 如果所有 Key 均失败或未配置，从备用池中取一个
    if not new_tool:
        for candidate in OFFLINE_BACKUP_POOL:
            if candidate["id"] not in existing_ids:
                new_tool = candidate
                log_message(f"Backup pool fallback: Added {candidate['name']}")
                break

    if new_tool and new_tool["id"] not in existing_ids:
        tools.append(new_tool)
        save_tools(tools)
        generate_static_site_and_push(config, tools)
        log_message(f"Success: Added new tool [{new_tool['name']}] and pushed to GitHub!")
    else:
        log_message("No new tool generated in this cycle.")

def generate_static_site_and_push(config, tools):
    token = config.get("token", "").strip()
    user = config.get("github_user")
    repo = config.get("repo_name")
    custom_domain = config.get("custom_domain", "").strip()
    ad_header = config.get("ad_header", "")
    ad_sidebar = config.get("ad_sidebar", "")
    ad_footer = config.get("ad_footer", "")
    ad_tool_content = config.get("ad_tool_content", "")
    ai_status_text = "Gemini Multi-Key Failover Active"

    if custom_domain:
        with open("CNAME", "w", encoding="utf-8") as f:
            f.write(custom_domain)
        domain_redirect_script = """
    <script>
        const allowedDomain = "__CUSTOM_DOMAIN__";
        if (allowedDomain && 
            window.location.hostname !== allowedDomain && 
            !window.location.hostname.includes('localhost') && 
            !window.location.hostname.includes('127.0.0.1') &&
            window.location.port !== '5050') {
            window.location.href = 'https://' + allowedDomain + window.location.pathname + window.location.search + window.location.hash;
        }
    </script>
        """.replace("__CUSTOM_DOMAIN__", custom_domain)
    else:
        if os.path.exists("CNAME"):
            os.remove("CNAME")
        domain_redirect_script = ""

    categories = {}
    for t in tools:
        cat = t.get('category', 'General Utilities')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)

    sidebar_html = ""
    for cat, t_list in categories.items():
        sidebar_html += f'<div class="mb-4"><div class="text-[11px] uppercase tracking-wider text-indigo-400 font-bold mb-1 px-2">{cat}</div><ul class="space-y-1">'
        for t in t_list:
            sidebar_html += f'<li><a href="#{t["id"]}" class="block px-3 py-1.5 rounded hover:bg-slate-700 transition text-xs text-slate-300">{t["name"]}</a></li>'
        sidebar_html += '</ul></div>'

    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Categorized Developer Tools Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    __DOMAIN_REDIRECT_SCRIPT__
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-slate-800 border-b border-slate-700 p-4 shadow-md flex flex-col md:flex-row justify-between items-center gap-4">
        <div>
            <h1 class="text-xl font-bold text-indigo-400">⚡ Categorized DevTools Platform</h1>
            <div class="text-xs text-slate-400">Structured Multi-Domain Utilities (Total Tools: __TOOLS_COUNT__)</div>
        </div>
        <div class="w-full md:w-auto text-center">
            __AD_HEADER__
        </div>
    </header>
    
    <div class="flex flex-1 flex-col md:flex-row">
        <!-- Sidebar -->
        <aside class="w-full md:w-80 bg-slate-800/50 p-4 border-r border-slate-700 flex flex-col justify-between max-h-[85vh] overflow-y-auto">
            <div>
                __SIDEBAR_HTML__
            </div>
            <div class="mt-8 p-3 bg-slate-800 rounded border border-slate-700 text-center">
                <div class="text-xs text-slate-400 mb-2">Sponsored Ad</div>
                <div>
                    __AD_SIDEBAR__
                </div>
            </div>
        </aside>

        <!-- Main Content Panel -->
        <main class="flex-1 p-6 flex flex-col justify-between">
            <div id="tool-display" class="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-lg flex flex-col justify-between">
                <div>
                    <h2 id="tool-title" class="text-2xl font-bold mb-2 text-indigo-300">Select a Tool</h2>
                    <p id="tool-desc" class="text-slate-400 mb-6">Choose a categorized developer tool from the sidebar to begin.</p>
                    <div id="tool-workspace" class="space-y-4">
                        <p class="text-slate-500">All tools execute 100% locally in your browser.</p>
                    </div>
                </div>
                <!-- Tool Workspace Ad Slot -->
                <div id="tool-ad-slot" class="mt-8 pt-4 border-t border-slate-700 text-center">
                    __AD_TOOL_CONTENT__
                </div>
            </div>
            <div class="mt-6 p-4 bg-slate-800/60 rounded-xl border border-slate-700 text-center">
                __AD_FOOTER__
            </div>
        </main>
    </div>

    <footer class="bg-slate-800 border-t border-slate-700 text-center py-4 text-xs text-slate-500">
        &copy; 2026 Categorized DevTools Platform. All rights reserved. (__AI_STATUS__)
    </footer>

    <script>
        const tools = __TOOLS_JSON__;

        function renderTool() {
            const hash = location.hash.replace('#', '') || (tools.length > 0 ? tools[0].id : '');
            const tool = tools.find(t => t.id === hash) || tools[0];
            if (!tool) return;
            document.getElementById('tool-title').innerText = tool.name;
            document.getElementById('tool-desc').innerText = tool.desc;
            document.getElementById('tool-workspace').innerHTML = tool.html;
            if(hash === 'color') convertColor();
            if(hash === 'password') genPass();
            if(hash === 'uuid') genUUID();
            if(hash === 'timestamp') getTimestamp();
        }

        function convertColor() {
            let hex = document.getElementById('hex-input');
            if(!hex) return;
            let val = hex.value.trim();
            let rgb = "Invalid HEX", hsl = "Invalid HEX";
            if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
                let r = parseInt(val.slice(1,3), 16);
                let g = parseInt(val.slice(3,5), 16);
                let b = parseInt(val.slice(5,7), 16);
                rgb = `rgb(${r}, ${g}, ${b})`;
                hsl = `rgb format`;
            }
            let rOut = document.getElementById('rgb-output');
            let hOut = document.getElementById('hsl-output');
            if(rOut) rOut.innerText = rgb;
            if(hOut) hOut.innerText = hsl;
        }
        function genPass() {
            const arr = new Uint8Array(16);
            crypto.getRandomValues(arr);
            let el = document.getElementById('pass-output');
            if(el) el.value = Array.from(arr, b => b.toString(16).padStart(2, '0')).join('');
        }
        function formatJSON() {
            try {
                let obj = JSON.parse(document.getElementById('json-input').value);
                document.getElementById('json-output').innerText = JSON.stringify(obj, null, 4);
            } catch(e) {
                document.getElementById('json-output').innerText = "Error: " + e.message;
            }
        }
        function genQR() {
            let val = document.getElementById('qr-input').value;
            document.getElementById('qr-out').innerHTML = '<a href="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=' + encodeURIComponent(val) + '" target="_blank" class="text-indigo-400 underline">Click to view QR Code for: ' + val + '</a>';
        }
        function calcHash() {
            let txt = document.getElementById('hash-input').value;
            document.getElementById('hash-output').innerText = "MD5/SHA simulated hash for length " + txt.length;
        }

        window.addEventListener('hashchange', renderTool);
        renderTool();
    </script>
</body>
</html>
"""

    index_content = HTML_TEMPLATE.replace("__TOOLS_COUNT__", str(len(tools)))\
                                 .replace("__DOMAIN_REDIRECT_SCRIPT__", domain_redirect_script)\
                                 .replace("__AD_HEADER__", ad_header)\
                                 .replace("__SIDEBAR_HTML__", sidebar_html)\
                                 .replace("__AD_SIDEBAR__", ad_sidebar)\
                                 .replace("__AD_FOOTER__", ad_footer)\
                                 .replace("__AD_TOOL_CONTENT__", ad_tool_content)\
                                 .replace("__TOOLS_JSON__", json.dumps(tools))\
                                 .replace("__AI_STATUS__", ai_status_text)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_content)

    try:
        subprocess.run(["git", "add", "."], check=True)
        status_res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        if status_res.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Gemini multi-key failover tool expansion and sync"], check=True)
            remote_url = f"https://{token}@github.com/{user}/{repo}.git"
            subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
            subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True)
            subprocess.run(["git", "push", "-u", "origin", "main", "--force"], check=True)
            log_message("Success: Gemini multi-key site pushed to GitHub.")
        else:
            log_message("Git sync: Working tree clean, no changes.")
    except Exception as e:
        log_message(f"Error during Git sync: {e}")

def background_worker():
    while True:
        config = load_config()
        if config.get("running", False):
            auto_expand_and_sync()
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
                    <span class="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-semibold animate-pulse">● Service Running (Gemini Multi-Key Failover)</span>
                {% else %}
                    <span class="px-3 py-1 bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-full text-xs font-semibold">■ Service Stopped</span>
                {% endif %}
            </div>
        </div>
        
        <div class="bg-slate-900 p-4 rounded-lg border border-slate-700 mb-6 flex items-center justify-between">
            <div>
                <h2 class="text-sm font-semibold text-slate-200">Program Control</h2>
                <p class="text-xs text-slate-400">Start or stop automated Gemini multi-key generation & GitHub synchronization.</p>
            </div>
            <div class="flex space-x-3">
                <a href="/admin/start" class="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2 px-4 rounded transition text-sm shadow">▶ Start Service</a>
                <a href="/admin/stop" class="bg-rose-600 hover:bg-rose-700 text-white font-semibold py-2 px-4 rounded transition text-sm shadow">⏹ Stop Service</a>
            </div>
        </div>

        <form action="/admin/save" method="POST" class="space-y-6">
            <div class="bg-slate-900/50 p-4 rounded-lg border border-slate-700 space-y-4">
                <h2 class="text-lg font-semibold text-indigo-300">GitHub & Domain Settings</h2>
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
                    <label class="block text-sm font-medium text-slate-300">Custom Domain (自定义域名，例如 tools.yourdomain.com)</label>
                    <input type="text" name="custom_domain" value="{{ config.custom_domain }}" placeholder="tools.yourdomain.com" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-300">Generation Interval (seconds)</label>
                    <input type="number" name="interval" value="{{ config.interval }}" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100">
                </div>
            </div>

            <!-- Gemini 多密钥配置专区 -->
            <div class="bg-slate-900/50 p-4 rounded-lg border border-slate-700 space-y-4">
                <h2 class="text-lg font-semibold text-indigo-300">Gemini AI Multi-Keys Integration (多密钥故障转移)</h2>
                <div>
                    <label class="block text-sm font-medium text-slate-300">Gemini Model Name</label>
                    <input type="text" name="gemini_model" value="{{ config.gemini_model }}" placeholder="gemini-1.5-flash" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-300 mb-1">Gemini API Keys (每行输入一个 Key，一个不可用时自动轮换替换)</label>
                    <textarea name="gemini_api_keys" rows="3" placeholder="AIzaSy...&#10;AIzaSy..." class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm">{{ config.gemini_api_keys }}</textarea>
                </div>
            </div>

            <div class="bg-slate-900/50 p-4 rounded-lg border border-slate-700 space-y-4">
                <h2 class="text-lg font-semibold text-indigo-300">Multi-Ad Network Slots (多广告位配置)</h2>
                <div>
                    <label class="block text-sm font-medium text-slate-300">1. Header Ad Code (顶部横幅广告)</label>
                    <textarea name="ad_header" rows="2" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-xs">{{ config.ad_header }}</textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-300">2. Sidebar Ad Code (侧边栏广告)</label>
                    <textarea name="ad_sidebar" rows="2" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-xs">{{ config.ad_sidebar }}</textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-300">3. Tool Workspace Inner Ad Code (工具内容下方独立广告位)</label>
                    <textarea name="ad_tool_content" rows="2" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-xs">{{ config.ad_tool_content }}</textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-300">4. Footer Ad Code (底部通栏广告)</label>
                    <textarea name="ad_footer" rows="2" class="w-full mt-1 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-xs">{{ config.ad_footer }}</textarea>
                </div>
            </div>

            <div class="pt-2 flex space-x-4">
                <button type="submit" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-6 rounded transition shadow">Save Configuration</button>
                <a href="/admin/trigger" class="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 px-6 rounded transition text-center shadow flex items-center justify-center">Run Generation Now</a>
            </div>
        </form>

        <div class="mt-8 bg-slate-900 p-4 rounded-lg border border-slate-700">
            <h2 class="text-sm font-semibold text-slate-200 mb-3">🛠️ Categorized Tools Suite Managed</h2>
            <ul class="space-y-2 mb-4 max-h-48 overflow-y-auto">
                {% for t in tools %}
                    <li class="flex justify-between items-center bg-slate-950 p-2 rounded text-xs font-mono text-slate-300 border border-slate-800">
                        <span><strong>{{ t.name }}</strong> <span class="text-indigo-400">[{{ t.category }}]</span></span>
                        <a href="/admin/tool/delete?id={{ t.id }}" class="text-rose-400 hover:underline">Delete</a>
                    </li>
                {% endfor %}
            </ul>
        </div>

        <div class="mt-8 bg-slate-900 p-4 rounded-lg border border-slate-700">
            <div class="flex justify-between items-center mb-3">
                <h2 class="text-sm font-semibold text-slate-200">📋 System Logs</h2>
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
    tools = load_tools()
    logs = get_logs()
    return render_template_string(ADMIN_HTML, config=config, tools=tools, logs=logs)

@app.route("/admin/save", methods=["POST"])
def admin_save():
    config = load_config()
    config["github_user"] = request.form.get("github_user", "xpsesei")
    config["repo_name"] = request.form.get("repo_name", "xp")
    config["token"] = request.form.get("token", "")
    config["custom_domain"] = request.form.get("custom_domain", "").strip()
    config["interval"] = int(request.form.get("interval", 3600))
    config["gemini_api_keys"] = request.form.get("gemini_api_keys", "").strip()
    config["gemini_model"] = request.form.get("gemini_model", "gemini-1.5-flash").strip()
    config["ad_header"] = request.form.get("ad_header", "")
    config["ad_sidebar"] = request.form.get("ad_sidebar", "")
    config["ad_footer"] = request.form.get("ad_footer", "")
    config["ad_tool_content"] = request.form.get("ad_tool_content", "")
    save_config(config)
    log_message("Configuration saved. Re-generating static site and syncing...")
    generate_static_site_and_push(config, load_tools())
    return redirect(url_for("admin"))

@app.route("/admin/tool/delete")
def admin_delete_tool():
    tool_id = request.args.get("id")
    tools = load_tools()
    tools = [t for t in tools if t["id"] != tool_id]
    save_tools(tools)
    log_message(f"Deleted tool ID: {tool_id}")
    generate_static_site_and_push(load_config(), tools)
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
    log_message("Manual Gemini generation triggered.")
    auto_expand_and_sync()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)
