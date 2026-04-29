import pygame
import socket
import json
import threading
import random
import sys
import time

# ==========================================
# 1. UDP & PYGAME SETUP
# ==========================================
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind((UDP_IP, UDP_PORT))
shared_player_state = {}

def listen_for_udp():
    global shared_player_state
    while True:
        try:
            data, _ = udp_sock.recvfrom(2048)
            shared_player_state = json.loads(data.decode())
        except Exception: pass
threading.Thread(target=listen_for_udp, daemon=True).start()

pygame.init()
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AI Cube Runner - Chaos Edition V5")
clock = pygame.time.Clock()

font = pygame.font.SysFont("impact", 36)
small_font = pygame.font.SysFont("impact", 24)
title_font = pygame.font.SysFont("impact", 72)

BLACK, WHITE, RED, BLUE, GREEN, GREY, YELLOW = (15, 15, 20), (255, 255, 255), (255, 50, 50), (50, 150, 255), (50, 255, 50), (100, 100, 100), (255, 215, 0)

try:
    qr_img = pygame.image.load("lobby_qr.png")
    qr_img = pygame.transform.scale(qr_img, (200, 200))
except FileNotFoundError:
    qr_img = None

# Global Settings 
SETTINGS = {
    "MODE": ["PARTY", "ENDLESS"], "MODE_IDX": 0,
    "LIVES": [3, 1, 5, 10], "LIVES_IDX": 0,
    "STAGE_TIME": [30, 15, 45, 60], "STAGE_TIME_IDX": 0,
    "RESPAWN": [3, 1, 5], "RESPAWN_IDX": 0
}

stage_names = {1: "NORMAL GRAVITY", 2: "ZERO-G FLIGHT", 3: "GRAVITY SWITCH"}

# ==========================================
# 2. ENTITIES
# ==========================================
class Player:
    def __init__(self, pid, name, hex_color):
        self.pid = pid
        self.name = name
        self.color = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        self.home_x = WIDTH // 2 
        self.x, self.y = self.home_x, HEIGHT // 2
        self.w, self.h = 40, 40
        self.y_vel = 0
        self.lives = 1 if SETTINGS["MODE"][SETTINGS["MODE_IDX"]] == "ENDLESS" else SETTINGS["LIVES"][SETTINGS["LIVES_IDX"]]
        self.is_dead = False
        self.respawn_time = 0
        self.is_jumping = False
        self.last_gesture = "NEUTRAL"
        self.gravity_dir = 1 

    def update(self, server_data, stage_type, game_state):
        if self.is_dead: return

        gesture = server_data.get('gesture', 'NEUTRAL')
        if server_data.get('force_neutral'): gesture = "NEUTRAL"

        # Slow Pushback Recovery (Harder to recover!)
        if self.x < self.home_x: self.x += 0.5 

        # --- PHYSICS ---
        if stage_type == 1 or game_state == "LOBBY": # Normal Gravity
            if gesture == "JUMP" and self.last_gesture != "JUMP" and not self.is_jumping:
                self.y_vel = -20
                self.is_jumping = True
            
            if gesture == "DUCK":
                self.h = 20
                if self.is_jumping: self.y_vel += 4 
            else:
                self.h = 40

            self.y += self.y_vel
            self.y_vel += 1.2 
            
            if self.y >= HEIGHT - self.h - 20:
                self.y, self.y_vel, self.is_jumping = HEIGHT - self.h - 20, 0, False

        elif stage_type == 2: # Zero-G
            self.h = 40
            if gesture == "JUMP": self.y -= 12
            elif gesture == "DUCK": self.y += 12
            self.y = max(20, min(self.y, HEIGHT - self.h - 20))

        elif stage_type == 3: # Gravity Switch
            self.h = 40
            if gesture == "JUMP": self.gravity_dir = -1 
            elif gesture == "DUCK": self.gravity_dir = 1  
            
            self.y_vel += 2.5 * self.gravity_dir
            self.y += self.y_vel
            
            if self.y >= HEIGHT - self.h - 20:
                self.y, self.y_vel = HEIGHT - self.h - 20, 0
            elif self.y <= 20:
                self.y, self.y_vel = 20, 0

        self.last_gesture = gesture

    def draw(self, surface):
        if self.is_dead:
            if self.lives <= 0: return # Permanently dead
            
            time_left = self.respawn_time - time.time()
            if time_left > 0:
                pygame.draw.rect(surface, self.color, (WIDTH//2, 50, 40, 40), 2, border_radius=4)
                surface.blit(font.render(str(int(time_left)+1), True, self.color), (WIDTH//2 + 10, 50))
            else:
                self.respawn()
            return

        pygame.draw.rect(surface, self.color, (self.x, self.y, self.w, self.h), border_radius=8)
        surface.blit(small_font.render(self.name[:6], True, WHITE), (self.x - 5, self.y - 25))

    def die(self):
        self.lives -= 1
        self.is_dead = True
        if self.lives > 0:
            self.respawn_time = time.time() + SETTINGS["RESPAWN"][SETTINGS["RESPAWN_IDX"]]

    def respawn(self):
        self.is_dead = False
        self.x, self.y, self.y_vel = WIDTH // 2, 50, 0
        self.gravity_dir, self.is_jumping = 1, True

# ==========================================
# 3. GAME ENGINE
# ==========================================
players = {}
obstacles = []
game_state = "LOBBY" 
global_stage = 1
current_stage_type = 1 
state_timer = 0
frame_count = 0
distance_traveled = 0
game_speed = 7
is_paused = False

def spawn_obstacle(stage_type):
    w = random.randint(40, 80)
    if stage_type == 1:
        ctype = random.choice([1, 2, 3])
        if ctype == 1: obstacles.append(pygame.Rect(WIDTH, HEIGHT - 60, w, 40)) # Floor
        elif ctype == 2: obstacles.append(pygame.Rect(WIDTH, HEIGHT - 100, w, 30)) # Exact height to force ducking
        else: obstacles.append(pygame.Rect(WIDTH, HEIGHT - 120, w, 100)) # Block
            
    elif stage_type == 2: # Flying
        w, h = random.randint(70, 120), random.randint(70, 120) # Bigger boxes!
        obstacles.append(pygame.Rect(WIDTH, random.randint(40, HEIGHT - 100), w, h)) # Middle space
        if random.random() > 0.6: obstacles.append(pygame.Rect(WIDTH, 20, w*1.5, 40)) # Roof sweeper
        if random.random() > 0.6: obstacles.append(pygame.Rect(WIDTH, HEIGHT - 60, w*1.5, 40)) # Floor sweeper
            
    elif stage_type == 3:
        pos = random.choice(['roof', 'floor', 'middle'])
        if pos == 'roof': obstacles.append(pygame.Rect(WIDTH, 20, w, 80))
        elif pos == 'floor': obstacles.append(pygame.Rect(WIDTH, HEIGHT - 100, w, 80))
        else: obstacles.append(pygame.Rect(WIDTH, HEIGHT // 2 - 40, w, 80))

# UI Buttons
btn_play = pygame.Rect(WIDTH//2 - 200, HEIGHT - 120, 180, 60)
btn_settings = pygame.Rect(WIDTH//2 + 20, HEIGHT - 120, 180, 60)
btn_pause = pygame.Rect(WIDTH - 120, 20, 100, 40)
btn_back = pygame.Rect(50, 50, 150, 50)

# ==========================================
# 4. MAIN LOOP
# ==========================================
while True:
    mouse_click = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_click = True

    screen.fill(BLACK)
    frame_count += 1
    
    for pid, data in shared_player_state.items():
        if pid not in players: players[pid] = Player(pid, data['name'], data['color'])

    # ------------------- STATE: PAUSED -------------------
    if is_paused:
        pygame.draw.rect(screen, RED, btn_pause, border_radius=8)
        screen.blit(small_font.render("RESUME", True, WHITE), (btn_pause.x + 15, btn_pause.y + 5))
        screen.blit(title_font.render("PAUSED", True, WHITE), (WIDTH//2 - 100, HEIGHT//2))
        if mouse_click and btn_pause.collidepoint(pygame.mouse.get_pos()): is_paused = False
        pygame.display.flip()
        clock.tick(60)
        continue

    # ------------------- STATE: SETTINGS -------------------
    if game_state == "SETTINGS":
        screen.blit(title_font.render("GAME SETTINGS", True, BLUE), (WIDTH//2 - 200, 50))
        pygame.draw.rect(screen, GREY, btn_back, border_radius=8)
        screen.blit(font.render("BACK", True, WHITE), (btn_back.x + 35, btn_back.y + 5))
        
        y_offset = 180
        for key, val in SETTINGS.items():
            if "IDX" in key: continue
            idx_key = f"{key}_IDX"
            current_val = val[SETTINGS[idx_key]]
            
            screen.blit(font.render(f"{key}: {current_val}", True, WHITE), (WIDTH//2 - 200, y_offset))
            btn_toggle = pygame.Rect(WIDTH//2 + 100, y_offset, 150, 40)
            pygame.draw.rect(screen, BLUE, btn_toggle, border_radius=8)
            screen.blit(small_font.render("CHANGE", True, WHITE), (btn_toggle.x + 35, btn_toggle.y + 5))
            
            if mouse_click and btn_toggle.collidepoint(pygame.mouse.get_pos()):
                SETTINGS[idx_key] = (SETTINGS[idx_key] + 1) % len(val)
                # Reset lives based on new mode/settings
                for p in players.values(): 
                    p.lives = 1 if SETTINGS["MODE"][SETTINGS["MODE_IDX"]] == "ENDLESS" else SETTINGS["LIVES"][SETTINGS["LIVES_IDX"]]

            y_offset += 80

        if mouse_click and btn_back.collidepoint(pygame.mouse.get_pos()): game_state = "LOBBY"

    # ------------------- STATE: LOBBY -------------------
    elif game_state == "LOBBY":
        pygame.draw.rect(screen, (40, 40, 50), (0, HEIGHT - 20, WIDTH, 20))
        screen.blit(title_font.render("PRACTICE LOBBY", True, WHITE), (WIDTH//2 - 220, 50))
        if qr_img: screen.blit(qr_img, (50, 150))
        
        pygame.draw.rect(screen, GREEN, btn_play, border_radius=8)
        screen.blit(font.render("START GAME", True, BLACK), (btn_play.x + 10, btn_play.y + 10))
        pygame.draw.rect(screen, BLUE, btn_settings, border_radius=8)
        screen.blit(font.render("SETTINGS", True, WHITE), (btn_settings.x + 25, btn_settings.y + 10))

        if frame_count % 120 == 0: spawn_obstacle(1)
        for obs in obstacles[:]:
            obs.x -= 3 
            pygame.draw.rect(screen, GREY, obs, border_radius=4)
            if obs.x < -100: obstacles.remove(obs)

        for p in players.values():
            p.update(shared_player_state.get(p.pid, {}), 1, "LOBBY")
            p_rect = pygame.Rect(p.x, p.y, p.w, p.h)
            for obs in obstacles:
                if p_rect.colliderect(obs): p.x = obs.x - p.w 
            if p.x < 0: p.x = 0 
            p.draw(screen)
            if shared_player_state.get(p.pid, {}).get('gesture') == "PAUSE": mouse_click, event.pos = True, btn_play.center

        if mouse_click:
            if btn_play.collidepoint(pygame.mouse.get_pos()):
                game_state, state_timer, global_stage, distance_traveled = "COUNTDOWN", time.time() + 3, 1, 0
                obstacles.clear()
                for p in players.values(): p.home_x, p.x, p.is_dead = WIDTH//2, WIDTH//2, False
            elif btn_settings.collidepoint(pygame.mouse.get_pos()):
                game_state = "SETTINGS"
                obstacles.clear()

    # ------------------- STATE: COUNTDOWN / TRANSITION -------------------
    elif game_state in ["COUNTDOWN", "TRANSITION"]:
        pygame.draw.rect(screen, (40, 40, 50), (0, HEIGHT - 20, WIDTH, 20))
        if current_stage_type == 3: pygame.draw.rect(screen, (40, 40, 50), (0, 0, WIDTH, 20))
            
        header = f"STAGE {global_stage}: {stage_names[current_stage_type]}" if game_state == "TRANSITION" else "GET READY!"
        text = title_font.render(header, True, BLUE)
        screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - 50))

        for p in players.values(): 
            p.update(shared_player_state.get(p.pid, {}), current_stage_type, game_state)
            p.draw(screen)

        time_left = state_timer - time.time()
        if time_left <= 0:
            if game_state == "COUNTDOWN":
                game_state, current_stage_type, state_timer = "TRANSITION", 1, time.time() + 3
            else:
                game_state, state_timer = "PLAYING", time.time() + SETTINGS["STAGE_TIME"][SETTINGS["STAGE_TIME_IDX"]]

    # ------------------- STATE: PLAYING -------------------
    elif game_state == "PLAYING":
        distance_traveled += game_speed // 2
        pygame.draw.rect(screen, (40, 40, 50), (0, HEIGHT - 20, WIDTH, 20))
        if current_stage_type == 3: pygame.draw.rect(screen, (40, 40, 50), (0, 0, WIDTH, 20))

        pygame.draw.rect(screen, GREY, btn_pause, border_radius=8)
        screen.blit(small_font.render("PAUSE", True, WHITE), (btn_pause.x + 20, btn_pause.y + 5))
        if mouse_click and btn_pause.collidepoint(pygame.mouse.get_pos()): is_paused = True

        screen.blit(font.render(f"DIST: {distance_traveled}m", True, YELLOW), (WIDTH//2 - 60, 20))
        
        is_endless = SETTINGS["MODE"][SETTINGS["MODE_IDX"]] == "ENDLESS"
        time_left = int(state_timer - time.time())
        if not is_endless:
            screen.blit(font.render(f"STAGE {global_stage} - {time_left}s", True, WHITE), (WIDTH//2 - 80, 60))
        
        if time_left <= 0 and not is_endless:
            game_state, global_stage = "TRANSITION", global_stage + 1
            current_stage_type = random.choice([1, 2, 3])
            state_timer = time.time() + 3
        elif time_left <= 0 and is_endless: # Rotate stages endlessly without pause
            current_stage_type = random.choice([1, 2, 3])
            state_timer = time.time() + SETTINGS["STAGE_TIME"][SETTINGS["STAGE_TIME_IDX"]]

        if frame_count % 50 == 0: spawn_obstacle(current_stage_type)
        for obs in obstacles[:]:
            obs.x -= game_speed
            pygame.draw.rect(screen, RED, obs, border_radius=4)
            if obs.x < -100: obstacles.remove(obs)

        hud_x, all_dead = 20, True
        
        # Player Updates & Sabotage
        for pid, p in players.items():
            if p.lives > 0: all_dead = False
            
            hud = font.render(f"{p.name[:6]}: {'❤️'*p.lives}" if p.lives > 0 else f"{p.name[:6]}: OUT", True, p.color if p.lives > 0 else GREY)
            screen.blit(hud, (hud_x, 20))
            hud_x += 250

            p.update(shared_player_state.get(p.pid, {}), current_stage_type, game_state)
            
            if not p.is_dead:
                p_rect = pygame.Rect(p.x, p.y, p.w, p.h)
                
                # --- SABOTAGE PVP COLLISIONS ---
                for opid, other_p in players.items():
                    if pid != opid and not other_p.is_dead:
                        if p_rect.colliderect(pygame.Rect(other_p.x, other_p.y, other_p.w, other_p.h)):
                            if p.x < other_p.x: p.x -= 3; other_p.x += 3
                            else: p.x += 3; other_p.x -= 3

                # Obstacle Collisions
                for obs in obstacles:
                    if p_rect.colliderect(obs):
                        p.x = obs.x - p.w 
                        break
                
                if p.x < -20: p.die()
            p.draw(screen)

        if all_dead and len(players) > 0:
            screen.blit(title_font.render("GAME OVER", True, RED))
            screen.blit(font.render(f"FINAL DISTANCE: {distance_traveled}m", True, YELLOW), (WIDTH//2 - 150, HEIGHT//2 + 80))
            pygame.display.flip()
            pygame.time.wait(4000)
            
            # Full reset based on settings
            for p in players.values(): 
                p.lives = 1 if SETTINGS["MODE"][SETTINGS["MODE_IDX"]] == "ENDLESS" else SETTINGS["LIVES"][SETTINGS["LIVES_IDX"]]
                p.is_dead = False
            game_state, global_stage = "LOBBY", 1
            obstacles.clear()

    pygame.display.flip()
    clock.tick(60)