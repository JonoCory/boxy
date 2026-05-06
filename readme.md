
I added a launcher so we just need to run the launcher and it will sart the game and server



run
```
pip install -r requirements.txt
```

then 
```
python launcher.py
```

![team](images/4playerLobby.png)



The game gets progessively harder harder 
faster, more bombs, more boxes to dodge

Here is a play through with the change in stage set to 15 seconds

![Gameplay Demo](images/boxyHighScore.gif)








THere are currently three different states.

## State 1: Noraml gravity (Always starts with this one)

![normal gravity Demo](images/boxyNormalGravityAndAntiGravity.gif)


## State 2: Zero gravity 
you move up and down with jump and duck

![zero gravity Demo](images/boxyZEROGRAVITY.gif)



## State 3: Gravity switch
Swap which way gravity pull s you wiht jump and duck

![gravity switch Demo](images/boxyGravitySwitch.gif)


## Menu

![menu Demo](images/boxyMenu.gif)


* It says "LAG" if that players hand is not being tracked


## Connecting warning that i cant get rid of
You always get this warning And have to click advance>proceed

![warning](images/warning.jpg)






## choose your name and colour
the device will say when it can detect a hand
The background will match the colour you choose.

![newplayer](images/newplayer.jpg)




## 4 Players


![4 players](images/fourPlayer.gif)

### Fome here below is is a quick AI generated markdown to explain the core stuff, itll propabaly outdated soon when i add more things

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

You will drop right into the game lobby

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

## connectiong my laptop

The "Public" Network Trap (Windows)
When you connect a laptop to Wi-Fi, Windows asks if it's a Public or Private network.
If it is set to Public, Windows completely blocks other devices on the network from seeing your laptop.

The Fix: On your laptop, go to Settings > Network & Internet > Wi-Fi. 
Click on your current Wi-Fi network's properties. Change the Network Profile type from "Public" to "Private".



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

**Empty Square Emojis in Game:**  (solved i think)
Pygame relies on local Windows fonts to render emojis.  
If your system is missing the **Segoe UI Emoji** font, emojis will appear as empty squares.  
The text instructions will still be readable.

---

**Cannot connect to the server / QR code doesn't load:**
- Ensure your PC network is set to **Private** (not Public)
- Ensure Windows Firewall is not blocking Python or port **8080**
- Ensure your phone is on the same Wi-Fi (not cellular data)

---
# 🧠 BOXY: Machine Learning Architecture & Technical Stack

BOXY utilizes an **Edge Computing** architecture to achieve near-zero latency for motion controls. Rather than sending a heavy video feed from the phone to the computer, the system splits the computational load: the phone handles the computer vision, and the PC handles the neural network inference and physics engine.

Here is a complete breakdown of the machine learning pipeline and the libraries that power it.

---

## 1. The Eyes: `MediaPipe` (JavaScript / HTML)
Instead of processing raw video on the server, the computer vision runs directly on the player's mobile browser using Google's **MediaPipe Hands**.

* **What it does:** MediaPipe is a highly optimized, pre-trained ML model that detects human hands in real-time. When it identifies a hand, it maps a digital "skeleton" consisting of **21 specific 3D landmarks** (knuckles, fingertips, wrist, etc.).
* **The Data Flow:** For every frame, MediaPipe calculates the exact X, Y, and Z coordinates of those 21 points. It packages these 63 raw numbers into a lightweight JSON payload and transmits them over the local Wi-Fi.
* **The Edge Advantage:** Because the phone only sends tiny arrays of text data (rather than streaming 30FPS video), network latency is drastically minimized, and the PC's CPU is freed up to run the game engine.

## 2. The Brain: `PyTorch` (Python)
Once the Python server receives the 63 coordinates, it feeds them into a custom AI trained using **PyTorch**, Meta's premier machine learning framework.

* **The Model Architecture:** The system uses a **Feedforward Neural Network** (specifically a Multilayer Perceptron). 
* **How it calculates gestures:**
  * **Input Layer:** Accepts the 63 numeric coordinates from the phone.
  * **Hidden Layers:** Passes the data through two dense layers (128 neurons, then 64 neurons). These layers use a `ReLU` activation function to detect geometric patterns (e.g., "If the Y-coordinate of the index finger is significantly higher than the wrist, the user is pointing up").
  * **Dropout (`nn.Dropout`):** During training, 20% of the neurons are randomly deactivated. This prevents the AI from simply memorizing specific hands and forces it to generalize the underlying *concept* of the gestures.
  * **Output Layer:** Outputs probability scores for the target classes (`JUMP`, `DUCK`, `PAUSE`, `NEUTRAL`).

## 3. The Translator: `Scikit-Learn` (Python)
Neural networks only understand raw numbers. The PyTorch model does not inherently know the word "JUMP"; it only predicts a class ID like `1` or `2`. 

* **What it does:** The project uses the `LabelEncoder` tool from **Scikit-Learn**. During the data collection phase, this tool looked at the training folder names and mapped them to integers.
* **Inference Phase:** When the server boots up, it loads a pickled version of this dictionary (`label_encoder.pkl`). When PyTorch predicts class `1`, the Label Encoder instantly translates it back to the human-readable string `"JUMP"`.

## 4. The Data Handlers: `NumPy` & `Pandas` (Python)
While these run behind the scenes, they are the workhorses of the training pipeline.
* **Pandas** was used to structure and organize thousands of frames of recorded hand coordinates into clean CSV datasets.
* **NumPy** converts those datasets into the high-speed mathematical matrices (Tensors) that PyTorch requires to train the neural network.

---

## 🛠️ The Core Infrastructure Stack

Beyond the Machine Learning, BOXY relies on a robust local server and engine stack:

* **`pygame-ce` (Pygame Community Edition):** The engine rendering the game. The Community Edition is used over standard Pygame for its significantly faster rendering pipelines, allowing for smooth 60FPS platforming and complex 2D collision resolution.
* **`aiohttp`, `werkzeug`, & `cryptography`:** These libraries generate a secure, temporary local HTTPS server. Mobile browsers (like iOS Safari and Android Chrome) strictly block access to the device's camera on standard HTTP connections. This stack generates on-the-fly SSL certificates to bypass this restriction locally.
* **`socket` (UDP):** The project uses User Datagram Protocol (UDP) for inter-process communication. Once the web server calculates the AI gesture, it blasts a UDP packet locally to the Pygame engine. UDP is connectionless and does not wait for acknowledgments, making it the perfect protocol for real-time game inputs where dropping an old frame is better than delaying a new one.

---

## 🔄 The Complete Data Pipeline Summary
1. **Phone Camera** captures a frame.
2. **MediaPipe (JS)** extracts 63 spatial coordinates.
3. **Wi-Fi** transmits the coordinates to the Python web server (throttled to 20Hz to prevent buffer bloat).
4. **PyTorch (Python)** processes the coordinates and predicts an integer ID.
5. **Scikit-Learn (Python)** translates the ID into a string action (e.g., `"DUCK"`).
6. **UDP Socket** instantly blasts the command to the Pygame client.
7. **Pygame-CE** executes the physics and updates the screen.



## Planned impovments
There are many improvments i want to make to the actual game play. this is just the base version.


