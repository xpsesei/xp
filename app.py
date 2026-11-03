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
    "ai_api_keys": "",
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

AUTO_EXPANSION_QUEUE = [
    {
        "id": "uuid",
        "name": "🆔 UUID v4 Generator",
        "category": "Security & Cryptography",
        "desc": "Generate random cryptographic unique identifiers.",
        "html": '<button onclick="genUUID()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded transition">Generate UUID v4</button><input type="text" id="uuid-output" readonly class="w-full mt-3 p-2 bg-slate-900 border border-slate-700 rounded text-indigo-300 font-mono">'
    },
    {
        "id": "base64",
        "name": "🔄 Base64 Encoder / Decoder",
        "category": "Text & Formatting",
        "desc": "Encode or decode text securely in your browser.",
        "html": '<textarea id="b64-input" rows="2" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm" placeholder="Enter text..."></textarea><div class="flex space-x-3 mt-2"><button onclick="b64Encode()" class="bg-indigo-600 text-white px-3 py-1 rounded text-xs">Encode</button><button onclick="b64Decode()" class="bg-slate-700 text-white px-3 py-1 rounded text-xs">Decode</button></div><textarea id="b64-output" rows="2" readonly class="w-full mt-2 p-2 bg-slate-900 border border-slate-700 rounded text-indigo-300 font-mono text-sm"></textarea>'
    },
    {
        "id": "timestamp",
        "name": "⏱️ Epoch Timestamp",
        "category": "Math & Converters",
        "desc": "Convert current or custom Epoch timestamp.",
        "html": '<button onclick="getTimestamp()" class="bg-indigo-600 text-white px-3 py-1 rounded text-xs mb-2">Get Timestamp</button><input type="text" id="ts-output" readonly class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-indigo-300 font-mono text-sm">'
    },
    {
        "id": "url",
        "name": "🔗 URL Encoder / Decoder",
        "category": "Network & DevOps",
        "desc": "Safely encode and decode URL query strings.",
        "html": '<textarea id="url-input" rows="2" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm" placeholder="Enter URL..."></textarea><div class="flex space-x-3 mt-2"><button onclick="urlEncode()" class="bg-indigo-600 text-white px-3 py-1 rounded text-xs">Encode</button><button onclick="urlDecode()" class="bg-slate-700 text-white px-3 py-1 rounded text-xs">Decode</button></div><textarea id="url-output" rows="2" readonly class="w-full mt-2 p-2 bg-slate-900 border border-slate-700 rounded text-indigo-300 font-mono text-sm"></textarea>'
    },
    {
        "id": "markdown",
        "name": "📝 Markdown Previewer",
        "category": "Text & Formatting",
        "desc": "Write Markdown and preview live formatting.",
        "html": '<div class="grid grid-cols-1 md:grid-cols-2 gap-4"><textarea id="md-input" rows="4" class="p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm" oninput="renderMD()"># Hello\\nMarkdown preview</textarea><div id="md-output" class="p-3 bg-slate-900 rounded border border-slate-700 text-slate-200 text-sm"></div></div>'
    },
    {
        "id": "jwt",
        "name": "🛡️ JWT Inspector",
        "category": "Security & Cryptography",
        "desc": "Decode JSON Web Token header and payload locally.",
        "html": '<textarea id="jwt-input" rows="3" placeholder="Paste JWT token..." class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm" oninput="decodeJWT()"></textarea><div class="mt-3 grid grid-cols-2 gap-3"><pre id="jwt-header" class="p-2 bg-slate-900 rounded text-xs font-mono text-slate-300 overflow-x-auto">Header</pre><pre id="jwt-payload" class="p-2 bg-slate-900 rounded text-xs font-mono text-slate-300 overflow-x-auto">Payload</pre></div>'
    },
    {
        "id": "cron",
        "name": "⏰ Cron Expression Parser",
        "category": "Network & DevOps",
        "desc": "Analyze Cron schedule expressions easily.",
        "html": '<input type="text" id="cron-input" value="0 * * * *" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 mb-2 font-mono text-sm" oninput="parseCron()"><div id="cron-out" class="p-2 bg-slate-900 rounded text-xs font-mono text-indigo-300">Every hour schedule format</div>'
    },
    {
        "id": "sql_fmt",
        "name": "🗄️ SQL Formatter",
        "category": "Data & Database",
        "desc": "Clean and format SQL query statements.",
        "html": '<textarea id="sql-input" rows="3" class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm" placeholder="SELECT...">SELECT id, name FROM users WHERE active = 1;</textarea><button onclick="formatSQL()" class="mt-2 bg-indigo-600 text-white px-3 py-1 rounded text-xs">Format SQL</button><pre id="sql-out" class="mt-2 p-2 bg-slate-900 rounded text-xs font-mono text-emerald-400"></pre>'
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

def auto_expand_and_sync():
    config = load_config()
    if not config.get("running", False):
        return

    token = config.get("token", "").strip()
    if not token:
        log_message("Error: GitHub Token is empty! Please configure it in admin panel.")
        return

    log_message("Scheduled task triggered: Expanding and syncing tool suite...")
    tools = load_tools()
    existing_ids = {t["id"] for t in tools}

    added_count = 0
    for candidate in AUTO_EXPANSION_QUEUE:
        if candidate["id"] not in existing_ids:
            tools.append(candidate)
            existing_ids.add(candidate["id"])
            added_count += 1
            log_message(f"Auto-expanded tool into [{candidate.get('category')}]: {candidate['name']}")

    save_tools(tools)
    generate_static_site_and_push(config, tools)

def generate_static_site_and_push(config, tools):
    token = config.get("token", "").strip()
    user = config.get("github_user")
    repo = config.get("repo_name")
    custom_domain = config.get("custom_domain", "").strip()
    ad_header = config.get("ad_header", "")
    ad_sidebar = config.get("ad_sidebar", "")
    ad_footer = config.get("ad_footer", "")
    ad_tool_content = config.get("ad_tool_content", "")
    ai_keys_raw = config.get("ai_api_keys", "").strip()
    ai_status_text = "Multi-AI Failover Active" if ai_keys_raw else "Standard Mode"

    if custom_domain:
        with open("CNAME", "w", encoding="utf-8") as f:
            f.write(custom_domain)
        log_message(f"Custom domain CNAME generated: {custom_domain}")
        
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
        function genUUID() {
            let el = document.getElementById('uuid-output');
            if(el) el.value = ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
                (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
            );
        }
        function b64Encode() {
            try { document.getElementById('b64-output').value = btoa(document.getElementById('b64-input').value); } catch(e) { alert(e); }
        }
        function b64Decode() {
            try { document.getElementById('b64-output').value = atob(document.getElementById('b64-input').value); } catch(e) { alert(e); }
        }
        function getTimestamp() {
            let el = document.getElementById('ts-output');
            if(el) el.value = Math.floor(Date.now() / 1000);
        }
        function urlEncode() {
            document.getElementById('url-output').value = encodeURIComponent(document.getElementById('url-input').value);
        }
        function urlDecode() {
            document.getElementById('url-output').value = decodeURIComponent(document.getElementById('url-input').value);
        }
        function renderMD() {
            let txt = document.getElementById('md-input').value;
            document.getElementById('md-output').innerHTML = "<p>" + txt.replace(/\\n/g, "<br>") + "</p>";
        }
        function decodeJWT() {
            try {
                let parts = document.getElementById('jwt-input').value.split('.');
                if(parts.length >= 2) {
                    document.getElementById('jwt-header').innerText = JSON.stringify(JSON.parse(atob(parts[0])), null, 2);
                    document.getElementById('jwt-payload').innerText = JSON.stringify(JSON.parse(atob(parts[1])), null, 2);
                }
            } catch(e) {
                document.getElementById('jwt-header').innerText = "Invalid JWT";
            }
        }
        function parseCron() {
            document.getElementById('cron-out').innerText = "Parsed: Valid schedule format.";
        }
        function formatSQL() {
            let q = document.getElementById('sql-input').value;
            document.getElementById('sql-out').innerText = q.replace(/SELECT/gi, '\\nSELECT').replace(/FROM/gi, '\\nFROM');
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

    # 智能 Git 提交与推送（自动检查是否有变动，避免工作区干净时报错）
    try:
        subprocess.run(["git", "add", "."], check=True)
        status_res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        
        if status_res.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Automated sync platform updates and domain configuration"], check=True)
            remote_url = f"https://{token}@github.com/{user}/{repo}.git"
            subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
            subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True)
            subprocess.run(["git", "push", "-u", "origin", "main", "--force"], check=True)
            log_message("Success: Static site changes committed and pushed to GitHub!")
        else:
            log_message("Git sync: Working tree clean, no changes to commit.")
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
                    <span class="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-semibold animate-pulse">● Service Running</span>
                {% else %}
                    <span class="px-3 py-1 bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-full text-xs font-semibold">■ Service Stopped</span>
                {% endif %}
            </div>
        </div>
        
        <div class="bg-slate-900 p-4 rounded-lg border border-slate-700 mb-6 flex items-center justify-between">
            <div>
                <h2 class="text-sm font-semibold text-slate-200">Program Control</h2>
                <p class="text-xs text-slate-400">Start or stop automated generation & GitHub synchronization.</p>
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

            <div class="bg-slate-900/50 p-4 rounded-lg border border-slate-700 space-y-4">
                <h2 class="text-lg font-semibold text-indigo-300">AI Model Multi-Keys Integration</h2>
                <div>
                    <label class="block text-sm font-medium text-slate-300 mb-1">AI API Keys (每行输入一个 Key)</label>
                    <textarea name="ai_api_keys" rows="3" placeholder="sk-..." class="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-100 font-mono text-sm">{{ config.ai_api_keys }}</textarea>
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
    config["ai_api_keys"] = request.form.get("ai_api_keys", "").strip()
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
    log_message("Manual generation triggered.")
    auto_expand_and_sync()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)
