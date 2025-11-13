// api/web_ui/dashboard.js
// Updated — adds reconnect, message queue, robust payload handling, safer DOM usage

const WS_PATH = "/ws";
const WS_URL = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + WS_PATH;

const devicesDiv = document.getElementById("controls");
const statusEl = document.getElementById("status");
const wsUrlEl = document.getElementById("ws-url");
if (wsUrlEl) wsUrlEl.textContent = WS_URL;

let devicesState = {}; // local copy
let msgQueue = [];
let reconnectDelay = 1000; // start 1s
let maxReconnect = 30000; // 30s
let ws = null;
let manuallyClosed = false; // when user closes intentionally (not used currently)

// small debounce helper
function debounce(fn, wait){
  let t;
  return (...args)=>{
    clearTimeout(t);
    t = setTimeout(()=>fn.apply(this,args), wait);
  };
}

// --------------------
// WebSocket connect + reconnect logic
// --------------------
function createWebSocket() {
  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    reconnectDelay = 1000; // reset
    if (statusEl) {
      statusEl.className = "status connected";
      statusEl.textContent = "Connected";
    }
    // flush queue
    while (msgQueue.length && ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msgQueue.shift()));
    }
    // ask for device list
    sendMessage({cmd: "list"});
  });

  ws.addEventListener("close", (ev) => {
    if (statusEl) {
      statusEl.className = "status disconnected";
      statusEl.textContent = "Disconnected";
    }
    if (!manuallyClosed) scheduleReconnect();
  });

  ws.addEventListener("error", (err) => {
    console.error("WS error", err);
    if (statusEl) {
      statusEl.className = "status disconnected";
      statusEl.textContent = "Error";
    }
    // let close handler schedule reconnect
  });

  ws.addEventListener("message", (evt) => {
    handleMessage(evt.data);
  });
}

function scheduleReconnect(){
  if (reconnectDelay > maxReconnect) reconnectDelay = maxReconnect;
  console.info(`WS reconnecting in ${reconnectDelay/1000}s...`);
  setTimeout(() => {
    console.info("WS reconnect attempt...");
    createWebSocket();
    reconnectDelay = Math.min(maxReconnect, reconnectDelay * 1.6);
  }, reconnectDelay);
}

// Initialize connection immediately
createWebSocket();

// send message safe (queues if not open)
function sendMessage(obj){
  const str = JSON.stringify(obj);
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.warn("WS not open, queueing message", obj);
    msgQueue.push(obj);
    return;
  }
  ws.send(str);
}

// --------------------
// UI builders
// --------------------
function createCard(name, state){
  const card = document.createElement("div");
  card.className = "card";
  card.id = `dev-${escapeId(name)}`;

  const title = document.createElement("h3");
  title.textContent = name;
  card.appendChild(title);

  const content = document.createElement("div");
  content.className = "content";

  // ensure predictable ordering
  const attrs = Object.keys(state || {}).sort();

  for(const attr of attrs){
    const row = document.createElement("div");
    row.className = "row";

    const label = document.createElement("div");
    label.className = "label";
    label.textContent = attr;
    row.appendChild(label);

    const val = state[attr];

    // boolean -> toggle (button)
    if(typeof val === "boolean"){
      const btn = document.createElement("button");
      btn.className = "toggle" + (val ? " on" : "");
      btn.setAttribute("aria-pressed", String(val));
      btn.onclick = () => {
        const newVal = !btn.classList.contains("on");
        btn.classList.toggle("on", newVal);
        btn.setAttribute("aria-pressed", String(newVal));
        sendMessage({cmd:"set", dev:name, attr:attr, val:newVal});
      };
      row.appendChild(btn);
    }
    // numeric -> slider + number
    else if(typeof val === "number"){
      const wrapper = document.createElement("div");
      wrapper.style.width = "100%";
      wrapper.style.display = "flex";
      wrapper.style.alignItems = "center";

      const slider = document.createElement("input");
      slider.type = "range";
      slider.className = "slider";
      slider.style.flex = "1";

      // heuristics for sensible ranges
      if(attr.toLowerCase().includes("brightness")) { slider.min=0; slider.max=100; slider.step=1; }
      else if(attr.toLowerCase().includes("temperature")) { slider.min=0; slider.max=50; slider.step=0.1; }
      else if(attr.toLowerCase().includes("humidity")) { slider.min=0; slider.max=100; slider.step=0.1; }
      else if(attr.toLowerCase().includes("lux")) { slider.min=0; slider.max=2000; slider.step=1; }
      else if(attr.toLowerCase().includes("setpoint")) { slider.min=5; slider.max=35; slider.step=1; }
      else { slider.min = 0; slider.max = 100; slider.step = 1; }

      slider.value = val;

      const number = document.createElement("input");
      number.type = "number";
      number.value = val;
      number.className = "small";
      number.style.marginLeft = "8px";
      number.style.width = "80px";

      const sendDebounced = debounce((v)=>{
        const num = Number(v);
        if(!Number.isNaN(num)){
          sendMessage({cmd:"set", dev:name, attr:attr, val:num});
        }
      }, 300);

      slider.oninput = () => {
        number.value = slider.value;
        sendDebounced(slider.value);
      };
      number.onchange = () => {
        slider.value = number.value;
        const parsed = number.value.includes(".") ? parseFloat(number.value) : parseInt(number.value);
        sendMessage({cmd:"set", dev:name, attr:attr, val: parsed});
      };

      wrapper.appendChild(slider);
      wrapper.appendChild(number);
      row.appendChild(wrapper);
    }
    // string -> select
    else if(typeof val === "string"){
      const select = document.createElement("select");

      if(attr.toLowerCase() === "mode"){
        ["auto","heat","cool"].forEach(opt=>{
          const o = document.createElement("option");
          o.value = opt;
          o.textContent = opt;
          if (val === opt) o.selected = true;
          select.appendChild(o);
        });
      } else {
        const o = document.createElement("option");
        o.value = val;
        o.textContent = val;
        o.selected = true;
        select.appendChild(o);
      }

      select.onchange = () => {
        sendMessage({cmd:"set", dev:name, attr:attr, val: select.value});
      };
      row.appendChild(select);
    } else {
      // fallback: show raw
      const span = document.createElement("div");
      span.textContent = String(val);
      row.appendChild(span);
    }

    content.appendChild(row);
  }

  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(state || {}, null, 2);
  content.appendChild(pre);

  card.appendChild(content);
  return card;
}

function renderDevices(devicesPayload){
  // Accept both: array-of-objects [{id, name, value}] or object map {name: {attr:val}}
  let normalized = {};

  if (Array.isArray(devicesPayload)) {
    // try to normalize array items
    devicesPayload.forEach(item=>{
      if (!item) return;
      const id = item.id || item.device_id || item.name || item.label;
      const baseName = item.name || id;
      // if value is primitive -> treat as single attribute "value"
      if (typeof item.value !== "undefined" && (typeof item.value !== "object" || item.value === null)) {
        normalized[baseName] = { value: item.value };
      } else if (typeof item.state === "object" && item.state !== null) {
        normalized[baseName] = item.state;
      } else {
        // fallback: include whole item as json
        normalized[baseName] = item;
      }
    });
  } else if (typeof devicesPayload === "object" && devicesPayload !== null) {
    normalized = devicesPayload;
  }

  devicesDiv.innerHTML = "";
  devicesState = normalized;
  Object.keys(normalized).forEach(name => devicesDiv.appendChild(createCard(name, normalized[name])));
}

// --------------------
// update one attribute visually
// --------------------
function updateDevice(dev, attr, val){
  if(!devicesState[dev]) devicesState[dev] = {};
  if (typeof attr !== "undefined" && attr !== null) devicesState[dev][attr] = val;

  const card = document.getElementById(`dev-${escapeId(dev)}`);
  if(!card) {
    // maybe a new device — re-render full
    renderDevices(devicesState);
    return;
  }

  const pre = card.querySelector("pre");
  if(pre) pre.textContent = JSON.stringify(devicesState[dev], null, 2);

  const rows = card.querySelectorAll(".row");
  rows.forEach(row=>{
    const label = row.querySelector(".label");
    if(label && label.textContent === attr){
      const toggle = row.querySelector(".toggle");
      if(toggle) toggle.classList.toggle("on", !!val);
      const slider = row.querySelector("input[type=range]");
      if(slider) slider.value = val;
      const number = row.querySelector("input[type=number]");
      if(number) number.value = val;
      const select = row.querySelector("select");
      if(select) select.value = val;
    }
  });
}

// --------------------
// Incoming WS message handler
// --------------------
function handleMessage(raw){
  let msg;
  try { msg = JSON.parse(raw); } catch (e) {
    console.warn("Invalid WS JSON:", raw);
    return;
  }

  // devices list (full)
  if (msg.status === "ok" && msg.devices){
    renderDevices(msg.devices);
    return;
  }

  // single device fetch response: {status:"ok", dev:..., state: {...}}
  if (msg.status === "ok" && msg.dev && msg.state){
    devicesState[msg.dev] = msg.state;
    // re-render specific card or full if missing
    const card = document.getElementById(`dev-${escapeId(msg.dev)}`);
    if (card) {
      updateDevice(msg.dev, null, null);
      const pre = card.querySelector("pre");
      if (pre) pre.textContent = JSON.stringify(msg.state, null, 2);
    } else {
      renderDevices(devicesState);
    }
    return;
  }

  // broadcast update events: { event: "update", dev, attr, val }
  if (msg.event === "update" && msg.dev){
    updateDevice(msg.dev, msg.attr, msg.val);
    return;
  }

  // unknown but log for debugging
  // console.debug("Unhandled WS message:", msg);
}

// --------------------
// Helpers
// --------------------
function escapeId(s) {
  // keep IDs safe for element IDs
  return String(s).replace(/\s+/g, "_").replace(/[^\w-]/g, "_");
}

// --------------------
// Logout helper
// --------------------
function confirmLogout() {
  if (confirm("Are you sure you want to log out?")) {
    window.location.href = "/logout";
  }
}

// ========================================================
//      ADD DEVICE: Matter + HomeKit QR MODAL LOGIC
// ========================================================
const addDeviceBtn = document.getElementById("add-device-btn");
const modal = document.getElementById("qr-modal");
const closeModalBtn = document.getElementById("close-qr-btn");
const refreshQRBtn = document.getElementById("refresh-qr-btn");

const matterQR = document.getElementById("matter-qr");
const homekitQR = document.getElementById("homekit-qr");
const matterPIN = document.getElementById("matter-pin");
const homekitPIN = document.getElementById("homekit-pin");

// safe no-op if UI elements missing
async function loadQR() {
  try {
    const mResp = await fetch("/qr/matter");
    if (!mResp.ok) throw new Error("Matter QR fetch failed: " + mResp.status);
    const m = await mResp.json();
    if (matterQR) matterQR.src = "data:image/png;base64," + (m.qr || "");
    if (matterPIN) matterPIN.innerHTML = "PIN: <b>" + (m.pin || "") + "</b>";

    const hResp = await fetch("/qr/homekit");
    if (!hResp.ok) throw new Error("HomeKit QR fetch failed: " + hResp.status);
    const h = await hResp.json();
    if (homekitQR) homekitQR.src = "data:image/png;base64," + (h.qr || "");
    if (homekitPIN) homekitPIN.innerHTML = "PIN: <b>" + (h.pin || "") + "</b>";
  }
  catch (err) {
    console.error("QR Load Failed:", err);
    // show a user-friendly message if modal present
    if (modal) {
      const errEl = modal.querySelector(".qr-error");
      if (errEl) errEl.textContent = "Failed to load QR codes. Please try Refresh.";
    }
  }
}

if (addDeviceBtn && modal) {
  addDeviceBtn.addEventListener("click", () => {
    modal.classList.remove("hidden");
    loadQR();
  });
}
if (closeModalBtn && modal) {
  closeModalBtn.addEventListener("click", () => modal.classList.add("hidden"));
}
if (refreshQRBtn) {
  refreshQRBtn.addEventListener("click", loadQR);
}

// If modal exists but add button missing, expose a small floating helper
(function autoAddQuickOpen(){
  if (!addDeviceBtn && document.body) {
    const btn = document.createElement("button");
    btn.id = "add-device-btn";
    btn.textContent = "Add Device";
    btn.style.position = "fixed";
    btn.style.right = "18px";
    btn.style.bottom = "18px";
    btn.style.zIndex = "999";
    btn.onclick = () => {
      if (modal) {
        modal.classList.remove("hidden");
        loadQR();
      } else {
        // open QR endpoints in new tab as fallback
        window.open("/qr/matter", "_blank");
        window.open("/qr/homekit", "_blank");
      }
    };
    document.body.appendChild(btn);
  }
})();
