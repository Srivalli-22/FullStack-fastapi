import json
import sys
import requests

OUT_FILE = 'static/api_test_results.json'
results = {}

try:
    # Login
    r = requests.post('http://localhost:8000/auth/login', data={'username':'demo@demo.com','password':'Demo@123'})
    results['login'] = {'status_code': r.status_code, 'text': None}
    try:
        results['login']['json'] = r.json()
    except Exception:
        results['login']['text'] = r.text

    if r.ok:
        token = r.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}

        # Shipments
        try:
            s = requests.get('http://localhost:8000/api/shipments/', headers=headers)
            results['shipments'] = {'status_code': s.status_code}
            try:
                results['shipments']['json'] = s.json()
            except Exception:
                results['shipments']['text'] = s.text
        except Exception as e:
            results['shipments'] = {'error': str(e)}

        # Device recent
        try:
            d = requests.get('http://localhost:8000/api/device/recent?limit=2', headers=headers)
            results['device_recent'] = {'status_code': d.status_code}
            try:
                results['device_recent']['json'] = d.json()
            except Exception:
                results['device_recent']['text'] = d.text
        except Exception as e:
            results['device_recent'] = {'error': str(e)}
    else:
        results['error'] = 'login_failed'

except Exception as e:
    results['exception'] = str(e)

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print('Wrote', OUT_FILE)
sys.exit(0)
