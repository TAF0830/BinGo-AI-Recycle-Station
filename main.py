import os
import json
import time
import random
import threading
import cv2
import numpy as np
import tf_keras as keras
import serial
import pyttsx3
from flask import Flask, render_template_string, jsonify, request

DATA_FILE = "users.json"

def load_user_database():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_user_database(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

user_database = load_user_database()

# system operate condition
station_state = {
    "active_user": None,
    "last_heartbeat": 0,
    "last_item": "",
    "last_reward": 0,
    "deposit_status": "Locked: Please scan QR code to start"
}

# point rule
REWARD_POINTS = {
    "RECYCLABLE WASTE": 10,
    "SPECIAL WASTE": 15,
    "FOOD WASTE": 3,
    "GENERAL WASTE": 1
}

SERIAL_PORT = "COM6"
BAUD_RATE = 115200

try:
    esp32 = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"Connected to ESP32-S3 ({SERIAL_PORT}) successfully!")
except Exception as e:
    print(f"Serial port notice: {e}")
    esp32 = None

def speak_async(text):
    def _speak():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass
    threading.Thread(target=_speak, daemon=True).start()

print("Loading AI vision model...")
model = keras.models.load_model("keras_model.h5", compile=False)

# follow labels.txt sequence(0 to 4)
CLASSES = [
    "FOOD WASTE",        # 0
    "GENERAL WASTE",     # 1
    "RECYCLABLE WASTE",  # 2
    "SPECIAL WASTE",     # 3
    "BACKGROUND"         # 4
]

# send to ESP32 instructions
CMD_MAP = {
    "FOOD WASTE": b"1",        # green light (GPIO 7)
    "GENERAL WASTE": b"2",     # yellow light(GPIO 6)
    "RECYCLABLE WASTE": b"3",  # white light (GPIO 5)
    "SPECIAL WASTE": b"4",     # red light (GPIO 4)
    "BACKGROUND": b"0"         # turn off all light
}

def vision_loop():
    global station_state, user_database
    cap = cv2.VideoCapture(0)
    
    pending_item = None
    background_start_time = 0
    item_detect_count = 0
    
    print("\n>>> SmartSort Multi-User Station Online! <<<\n")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        now = time.time()
        current_user = station_state.get("active_user")

        # 1. User disconnected or timed out (> 8s without heartbeat), auto-lock station and reset LEDs/actuators
        if current_user and (now - station_state["last_heartbeat"] > 8):
            print(f"[Session Ended] User {current_user} session closed.")
            station_state["active_user"] = None
            station_state["deposit_status"] = "Locked: Please scan QR code to start"
            current_user = None
            if esp32:
                esp32.write(b"0")

        # 2. Unauthenticated / QR code not scanned state
        if not current_user:
            station_state["deposit_status"] = "Locked: Please scan QR code to start"
            cv2.putText(frame, "LOCKED: SCAN QR CODE TO START", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
            cv2.putText(frame, "Waiting for user authentication...", (20, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)
            cv2.imshow("SmartSort Station", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        # 3. Image preprocessing (convert BGR to RGB, preserve original resize)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(frame_rgb, (224, 224), interpolation=cv2.INTER_AREA)
        img_array = np.asarray(img_resized, dtype=np.float32).reshape(1, 224, 224, 3)
        img_norm = (img_array / 127.5) - 1.0
        
        predictions = model.predict(img_norm, verbose=0)
        idx = int(np.argmax(predictions))
        confidence = float(predictions[0][idx])
        predicted_name = CLASSES[idx]
        
        cv2.putText(frame, f"User: {current_user}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if confidence > 0.75 and predicted_name != "BACKGROUND":
            background_start_time = 0
            item_detect_count += 1
            if item_detect_count > 3:
                if pending_item != predicted_name:
                    pending_item = predicted_name
                    if esp32 and pending_item in CMD_MAP:
                        esp32.write(CMD_MAP[pending_item])
                    print(f"[Detected] {pending_item} (Conf: {confidence:.2%}) -> Drop into bin...")
                
                station_state["deposit_status"] = f"Detected: {pending_item} (Drop into bin)"
                cv2.putText(frame, f"Detected: {pending_item} ({confidence:.0%})", (20, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
                
        else:
            item_detect_count = 0
            if pending_item:
                if background_start_time == 0:
                    background_start_time = now
                
                # Waste removed and background detected for > 1.2s confirms successful deposit
                if now - background_start_time > 1.2:
                    earned = REWARD_POINTS.get(pending_item, 0)
                    
                    if current_user in user_database:
                        user_database[current_user]["points"] += earned
                        user_database[current_user].setdefault("history", []).append({
                            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "item": pending_item,
                            "earned": earned
                        })
                        save_user_database(user_database)
                        print(f"*** [Awarded] User: {current_user} | Item: {pending_item} | +{earned} pts | Balance: {user_database[current_user]['points']} pts ***")
                    
                    station_state["last_item"] = pending_item
                    station_state["last_reward"] = earned
                    station_state["deposit_status"] = f"Deposit Confirmed! +{earned} Points"
                    
                    #Settlement completed, send '0' to turn off all LEDs
                    if esp32:
                        esp32.write(b"0")
                    speak_async(f"Deposit confirmed! {earned} points added.")
                    
                    pending_item = None
                    background_start_time = 0
                else:
                    cv2.putText(frame, "Verifying deposit...", (20, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            else:
                station_state["deposit_status"] = f"Ready for {current_user}"
                cv2.putText(frame, "Ready - Show waste to camera", (20, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        cv2.imshow("SmartSort Station", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    if esp32:
        esp32.write(b"0")
        esp32.close()

MOBILE_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>SmartSort Mobile Station</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @keyframes pulse-gold { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.06); } }
    .score-bounce { animation: pulse-gold 0.5s ease-in-out; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen pb-10 font-sans selection:bg-emerald-500 selection:text-white">

  <!-- Mobile Top Bar -->
  <div class="sticky top-0 z-30 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-4 py-3 flex justify-between items-center shadow-md">
    <div class="flex items-center space-x-2">
      <div class="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold">♻</div>
      <div>
        <h1 class="text-sm font-bold text-emerald-400 tracking-tight">SmartSort Station</h1>
        <div class="flex items-center space-x-1">
          <p id="user-display" class="text-[10px] text-slate-400 font-mono">Loading...</p>
          <button onclick="changeAccountPrompt()" class="text-[9px] text-emerald-400 underline ml-1">[Switch ID]</button>
        </div>
      </div>
    </div>
    <button id="session-btn" onclick="toggleSession()" class="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-600 text-white shadow-lg active:scale-95 transition">
      Start Deposit
    </button>
  </div>

  <div class="max-w-md mx-auto p-4 space-y-4">

    <!-- Points Card -->
    <div class="bg-gradient-to-br from-emerald-900/50 via-slate-900 to-slate-900 p-5 rounded-2xl border border-emerald-500/30 shadow-xl relative overflow-hidden">
      <div class="text-[11px] font-medium tracking-wider uppercase text-emerald-400">My Eco-Points Balance</div>
      <div class="flex items-baseline space-x-2 mt-1">
        <div id="user-points" class="text-4xl font-extrabold text-amber-400">0</div>
        <span class="text-xs text-slate-400">pts</span>
      </div>
      <div class="mt-3 pt-3 border-t border-slate-800 text-[11px] flex justify-between text-slate-400">
        <span>Recent: <strong id="last-item" class="text-slate-200">None</strong></span>
        <span>Awarded: <strong id="points-added" class="text-amber-400">+0 pts</strong></span>
      </div>
    </div>

    <!-- Live Deposit Status -->
    <div class="bg-slate-900 p-3.5 rounded-xl border border-slate-800 flex items-center space-x-3 shadow-sm">
      <div id="status-indicator" class="w-2.5 h-2.5 rounded-full bg-red-500"></div>
      <div class="flex-1 text-xs">
        <div class="text-slate-400 text-[10px]">Bin Station Status</div>
        <div id="ai-status" class="font-semibold text-slate-100">Ready to Connect</div>
      </div>
    </div>

    <!-- 4 Waste Categories -->
    <div class="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80">
      <div class="text-[11px] font-semibold text-slate-300 mb-2">Deposit Reward Rates</div>
      <div class="grid grid-cols-2 gap-2 text-[11px]">
        <div class="p-2 bg-slate-900 rounded-lg border border-slate-800">
          <div class="text-emerald-400 font-bold">Recyclable</div>
          <div class="text-[10px] text-slate-400">+10 pts / item</div>
        </div>
        <div class="p-2 bg-slate-900 rounded-lg border border-slate-800">
          <div class="text-purple-400 font-bold">Special Waste</div>
          <div class="text-[10px] text-slate-400">+15 pts / item</div>
        </div>
        <div class="p-2 bg-slate-900 rounded-lg border border-slate-800">
          <div class="text-amber-400 font-bold">Food Waste</div>
          <div class="text-[10px] text-slate-400">+3 pts / deposit</div>
        </div>
        <div class="p-2 bg-slate-900 rounded-lg border border-slate-800">
          <div class="text-slate-400 font-bold">General Waste</div>
          <div class="text-[10px] text-slate-500">+1 pt / item</div>
        </div>
      </div>
    </div>

    <!-- My Vouchers Section -->
    <div class="bg-slate-900 p-4 rounded-xl border border-slate-800 space-y-2">
      <div class="flex justify-between items-center mb-1">
        <h2 class="text-xs font-bold text-slate-200">My Vouchers (<span id="voucher-count">0</span>)</h2>
        <span class="text-[10px] text-slate-400">Personal Digital Wallet</span>
      </div>
      <div id="voucher-list" class="space-y-2 max-h-44 overflow-y-auto pr-1 text-xs">
        <div class="text-slate-500 italic text-center py-3 text-[11px]">No vouchers yet. Earn points to redeem below!</div>
      </div>
    </div>

    <!-- Sponsored Rewards -->
    <div class="space-y-3">
      <div class="flex justify-between items-center px-1">
        <h2 class="text-xs font-bold uppercase tracking-wider text-slate-300">Sponsored Rewards</h2>
        <span class="text-[10px] text-emerald-400">Partner Vouchers</span>
      </div>

      <div class="bg-slate-900 p-3.5 rounded-xl border border-slate-800 space-y-2">
        <div class="flex justify-between items-start">
          <div>
            <h3 class="text-xs font-bold text-slate-100">Tealive RM 2 OFF</h3>
            <p class="text-[10px] text-slate-400 mt-0.5">Min. spend RM 12 on drinks.</p>
          </div>
          <span class="text-xs font-extrabold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">100 pts</span>
        </div>
        <button onclick="redeemVoucher('Tealive RM 2 Voucher', 100)" class="w-full py-2 bg-emerald-600 hover:bg-emerald-500 active:scale-95 transition text-white rounded-lg text-xs font-bold shadow-md">
          Redeem Voucher
        </button>
      </div>

      <div class="bg-slate-900 p-3.5 rounded-xl border border-slate-800 space-y-2">
        <div class="flex justify-between items-start">
          <div>
            <h3 class="text-xs font-bold text-slate-100">GrabRide / e-Scooter RM 3 OFF</h3>
            <p class="text-[10px] text-slate-400 mt-0.5">Applicable to rides & e-scooters.</p>
          </div>
          <span class="text-xs font-extrabold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">120 pts</span>
        </div>
        <button onclick="redeemVoucher('Grab RM 3 Voucher', 120)" class="w-full py-2 bg-emerald-600 hover:bg-emerald-500 active:scale-95 transition text-white rounded-lg text-xs font-bold shadow-md">
          Redeem Voucher
        </button>
      </div>

      <div class="bg-slate-900 p-3.5 rounded-xl border border-slate-800 space-y-2">
        <div class="flex justify-between items-start">
          <div>
            <h3 class="text-xs font-bold text-slate-100">Campus Bookstore RM 3 OFF</h3>
            <p class="text-[10px] text-slate-400 mt-0.5">Min. spend RM 15 on stationery.</p>
          </div>
          <span class="text-xs font-extrabold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">150 pts</span>
        </div>
        <button onclick="redeemVoucher('Bookstore RM 3 Voucher', 150)" class="w-full py-2 bg-emerald-600 hover:bg-emerald-500 active:scale-95 transition text-white rounded-lg text-xs font-bold shadow-md">
          Redeem Voucher
        </button>
      </div>

      <div class="bg-slate-900 p-3.5 rounded-xl border border-slate-800 space-y-2">
        <div class="flex justify-between items-start">
          <div>
            <h3 class="text-xs font-bold text-slate-100">Subway Eco-Combo RM 5 OFF</h3>
            <p class="text-[10px] text-slate-400 mt-0.5">Valid for green combo meal.</p>
          </div>
          <span class="text-xs font-extrabold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">250 pts</span>
        </div>
        <button onclick="redeemVoucher('Subway RM 5 Voucher', 250)" class="w-full py-2 bg-emerald-600 hover:bg-emerald-500 active:scale-95 transition text-white rounded-lg text-xs font-bold shadow-md">
          Redeem Voucher
        </button>
      </div>
    </div>

  </div>

  <script>
    function setCookie(name, value, days) {
      let expires = "";
      if (days) {
        let date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
      }
      document.cookie = name + "=" + (value || "")  + expires + "; path=/";
    }

    function getCookie(name) {
      let nameEQ = name + "=";
      let ca = document.cookie.split(';');
      for(let i=0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
      }
      return null;
    }

    function getUserId() {
      let uid = getCookie('smartsort_uid') || localStorage.getItem('smartsort_uid');
      if (!uid) {
        uid = 'User_' + Math.floor(1000 + Math.random() * 9000);
        setCookie('smartsort_uid', uid, 365);
        localStorage.setItem('smartsort_uid', uid);
      }
      return uid;
    }

    let myUserId = getUserId();
    document.getElementById('user-display').innerText = 'ID: ' + myUserId;
    let isConnected = false;

    function changeAccountPrompt() {
      let custom = prompt("Enter your account username / ID:", myUserId);
      if (custom && custom.trim() !== "") {
        myUserId = custom.trim();
        setCookie('smartsort_uid', myUserId, 365);
        localStorage.setItem('smartsort_uid', myUserId);
        document.getElementById('user-display').innerText = 'ID: ' + myUserId;
        if (isConnected) {
          claimSession();
        }
        updateDashboard();
      }
    }

    async function toggleSession() {
      const btn = document.getElementById('session-btn');
      if (!isConnected) {
        await fetch('/api/active_session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: myUserId, action: 'start' })
        });
        isConnected = true;
        btn.innerText = "Finish Session";
        btn.className = "inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-rose-600 text-white shadow-lg active:scale-95 transition";
      } else {
        await fetch('/api/active_session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: myUserId, action: 'stop' })
        });
        isConnected = false;
        btn.innerText = "Start Deposit";
        btn.className = "inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-600 text-white shadow-lg active:scale-95 transition";
      }
      updateDashboard();
    }

    let currentScore = 0;

    function renderVouchers(vouchers) {
      const listEl = document.getElementById('voucher-list');
      const countEl = document.getElementById('voucher-count');
      countEl.innerText = vouchers.length;

      if (!vouchers || vouchers.length === 0) {
        listEl.innerHTML = '<div class="text-slate-500 italic text-center py-3 text-[11px]">No vouchers yet. Earn points to redeem below!</div>';
        return;
      }

      listEl.innerHTML = vouchers.map(v => `
        <div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex justify-between items-center shadow-inner">
          <div>
            <div class="font-bold text-slate-200 text-xs">${v.title}</div>
            <div class="font-mono text-emerald-400 font-bold tracking-wider text-[11px] mt-0.5">${v.code}</div>
            <div class="text-[9px] text-slate-500">${v.time}</div>
          </div>
          <span class="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">Active</span>
        </div>
      `).join('');
    }

    async function updateDashboard() {
      try {
        const res = await fetch(`/api/user_data?user_id=${myUserId}`);
        const data = await res.json();
        const pointsEl = document.getElementById('user-points');
        const aiStatus = document.getElementById('ai-status');
        const lastItem = document.getElementById('last-item');
        const pointsAdded = document.getElementById('points-added');
        const indicator = document.getElementById('status-indicator');

        if (data.points !== currentScore) {
          pointsEl.classList.remove('score-bounce');
          void pointsEl.offsetWidth;
          pointsEl.classList.add('score-bounce');
          currentScore = data.points;
        }

        pointsEl.innerText = data.points;
        aiStatus.innerText = data.deposit_status;
        lastItem.innerText = data.last_item || "None";
        pointsAdded.innerText = data.last_reward ? `+${data.last_reward} pts` : "+0 pts";
        
        if (data.active_user === myUserId) {
          indicator.className = "w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping";
        } else {
          indicator.className = "w-2.5 h-2.5 rounded-full bg-amber-500";
        }

        renderVouchers(data.vouchers || []);
      } catch (err) {}
    }

    async function redeemVoucher(name, cost) {
      const res = await fetch('/api/redeem', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: myUserId, item: name, cost: cost })
      });
      const result = await res.json();
      alert(result.message);
      updateDashboard();
    }

    toggleSession();
    setInterval(updateDashboard, 1000);
    updateDashboard();
  </script>
</body>
</html>"""

app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string(MOBILE_HTML_PAGE)

@app.route("/api/active_session", methods=["POST"])
def active_session():
    data = request.json or {}
    uid = data.get("user_id")
    action = data.get("action", "start")
    
    if action == "start" and uid:
        station_state["active_user"] = uid
        station_state["last_heartbeat"] = time.time()
        station_state["deposit_status"] = f"Ready for {uid}"
        if uid not in user_database:
            user_database[uid] = {"points": 0, "history": [], "vouchers": []}
            save_user_database(user_database)
    elif action == "stop":
        if station_state["active_user"] == uid:
            station_state["active_user"] = None
            station_state["deposit_status"] = "Locked: Please scan QR code to start"
            if esp32:
                esp32.write(b"0")
                
    return jsonify({"success": True, "active_user": station_state["active_user"]})

@app.route("/api/user_data")
def get_user_data():
    uid = request.args.get("user_id")
    
    if uid and station_state["active_user"] == uid:
        station_state["last_heartbeat"] = time.time()
        
    if uid and uid not in user_database:
        user_database[uid] = {"points": 0, "history": [], "vouchers": []}
        save_user_database(user_database)
        
    u_info = user_database.get(uid, {"points": 0, "history": [], "vouchers": []})
    return jsonify({
        "points": u_info.get("points", 0),
        "vouchers": u_info.get("vouchers", []),
        "active_user": station_state["active_user"],
        "deposit_status": station_state["deposit_status"],
        "last_item": station_state["last_item"],
        "last_reward": station_state["last_reward"]
    })

@app.route("/api/redeem", methods=["POST"])
def redeem():
    data = request.json or {}
    uid = data.get("user_id")
    item_name = data.get("item")
    cost = data.get("cost", 0)
    
    if not uid or uid not in user_database:
        return jsonify({"success": False, "message": "User session not found!"})
        
    user_info = user_database[uid]
    if user_info.get("points", 0) >= cost:
        user_info["points"] -= cost
        
        prefix = item_name[:3].upper()
        random_num = random.randint(1000, 9999)
        voucher_code = f"{prefix}-{random_num}-ECO"
        
        new_voucher = {
            "title": item_name,
            "code": voucher_code,
            "cost": cost,
            "time": time.strftime("%Y-%m-%d %H:%M")
        }
        
        user_info.setdefault("vouchers", []).insert(0, new_voucher)
        save_user_database(user_database)
        
        return jsonify({
            "success": True, 
            "message": f"Redeemed successfully!\nCode: {voucher_code}\nAdded to your 'My Vouchers'!"
        })
    else:
        return jsonify({
            "success": False, 
            "message": f"Insufficient points! Required: {cost} pts, Current: {user_info.get('points', 0)} pts."
        })

if __name__ == "__main__":
    t = threading.Thread(target=vision_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False)
