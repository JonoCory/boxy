import asyncio
import socket
import csv
import os
import json
import qrcode
from aiohttp import web
from werkzeug.serving import make_ssl_devcert

# ==========================================
# 1. SERVER SETUP
# ==========================================
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

LOCAL_IP = get_local_ip()
PORT = 8081 # Using 8081 so it doesn't conflict with your game server

# Generate SSL cert (Phones require HTTPS for camera access)
cert_path = os.path.join(os.getcwd(), 'local_ssl')
make_ssl_devcert(cert_path, host=LOCAL_IP)
import ssl
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(f'{cert_path}.crt', f'{cert_path}.key')

# ==========================================
# 2. ROUTES
# ==========================================
async def handle_html(request):
    return web.FileResponse('collector_remote.html')

async def handle_save(request):
    try:
        data = await request.json()
        label = data.get('label')
        landmarks = data.get('landmarks')
        
        file_exists = os.path.isfile('gesture_dataset.csv')
        
        # Save to CSV
        with open('gesture_dataset.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            # Write headers if it's a brand new file
            if not file_exists:
                headers = ['label'] + [f'lm_{i}_{axis}' for i in range(21) for axis in ['x', 'y', 'z']]
                writer.writerow(headers)
            
            # Write the data
            writer.writerow([label] + landmarks)
            
        print(f"✅ Saved 1 example of {label}")
        return web.json_response({"status": "ok"})
    except Exception as e:
        print(f"Error: {e}")
        return web.json_response({"status": "error"})

# ==========================================
# 3. START SERVER
# ==========================================
app = web.Application()
app.router.add_get('/', handle_html)
app.router.add_post('/save', handle_save)

public_url = f"https://{LOCAL_IP}:{PORT}"
print(f"\n📸 DATA COLLECTOR RUNNING AT: {public_url}")
qr = qrcode.QRCode(box_size=5, border=2)
qr.add_data(public_url)
qr.make(fit=True)
qr.make_image().save("collector_qr.png")
print("📱 Scan 'collector_qr.png' to start recording gestures.")

web.run_app(app, host='0.0.0.0', port=PORT, ssl_context=ssl_context)