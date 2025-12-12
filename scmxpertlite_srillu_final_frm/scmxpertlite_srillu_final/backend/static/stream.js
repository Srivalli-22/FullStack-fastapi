// stream.js - Fetch device data from the API

function showToast(msg) {
  const t = document.getElementById("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2000);
}

function getToken() {
  return localStorage.getItem('access_token') || localStorage.getItem('token');
}

async function loadData() {
  const select = document.getElementById("deviceId");
  const devId = select.value;
  if (!devId) {
    showToast("Please select a Device Id.");
    return;
  }

  const token = getToken();
  if (!token) {
    showToast("Please login first");
    window.location.href = "/login";
    return;
  }

  try {
    showToast("Loading device data...");
    
    const res = await fetch('http://localhost:8000/api/device/recent?limit=20', {
      method: 'GET',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    });

    if (!res.ok) {
      const err = await res.json();
      console.error('Error:', err);
      showToast('Failed to fetch: ' + (err.detail || 'Unknown error'));
      return;
    }

    const data = await res.json();
    const body = document.getElementById("dataBody");
    body.innerHTML = "";

    // Filter by selected device if needed
    const filteredData = data.filter(r => r.device_id === devId || !devId);

    if (filteredData.length === 0) {
      showToast("No data found for this device.");
      return;
    }

    filteredData.forEach(r => {
      const tr = document.createElement("tr");
      const battery = r.battery.toFixed(1);
      const temp = r.temperature;
      const rf = r.route_from || '-';
      const rt = r.route_to || '-';
      const ts = new Date(r.timestamp).toLocaleString();

      tr.innerHTML =
        "<td>" + r.device_id + "</td>" +
        "<td>" + battery + "</td>" +
        "<td>" + temp + "</td>" +
        "<td>" + rf + "</td>" +
        "<td>" + rt + "</td>" +
        "<td>" + ts + "</td>";

      body.appendChild(tr);
    });

    showToast("Data loaded successfully!");
  } catch (err) {
    console.error('Error loading data:', err);
    showToast('Network error: ' + err.message);
  }
}

// Auto-load data on page load
window.addEventListener('load', () => {
  const token = getToken();
  if (!token) {
    window.location.href = '/login';
    return;
  }
  
  // Try to load initial data
  const select = document.getElementById("deviceId");
  if (select && select.options.length > 1) {
    // Set first device and load
    select.selectedIndex = 1;
    loadData();
  }
});
