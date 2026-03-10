"""
Side Hustle Idea Generator — Make money from your skills

Setup:
  pip install -r requirements.txt
  cp .env.example .env          # add your GROQ_API_KEY
  uvicorn main:app --reload
  open http://localhost:8000
"""
import os, sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DB_FILE      = "side_hustle_idea_generator.db"
SYSTEM_PROMPT = "You are an expert Side Hustle Idea Generator assistant. Describe your skills and time availability. Get 10 side hustle ideas ranked by earning potential."

app = FastAPI(title="Side Hustle Idea Generator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Database ───────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                result TEXT,
                ts     TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

init_db()


# ── Frontend (injected HTML app) ───────────────────────────────────────────────

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Side Hustle Idea Generator</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Barlow:ital,wght@0,300;0,400;0,500;0,600;1,300&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --acc:#f5c842;--acc2:#ffd96a;--bg:#09080a;
  --s1:color-mix(in srgb,var(--bg) 70%,#111);
  --s2:color-mix(in srgb,var(--bg) 50%,#111);
  --b1:rgba(255,255,255,.07);--b2:rgba(255,255,255,.12);
  --text:#f0f0f8;--muted:#8090a0;--dim:#3a4050;
  --ok:#34d399;--err:#f87171;
}
html{scroll-behavior:smooth}
body{font-family:'Barlow',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}

/* ── Auth overlay ─────────────────────────────────────────────────── */
#auth-overlay{
  position:fixed;inset:0;z-index:200;
  display:flex;align-items:stretch;
  background:var(--bg);
}
/* left panel: branding */
.auth-panel-left{
  flex:1;display:none;
  background:linear-gradient(145deg,var(--acc),color-mix(in srgb,var(--acc2) 80%,black 20%));
  padding:48px;flex-direction:column;justify-content:flex-end;
}
@media(min-width:700px){.auth-panel-left{display:flex}}
.auth-panel-brand{font-family:'Syne',sans-serif;font-size:36px;font-weight:800;color:#fff;line-height:1.1;margin-bottom:12px;letter-spacing:-1px}
.auth-panel-sub{color:rgba(255,255,255,.7);font-size:15px;font-weight:300;line-height:1.7;max-width:320px}
/* right panel: form */
.auth-panel-right{
  width:100%;max-width:440px;
  padding:48px 40px;
  display:flex;flex-direction:column;justify-content:center;
  background:var(--s1);
  border-left:1px solid var(--b1);
}
@media(max-width:699px){.auth-panel-right{max-width:100%;padding:32px 24px}}
.auth-box{width:100%}
.auth-logo{font-family:'Syne',sans-serif;font-size:20px;font-weight:800;letter-spacing:-.4px;color:var(--acc);margin-bottom:4px}
.auth-sub-txt{color:var(--muted);font-size:13px;margin-bottom:32px;font-weight:300}
.auth-tabs{display:flex;gap:0;margin-bottom:24px;border-bottom:1px solid var(--b1)}
.auth-tab{flex:1;padding:9px 0;text-align:center;font-size:12px;font-weight:600;letter-spacing:.06em;cursor:pointer;transition:all .15s;color:var(--muted);border:none;background:none;font-family:'Barlow',sans-serif;border-bottom:2px solid transparent;margin-bottom:-1px}
.auth-tab.active{color:var(--text);border-bottom-color:var(--acc)}
.auth-field{margin-bottom:16px}
.auth-field label{display:block;font-size:10px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:7px}
.auth-field input{width:100%;background:var(--s2);border:1px solid var(--b1);border-radius:6px;color:var(--text);padding:12px 16px;font-size:14px;font-family:'Barlow',sans-serif;font-weight:300;outline:none;transition:all .2s}
.auth-field input:focus{border-color:color-mix(in srgb,var(--acc) 70%,transparent);box-shadow:0 0 0 3px color-mix(in srgb,var(--acc) 10%,transparent)}
.auth-field input::placeholder{color:var(--dim)}
.auth-btn{width:100%;background:var(--acc);color:var(--bg);border:none;border-radius:6px;padding:13px;font-weight:700;font-size:14px;font-family:'Barlow',sans-serif;cursor:pointer;transition:all .15s;margin-top:4px;letter-spacing:.02em}
.auth-btn:hover{filter:brightness(1.08);transform:translateY(-1px)}
.auth-err{color:var(--err);font-size:12px;margin-top:10px}

/* ── Setup overlay ────────────────────────────────────────────────── */
#setup-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);backdrop-filter:blur(12px);z-index:200;align-items:center;justify-content:center;}
#setup-local,#setup-deployed{background:var(--s1);border:1px solid var(--b2);border-radius:12px;padding:40px;max-width:460px;width:90%;text-align:center;display:none;}
#setup-key-input{width:100%;background:var(--s2);border:1px solid var(--b1);border-radius:8px;color:var(--text);padding:12px 16px;font-size:14px;outline:none;margin-bottom:12px;font-family:monospace;box-sizing:border-box;}

/* ── API key banner ───────────────────────────────────────────────── */
#apikey-banner{display:none;background:rgba(248,113,113,.1);border-bottom:1px solid rgba(248,113,113,.2);padding:10px 28px;font-size:12px;color:var(--err);align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
#apikey-banner input{background:var(--s2);border:1px solid var(--b1);border-radius:6px;color:var(--text);padding:7px 12px;font-size:12px;font-family:monospace;width:280px;outline:none;}
#apikey-banner button{background:var(--err);color:#fff;border:none;border-radius:6px;padding:7px 14px;font-size:12px;cursor:pointer;font-family:'Barlow',sans-serif;font-weight:600;}

/* ── Header ───────────────────────────────────────────────────────── */
header{
  position:sticky;top:0;z-index:100;
  display:flex;align-items:center;justify-content:space-between;
  padding:13px 32px;
  background:rgba(0,0,0,.5);backdrop-filter:blur(20px);
  border-bottom:1px solid var(--b1);
}
.logo{font-family:'Syne',sans-serif;font-size:18px;font-weight:800;letter-spacing:-.4px;color:var(--text)}
.logo span{color:var(--acc)}
.mode-badge{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);border:1px solid var(--b1);border-radius:99px;padding:3px 11px}
.hdr-right{display:flex;align-items:center;gap:14px}
.user-chip{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}
.user-avatar{width:28px;height:28px;border-radius:6px;background:var(--acc);color:var(--bg);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800}
.btn-logout{font-size:11px;color:var(--muted);cursor:pointer;background:transparent;border:1px solid var(--b1);border-radius:6px;padding:5px 12px;transition:all .15s;font-family:'Barlow',sans-serif;font-weight:500}
.btn-logout:hover{border-color:var(--err);color:var(--err)}

/* ── Hero band ────────────────────────────────────────────────────── */
.hero-band{
  background:linear-gradient(145deg,var(--acc),color-mix(in srgb,var(--acc2) 80%,black 20%));
  padding:72px max(24px,calc(50vw - 430px)) 110px;
  position:relative;overflow:hidden;
}
.hero-band::before{
  content:'';position:absolute;inset:0;
  background:url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23fff' fill-opacity='.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}
.hero-kicker{
  display:inline-flex;align-items:center;gap:8px;
  font-size:10px;font-weight:600;letter-spacing:.2em;text-transform:uppercase;
  color:rgba(255,255,255,.7);margin-bottom:18px;
}
.hero-band h1{
  font-family:'Syne',sans-serif;
  font-size:clamp(32px,6vw,64px);font-weight:800;line-height:1.05;
  letter-spacing:-2px;color:#fff;margin-bottom:16px;max-width:720px;
}
.hero-band h1 em{font-style:normal;opacity:.75}
.hero-band p{color:rgba(255,255,255,.65);font-size:16px;line-height:1.75;font-weight:300;max-width:560px}

/* ── Main content area ─────────────────────────────────────────────── */
.below-hero{
  max-width:860px;margin:-64px auto 0;padding:0 24px 80px;position:relative;z-index:10;
}

/* ── Cards ────────────────────────────────────────────────────────── */
.card{
  background:var(--s1);border:1px solid var(--b1);border-radius:14px;
  padding:28px;margin-bottom:16px;
  box-shadow:0 24px 64px rgba(0,0,0,.4);
  transition:border-color .2s;
}
.card:focus-within{border-color:var(--b2)}
.card-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.card-lbl{font-size:10px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.card-action{font-size:11px;color:var(--dim);cursor:pointer;transition:color .15s;background:none;border:none;font-family:'Barlow',sans-serif;font-weight:500}
.card-action:hover{color:var(--muted)}

/* ── Inputs ───────────────────────────────────────────────────────── */
.field{margin-bottom:18px}
.field:last-child{margin-bottom:0}
.field label{display:block;font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
.field input[type=text],
.field textarea,
.field select{
  width:100%;background:var(--s2);border:1px solid var(--b1);border-radius:8px;
  color:var(--text);padding:13px 16px;font-size:15px;
  font-family:'Barlow',sans-serif;font-weight:300;
  outline:none;transition:all .2s;
}
.field input[type=text]:focus,
.field textarea:focus,
.field select:focus{
  border-color:color-mix(in srgb,var(--acc) 60%,transparent);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--acc) 10%,transparent);
}
.field input::placeholder,.field textarea::placeholder{color:var(--dim)}
.field textarea{resize:vertical;min-height:110px;line-height:1.6}
.field select{cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238090a0' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 14px center;padding-right:36px}
.field select option{background:var(--s1)}

/* ── Buttons ──────────────────────────────────────────────────────── */
.btn-row{display:flex;align-items:center;gap:12px;margin-top:22px;flex-wrap:wrap}
.btn-primary{
  font-family:'Syne',sans-serif;font-size:14px;font-weight:800;letter-spacing:-.2px;
  background:var(--acc);color:var(--bg);
  border:none;border-radius:8px;padding:12px 28px;
  cursor:pointer;transition:all .15s;display:inline-flex;align-items:center;gap:8px;
  box-shadow:0 4px 20px color-mix(in srgb,var(--acc) 35%,transparent);
}
.btn-primary:hover{filter:brightness(1.08);transform:translateY(-2px);box-shadow:0 8px 28px color-mix(in srgb,var(--acc) 45%,transparent)}
.btn-primary:active{transform:none;box-shadow:none}
.btn-primary:disabled{opacity:.35;cursor:not-allowed;transform:none;box-shadow:none}
.btn-ghost{font-family:'Barlow',sans-serif;font-weight:500;background:transparent;color:var(--muted);border:1px solid var(--b2);border-radius:8px;padding:12px 20px;font-size:14px;cursor:pointer;transition:all .15s}
.btn-ghost:hover{border-color:var(--b2);color:var(--text);background:var(--s2)}
.hint{font-size:11px;color:var(--dim)}

/* ── Loading ──────────────────────────────────────────────────────── */
.loading{display:none;align-items:center;gap:10px;margin-top:16px;color:var(--acc);font-size:13px;font-weight:500}
.spin{width:16px;height:16px;flex-shrink:0;border:2px solid color-mix(in srgb,var(--acc) 20%,transparent);border-top-color:var(--acc);border-radius:50%;animation:spin .55s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Result ───────────────────────────────────────────────────────── */
#result-card{display:none}
.result-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.result-lbl{font-family:'Syne',sans-serif;font-size:16px;font-weight:800;letter-spacing:-.3px;color:var(--text)}
.copy-btn{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--muted);background:none;border:1px solid var(--b1);border-radius:6px;padding:5px 12px;cursor:pointer;transition:all .15s;font-family:'Barlow',sans-serif;font-weight:500}
.copy-btn:hover{border-color:var(--acc);color:var(--acc)}
.copy-btn.copied{border-color:var(--ok);color:var(--ok)}
.result-text{background:var(--s2);border:1px solid var(--b1);border-left:3px solid var(--acc);border-radius:0 10px 10px 0;padding:20px 22px;font-size:15px;line-height:1.85;white-space:pre-wrap;color:var(--text);font-weight:300;animation:fadeUp .25s ease}
.result-list{list-style:none;display:flex;flex-direction:column;gap:10px}
.result-list li{background:var(--s2);border:1px solid var(--b1);border-radius:10px;padding:16px 18px;font-size:15px;line-height:1.7;color:var(--text);font-weight:300;animation:fadeUp .2s ease both;display:flex;gap:12px;align-items:baseline}
.result-list li strong{color:var(--acc);font-family:'Syne',sans-serif;font-size:14px;font-weight:700;display:block;margin-bottom:4px}
.result-list .item-num{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:6px;background:color-mix(in srgb,var(--acc) 15%,transparent);color:var(--acc);font-size:11px;font-weight:700;font-family:'Syne',sans-serif;flex-shrink:0}
.result-steps{display:flex;flex-direction:column;gap:10px}
.result-step{display:flex;gap:16px;background:var(--s2);border:1px solid var(--b1);border-radius:10px;padding:16px 18px;animation:fadeUp .2s ease both}
.step-num{display:flex;align-items:center;justify-content:center;flex-shrink:0;width:32px;height:32px;border-radius:8px;background:var(--acc);color:var(--bg);font-size:13px;font-weight:800;font-family:'Syne',sans-serif;margin-top:1px}
.step-body{font-size:15px;line-height:1.7;color:var(--text);font-weight:300}
.step-body strong{display:block;font-weight:700;margin-bottom:4px;font-size:13px;font-family:'Syne',sans-serif;color:var(--text)}
.result-actions-bar{display:flex;gap:8px;margin-top:16px;padding-top:16px;border-top:1px solid var(--b1);flex-wrap:wrap}
.result-action-btn{display:inline-flex;align-items:center;gap:5px;background:transparent;border:1px solid var(--b1);color:var(--muted);border-radius:7px;padding:7px 14px;font-size:11px;font-weight:600;cursor:pointer;transition:all .15s;font-family:'Barlow',sans-serif;letter-spacing:.02em}
.result-action-btn:hover{border-color:var(--acc);color:var(--acc);background:color-mix(in srgb,var(--acc) 6%,transparent)}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}

/* ── History ──────────────────────────────────────────────────────── */
.history-empty{color:var(--dim);font-size:13px;padding:8px 0}
.history-item{padding:14px 0;border-bottom:1px solid var(--b1);display:grid;grid-template-columns:1fr auto;gap:12px;align-items:start;cursor:pointer;transition:opacity .15s}
.history-item:last-child{border:none}
.history-item:hover{opacity:.75}
.hi-prompt{font-size:12px;color:var(--muted);margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hi-preview{font-size:12px;color:var(--dim);line-height:1.5;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.hi-time{font-size:10px;color:var(--dim);white-space:nowrap;padding-top:2px}
.hi-del{background:none;border:none;color:var(--dim);cursor:pointer;font-size:14px;padding:0 4px;line-height:1;transition:color .15s}
.hi-del:hover{color:var(--err)}

/* ── Footer ───────────────────────────────────────────────────────── */
footer{margin-top:60px;padding-top:18px;border-top:1px solid var(--b1);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
.foot-note{font-size:11px;color:var(--dim)}
.foot-links{display:flex;gap:14px}
.foot-links a{font-size:11px;color:var(--dim);text-decoration:none;transition:color .15s}
.foot-links a:hover{color:var(--muted)}

@media(max-width:600px){.hero-band{padding:52px 20px 90px}.below-hero{padding:0 16px 60px}.below-hero{margin-top:-48px}.hero-band h1{font-size:32px;letter-spacing:-1px}}
</style>
</head>
<body>

<div id="auth-overlay">
  <div class="auth-panel-left">
    <div class="auth-panel-brand">Side Hustle Idea Generator</div>
    <div class="auth-panel-sub">Describe your skills and time availability. Get 10 side hustle ideas ranked by earning potential. Built for users.</div>
  </div>
  <div class="auth-panel-right">
    <div class="auth-box">
      <div class="auth-logo">Side Hustle Idea Generator</div>
      <div class="auth-sub-txt">Make money from your skills</div>
      <div class="auth-tabs">
        <button class="auth-tab active" onclick="switchTab('login')">Log in</button>
        <button class="auth-tab" onclick="switchTab('signup')">Sign up</button>
      </div>
      <div id="login-form">
        <div class="auth-field"><label>Email</label><input type="email" id="login-email" placeholder="you@example.com"></div>
        <div class="auth-field"><label>Password</label><input type="password" id="login-pw" placeholder="••••••••"></div>
        <button class="auth-btn" onclick="login()">Log in</button>
      </div>
      <div id="signup-form" style="display:none">
        <div class="auth-field"><label>Name</label><input type="text" id="signup-name" placeholder="Jane Smith"></div>
        <div class="auth-field"><label>Email</label><input type="email" id="signup-email" placeholder="you@example.com"></div>
        <div class="auth-field"><label>Password</label><input type="password" id="signup-pw" placeholder="Min 6 characters"></div>
        <button class="auth-btn" onclick="signup()">Create account</button>
      </div>
      <div class="auth-err" id="auth-err"></div>
    </div>
  </div>
</div>

<div id="setup-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);backdrop-filter:blur(12px);z-index:200;align-items:center;justify-content:center;">
  <div id="setup-local" style="background:var(--s1);border:1px solid var(--b2);border-radius:14px;padding:40px;max-width:460px;width:90%;text-align:center;display:none;">
    <div style="font-size:36px;margin-bottom:12px">🔑</div>
    <h2 style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;margin-bottom:8px">One-time setup</h2>
    <p style="color:var(--muted);font-size:13px;line-height:1.7;margin-bottom:6px;font-weight:300">Paste your free Groq API key below.</p>
    <p style="margin-bottom:24px"><a href="https://console.groq.com" target="_blank" style="color:var(--acc);font-size:12px;font-weight:600">Get a free key at console.groq.com →</a></p>
    <input id="setup-key-input" type="password" placeholder="gsk_..." style="width:100%;background:var(--s2);border:1px solid var(--b1);border-radius:8px;color:var(--text);padding:12px 16px;font-size:14px;outline:none;margin-bottom:12px;font-family:monospace;box-sizing:border-box;">
    <div id="setup-err" style="color:var(--err);font-size:12px;margin-bottom:10px;min-height:18px"></div>
    <button onclick="saveSetupKey()" style="width:100%;background:var(--acc);color:var(--bg);border:none;border-radius:8px;padding:13px;font-weight:800;font-size:14px;cursor:pointer;font-family:'Syne',sans-serif">Save &amp; Start</button>
  </div>
  <div id="setup-deployed" style="background:var(--s1);border:1px solid var(--b2);border-radius:14px;padding:40px;max-width:460px;width:90%;text-align:center;display:none;">
    <div style="font-size:36px;margin-bottom:12px">⚙️</div>
    <h2 style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;margin-bottom:8px">Not configured</h2>
    <p style="color:var(--muted);font-size:13px;line-height:1.7;font-weight:300;margin-bottom:24px">Add <code style="background:var(--s2);padding:2px 6px;border-radius:4px">GROQ_API_KEY</code> as an environment variable in your hosting dashboard.</p>
    <a href="https://console.groq.com" target="_blank" style="display:inline-block;background:var(--acc);color:var(--bg);text-decoration:none;border-radius:8px;padding:11px 22px;font-weight:800;font-size:13px;font-family:'Syne',sans-serif">Get a free Groq key →</a>
  </div>
</div>

<div id="apikey-banner">
  <span>⚡ Enter your free Groq API key</span>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
    <input type="password" id="apikey-input" placeholder="gsk_...">
    <button onclick="saveApiKey()">Save key</button>
    <a href="https://console.groq.com" target="_blank" style="font-size:11px;color:var(--muted);text-decoration:none">Get free key →</a>
  </div>
</div>

<header id="main-header" style="display:none">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo"><span>Side Hustle Idea Generator</span></div>
    <div class="mode-badge" id="mode-badge">HTML App</div>
  </div>
  <div class="hdr-right">
    <div class="user-chip">
      <div class="user-avatar" id="user-avatar">?</div>
      <span id="user-name" style="font-size:12px"></span>
    </div>
    <button class="btn-logout" onclick="logout()">Log out</button>
  </div>
</header>

<div id="main-app" style="display:none">
  <div class="hero-band">
    <div class="hero-kicker">✦ AI-powered tool</div>
    <h1><em>Side Hustle Idea Generator</em><br>Make money from your skills</h1>
    <p>Describe your skills and time availability. Get 10 side hustle ideas ranked by earning potential. Built for users.</p>
  </div>

  <div class="below-hero">
    <div class="card" id="input-card">
      <div class="card-hd">
        <div class="card-lbl">Your inputs</div>
        <button class="card-action" onclick="clearForm()">Clear</button>
      </div>
          <div class="field">
      <label for="field-skills">Skills</label>
      <textarea id="field-skills" placeholder="Enter skills..." required></textarea>
    </div>
    <div class="field">
      <label for="field-available_hours">Available Hours</label>
      <input type="text" id="field-available_hours" placeholder="e.g. your available hours">
    </div>
    <div class="field">
      <label for="field-income_goal">Income Goal</label>
      <select id="field-income_goal">
        <option value="">— Select —</option>
      <option value="Make a request">Make a request</option>
      <option value="Follow up">Follow up</option>
      <option value="Decline politely">Decline politely</option>
      <option value="Introduce myself">Introduce myself</option>
      <option value="Give feedback">Give feedback</option>
      <option value="Share update">Share update</option>
      </select>
    </div>
    <div class="field">
      <label for="field-interests">Interests</label>
      <input type="text" id="field-interests" placeholder="e.g. your interests">
    </div>
      <div class="btn-row">
        <button class="btn-primary" onclick="generate()" id="gen-btn">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
          Generate
        </button>
        <button class="btn-ghost" onclick="clearForm()">Clear</button>
        <span class="hint">Ctrl + Enter</span>
      </div>
      <div class="loading" id="loading">
        <div class="spin"></div>
        <span id="loading-text">Generating...</span>
      </div>
    </div>

    <div class="card" id="result-card">
      <div class="result-hd">
        <div class="result-lbl">Result</div>
        <button class="copy-btn" id="copy-btn" onclick="copyResult()">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
          Copy
        </button>
      </div>
      <div id="result-content"></div>
      <div class="result-actions-bar">
        <button class="result-action-btn" onclick="regenerate()">↻ Regenerate</button>
        <button class="result-action-btn" onclick="improveResult()">✦ Improve</button>
        <button class="result-action-btn" onclick="differentStyle()">◎ Different Style</button>
      </div>
    </div>

    <div class="card" id="history-section">
      <div class="card-hd">
        <div class="card-lbl">History</div>
        <button class="card-action" onclick="clearHistory()">Clear all</button>
      </div>
      <div id="history-list"><div class="history-empty">No history yet — generate something above.</div></div>
    </div>

    <footer>
      <div class="foot-note">Side Hustle Idea Generator · Powered by Groq llama-3.3-70b</div>
      <div class="foot-links">
        <a href="#" onclick="logout();return false">Log out</a>
        
      </div>
    </footer>
  </div>
</div>

<script>
const APP={name:'Side Hustle Idea Generator',mode:'fastapi',auth:false,systemPrompt:"You are an expert Side Hustle Idea Generator assistant. Describe your skills and time availability. Get 10 side hustle ideas ranked by earning potential.",promptTemplate:"Skills: {{skills}}\\nAvailable Hours: {{available_hours}}\\nIncome Goal: {{income_goal}}\\nInterests: {{interests}}",resultFormat:'list',resultConfig:{"label": "Result", "copyable": true},inputs:[{"id": "skills", "label": "Skills", "type": "textarea", "placeholder": "Enter skills...", "required": true}, {"id": "available_hours", "label": "Available Hours", "type": "text", "placeholder": "e.g. your available hours", "required": false}, {"id": "income_goal", "label": "Income Goal", "type": "select", "options": ["Make a request", "Follow up", "Decline politely", "Introduce myself", "Give feedback", "Share update"], "required": false}, {"id": "interests", "label": "Interests", "type": "text", "placeholder": "e.g. your interests", "required": false}]};
const USERS_KEY=APP.name+':users',SESSION_KEY=APP.name+':session';
function getUsers(){try{return JSON.parse(localStorage.getItem(USERS_KEY)||'{}')}catch{return{}}}
function getSession(){try{return JSON.parse(localStorage.getItem(SESSION_KEY)||'null')}catch{return null}}
function saveSession(s){localStorage.setItem(SESSION_KEY,JSON.stringify(s))}
function switchTab(tab){document.getElementById('login-form').style.display=tab==='login'?'':'none';document.getElementById('signup-form').style.display=tab==='signup'?'':'none';document.querySelectorAll('.auth-tab').forEach((t,i)=>t.classList.toggle('active',i===(tab==='login'?0:1)));document.getElementById('auth-err').textContent=''}
function signup(){const name=document.getElementById('signup-name').value.trim(),email=document.getElementById('signup-email').value.trim().toLowerCase(),pw=document.getElementById('signup-pw').value;if(!name||!email||!pw){setAuthErr('All fields required.');return}if(pw.length<6){setAuthErr('Password must be 6+ characters.');return}const users=getUsers();if(users[email]){setAuthErr('Account exists. Log in instead.');return}users[email]={name,pw,created:Date.now()};localStorage.setItem(USERS_KEY,JSON.stringify(users));saveSession({email,name});onLoggedIn({email,name})}
function login(){const email=document.getElementById('login-email').value.trim().toLowerCase(),pw=document.getElementById('login-pw').value;if(!email||!pw){setAuthErr('Enter your email and password.');return}const users=getUsers();if(!users[email]||users[email].pw!==pw){setAuthErr('Incorrect email or password.');return}const session={email,name:users[email].name};saveSession(session);onLoggedIn(session)}
function logout(){localStorage.removeItem(SESSION_KEY);document.getElementById('auth-overlay').style.display='flex';document.getElementById('main-header').style.display='none';document.getElementById('main-app').style.display='none';document.getElementById('auth-err').textContent='';document.getElementById('login-email').value='';document.getElementById('login-pw').value=''}
function setAuthErr(msg){document.getElementById('auth-err').textContent=msg}
function onLoggedIn(session){document.getElementById('auth-overlay').style.display='none';document.getElementById('main-header').style.display='flex';document.getElementById('main-app').style.display='block';document.getElementById('user-name').textContent=session.name.split(' ')[0];document.getElementById('user-avatar').textContent=session.name[0].toUpperCase();checkApiKey();renderHistory()}
function checkApiKey(){if(APP.mode!=='html')return;const key=localStorage.getItem(APP.name+':apikey')||'';document.getElementById('apikey-banner').style.display=key?'none':'flex';if(key)document.getElementById('apikey-input').value=key}
function saveApiKey(){const key=document.getElementById('apikey-input').value.trim();if(!key)return;localStorage.setItem(APP.name+':apikey',key);document.getElementById('apikey-banner').style.display='none'}
function buildPrompt(){let prompt=APP.promptTemplate;for(const inp of APP.inputs){const el=document.getElementById('field-'+inp.id);const val=el?el.value.trim():'';if(inp.required&&!val)throw new Error(`Please fill in "${inp.label}"`);prompt=prompt.replace(new RegExp('\\\\{\\\\{'+inp.id+'\\\\}\\\\}','g'),val||'(not specified)')}return prompt}
async function callGroq(userPrompt){if(APP.mode==='html'){const key=localStorage.getItem(APP.name+':apikey')||'';if(!key)throw new Error('Please enter your Groq API key above.');const r=await fetch('https://api.groq.com/openai/v1/chat/completions',{method:'POST',headers:{'Authorization':'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({model:'llama-3.3-70b-versatile',messages:[{role:'system',content:APP.systemPrompt},{role:'user',content:userPrompt}],max_tokens:1500})});if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e?.error?.message||'Groq API error '+r.status)}const d=await r.json();return d.choices[0].message.content}else{const r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:userPrompt})});if(!r.ok){const e=await r.json().catch(()=>({}));if(e?.detail==='NO_KEY'){showSetup();throw new Error('__SILENT__')}throw new Error(e?.detail||'Server error '+r.status)}const d=await r.json();return d.result}}
let lastResult='',lastPrompt='';
async function generate(){let prompt;try{prompt=buildPrompt()}catch(e){showErr(e.message);return}lastPrompt=prompt;setLoading(true);document.getElementById('result-card').style.display='none';try{const result=await callGroq(prompt);lastResult=result;renderResult(result);saveToHistory(prompt,result);renderHistory()}catch(e){if(e.message!=='__SILENT__')showErr(e.message)}finally{setLoading(false)}}
function renderResult(text){const card=document.getElementById('result-card');const content=document.getElementById('result-content');card.style.display='block';card.scrollIntoView({behavior:'smooth',block:'nearest'});if(APP.resultFormat==='text'){content.innerHTML=`<div class="result-text">${esc(text)}</div>`}else if(APP.resultFormat==='list'){const items=parseList(text);const ul=document.createElement('ul');ul.className='result-list';items.forEach((item,i)=>{const li=document.createElement('li');li.style.animationDelay=(i*0.04)+'s';const lines=item.trim().split('\\n');if(lines.length>1){li.innerHTML=`<span class="item-num">${i+1}</span><div><strong>${esc(lines[0])}</strong>${esc(lines.slice(1).join('\\n'))}</div>`}else{li.innerHTML=`<span class="item-num">${i+1}</span>${esc(item)}`}ul.appendChild(li)});content.innerHTML='';content.appendChild(ul)}else if(APP.resultFormat==='steps'){const steps=parseSteps(text);const wrap=document.createElement('div');wrap.className='result-steps';steps.forEach((step,i)=>{const div=document.createElement('div');div.className='result-step';div.style.animationDelay=(i*0.05)+'s';div.innerHTML=`<div class="step-num">${i+1}</div><div class="step-body">${formatStepBody(step)}</div>`;wrap.appendChild(div)});content.innerHTML='';content.appendChild(wrap)}}
function parseList(text){const numbered=text.match(/^\\d+[\\.\\)]\\s+.+/mg);if(numbered&&numbered.length>=2){const items=[];let cur='';for(const line of text.split('\\n')){if(/^\\d+[\\.\\)]\\s/.test(line)){if(cur)items.push(cur.trim());cur=line.replace(/^\\d+[\\.\\)]\\s+/,'')}else if(cur){cur+='\\n'+line}}if(cur)items.push(cur.trim());return items.filter(Boolean)}const blocks=text.split(/\\n{2,}/).filter(b=>b.trim());if(blocks.length>=2)return blocks;return text.split('\\n').filter(l=>l.trim())}
function parseSteps(text){const numbered=[];let cur='';for(const line of text.split('\\n')){if(/^\\d+[\\.\\)]\\s/.test(line)||/^\\*\\*[\\w]/.test(line)){if(cur.trim())numbered.push(cur.trim());cur=line.replace(/^\\d+[\\.\\)]\\s+/,'').replace(/^\\*\\*/,'').replace(/\\*\\*$/,'')}else{cur+='\\n'+line}}if(cur.trim())numbered.push(cur.trim());if(numbered.length>=2)return numbered;return text.split(/\\n{2,}/).filter(b=>b.trim())}
function formatStepBody(text){return esc(text).replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>')}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>')}
async function copyResult(){try{await navigator.clipboard.writeText(lastResult);const btn=document.getElementById('copy-btn');btn.textContent='✓ Copied!';btn.classList.add('copied');setTimeout(()=>{btn.innerHTML='<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy';btn.classList.remove('copied')},2000)}catch{}}
const HIST_KEY=APP.name+':history';
function loadHistory(){try{return JSON.parse(localStorage.getItem(HIST_KEY)||'[]')}catch{return[]}}
function saveToHistory(prompt,result){const hist=loadHistory();hist.unshift({id:Date.now(),prompt:prompt.substring(0,120),result,ts:new Date().toLocaleString()});localStorage.setItem(HIST_KEY,JSON.stringify(hist.slice(0,50)))}
function deleteHistoryItem(id){const hist=loadHistory().filter(h=>h.id!==id);localStorage.setItem(HIST_KEY,JSON.stringify(hist));renderHistory()}
function clearHistory(){localStorage.removeItem(HIST_KEY);renderHistory()}
function renderHistory(){const hist=loadHistory();const el=document.getElementById('history-list');if(!hist.length){el.innerHTML='<div class="history-empty">No history yet — generate something above.</div>';return}el.innerHTML=hist.map(h=>`<div class="history-item" onclick="loadHistoryItem(${h.id})"><div><div class="hi-prompt">${esc(h.prompt)}</div><div class="hi-preview">${esc((h.result||'').substring(0,100))}</div></div><div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px"><span class="hi-time">${h.ts}</span><button class="hi-del" onclick="event.stopPropagation();deleteHistoryItem(${h.id})" title="Delete">✕</button></div></div>`).join('')}
function loadHistoryItem(id){const item=loadHistory().find(h=>h.id===id);if(!item)return;lastResult=item.result;renderResult(item.result)}
function setLoading(on){document.getElementById('gen-btn').disabled=on;document.getElementById('loading').style.display=on?'flex':'none'}
function showErr(msg){alert(msg)}
function clearForm(){APP.inputs.forEach(inp=>{const el=document.getElementById('field-'+inp.id);if(el)el.value=''});document.getElementById('result-card').style.display='none'}
document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key==='Enter'&&document.getElementById('main-app').style.display!=='none')generate()});
async function regenerate(){if(!lastPrompt)return;setLoading(true);document.getElementById('result-card').style.display='none';try{const result=await callGroq(lastPrompt);lastResult=result;renderResult(result);saveToHistory(lastPrompt,result);renderHistory()}catch(e){if(e.message!=='__SILENT__')showErr(e.message)}finally{setLoading(false)}}
async function improveResult(){if(!lastResult)return;setLoading(true);document.getElementById('result-card').style.display='none';const p='Improve and expand this result:\\n\\n'+lastResult;try{const result=await callGroq(p);lastResult=result;renderResult(result);saveToHistory(p,result);renderHistory()}catch(e){if(e.message!=='__SILENT__')showErr(e.message)}finally{setLoading(false)}}
async function differentStyle(){if(!lastResult)return;setLoading(true);document.getElementById('result-card').style.display='none';const p='Rewrite in a completely different style and format:\\n\\n'+lastResult;try{const result=await callGroq(p);lastResult=result;renderResult(result);saveToHistory(p,result);renderHistory()}catch(e){if(e.message!=='__SILENT__')showErr(e.message)}finally{setLoading(false)}}
function showSetup(){const overlay=document.getElementById('setup-overlay');const isLocal=location.hostname==='localhost'||location.hostname==='127.0.0.1';document.getElementById('setup-local').style.display=isLocal?'block':'none';document.getElementById('setup-deployed').style.display=isLocal?'none':'block';overlay.style.display='flex';if(isLocal)setTimeout(()=>document.getElementById('setup-key-input').focus(),100)}
async function saveSetupKey(){const key=document.getElementById('setup-key-input').value.trim();const errEl=document.getElementById('setup-err');errEl.textContent='';if(!key){errEl.textContent='Please paste your API key.';return}if(!key.startsWith('gsk_')){errEl.textContent="Groq keys start with gsk_";return}try{const r=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key})});if(!r.ok){const e=await r.json().catch(()=>({}));errEl.textContent=e?.detail||'Error saving key.';return}document.getElementById('setup-overlay').style.display='none'}catch(e){errEl.textContent='Could not save key: '+e.message}}
(function init(){if(typeof __LP_PREVIEW__!=='undefined'&&__LP_PREVIEW__){const s={email:'preview@launchpad.app',name:'Preview'};saveSession(s);onLoggedIn(s);return}if(!APP.auth){document.getElementById('auth-overlay').style.display='none';document.getElementById('main-header').style.display='flex';document.getElementById('main-app').style.display='block';const bl=document.querySelector('.btn-logout');if(bl)bl.style.display='none';if(APP.mode==='fastapi'){fetch('/api/health').then(r=>r.json()).then(d=>{if(!d.ai_ready)showSetup()}).catch(()=>{})}return}const session=getSession();if(session){onLoggedIn(session);if(APP.mode==='fastapi'){fetch('/api/health').then(r=>r.json()).then(d=>{if(!d.ai_ready)showSetup()}).catch(()=>{})}}})();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


# ── API ────────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str

class SetupRequest(BaseModel):
    api_key: str

@app.post("/api/setup")
def setup(req: SetupRequest):
    """Write the API key to .env so user never has to touch a file."""
    key = req.api_key.strip()
    if not key.startswith("gsk_"):
        raise HTTPException(400, detail="Invalid key. Groq keys start with gsk_")
    # Write .env file
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path, "w") as f:
        f.write("GROQ_API_KEY=" + key + chr(10))
    # Reload into current process
    os.environ["GROQ_API_KEY"] = key
    global GROQ_API_KEY
    GROQ_API_KEY = key
    return {"ok": True}

@app.post("/api/generate")
async def generate(req: GenerateRequest):
    if not GROQ_API_KEY:
        raise HTTPException(400, detail="NO_KEY")
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": req.prompt},
                ],
                "max_tokens": 1500,
            },
        )
        r.raise_for_status()
        result = r.json()["choices"][0]["message"]["content"]
    with get_db() as conn:
        conn.execute("INSERT INTO queries (prompt, result) VALUES (?, ?)", (req.prompt, result))
        conn.commit()
    return {"result": result}

@app.get("/api/history")
def history():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, prompt, result, ts FROM queries ORDER BY ts DESC LIMIT 20"
        ).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Side Hustle Idea Generator", "ai_ready": bool(GROQ_API_KEY)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
