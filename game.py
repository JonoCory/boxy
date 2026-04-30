import pygame
import socket
import json
import threading
import random
import sys
import time
import os
from datetime import date

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
pygame.display.set_caption("BOXY - V19")
clock = pygame.time.Clock()

font = pygame.font.SysFont("impact", 36)
small_font = pygame.font.SysFont("impact", 24)
title_font = pygame.font.SysFont("impact", 72)
massive_font = pygame.font.SysFont("impact", 120)
try:
    emoji_font = pygame.font.SysFont("segoe ui emoji", 36)
except:
    emoji_font = font

# Color Palette
BLACK, WHITE, RED, BLUE = (15, 15, 20), (255, 255, 255), (255, 50, 50), (50, 150, 255)
GREEN, GREY, ORANGE, YELLOW = (50, 255, 50), (100, 100, 100), (255, 140, 0), (255, 215, 0)
LIFE_COLOR = (0, 255, 150)

def load_qr():
    try: return pygame.transform.scale(pygame.image.load("lobby_qr.png"), (200, 200))
    except Exception: return None
qr_img = load_qr()

# --- HIGH SCORE SYSTEM ---
def load_scores():
    try:
        with open("highscores.json", "r") as f:
            return json.load(f)
    except: return []

def save_score(name, score):
    scores = load_scores()
    scores.append({"name": name, "score": score, "date": str(date.today())})
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:10] 
    with open("highscores.json", "w") as f: json.dump(scores, f)
    return scores

def get_top_score():
    s = load_scores()
    if s: return s[0]
    return {"name": "---", "score": 0}

all_time_top = get_top_score()
session_top = {"name": "---", "score": 0}

# GLOBALS
SETTINGS = {
    "MODE": ["PARTY", "ENDLESS"], "MODE_IDX": 0,
    "DIFFICULTY": ["EASY", "NORMAL", "HARD"], "DIFFICULTY_IDX": 1,
    "LIVES": [3, 1, 5, 10], "LIVES_IDX": 0,
    "STAGE_TIME": [30, 15, 45, 60], "STAGE_TIME_IDX": 0
}

stage_names = {1: "NORMAL GRAVITY", 2: "ZERO-G FLIGHT", 3: "GRAVITY SWITCH"}
champion_pid = None 
kicked_pids = set() # Ban list to prevent zombie players!
confirm_clear_timer = 0 # Timer for "Are You Sure?" score clearing

def get_diff_mult():
    mapping = {"EASY": 0.8, "NORMAL": 1.0, "HARD": 1.4}
    return mapping[SETTINGS["DIFFICULTY"][SETTINGS["DIFFICULTY_IDX"]]]

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
        self.pause_hold_time = 0  
        self.on_ground = False 
        self.hit_ceiling = False 
        self.invincible_timer = 0 
        self.last_update_hash = None
        self.time_since_last_packet = 0
        self.final_distance = 0 

    def update_intent(self, server_data, stage_type, game_state):
        if self.is_dead: return

        gesture = server_data.get('gesture', 'NEUTRAL')
        
        current_hash = hash(str(server_data.get('wrist_x')) + str(gesture))
        if current_hash == self.last_update_hash and current_hash != hash("NoneNEUTRAL"):
            self.time_since_last_packet += 1
        else:
            self.time_since_last_packet = 0
        self.last_update_hash = current_hash

        if gesture == "PAUSE": self.pause_hold_time += 1
        else: self.pause_hold_time = 0

        if stage_type == 1 or game_state == "LOBBY": 
            if gesture == "JUMP" and self.last_gesture != "JUMP" and self.on_ground and not self.hit_ceiling:
                self.y_vel = -17 
                self.on_ground = False
            if gesture == "DUCK":
                self.h = 20
                if not self.on_ground: self.y_vel += 3 
            else: self.h = 40
            self.y_vel += 0.8 

        elif stage_type == 2: 
            self.h = 40
            if gesture == "JUMP": self.y_vel = -8 
            elif gesture == "DUCK": self.y_vel = 8
            else: self.y_vel = 0 

        elif stage_type == 3: 
            self.h = 40
            if gesture == "JUMP": self.gravity_dir = -1 
            elif gesture == "DUCK": self.gravity_dir = 1  
            self.y_vel += 1.2 * self.gravity_dir
            if self.y_vel > 15: self.y_vel = 15
            if self.y_vel < -15: self.y_vel = -15

        self.last_gesture = gesture

    def draw(self, surface):
        if self.is_dead:
            if self.lives <= 0: return 
            time_left = self.respawn_time - time.time()
            if time_left > 0:
                pygame.draw.rect(surface, self.color, (WIDTH//2 - 20, 50, 40, 40), 2, border_radius=4)
                surface.blit(font.render(str(int(time_left)+1), True, self.color), (WIDTH//2 - 10, 50))
            else: self.respawn()
            return

        if self.invincible_timer > 0: self.invincible_timer -= 1

        if self.invincible_timer == 0 or self.invincible_timer % 10 < 5:
            pygame.draw.rect(surface, self.color, (self.x, self.y, self.w, self.h), border_radius=8)
            surface.blit(small_font.render(self.name[:6], True, WHITE), (self.x - 5, self.y - 25))
            
            global champion_pid
            if self.pid == champion_pid:
                surface.blit(emoji_font.render("👑", True, WHITE), (self.x + 2, self.y - 50))

        if self.pause_hold_time > 0:
            bar_w = self.w
            fill_w = min(bar_w, int(bar_w * (self.pause_hold_time / 90)))
            bar_y = self.y - 40 if self.pid != champion_pid else self.y - 65
            pygame.draw.rect(surface, GREY, (self.x, bar_y, bar_w, 8), border_radius=4)
            pygame.draw.rect(surface, GREEN, (self.x, bar_y, fill_w, 8), border_radius=4)
            
        if self.time_since_last_packet > 60: 
            surface.blit(small_font.render("⚠️ LAG", True, ORANGE), (self.x - 10, self.y - 50))

    def die(self, current_distance):
        self.lives -= 1
        self.is_dead = True
        self.pause_hold_time = 0 
        if self.lives <= 0:
            self.final_distance = current_distance 
        else:
            self.respawn_time = time.time() + 3 

    def respawn(self):
        self.is_dead = False
        self.x, self.y, self.y_vel = WIDTH // 2, 50, 0
        self.gravity_dir, self.on_ground = 1, False
        self.invincible_timer = 120 

# ==========================================
# 3. GAME ENGINE
# ==========================================
players = {}
obstacles = [] 
explosions = [] 
game_state = "LOBBY" 
global_stage, current_stage_type, state_timer, frame_count, distance_traveled = 1, 1, 0, 0, 0
is_paused = False

def spawn_obstacle(stage_type, current_diff):
    dist_mod = distance_traveled / 1000 
    w = random.randint(40, 80 + int(dist_mod * 5))
    h_mod = int(dist_mod * 8)
    
    if random.random() < 0.01:
        obstacles.append({"rect": pygame.Rect(WIDTH, random.randint(100, HEIGHT - 150), 30, 30), "type": "life"})
        return

    bomb_chance = min(0.08 + (dist_mod * 0.015) * current_diff, 0.45)
    if random.random() < bomb_chance:
        y_max = HEIGHT - 180 if stage_type == 1 else 40 
        bomb_y = random.randint(y_max, HEIGHT - 80)
        
        if stage_type == 1 and random.random() < 0.25: bomb_y = HEIGHT - 50
            
        obstacles.append({"rect": pygame.Rect(WIDTH, bomb_y, 30, 30), "type": "bomb"})
        if dist_mod > 10 and random.random() > 0.5:
             obstacles.append({"rect": pygame.Rect(WIDTH + 40, bomb_y + random.choice([-40, 40]), 30, 30), "type": "bomb"})
        return

    if stage_type == 1: 
        ctype = random.choices([1, 2, 3, 4, 5], weights=[3, 3, 2, 2, 2])[0]
        if ctype == 1: obstacles.append({"rect": pygame.Rect(WIDTH, HEIGHT - 60, w, 40), "type": "box"})
        elif ctype == 2: obstacles.append({"rect": pygame.Rect(WIDTH, HEIGHT - 90, w, 50), "type": "box"}) 
        elif ctype == 3: 
            var_h = 120 + random.randint(0, min(60, h_mod))
            obstacles.append({"rect": pygame.Rect(WIDTH, HEIGHT - 20 - var_h, w, var_h), "type": "box"}) 
        elif ctype == 4: 
            plat_w = random.randint(200, 450)
            plat_y = HEIGHT - random.randint(110, 180 + h_mod)
            obstacles.append({"rect": pygame.Rect(WIDTH, plat_y, plat_w, 20), "type": "box"})
            if random.random() > 0.5: obstacles.append({"rect": pygame.Rect(WIDTH + (plat_w//2), HEIGHT - 60, 40, 40), "type": "box"}) 
            else: obstacles.append({"rect": pygame.Rect(WIDTH + (plat_w//2), plat_y - 40, 40, 40), "type": "box"}) 
        elif ctype == 5: 
            step_w = 80 + int(dist_mod * 2)
            gap1 = random.randint(140, 220)
            gap2 = gap1 + random.randint(140, 220)
            y1 = HEIGHT - random.randint(60, 100)
            y2 = y1 - random.randint(40, 80)
            y3 = y2 - random.randint(40, 80)
            obstacles.append({"rect": pygame.Rect(WIDTH, y1, step_w, 20), "type": "box"}) 
            obstacles.append({"rect": pygame.Rect(WIDTH + gap1, y2, step_w, 20), "type": "box"}) 
            obstacles.append({"rect": pygame.Rect(WIDTH + gap2, y3, step_w, 20), "type": "box"}) 
            
    elif stage_type == 2: 
        sweeper_h = 60 + min(150, h_mod)
        if random.random() > 0.4: obstacles.append({"rect": pygame.Rect(WIDTH, 20, w*4, sweeper_h), "type": "box"})
        if random.random() > 0.4: obstacles.append({"rect": pygame.Rect(WIDTH + (w*2), HEIGHT - 20 - sweeper_h, w*4, sweeper_h), "type": "box"})
        scatter_w, scatter_h = random.randint(60, 110 + h_mod), random.randint(60, 110 + h_mod) 
        obstacles.append({"rect": pygame.Rect(WIDTH + 100, random.randint(100, HEIGHT - scatter_h - 100), scatter_w, scatter_h), "type": "box"})
            
    elif stage_type == 3: 
        x_offset = WIDTH
        if random.random() > 0.3: obstacles.append({"rect": pygame.Rect(x_offset, 20, w, random.randint(80, 120 + h_mod)), "type": "box"})
        x_offset += random.randint(100, 200) 
        if random.random() > 0.3: obstacles.append({"rect": pygame.Rect(x_offset, HEIGHT - random.randint(100, 140 + h_mod), w, random.randint(80, 120 + h_mod)), "type": "box"})
        x_offset += random.randint(100, 200)
        if random.random() > 0.5: obstacles.append({"rect": pygame.Rect(x_offset, HEIGHT // 2 - 40, w, 80 + min(60, h_mod)), "type": "box"})

def draw_button(surface, rect, color, text_str, text_color):
    pygame.draw.rect(surface, color, rect, border_radius=8)
    text = font.render(text_str, True, text_color)
    surface.blit(text, (rect.centerx - text.get_width()//2, rect.centery - text.get_height()//2))

# Perfectly centered, elevated horizontal button layout
button_y = HEIGHT - 180
btn_play = pygame.Rect(240, button_y, 220, 60)
btn_settings = pygame.Rect(490, button_y, 220, 60)
btn_leaderboard = pygame.Rect(740, button_y, 220, 60)

btn_pause = pygame.Rect(WIDTH - 120, 20, 100, 40)
p_btn_resume = pygame.Rect(WIDTH//2 - 160, HEIGHT//2 - 90, 320, 50)
p_btn_restart = pygame.Rect(WIDTH//2 - 160, HEIGHT//2 - 20, 320, 50)
p_btn_lobby = pygame.Rect(WIDTH//2 - 160, HEIGHT//2 + 50, 320, 50)

# ==========================================
# 4. MAIN LOOP
# ==========================================
while True:
    mouse_click = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN: mouse_click = True

    screen.fill(BLACK)
    frame_count += 1
    
    current_diff = get_diff_mult()
    dynamic_game_speed = (5 + (distance_traveled / 3000)) * current_diff
    
    # Sync players securely avoiding zombie packets
    for pid, data in list(shared_player_state.items()):
        if pid not in kicked_pids and pid not in players: 
            players[pid] = Player(pid, data['name'], data['color'])

    if confirm_clear_timer > 0:
        confirm_clear_timer -= 1

    # ------------------- STATE: PAUSED -------------------
    if is_paused:
        screen.blit(massive_font.render("PAUSED", True, WHITE), (WIDTH//2 - 180, HEIGHT//2 - 250))
        draw_button(screen, p_btn_resume, GREEN, "RESUME", BLACK)
        draw_button(screen, p_btn_restart, ORANGE, "RESTART GAME", BLACK)
        draw_button(screen, p_btn_lobby, BLUE, "QUIT TO LOBBY", WHITE)
        
        y_kick = HEIGHT//2 + 120
        pid_to_remove = None
        for p in players.values():
            screen.blit(small_font.render(p.name, True, p.color), (WIDTH//2 - 150, y_kick))
            btn_kick = pygame.Rect(WIDTH//2 + 50, y_kick - 5, 100, 35)
            draw_button(screen, btn_kick, RED, "KICK", WHITE)
            if mouse_click and btn_kick.collidepoint(pygame.mouse.get_pos()): pid_to_remove = p.pid
            y_kick += 45
            
        if pid_to_remove:
            kicked_pids.add(pid_to_remove)
            del players[pid_to_remove]
            if pid_to_remove in shared_player_state: del shared_player_state[pid_to_remove]

        if mouse_click:
            if p_btn_resume.collidepoint(pygame.mouse.get_pos()): 
                is_paused = False
                for p in players.values(): p.pause_hold_time = 0
            elif p_btn_restart.collidepoint(pygame.mouse.get_pos()):
                game_state, global_stage, distance_traveled, state_timer = "COUNTDOWN", 1, 0, time.time() + 1.5
                current_stage_type = 1
                obstacles.clear(); explosions.clear(); is_paused = False
                
                start_xs = [WIDTH//2, WIDTH//2 - 90, WIDTH//2 - 180, WIDTH//2 - 270]
                alive_players = list(players.values())
                random.shuffle(alive_players)
                for i, p in enumerate(alive_players):
                    p.lives = 1 if SETTINGS["MODE"][SETTINGS["MODE_IDX"]] == "ENDLESS" else SETTINGS["LIVES"][SETTINGS["LIVES_IDX"]]
                    p.is_dead, p.pause_hold_time = False, 0
                    p.home_x = start_xs[i % len(start_xs)]
                    p.x, p.y, p.y_vel = p.home_x, 50, 0
                    p.respawn()
                    
            elif p_btn_lobby.collidepoint(pygame.mouse.get_pos()):
                game_state, is_paused, distance_traveled = "LOBBY", False, 0
                obstacles.clear(); explosions.clear()
                
        pygame.display.flip(); clock.tick(60); continue

    # ------------------- STATE: SETTINGS -------------------
    elif game_state == "SETTINGS":
        screen.blit(title_font.render("GAME SETTINGS", True, BLUE), (WIDTH//2 - 200, 50))
        btn_back = pygame.Rect(50, 50, 150, 50)
        draw_button(screen, btn_back, GREY, "BACK", WHITE)
        
        y_offset = 180
        for key, val in SETTINGS.items():
            if "IDX" in key: continue
            idx_key = f"{key}_IDX"
            screen.blit(font.render(f"{key}: {val[SETTINGS[idx_key]]}", True, WHITE), (WIDTH//2 - 250, y_offset))
            btn_toggle = pygame.Rect(WIDTH//2 + 50, y_offset, 150, 40)
            draw_button(screen, btn_toggle, BLUE, "CHANGE", WHITE)
            if mouse_click and btn_toggle.collidepoint(pygame.mouse.get_pos()):
                SETTINGS[idx_key] = (SETTINGS[idx_key] + 1) % len(val)
                for p in players.values(): 
                    p.lives = 1 if SETTINGS["MODE"][SETTINGS["MODE_IDX"]] == "ENDLESS" else SETTINGS["LIVES"][SETTINGS["LIVES_IDX"]]
            y_offset += 70

        y_kick = 180
        pid_to_remove = None
        for p in players.values():
            screen.blit(small_font.render(p.name, True, p.color), (WIDTH - 300, y_kick))
            btn_kick = pygame.Rect(WIDTH - 150, y_kick - 5, 100, 35)
            draw_button(screen, btn_kick, RED, "KICK", WHITE)
            if mouse_click and btn_kick.collidepoint(pygame.mouse.get_pos()): pid_to_remove = p.pid
            y_kick += 45
            
        if pid_to_remove:
            kicked_pids.add(pid_to_remove)
            del players[pid_to_remove]
            if pid_to_remove in shared_player_state: del shared_player_state[pid_to_remove]

        # Two-stage Clear Score Mechanism
        if confirm_clear_timer > 0: btn_text, btn_color = "ARE YOU SURE?", ORANGE
        else: btn_text, btn_color = "CLEAR HIGH SCORES", RED
        
        btn_clear_scores = pygame.Rect(WIDTH//2 - 150, HEIGHT - 100, 300, 50)
        draw_button(screen, btn_clear_scores, btn_color, btn_text, WHITE)

        if mouse_click:
            if btn_back.collidepoint(pygame.mouse.get_pos()): 
                game_state = "LOBBY"
                confirm_clear_timer = 0
            elif btn_clear_scores.collidepoint(pygame.mouse.get_pos()): 
                if confirm_clear_timer > 0:
                    with open("highscores.json", "w") as f: json.dump([], f)
                    all_time_top = {"name": "---", "score": 0}
                    confirm_clear_timer = 0
                else:
                    confirm_clear_timer = 180 # Require second click within 3 seconds

    # ------------------- STATE: LEADERBOARD -------------------
    elif game_state == "LEADERBOARD":
        screen.blit(title_font.render("ALL-TIME CHAMPIONS", True, ORANGE), (WIDTH//2 - 320, 50))
        btn_back = pygame.Rect(50, 50, 150, 50)
        draw_button(screen, btn_back, GREY, "BACK", WHITE)

        scores = load_scores()
        y_offset = 160
        
        if not scores:
            screen.blit(font.render("NO SCORES RECORDED YET.", True, GREY), (WIDTH//2 - 180, y_offset))
        else:
            for i, s in enumerate(scores):
                if i == 0: color, rank_str = YELLOW, "1ST"
                elif i == 1: color, rank_str = (200, 200, 200), "2ND"  
                elif i == 2: color, rank_str = (205, 127, 50), "3RD"   
                else: color, rank_str = WHITE, f"{i+1}TH"

                row_text = f"{rank_str.ljust(5)}  {s['name'].ljust(12)}  {s['score']}m"
                screen.blit(font.render(row_text, True, color), (WIDTH//2 - 250, y_offset))
                screen.blit(small_font.render(f"({s.get('date', '')})", True, GREY), (WIDTH//2 + 100, y_offset + 5))
                y_offset += 45

        if mouse_click and btn_back.collidepoint(pygame.mouse.get_pos()):
            game_state = "LOBBY"

    # ------------------- STATE: LOBBY -------------------
    elif game_state == "LOBBY":
        pygame.draw.rect(screen, (40, 40, 50), (0, HEIGHT - 20, WIDTH, 20))
        screen.blit(massive_font.render("BOXY", True, BLUE), (WIDTH//2 - 130, 20))
        
        screen.blit(small_font.render("👑 ALL TIME HIGH SCORE 👑", True, YELLOW), (20, 20))
        screen.blit(font.render(f"{all_time_top['name']}: {all_time_top['score']}m", True, WHITE), (20, 50))
        screen.blit(small_font.render("🔥 SESSION TOP 🔥", True, ORANGE), (20, 110))
        screen.blit(font.render(f"{session_top['name']}: {session_top['score']}m", True, WHITE), (20, 140))

        # Reorganized Layout: Left side for QR, Right Side for Instructions
        if not qr_img and frame_count % 60 == 0: qr_img = load_qr()
        if qr_img:
            screen.blit(qr_img, (150, 180))
            screen.blit(small_font.render("SCAN TO JOIN", True, WHITE), (190, 390))
        else: screen.blit(small_font.render("WAITING FOR SERVER...", True, GREY), (150, 200))
        
        inst_x, inst_y = WIDTH - 450, 180
        screen.blit(emoji_font.render("☝️ JUMP/UP", True, WHITE), (inst_x, inst_y))
        screen.blit(emoji_font.render("✊ DUCK/DOWN", True, WHITE), (inst_x, inst_y + 50))
        screen.blit(emoji_font.render("🖐️ NEUTRAL", True, WHITE), (inst_x, inst_y + 100))
        screen.blit(emoji_font.render("🤙 HOLD TO START/PAUSE", True, GREEN), (inst_x, inst_y + 150))
        
        bomb_warn_rect = pygame.Rect(WIDTH - 500, 390, 350, 60)
        pygame.draw.rect(screen, (30, 30, 30), bomb_warn_rect, border_radius=10)
        sample_bomb = pygame.Rect(WIDTH - 480, 405, 30, 30)
        pygame.draw.rect(screen, ORANGE, sample_bomb, border_radius=15)
        pygame.draw.rect(screen, YELLOW, sample_bomb, 3, border_radius=15)
        screen.blit(font.render("AVOID THE BOMBS!", True, ORANGE), (WIDTH - 435, 400))
        
        draw_button(screen, btn_play, GREEN, "START GAME", BLACK)
        draw_button(screen, btn_settings, BLUE, "SETTINGS", WHITE)
        draw_button(screen, btn_leaderboard, ORANGE, "LEADERBOARD", BLACK)

        start_game_triggered = False

        player_list = sorted(list(players.values()), key=lambda p: p.pid)
        for idx, p in enumerate(player_list):
            target_x = (WIDTH / (len(player_list) + 1)) * (idx + 1)
            p.home_x = target_x
            if abs(p.x - target_x) > 2: p.x += (target_x - p.x) * 0.1 
                
            p.update_intent(shared_player_state.get(p.pid, {}), 1, "LOBBY")
            p.y += p.y_vel
            if p.y >= HEIGHT - p.h - 20: p.y, p.y_vel, p.on_ground = HEIGHT - p.h - 20, 0, True
            
            p.draw(screen)
            if p.pause_hold_time >= 90:
                start_game_triggered = True
                p.pause_hold_time = 0

        if mouse_click:
            if btn_play.collidepoint(pygame.mouse.get_pos()) and len(players) > 0: start_game_triggered = True
            elif btn_settings.collidepoint(pygame.mouse.get_pos()): game_state = "SETTINGS"
            elif btn_leaderboard.collidepoint(pygame.mouse.get_pos()): game_state = "LEADERBOARD"

        if start_game_triggered and len(players) > 0:
            game_state, state_timer, global_stage, distance_traveled = "COUNTDOWN", time.time() + 1.5, 1, 0
            current_stage_type = 1
            obstacles.clear(); explosions.clear()
            
            start_xs = [WIDTH//2, WIDTH//2 - 90, WIDTH//2 - 180, WIDTH//2 - 270]
            random.shuffle(player_list)
            for i, p in enumerate(player_list): 
                p.lives = 1 if SETTINGS["MODE"][SETTINGS["MODE_IDX"]] == "ENDLESS" else SETTINGS["LIVES"][SETTINGS["LIVES_IDX"]]
                p.home_x = start_xs[i % len(start_xs)]
                p.x, p.y, p.is_dead, p.pause_hold_time, p.y_vel = p.home_x, 50, False, 0, 0

    # ------------------- STATE: COUNTDOWN / TRANSITION / PLAYING -------------------
    elif game_state in ["COUNTDOWN", "TRANSITION", "PLAYING"]:
        pygame.draw.rect(screen, (40, 40, 50), (0, HEIGHT - 20, WIDTH, 20))
        if current_stage_type == 3: pygame.draw.rect(screen, (40, 40, 50), (0, 0, WIDTH, 20))
        
        alive_players = [p for p in players.values() if p.lives > 0]
        if len(alive_players) == 1 and len(players) > 1: champion_pid = alive_players[0].pid

        if game_state == "PLAYING":
            distance_traveled += int(dynamic_game_speed // 2)
            draw_button(screen, btn_pause, GREY, "PAUSE", WHITE)
            if mouse_click and btn_pause.collidepoint(pygame.mouse.get_pos()): is_paused = True
            
            screen.blit(font.render(f"DIST: {distance_traveled}m", True, YELLOW), (WIDTH//2 - 60, 20))
            is_endless = SETTINGS["MODE"][SETTINGS["MODE_IDX"]] == "ENDLESS"
            time_left = int(state_timer - time.time())
            if not is_endless: screen.blit(font.render(f"STAGE {global_stage} - {time_left}s", True, WHITE), (WIDTH//2 - 80, 60))
            
            if time_left <= 0:
                if not is_endless: game_state, global_stage, state_timer = "TRANSITION", global_stage + 1, time.time() + 1.5
                else: state_timer = time.time() + SETTINGS["STAGE_TIME"][SETTINGS["STAGE_TIME_IDX"]]
                possible_stages = [1, 2, 3]
                if current_stage_type in possible_stages: possible_stages.remove(current_stage_type)
                current_stage_type = random.choice(possible_stages)

            spawn_rate = max(20, int(90 / current_diff) - int(distance_traveled / 1000)) 
            if frame_count % spawn_rate == 0: spawn_obstacle(current_stage_type, current_diff)
        
        else: 
            header = f"STAGE {global_stage}: {stage_names[current_stage_type]}" if game_state == "TRANSITION" else "GET READY!"
            screen.blit(title_font.render(header, True, BLUE), (WIDTH//2 - 300, HEIGHT//2 - 50))
            if state_timer - time.time() <= 0:
                if game_state == "COUNTDOWN":
                    game_state, current_stage_type, state_timer = "TRANSITION", 1, time.time() + 1.5
                else:
                    game_state, state_timer = "PLAYING", time.time() + SETTINGS["STAGE_TIME"][SETTINGS["STAGE_TIME_IDX"]]

        for exp in explosions[:]:
            pygame.draw.circle(screen, YELLOW, (int(exp["x"]), int(exp["y"])), int(exp["radius"]), 5)
            pygame.draw.circle(screen, ORANGE, (int(exp["x"]), int(exp["y"])), int(exp["radius"] * 0.8), 3)
            exp["radius"] += 8
            exp["x"] -= dynamic_game_speed 
            if exp["radius"] > 150: explosions.remove(exp)

        for obs in obstacles[:]:
            obs["rect"].x -= dynamic_game_speed
            if obs["rect"].right < -20: obstacles.remove(obs)
            
            rect, otype = obs["rect"], obs["type"]
            if otype == "bomb":
                pygame.draw.rect(screen, ORANGE, rect, border_radius=15) 
                pygame.draw.rect(screen, YELLOW, rect, 3, border_radius=15) 
            elif otype == "life":
                pygame.draw.rect(screen, LIFE_COLOR, rect, border_radius=8) 
                screen.blit(small_font.render("+1", True, WHITE), (rect.x + 2, rect.y))
            else:
                pygame.draw.rect(screen, RED, rect, border_radius=4)

        hud_x, all_dead = 20, True
        for pid, p in players.items():
            if p.lives > 0: all_dead = False
            hud = font.render(f"{p.name[:6]}: {'❤️'*p.lives}" if p.lives > 0 else f"{p.name[:6]}: OUT", True, p.color if p.lives > 0 else GREY)
            screen.blit(hud, (hud_x, 20))
            hud_x += 250
            
            if p.pause_hold_time >= 90 and game_state == "PLAYING":
                is_paused = True
                p.pause_hold_time = 0

        # Phase 1: Update Intent
        for p in players.values(): p.update_intent(shared_player_state.get(p.pid, {}), current_stage_type, game_state)
            
        # Phase 2: X-Axis Movement & Collisions
        for p in players.values():
            if p.is_dead: continue
            
            if p.x < p.home_x: p.x += (dynamic_game_speed * 0.15) 
            
            p_rect = pygame.Rect(p.x, p.y, p.w, p.h)
            for obs in obstacles[:]:
                if p_rect.colliderect(obs["rect"]):
                    if obs["type"] == "bomb":
                        if p.invincible_timer == 0:
                            explosions.append({"x": p.x + p.w//2, "y": p.y + p.h//2, "radius": 10})
                            p.die(distance_traveled) 
                            if obs in obstacles: obstacles.remove(obs)
                    elif obs["type"] == "life":
                        p.lives += 1
                        if obs in obstacles: obstacles.remove(obs)
                    else:
                        dx = min(p_rect.right, obs["rect"].right) - max(p_rect.left, obs["rect"].left)
                        dy = min(p_rect.bottom, obs["rect"].bottom) - max(p_rect.top, obs["rect"].top)
                        if dx < dy: 
                            p.x = obs["rect"].left - p.w
                            p_rect.x = p.x
            if p.x < -20: p.die(distance_traveled)

        # Phase 3: Y-Axis Movement & Collisions
        for p in players.values():
            if p.is_dead: continue
            
            p.on_ground, p.hit_ceiling = False, False
            p.y += p.y_vel
            p_rect = pygame.Rect(p.x, p.y, p.w, p.h)
            
            if current_stage_type in [1, 3]:
                if p.y >= HEIGHT - p.h - 20: p.y, p.y_vel, p.on_ground = HEIGHT - p.h - 20, 0, True
                if current_stage_type == 3 and p.y <= 20: p.y, p.y_vel, p.on_ground = 20, 0, True
            elif current_stage_type == 2: p.y = max(20, min(p.y, HEIGHT - p.h - 20))

            for obs in obstacles:
                if obs["type"] not in ["bomb", "life"] and p_rect.colliderect(obs["rect"]):
                    if p.y_vel > 0: 
                        p.y = obs["rect"].top - p.h
                        p.y_vel, p.on_ground = 0, True
                    elif p.y_vel < 0: 
                        p.y = obs["rect"].bottom
                        p.y_vel = 2 
                    p_rect.y = p.y

        # Phase 4: PVP & Rendering 
        sorted_players = sorted([p for p in players.values() if not p.is_dead], key=lambda p: p.y)
        for p in sorted_players:
            p_rect = pygame.Rect(p.x, p.y, p.w, p.h)
            for other_p in sorted_players:
                if p.pid == other_p.pid or p.invincible_timer > 0 or other_p.invincible_timer > 0: continue
                o_rect = pygame.Rect(other_p.x, other_p.y, other_p.w, other_p.h)
                if p_rect.colliderect(o_rect):
                    dx = min(p_rect.right, o_rect.right) - max(p_rect.left, o_rect.left)
                    dy = min(p_rect.bottom, o_rect.bottom) - max(p_rect.top, o_rect.top)
                    if dx > dy: 
                        if p.y < other_p.y: 
                            p.y = o_rect.top - p.h
                            p.y_vel, p.on_ground = 0, True
                            other_p.hit_ceiling = True 
                    else: 
                        if p.x < other_p.x: p.x -= 2; other_p.x += 2
                        else: p.x += 2; other_p.x -= 2
            p.draw(screen)

        for p in players.values():
            if p.is_dead: p.draw(screen)

        # Death Check
        if all_dead and len(players) > 0:
            for p in players.values(): 
                if p.lives > 0: p.final_distance = distance_traveled
                if p.final_distance > session_top["score"]: session_top = {"name": p.name, "score": p.final_distance}
                save_score(p.name, p.final_distance)
            
            all_time_top = get_top_score()
            game_state, state_timer = "GAME_OVER", time.time() + 6

    # ------------------- STATE: GAME OVER -------------------
    elif game_state == "GAME_OVER":
        screen.blit(title_font.render("GAME OVER", True, RED), (WIDTH//2 - 180, 50))
        
        podium = sorted(players.values(), key=lambda p: p.final_distance, reverse=True)
        y_pos = 180
        for i, p in enumerate(podium):
            rank = i + 1
            color = YELLOW if rank == 1 else WHITE
            text = f"#{rank} - {p.name} - {p.final_distance}m"
            screen.blit(font.render(text, True, color), (WIDTH//2 - 150, y_pos))
            y_pos += 60

        if state_timer - time.time() <= 0:
            player_list = sorted(list(players.values()), key=lambda p: p.pid)
            for idx, p in enumerate(player_list):
                p.lives = 1 if SETTINGS["MODE"][SETTINGS["MODE_IDX"]] == "ENDLESS" else SETTINGS["LIVES"][SETTINGS["LIVES_IDX"]]
                p.is_dead, p.pause_hold_time = False, 0
                p.home_x = (WIDTH / (len(player_list) + 1)) * (idx + 1)
                p.x, p.y, p.y_vel = p.home_x, 50, 0
                
            game_state, global_stage, distance_traveled = "LOBBY", 1, 0
            obstacles.clear(); explosions.clear()

    pygame.display.flip()
    clock.tick(60)