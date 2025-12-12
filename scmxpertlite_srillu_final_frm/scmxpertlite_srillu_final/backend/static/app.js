// Get token from localStorage (check both keys for compatibility)
function getToken() {
  return localStorage.getItem('access_token') || localStorage.getItem('token');
}

// Check if user is authenticated
function checkAuth() {
  const token = getToken();
  if (!token) {
    window.location.href = '/login';
    return false;
  }
  return true;
}

// Fetch device recent events
async function fetchRecent(){
  const token = getToken();
  if (!token) {
    alert('Please login first');
    window.location.href = '/login';
    return;
  }

  try {
    const res = await fetch('http://localhost:8000/api/device/recent?limit=20', {
      method: 'GET',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    });

    if(!res.ok) {
      const err = await res.json();
      console.error('Error:', err);
      alert('Failed to fetch: ' + (err.detail || 'Unknown error'));
      return;
    }

    const data = await res.json();
    const tbody = document.getElementById('dataBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    data.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${r.device_id}</td><td>${r.battery.toFixed(1)}</td><td>${r.temperature}</td><td>${r.route_from||'-'}</td><td>${r.route_to||'-'}</td><td>${new Date(r.timestamp).toLocaleString()}</td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Fetch error:', err);
    alert('Network error: ' + err.message);
  }
}

// Fetch user shipments
async function fetchShipments(){
  const token = getToken();
  if (!token) {
    alert('Please login first');
    window.location.href = '/login';
    return;
  }

  try {
    const res = await fetch('http://localhost:8000/api/shipments/', {
      method: 'GET',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    });

    if(!res.ok) {
      const err = await res.json();
      console.error('Error:', err);
      alert('Failed to fetch shipments: ' + (err.detail || 'Unknown error'));
      return;
    }

    const data = await res.json();
    const tbody = document.getElementById('shipmentsBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    data.forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${s.shipment_number}</td>
        <td>${s.container_number||'-'}</td>
        <td>${s.route||'-'}</td>
        <td>${s.goods_type||'-'}</td>
        <td>${s.device_id||'-'}</td>
        <td>${new Date(s.created_at).toLocaleString()}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Fetch error:', err);
    alert('Network error: ' + err.message);
  }
}

// Create new shipment
async function createShipment(formData) {
  const token = getToken();
  if (!token) {
    alert('Please login first');
    window.location.href = '/login';
    return;
  }

  try {
    const res = await fetch('http://localhost:8000/api/shipments/', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData)
    });

    if(!res.ok) {
      const err = await res.json();
      console.error('Error:', err);
      alert('Failed to create shipment: ' + (err.detail || 'Unknown error'));
      return false;
    }

    const data = await res.json();
    alert('Shipment created successfully!');
    return data;
  } catch (err) {
    console.error('Create error:', err);
    alert('Network error: ' + err.message);
    return false;
  }
}

// Publish device data
async function publishDeviceData(payload) {
  const token = getToken();
  if (!token) {
    alert('Please login first');
    return false;
  }

  try {
    const res = await fetch('http://localhost:8000/api/device/publish', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if(!res.ok) {
      const err = await res.json();
      console.error('Error:', err);
      alert('Failed: ' + (err.detail || 'Unknown error'));
      return false;
    }

    const data = await res.json();
    alert('Data published successfully!');
    return true;
  } catch (err) {
    console.error('Publish error:', err);
    alert('Network error: ' + err.message);
    return false;
  }
}

// Logout function
function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('token');
  localStorage.removeItem('displayName');
  window.location.href = '/login';
}
