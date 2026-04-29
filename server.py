import asyncio
import socket
import json
import torch
import torch.nn as nn
import pickle
import qrcode
import os
import warnings
from aiohttp import web
from werkzeug.serving import make_ssl_devcert

warnings.filterwarnings("ignore")

# ==========================================
# 1. LOAD THE AI MODEL
# ==========================================
class GestureBrain(nn.Module):
    def __init__(self, num_classes):
        super(GestureBrain, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(63, 128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, num_classes)
        )
    def forward(self, x): return self.net(x)

# Load encoder and model
try:
    with open('label_encoder.pkl', 'rb') as f:
        encoder = pickle.load(f)
    model = GestureBrain(len(encoder.classes_))
    model.load_state_dict(torch.load('gesture_model.pth'))
    model.eval()
    print("🧠 PyTorch AI Loaded Successfully.")
except Exception as e:
    print(f"⚠️ Error loading model: {e}. Make sure you train it first!")
    exit()

# ==========================================
# 2. UDP SETUP (Blazing fast comms to Pygame)
# ==========================================
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ==========================================
# 3. WEB SERVER SETUP
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
WEB_PORT = 8080

# Generate SSL for mobile webcam access
cert_path = os.path.join(os.getcwd(), 'local_ssl')
make_ssl_devcert(cert_path, host=LOCAL_IP)
import ssl
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(f'{cert_path}.crt', f'{cert_path}.key')

players_state = {}

async def handle_html(request):
    return web.FileResponse('remote.html')

async def handle_update(request):
    try:
        data = await request.json()
        pid = data.get('id')
        
        # Enforce 4-player limit
        if pid not in players_state and len(players_state) >= 4:
            return web.json_response({"status": "full"})

        # Run AI Inference
        landmarks = data.get('landmarks')
        gesture = "NEUTRAL"
        if landmarks:
            with torch.no_grad():
                tensor_data = torch.FloatTensor([landmarks])
                prediction = model(tensor_data)
                predicted_idx = torch.max(prediction.data, 1)[1].item()
                gesture = encoder.inverse_transform([predicted_idx])[0]

        # Update State
        players_state[pid] = {
            "name": data.get('name', "Player"),
            "color": data.get('color', "#ffffff"),
            "gesture": gesture,
            "wrist_x": data.get('wrist_x', 0.5)
        }

        # Blast state to Pygame via UDP
        udp_sock.sendto(json.dumps(players_state).encode(), (UDP_IP, UDP_PORT))

        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)})

# Start Web Server
app = web.Application()
app.router.add_get('/', handle_html)
app.router.add_post('/update', handle_update)

public_url = f"https://{LOCAL_IP}:{WEB_PORT}"
print(f"\n🚀 SERVER RUNNING AT: {public_url}")
qr = qrcode.QRCode(box_size=5, border=2)
qr.add_data(public_url)
qr.make(fit=True)
qr.make_image().save("lobby_qr.png")
print("📱 Scan 'lobby_qr.png' to join.")

web.run_app(app, host='0.0.0.0', port=WEB_PORT, ssl_context=ssl_context)