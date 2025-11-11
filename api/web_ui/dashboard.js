// api/web_ui/dashboard.js
const WS_URL = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws";
const socket = new WebSocket(WS_URL);
const devicesDiv = document.getElementById("controls");
const statusEl = document.getElementById("status");
const wsUrlEl = document.getElementById("ws-url");
wsUrlEl.textContent = WS_URL;

let devicesState = {}; // local copy

// small debounce helper
function debounce(fn, wait){
  let t;
  return (...args)=>{
    clearTimeout(t);
    t = setTimeout(()=>fn.apply(this,args), wait);
  };
}

// send message safe (only when open)
function sendMessage(obj){
  if(socket.readyState !== WebSocket.OPEN){
    console.warn("WS not open", obj);
    return;
  }
  socket.send(JSON.stringify(obj));
}

// UI builders
function createCard(name, state){
  const card = document.createElement("div");
  card.className = "card";
  card.id = `dev-${name}`;

  const title = document.createElement("h3");
  title.textContent = name;
  card.appendChild(title);

  // content area
  const content = document.createElement("div");
  content.className = "content";

  // Build controls according to attributes
  for(const attr of Object.keys(state)){
    const row = document.createElement("div");
    row.className = "row";

    const label = document.createElement("div");
    label.className = "label";
    label.textContent = attr;
    row.appendChild(label);

    // boolean -> toggle
    const val = state[attr];
    if(typeof val === "boolean"){
      const btn = document.createElement("button");
      btn.className = "toggle" + (val ? " on" : "");
      btn.setAttribute("aria-pressed", val);
      btn.onclick = () => {
        const newVal = !btn.classList.contains("on");
        // update UI immediately
        btn.classList.toggle("on", newVal);
        sendMessage({cmd:"set", dev:name, attr:attr, val:newVal});
      };
      row.appendChild(btn);
    }
    // numeric -> slider + number (for brightness, setpoint, lux, temperature, humidity)
    else if(typeof val === "number"){
      const wrapper = document.createElement("div");
      wrapper.style.width = "100%";

      // slider for brightness and numeric ranges (we assume 0-100 for brightness, sensible ranges otherwise)
      const slider = document.createElement("input");
      slider.type = "range";
      slider.className = "slider";
      // defaults and heuristics:
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

      // send debounced slider updates
      const sendDebounced = debounce((v)=>{
        // validation: convert to number
        const num = Number(v);
        if(Number.isNaN(num)) return;
        sendMessage({cmd:"set", dev:name, attr:attr, val: typeof val === "number" && Number.isInteger(val) ? parseInt(num) : parseFloat(num)});
      }, 300);

      slider.oninput = () => {
        number.value = slider.value;
        sendDebounced(slider.value);
      };
      number.onchange = () => {
        slider.value = number.value;
        sendMessage({cmd:"set", dev:name, attr:attr, val: (number.value.includes(".") ? parseFloat(number.value) : parseInt(number.value))});
      };

      wrapper.appendChild(slider);
      wrapper.appendChild(number);
      row.appendChild(wrapper);
    }
    // string -> selection (thermostat mode)
    else if(typeof val === "string"){
      const select = document.createElement("select");
      // if thermostat mode
      if(attr.toLowerCase() === "mode"){
        ["auto","heat","cool"].forEach(opt=>{
          const o = document.createElement("option");
          o.value = opt;
          o.textContent = opt;
          o.selected = (val === opt);
          select.appendChild(o);
        });
      } else {
        const o = document.createElement("option"); o.value = val; o.textContent = val; select.appendChild(o);
      }
      select.onchange = () => {
        sendMessage({cmd:"set", dev:name, attr:attr, val: select.value});
      };
      row.appendChild(select);
    }
    content.appendChild(row);
  }

  // raw state for quick glance
  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(state, null, 2);
  content.appendChild(pre);

  card.appendChild(content);
  return card;
}

function renderDevices(all){
  devicesDiv.innerHTML = "";
  devicesState = all;
  for(const name of Object.keys(all)){
    const card = createCard(name, all[name]);
    devicesDiv.appendChild(card);
  }
}

// update one attribute visually when broadcasts come in
function updateDevice(dev, attr, val){
  // update local model
  if(!devicesState[dev]) devicesState[dev] = {};
  devicesState[dev][attr] = val;

  const card = document.getElementById(`dev-${dev}`);
  if(!card) return;

  // update pre text
  const pre = card.querySelector("pre");
  if(pre){
    pre.textContent = JSON.stringify(devicesState[dev], null, 2);
  }
  // update controls if present
  const inputs = card.querySelectorAll(".row");
  inputs.forEach(row=>{
    const label = row.querySelector(".label");
    if(label && label.textContent === attr){
      // buttons
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

// WS handlers
socket.onopen = () => {
  statusEl.className = "status connected";
  statusEl.textContent = "Connected";
  sendMessage({cmd:"list"});
};
socket.onclose = () => {
  statusEl.className = "status disconnected";
  statusEl.textContent = "Disconnected";
};
socket.onerror = (e) => {
  console.error("WS error", e);
  statusEl.className = "status disconnected";
  statusEl.textContent = "Error";
};
socket.onmessage = (evt) => {
  let msg;
  try { msg = JSON.parse(evt.data); } catch(e){ console.warn("bad json", evt.data); return; }
  // message types: status ok + devices list, status ok single ..., event update
  if(msg.status === "ok" && msg.devices){
    renderDevices(msg.devices);
  } else if(msg.status === "ok" && msg.dev && msg.state){
    // get response for single device read
    // update devicesState and UI
    devicesState[msg.dev] = msg.state;
    updateDevice(msg.dev, null, null); // refresh
    const card = document.getElementById(`dev-${msg.dev}`);
    if(card) card.querySelector("pre").textContent = JSON.stringify(msg.state,null,2);
  } else if(msg.event === "update"){
    updateDevice(msg.dev, msg.attr, msg.val);
  } else {
    // ignore other messages or log
    // console.log("msg", msg);
  }
};
function confirmLogout() {
  if (confirm("Are you sure you want to log out?")) {
    window.location.href = "/logout";
  }
}

