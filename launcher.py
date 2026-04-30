import subprocess
import sys
import time

print("Starting AI Cube Runner Chaos Edition...")

# Start the server in the background
server_process = subprocess.Popen([sys.executable, "server.py"])

# Give the server a second to generate the SSL cert and QR code
time.sleep(2)

# Start the game engine
game_process = subprocess.Popen([sys.executable, "game.py"])

try:
    # Keep the launcher running until you close the game window
    game_process.wait()
except KeyboardInterrupt:
    pass
finally:
    # When the game closes, kill the server automatically so it doesn't run forever in the background!
    print("\nShutting down server...")
    server_process.terminate()
    sys.exit()