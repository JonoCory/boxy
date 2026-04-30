
I added a launcher so we just need to run the launcher and it will sart the game and server



run
```
pip install -r requirements.txt
```

or

```
pip install pygame torch pandas numpy scikit-learn qrcode aiohttp werkzeug mediapipe opencv-python
```

also this one is important

```
python -m pip install cryptography
```


### This is a quick AI generated markdown to explain the core stuff, itll propabaly outdated soon when i add more things

## 📌 Notes

**Note on Pygame:**  
We use `pygame-ce` (Community Edition) for better modern Windows support. If you have issues installing standard pygame, the requirements file handles the CE version.

**Note on Cryptography:**  
The `cryptography` package is required to generate local SSL certificates so phones allow camera access.

---

## 🕹️ How to Play
### 
```bash
python launcher.py
```

this will start both



### OLD way 1. Start the Server (The "Brain")
Open a terminal and run:
```bash
python server.py
```

⚠️ Windows Defender Firewall will likely pop up. You **MUST** check *"Allow on Private Networks"* or the phones won't be able to connect.

---

### OLD 2. Start the Game Engine (The "Brawn")
Open a second, separate terminal and run:
```bash
python game.py
```


---

### 3. Join the Lobby via Phone
- When the game launches, a QR Code will appear on the lobby screen (and in the server terminal).
- Scan the QR code with your phone.

**Bypass the Security Warning:**  
Because we are hosting locally, your phone will warn you about an unsafe certificate. Click:  
**Advanced → Proceed to site**  
(This is completely safe and required for the browser to allow camera access).

- Enter your name  
- Pick a color  
- Hit **START**

You will drop right into the game lobby!

---

## ✋ Gesture Controls

Hold your hand in front of your phone's camera. The game tracks your hand's shape and its left/right position.

| Gesture | Pose | Action |
|--------|------|--------|
| NEUTRAL | 🖐️ Open Hand | Normal running stance |
| JUMP | ☝️ Index Finger Up | Jump / Fly Up / Fall to the Ceiling |
| DUCK | ✊ Closed Fist | Duck / Fly Down / Fall to the Floor |
| PAUSE / READY | 🤙 Surfer / 'Y' | Start the game from the lobby or pause mid-game |

The pause and start have a time so you have to hold that position for a bit

**Movement:**  
after no mistakes you slowly recover and move back to the center

---

## 🌪️ Game Mechanics & Stages

**PvP Pushback:**  
If your cube collides with another player, you will push each other. Sabotage your friends by pushing them into incoming boxes.

**Ghost Respawn:**  
If you fall off the screen, you lose a life. You will respawn as a ghost dropping from the ceiling after 3 seconds.

### Stages

- **State 1 (Gravity Survival):**  
  Standard gravity. Jump over low blocks, duck under high blocks.

- **State 2 (Zero-G Flight):**  
  Gravity is disabled. Navigate massive obstacles floating in mid-space.

- **State 3 (Gravity Switch):**  
  *Gravity Guy rules.*  
  Jumping pulls you to the roof. Ducking pulls you to the floor. Stay alive.

- **Endless Mode:**  
  Toggle this in the Settings Menu.  
  1 Life, endless looping stages. Survive for the highest distance score.

---

## ⚠️ Known Issues & Troubleshooting ( solved)

**Phones randomly disconnecting or getting stuck ducking:**  
Mobile browsers (especially iOS Safari) aggressively pause JavaScript when the screen dims to save battery.  
We implemented a WakeLock, but if your phone screen dims, tap it to wake it up.  
If a gesture gets permanently stuck, quickly refresh the web page on your phone and rejoin.



---

**SSL / HTTPS Warning on Phones:**  ( dont know how to stop this)
Mobile browsers refuse to open the camera on standard `http://` sites.  
We generate a temporary ad-hoc `https://` certificate. Your phone flags this as *"Not Secure"* because it isn’t issued by a global authority.  
You must click: **Advanced → Proceed** to play.

---

**Empty Square Emojis in Game:**  
Pygame relies on local Windows fonts to render emojis.  
If your system is missing the **Segoe UI Emoji** font, emojis will appear as empty squares.  
The text instructions will still be readable.

---

**Cannot connect to the server / QR code doesn't load:**
- Ensure your PC network is set to **Private** (not Public)
- Ensure Windows Firewall is not blocking Python or port **8080**
- Ensure your phone is on the same Wi-Fi (not cellular data)

---

## planned impovments
There are many improvments i want to make to the actual game play. this is just the base version.


