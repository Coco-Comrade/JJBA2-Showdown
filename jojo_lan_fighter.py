import pygame
import socket
import threading
import json
import time
import os
import urllib.parse
import urllib.request

pygame.init()
try:
    pygame.mixer.init()
    pygame.mixer.music.set_volume(0.5)
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Use a local filename like "intro.mp3", or a direct audio-file URL ending in
# .mp3, .ogg, or .wav. Normal web pages/YouTube links will not play in Pygame.
MUSIC_SOURCE = "intro.mp3"
SWEETIE_IMAGE_FILE = os.path.join(BASE_DIR, "sweetie_fox.png")
music_error_printed = False
sweetie_image = None
sweetie_popup_open = False
prev_c_and_p = False

# =========================
# SETTINGS
# =========================
WIDTH = 1280
HEIGHT = 720
FPS = 60
NET_FPS = 30
GRAVITY = 1
GROUND_Y = 580
PORT = 5555

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (210, 45, 70)
GREEN = (55, 210, 125)
BLUE = (50, 120, 230)
YELLOW = (235, 220, 75)
PURPLE = (155, 85, 215)
CYAN = (80, 230, 230)
PINK = (245, 105, 180)
ORANGE = (240, 145, 45)
GRAY = (125, 125, 145)
DARK = (18, 16, 32)
NIGHT = (9, 8, 20)
SAND = (155, 120, 62)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("JJBA2: The Showdown")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 28)
small_font = pygame.font.SysFont("arial", 20)
big_font = pygame.font.SysFont("arial", 64)


# =========================
# THEME / COMBAT DATA
# =========================
CHARACTERS = {
    "joseph": {
        "name": "Joseph",
        "title": "Trickster Ripple",
        "color": RED,
        "accent": CYAN,
        "aura": (75, 210, 255),
        "speed": 7,
        "jump": -21,
    },
    "caesar": {
        "name": "Caesar",
        "title": "Bubble Maestro",
        "color": GREEN,
        "accent": YELLOW,
        "aura": (255, 240, 95),
        "speed": 6,
        "jump": -20,
    },
    "wamuu": {
        "name": "Wamuu",
        "title": "Wind Warrior",
        "color": PURPLE,
        "accent": ORANGE,
        "aura": (255, 155, 60),
        "speed": 5,
        "jump": -19,
    },
    "lisa": {
        "name": "Lisa Lisa",
        "title": "Ripple Master",
        "color": PINK,
        "accent": WHITE,
        "aura": (255, 190, 230),
        "speed": 6,
        "jump": -22,
    },
}

ATTACKS = {
    "light": {
        "label": "Ripple Jab",
        "startup": 4,
        "active": 5,
        "recovery": 9,
        "damage": 4,
        "stun": 12,
        "range": 58,
        "height": 42,
        "y_offset": 52,
        "knockback": 9,
    },
    "medium": {
        "label": "Bubble Cutter",
        "startup": 7,
        "active": 7,
        "recovery": 14,
        "damage": 8,
        "stun": 17,
        "range": 78,
        "height": 48,
        "y_offset": 46,
        "knockback": 14,
    },
    "heavy": {
        "label": "Sunlight Overdrive",
        "startup": 11,
        "active": 8,
        "recovery": 22,
        "damage": 14,
        "stun": 25,
        "range": 96,
        "height": 56,
        "y_offset": 38,
        "knockback": 22,
    },
}

ATTACK_BUTTONS = ("light", "medium", "heavy")


# =========================
# NETWORK HELPERS
# =========================
def get_local_ip():
    """Return the best LAN IP to show other players."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
    finally:
        if s:
            s.close()


def send_json(sock, data):
    message = json.dumps(data) + "\n"
    sock.sendall(message.encode())


def tune_socket(sock):
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass


def recv_json(sock, buffer):
    while "\n" not in buffer:
        chunk = sock.recv(4096).decode()
        if not chunk:
            raise ConnectionError("Disconnected")
        buffer += chunk

    line, buffer = buffer.split("\n", 1)
    return json.loads(line), buffer


# =========================
# LAN SERVER
# =========================
class LobbyServer:
    def __init__(self):
        self.host = "0.0.0.0"
        self.port = PORT
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.inputs = {0: empty_input(), 1: empty_input()}
        self.lock = threading.Lock()
        self.running = True
        self.started = False
        self.thread = None

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(2)
        self.thread = threading.Thread(target=self.accept_loop, daemon=True)
        self.thread.start()

    def accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                tune_socket(conn)

                with self.lock:
                    if len(self.clients) >= 2:
                        send_json(conn, {"type": "full"})
                        conn.close()
                        continue

                    player_id = 0 if 0 not in self.clients else 1
                    self.clients[player_id] = conn
                    self.started = len(self.clients) == 2

                send_json(conn, {"type": "welcome", "player_id": player_id})

                thread = threading.Thread(target=self.client_loop, args=(conn, player_id), daemon=True)
                thread.start()

            except Exception:
                break

    def client_loop(self, conn, player_id):
        buffer = ""
        while self.running:
            try:
                data, buffer = recv_json(conn, buffer)
                if data.get("type") == "input":
                    with self.lock:
                        self.inputs[player_id] = data["input"]
            except Exception:
                with self.lock:
                    if player_id in self.clients:
                        del self.clients[player_id]
                    self.inputs[player_id] = empty_input()
                    self.started = False
                break

    def get_inputs(self):
        with self.lock:
            return json.loads(json.dumps(self.inputs))

    def broadcast_state(self, state):
        with self.lock:
            client_items = list(self.clients.items())

        dead = []
        for pid, conn in client_items:
            try:
                send_json(conn, {"type": "state", "state": state})
            except Exception:
                dead.append(pid)

        if dead:
            with self.lock:
                for pid in dead:
                    if pid in self.clients:
                        del self.clients[pid]
                    self.inputs[pid] = empty_input()
                self.started = len(self.clients) == 2

    def player_count(self):
        with self.lock:
            return len(self.clients)

    def stop(self):
        self.running = False
        try:
            self.server_socket.close()
        except Exception:
            pass
        with self.lock:
            for conn in self.clients.values():
                try:
                    conn.close()
                except Exception:
                    pass
            self.clients.clear()


# =========================
# LAN CLIENT
# =========================
class GameClient:
    def __init__(self):
        self.sock = None
        self.buffer = ""
        self.player_id = None
        self.latest_state = None
        self.error = None
        self.running = False
        self.receiver_thread = None
        self.lock = threading.Lock()
        self.last_sent_input = None
        self.last_input_send_time = 0

    def connect(self, host_ip):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tune_socket(self.sock)
        self.sock.settimeout(8)
        self.sock.connect((host_ip, PORT))
        self.sock.settimeout(None)

        data, self.buffer = recv_json(self.sock, self.buffer)
        if data["type"] == "full":
            raise ConnectionError("Lobby is full")

        self.player_id = data["player_id"]
        self.running = True
        self.receiver_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.receiver_thread.start()
        return self.player_id

    def receive_loop(self):
        while self.running:
            try:
                data, self.buffer = recv_json(self.sock, self.buffer)
                if data.get("type") == "state":
                    with self.lock:
                        self.latest_state = data["state"]
            except Exception as e:
                if self.running:
                    self.error = e
                self.running = False
                break

    def send_input(self, input_data):
        now = time.perf_counter()
        if input_data == self.last_sent_input and now - self.last_input_send_time < 0.1:
            return
        send_json(self.sock, {"type": "input", "input": input_data})
        self.last_sent_input = dict(input_data)
        self.last_input_send_time = now

    def get_state(self):
        with self.lock:
            return json.loads(json.dumps(self.latest_state)) if self.latest_state else None

    def close(self):
        self.running = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


# =========================
# PLAYER
# =========================
class Fighter:
    def __init__(self, x, y, character_key, facing_right=True):
        self.character_key = character_key
        self.character = CHARACTERS[character_key]
        self.rect = pygame.Rect(x, y, 80, 160)
        self.color = self.character["color"]
        self.speed = self.character["speed"]
        self.jump_power = self.character["jump"]
        self.vel_y = 0
        self.on_ground = False

        self.hp = 100
        self.blocking = False
        self.attacking = False
        self.attack_timer = 0
        self.attack_total = 0
        self.attack_type = None
        self.hit_cooldown = 0
        self.hit_stun = 0
        self.facing_right = facing_right
        self.prev_attack_buttons = {button: False for button in ATTACK_BUTTONS}
        self.combo_text_timer = 0

    def reset(self, x, y, facing_right):
        self.rect.x = x
        self.rect.y = y
        self.vel_y = 0
        self.hp = 100
        self.blocking = False
        self.attacking = False
        self.attack_timer = 0
        self.attack_total = 0
        self.attack_type = None
        self.hit_cooldown = 0
        self.hit_stun = 0
        self.facing_right = facing_right
        self.prev_attack_buttons = {button: False for button in ATTACK_BUTTONS}
        self.combo_text_timer = 0

    def face_opponent(self, opponent):
        if self.attacking or self.hit_stun > 0:
            return
        self.facing_right = self.rect.centerx <= opponent.rect.centerx

    def move_from_input(self, inp):
        if self.hp <= 0:
            self.remember_attack_buttons(inp)
            return

        if self.hit_stun > 0:
            self.blocking = False
            self.remember_attack_buttons(inp)
            return

        dx = 0
        can_walk = not self.attacking or self.get_attack_phase() == "startup"

        if can_walk:
            if inp["left"]:
                dx -= self.speed
            if inp["right"]:
                dx += self.speed

        if inp["jump"] and self.on_ground and not self.attacking:
            self.vel_y = self.jump_power
            self.on_ground = False

        self.blocking = inp["block"] and not self.attacking and self.on_ground

        if not self.attacking and not self.blocking:
            for button in ATTACK_BUTTONS:
                if inp[button] and not self.prev_attack_buttons[button]:
                    self.start_attack(button)
                    break

        self.rect.x += dx
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(WIDTH, self.rect.right)
        self.remember_attack_buttons(inp)

    def remember_attack_buttons(self, inp):
        for button in ATTACK_BUTTONS:
            self.prev_attack_buttons[button] = inp[button]

    def apply_gravity(self):
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y

        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vel_y = 0
            self.on_ground = True

    def start_attack(self, attack_type):
        data = ATTACKS[attack_type]
        self.attacking = True
        self.attack_type = attack_type
        self.attack_total = data["startup"] + data["active"] + data["recovery"]
        self.attack_timer = self.attack_total

    def get_attack_phase(self):
        if not self.attacking or not self.attack_type:
            return None
        data = ATTACKS[self.attack_type]
        elapsed = self.attack_total - self.attack_timer
        if elapsed < data["startup"]:
            return "startup"
        if elapsed < data["startup"] + data["active"]:
            return "active"
        return "recovery"

    def update(self):
        if self.attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attacking = False
                self.attack_type = None
                self.attack_total = 0

        if self.hit_cooldown > 0:
            self.hit_cooldown -= 1

        if self.hit_stun > 0:
            self.hit_stun -= 1

        if self.combo_text_timer > 0:
            self.combo_text_timer -= 1

    def get_attack_box(self):
        if self.get_attack_phase() != "active":
            return None
        data = ATTACKS[self.attack_type]
        if self.facing_right:
            return pygame.Rect(self.rect.right, self.rect.y + data["y_offset"], data["range"], data["height"])
        return pygame.Rect(self.rect.left - data["range"], self.rect.y + data["y_offset"], data["range"], data["height"])

    def take_damage(self, amount, stun, knockback, attacker_on_left):
        if self.hit_cooldown > 0:
            return False

        blocked = self.blocking
        if blocked:
            amount = max(1, amount // 3)
            stun = max(5, stun // 2)
            knockback = max(6, knockback // 2)

        self.hp = max(0, self.hp - amount)
        self.hit_cooldown = 18
        self.hit_stun = stun
        self.combo_text_timer = 28
        self.attacking = False
        self.attack_type = None
        self.attack_timer = 0

        self.rect.x += knockback if attacker_on_left else -knockback
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(WIDTH, self.rect.right)
        return True

    def to_dict(self):
        return {
            "x": self.rect.x,
            "y": self.rect.y,
            "hp": self.hp,
            "blocking": self.blocking,
            "attacking": self.attacking,
            "attack_type": self.attack_type,
            "attack_phase": self.get_attack_phase(),
            "facing_right": self.facing_right,
            "hit_cooldown": self.hit_cooldown,
            "hit_stun": self.hit_stun,
            "combo_text_timer": self.combo_text_timer,
            "character_key": self.character_key,
        }


# =========================
# UI
# =========================
def fitted_font(text, base_size, max_width, bold=False, min_size=12):
    size = base_size
    while size > min_size:
        candidate = pygame.font.SysFont("arial", size, bold=bold)
        if candidate.size(text)[0] <= max_width:
            return candidate
        size -= 1
    return pygame.font.SysFont("arial", min_size, bold=bold)


def render_fitted(text, base_font, color, max_width=None, bold=False, min_size=12):
    if max_width is None:
        return base_font.render(text, True, color)
    fitted = fitted_font(text, base_font.get_height(), max_width, bold=bold, min_size=min_size)
    return fitted.render(text, True, color)


def draw_text(text, x, y, use_big=False, color=WHITE, max_width=None):
    img = render_fitted(text, big_font if use_big else font, color, max_width, bold=use_big)
    screen.blit(img, (x, y))


def draw_small(text, x, y, color=WHITE, max_width=None):
    img = render_fitted(text, small_font, color, max_width)
    screen.blit(img, (x, y))


def draw_center(text, y, use_big=False, color=WHITE, max_width=None):
    f = big_font if use_big else font
    img = render_fitted(text, f, color, max_width or WIDTH - 80, bold=use_big, min_size=14)
    screen.blit(img, (WIDTH // 2 - img.get_width() // 2, y))


def draw_text_in_rect(text, rect, base_font=None, color=WHITE, align="center", bold=False, min_size=12):
    base_font = base_font or font
    img = render_fitted(text, base_font, color, rect.width, bold=bold, min_size=min_size)
    if align == "left":
        x = rect.left
    elif align == "right":
        x = rect.right - img.get_width()
    else:
        x = rect.centerx - img.get_width() // 2
    y = rect.centery - img.get_height() // 2
    screen.blit(img, (x, y))


def draw_hp_bar(x, y, hp, name, accent):
    pygame.draw.rect(screen, (45, 38, 55), (x - 4, y - 4, 308, 38), border_radius=4)
    pygame.draw.rect(screen, RED, (x, y, 300, 30), border_radius=3)
    pygame.draw.rect(screen, GREEN, (x, y, 3 * max(0, hp), 30), border_radius=3)
    pygame.draw.rect(screen, accent, (x, y, 300, 30), 2, border_radius=3)
    draw_small(name, x, y - 26, accent)


def draw_stage():
    screen.fill(NIGHT)
    pygame.draw.rect(screen, (28, 24, 48), (0, 0, WIDTH, HEIGHT))
    pygame.draw.circle(screen, (240, 215, 95), (WIDTH // 2, 120), 62)

    for i in range(7):
        x = 100 + i * 190
        pygame.draw.polygon(screen, (36, 32, 64), [(x, 220), (x + 70, 220), (x + 42, GROUND_Y)])
        pygame.draw.line(screen, (85, 75, 110), (x, 220), (x + 42, GROUND_Y), 2)

    pygame.draw.rect(screen, (95, 72, 50), (0, GROUND_Y - 40, WIDTH, 40))
    pygame.draw.rect(screen, (55, 36, 28), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(screen, YELLOW, (0, GROUND_Y), (WIDTH, GROUND_Y), 3)

    for x in range(40, WIDTH, 120):
        pygame.draw.circle(screen, (170, 130, 70), (x, GROUND_Y + 48), 16, 2)

    draw_center("BATTLE TENDENCY ARENA", 632, False, (115, 110, 140))


def draw_aura(rect, color, facing_right, pulse):
    radius = 22 + (pulse % 16)
    center = (rect.centerx - 18 if facing_right else rect.centerx + 18, rect.y + 34)
    pygame.draw.circle(screen, color, center, radius, 2)
    pygame.draw.circle(screen, color, (rect.centerx, rect.y + 80), radius + 10, 1)


def draw_fighter_from_state(p):
    char = CHARACTERS[p.get("character_key", "joseph")]
    rect = pygame.Rect(p["x"], p["y"], 80, 160)
    facing_right = p["facing_right"]
    pulse = pygame.time.get_ticks() // 80

    draw_aura(rect, char["aura"], facing_right, pulse)

    body_color = char["color"]
    if p["hit_cooldown"] > 0:
        body_color = WHITE
    elif p["hit_stun"] > 0:
        body_color = (255, 120, 120)

    pygame.draw.rect(screen, body_color, rect, border_radius=4)
    pygame.draw.rect(screen, char["accent"], rect, 3, border_radius=4)

    head = pygame.Rect(rect.x + 18, rect.y - 28, 44, 44)
    pygame.draw.ellipse(screen, (235, 190, 150), head)
    eye_x = rect.x + (50 if facing_right else 26)
    pygame.draw.circle(screen, BLACK, (eye_x, rect.y - 8), 4)

    scarf_y = rect.y + 35
    if facing_right:
        pygame.draw.polygon(screen, char["accent"], [(rect.right - 4, scarf_y), (rect.right + 42, scarf_y + 12), (rect.right - 4, scarf_y + 24)])
    else:
        pygame.draw.polygon(screen, char["accent"], [(rect.left + 4, scarf_y), (rect.left - 42, scarf_y + 12), (rect.left + 4, scarf_y + 24)])

    if p["blocking"]:
        shield_x = rect.right + 10 if facing_right else rect.left - 32
        pygame.draw.ellipse(screen, BLUE, (shield_x, rect.y + 20, 26, 100), 4)

    if p["attacking"]:
        attack_type = p["attack_type"]
        phase = p.get("attack_phase")
        data = ATTACKS.get(attack_type, ATTACKS["light"])
        atk_color = char["accent"] if phase == "active" else GRAY
        if facing_right:
            atk = pygame.Rect(rect.right, rect.y + data["y_offset"], data["range"], data["height"])
        else:
            atk = pygame.Rect(rect.left - data["range"], rect.y + data["y_offset"], data["range"], data["height"])
        pygame.draw.rect(screen, atk_color, atk, 3, border_radius=4)
        if phase == "active":
            pygame.draw.circle(screen, atk_color, atk.center, max(16, data["height"] // 2), 2)

    if p["combo_text_timer"] > 0:
        draw_small("ORA!", rect.centerx - 18, rect.y - 62, char["accent"])


def draw_match(state, player_id):
    draw_stage()
    p1 = state["players"]["0"]
    p2 = state["players"]["1"]
    c1 = CHARACTERS[p1.get("character_key", "joseph")]
    c2 = CHARACTERS[p2.get("character_key", "caesar")]

    draw_fighter_from_state(p1)
    draw_fighter_from_state(p2)

    draw_hp_bar(50, 48, p1["hp"], f"P1  {c1['name']}", c1["accent"])
    draw_hp_bar(WIDTH - 350, 48, p2["hp"], f"P2  {c2['name']}", c2["accent"])
    draw_center(f"You are Player {player_id + 1}", 12)

    if p1.get("attacking") and p1.get("attack_type"):
        draw_small(ATTACKS[p1["attack_type"]]["label"], 52, 86, c1["accent"])
    if p2.get("attacking") and p2.get("attack_type"):
        label = ATTACKS[p2["attack_type"]]["label"]
        img = small_font.render(label, True, c2["accent"])
        screen.blit(img, (WIDTH - 52 - img.get_width(), 86))

    if state.get("disconnected"):
        draw_center("OPPONENT DISCONNECTED", 240, True, YELLOW)
        draw_center("Press Esc to return to the menu", 340)
        return

    if state["winner"] is not None:
        winner = state["winner"] + 1
        draw_center(f"PLAYER {winner} WINS!", 240, True, YELLOW)
        draw_center("Press R to restart", 330)
        draw_center("Press Esc to return to the menu", 370)


def load_sweetie_image():
    global sweetie_image
    if sweetie_image is not None:
        return sweetie_image
    try:
        img = pygame.image.load(SWEETIE_IMAGE_FILE).convert()
        sweetie_image = pygame.transform.smoothscale(img, (675, 360))
    except Exception:
        sweetie_image = None
    return sweetie_image


def handle_secret_image_toggle():
    global sweetie_popup_open, prev_c_and_p
    keys = pygame.key.get_pressed()
    c_and_p = keys[pygame.K_c] and keys[pygame.K_p]
    if c_and_p and not prev_c_and_p:
        sweetie_popup_open = not sweetie_popup_open
    prev_c_and_p = c_and_p


def play_menu_music():
    global music_error_printed
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            pygame.mixer.music.set_volume(0.5)
        music_file = get_music_file()
        if not music_file:
            return
        if not os.path.exists(music_file):
            if not music_error_printed:
                print(f"Music file not found: {music_file}")
                music_error_printed = True
            return
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
    except Exception as e:
        if not music_error_printed:
            print(f"Could not play music: {e}")
            print("Try converting the soundtrack to .ogg or .wav if this Pygame build cannot play MP3 files.")
            music_error_printed = True


def stop_menu_music():
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    except Exception:
        pass


def get_music_file():
    global music_error_printed
    source = MUSIC_SOURCE.strip()
    parsed = urllib.parse.urlparse(source)
    is_url = parsed.scheme in ("http", "https")

    if not is_url:
        return source if os.path.isabs(source) else os.path.join(BASE_DIR, source)

    ext = os.path.splitext(parsed.path)[1].lower()
    if ext not in (".mp3", ".ogg", ".wav"):
        if not music_error_printed:
            print("Music URL must point directly to an .mp3, .ogg, or .wav file.")
            print("A YouTube, Spotify, or normal webpage link will not work in Pygame.")
            music_error_printed = True
        return None

    cached_file = os.path.join(BASE_DIR, "downloaded_intro" + ext)
    if os.path.exists(cached_file):
        return cached_file

    if not music_error_printed:
        print("Downloading music file...")
    urllib.request.urlretrieve(source, cached_file)
    return cached_file


def draw_gold_frame(rect, thickness=3):
    pygame.draw.rect(screen, BLACK, rect, border_radius=3)
    pygame.draw.rect(screen, (205, 150, 25), rect, thickness, border_radius=3)
    pygame.draw.rect(screen, (70, 45, 15), rect.inflate(-10, -10), 1, border_radius=3)

    for sx, sy in [
        (rect.left, rect.top),
        (rect.right - 18, rect.top),
        (rect.left, rect.bottom - 18),
        (rect.right - 18, rect.bottom - 18),
    ]:
        pygame.draw.line(screen, YELLOW, (sx + 3, sy + 3), (sx + 15, sy + 3), 2)
        pygame.draw.line(screen, YELLOW, (sx + 3, sy + 3), (sx + 3, sy + 15), 2)


def draw_menu_background():
    screen.fill((5, 3, 9))

    for i in range(0, WIDTH, 34):
        pygame.draw.line(screen, (32, 7, 45), (i, 0), (WIDTH - i // 2, HEIGHT), 1)
    for i in range(0, WIDTH, 70):
        pygame.draw.line(screen, (55, 10, 75), (i, HEIGHT), (WIDTH - i, 0), 2)

    sfx_font = pygame.font.SysFont("arial", 72, bold=True)
    for i, txt in enumerate(["ゴ", "ゴ", "ゴ", "ゴ", "ゴ"]):
        img = sfx_font.render(txt, True, (55, 8, 75))
        img.set_alpha(135)
        screen.blit(img, (430 + i * 120, 25 + (i % 2) * 42))

    pygame.draw.rect(screen, BLACK, (0, 0, WIDTH, 16))
    pygame.draw.rect(screen, BLACK, (0, HEIGHT - 16, WIDTH, 16))
    pygame.draw.rect(screen, BLACK, (0, 0, 16, HEIGHT))
    pygame.draw.rect(screen, BLACK, (WIDTH - 16, 0, 16, HEIGHT))


def draw_menu_button(text, rect, selected):
    if selected:
        pygame.draw.rect(screen, (255, 200, 30), rect.inflate(14, 14), 3, border_radius=4)
        pygame.draw.rect(screen, (95, 52, 8), rect.inflate(8, 8), 2, border_radius=4)

    draw_gold_frame(rect, 3)
    inner = rect.inflate(-10, -10)
    fill = (45, 13, 52) if selected else (18, 14, 28)
    pygame.draw.rect(screen, fill, inner, border_radius=3)

    if selected:
        pygame.draw.polygon(
            screen,
            YELLOW,
            [(rect.left + 18, rect.centery), (rect.left + 31, rect.centery - 10), (rect.left + 31, rect.centery + 10)],
        )

    label_rect = rect.inflate(-54 if selected else -28, -14)
    if selected:
        label_rect.x += 18
    draw_text_in_rect(text.upper(), label_rect, font, WHITE if selected else (175, 170, 185), min_size=15)


def draw_video_panel(x, y, w, h, title="SWEETIE FOX", show_close=False):
    panel = pygame.Rect(x, y, w, h)
    draw_gold_frame(panel, 3)
    draw_text_in_rect(title, pygame.Rect(x + 45, y + 8, w - 90, 34), font, WHITE, min_size=14)

    if show_close:
        close = pygame.Rect(panel.right - 36, panel.top + 8, 26, 26)
        pygame.draw.rect(screen, BLACK, close)
        pygame.draw.rect(screen, YELLOW, close, 2)
        draw_small("X", close.x + 7, close.y + 3, WHITE)

    img = load_sweetie_image()
    image_rect = pygame.Rect(x + 5, y + 55, w - 10, h - 115)
    if img:
        fitted = pygame.transform.smoothscale(img, (image_rect.width, image_rect.height))
        screen.blit(fitted, image_rect.topleft)
    else:
        pygame.draw.rect(screen, (28, 12, 40), image_rect)
        draw_center("Missing sweetie_fox.png", y + 170, False, RED, w - 40)
        draw_center("Put the image in your game folder", y + 215, False, WHITE, w - 40)

    pygame.draw.rect(screen, BLACK, (x + 5, y + h - 58, w - 10, 53))
    draw_small("SBR EP 2 Gyro Teaches Johnny How To Roll Balls", x + 20, y + h - 47, WHITE, w - 115)
    draw_small("(Cosplay Sweetie Fox)", x + 20, y + h - 22, WHITE, w - 115)
    draw_small("20:08", x + w - 75, y + h - 35, WHITE)


def draw_secret_image_popup():
    if not sweetie_popup_open:
        return

    draw_video_panel(330, 145, 675, 470, title="SWEETIE FOX", show_close=True)


def draw_showdown_preview(x, y, w, h):
    panel = pygame.Rect(x, y, w, h)
    draw_gold_frame(panel, 3)
    draw_text_in_rect("BATTLE TENDENCY", pygame.Rect(x + 20, y + 8, w - 40, 38), font, WHITE, min_size=15)

    arena = pygame.Rect(x + 16, y + 58, w - 32, h - 86)
    pygame.draw.rect(screen, (16, 12, 30), arena)
    pygame.draw.rect(screen, (65, 42, 75), arena, 2)
    pygame.draw.circle(screen, (238, 208, 82), (arena.centerx, arena.y + 55), 42)
    pygame.draw.rect(screen, (82, 55, 35), (arena.x, arena.bottom - 62, arena.width, 62))
    pygame.draw.line(screen, YELLOW, (arena.x, arena.bottom - 62), (arena.right, arena.bottom - 62), 3)

    for i in range(5):
        pillar_x = arena.x + 42 + i * 105
        pygame.draw.polygon(screen, (42, 35, 65), [(pillar_x, arena.y + 95), (pillar_x + 42, arena.y + 95), (pillar_x + 25, arena.bottom - 62)])

    joseph = pygame.Rect(arena.x + 115, arena.bottom - 182, 70, 120)
    caesar = pygame.Rect(arena.right - 185, arena.bottom - 182, 70, 120)
    pygame.draw.circle(screen, CYAN, (joseph.centerx, joseph.y + 35), 42, 2)
    pygame.draw.circle(screen, YELLOW, (caesar.centerx, caesar.y + 35), 42, 2)
    pygame.draw.rect(screen, RED, joseph, border_radius=4)
    pygame.draw.rect(screen, GREEN, caesar, border_radius=4)
    pygame.draw.ellipse(screen, (235, 190, 150), (joseph.x + 16, joseph.y - 24, 38, 38))
    pygame.draw.ellipse(screen, (235, 190, 150), (caesar.x + 16, caesar.y - 24, 38, 38))
    pygame.draw.polygon(screen, CYAN, [(joseph.right - 3, joseph.y + 30), (joseph.right + 36, joseph.y + 42), (joseph.right - 3, joseph.y + 54)])
    pygame.draw.polygon(screen, YELLOW, [(caesar.left + 3, caesar.y + 30), (caesar.left - 36, caesar.y + 42), (caesar.left + 3, caesar.y + 54)])

    versus = big_font.render("VS", True, PINK)
    screen.blit(versus, (arena.centerx - versus.get_width() // 2, arena.centery - 35))
    draw_small("JOSEPH JOESTAR", arena.x + 58, arena.bottom - 42, CYAN, 185)
    draw_small("CAESAR ZEPPELI", arena.right - 220, arena.bottom - 42, YELLOW, 185)


def draw_lobby_side_panel(players=1):
    panel = pygame.Rect(960, 25, 295, 445)
    draw_gold_frame(panel, 3)
    draw_text("LOBBY", 990, 48, False, YELLOW, 240)
    pygame.draw.line(screen, (185, 130, 25), (990, 95), (1228, 95), 2)
    draw_small("STATUS: WAITING...", 990, 120, WHITE, 240)
    draw_small(f"PLAYERS: {players} / 2", 990, 155, WHITE, 240)
    draw_small("HOST: YOU", 990, 190, WHITE, 240)
    draw_small(f"PORT: {PORT}", 990, 225, WHITE, 240)

    p1 = pygame.Rect(980, 262, 255, 90)
    pygame.draw.rect(screen, (70, 10, 13), p1, border_radius=3)
    pygame.draw.rect(screen, RED, p1, 2, border_radius=3)
    draw_text("PLAYER 1", 995, 282, False, RED, 150)
    draw_small("YOU", 995, 326, WHITE, 150)
    pygame.draw.rect(screen, RED, (1170, 292, 32, 48), border_radius=4)
    pygame.draw.circle(screen, (235, 190, 150), (1186, 284), 15)

    p2 = pygame.Rect(980, 372, 255, 72)
    p2_color = GREEN if players >= 2 else GRAY
    pygame.draw.rect(screen, (18, 18, 24), p2, border_radius=3)
    pygame.draw.rect(screen, p2_color, p2, 2, border_radius=3)
    draw_text("PLAYER 2", 995, 388, False, p2_color, 165)
    draw_small("READY" if players >= 2 else "WAITING...", 995, 426, BLUE, 165)

    controls = pygame.Rect(960, 488, 295, 207)
    draw_gold_frame(controls, 3)
    draw_small("CONTROLS", 990, 510, CYAN, 240)
    draw_small("MOVE: A/D OR ARROWS", 990, 540, WHITE, 240)
    draw_small("JUMP: W OR UP", 990, 564, WHITE, 240)
    draw_small("BLOCK: S OR DOWN", 990, 588, WHITE, 240)
    draw_small("LIGHT: J", 990, 612, WHITE, 240)
    draw_small("MEDIUM: K", 990, 636, WHITE, 240)
    draw_small("HEAVY: L", 990, 660, WHITE, 240)
    draw_small("MENU: ESC", 990, 684, WHITE, 240)


def message_screen(title, lines):
    handle_secret_image_toggle()
    screen.fill(DARK)
    draw_center(title, 160, True, YELLOW)
    for i, line in enumerate(lines):
        draw_center(line, 270 + i * 45)
    draw_secret_image_popup()
    pygame.display.flip()


def text_input_screen(title, default_text=""):
    text = default_text
    while True:
        clock.tick(FPS)
        handle_secret_image_toggle()
        draw_menu_background()
        draw_center(title, 160, True, YELLOW)
        draw_center("Enter the host IP, then press Enter", 260)
        draw_center(text + "_", 330)
        draw_center("Backspace = delete    Esc = cancel", 500)
        draw_secret_image_popup()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and text.strip():
                    return text.strip()
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    ch = event.unicode
                    if ch.isdigit() or ch == ".":
                        text += ch


# =========================
# INPUT
# =========================
def empty_input():
    return {
        "left": False,
        "right": False,
        "jump": False,
        "block": False,
        "light": False,
        "medium": False,
        "heavy": False,
        "restart": False,
        "menu": False,
    }


def get_local_input():
    keys = pygame.key.get_pressed()
    inp = empty_input()
    inp["left"] = keys[pygame.K_a] or keys[pygame.K_LEFT]
    inp["right"] = keys[pygame.K_d] or keys[pygame.K_RIGHT]
    inp["jump"] = keys[pygame.K_w] or keys[pygame.K_UP]
    inp["block"] = keys[pygame.K_s] or keys[pygame.K_DOWN]
    inp["light"] = keys[pygame.K_j] or keys[pygame.K_KP1]
    inp["medium"] = keys[pygame.K_k] or keys[pygame.K_KP2]
    inp["heavy"] = keys[pygame.K_l] or keys[pygame.K_KP3]
    inp["restart"] = keys[pygame.K_r]
    inp["menu"] = keys[pygame.K_ESCAPE]
    return inp


# =========================
# SERVER-SIDE GAME SIM
# =========================
def handle_combat(attacker, defender):
    atk_box = attacker.get_attack_box()
    if atk_box and atk_box.colliderect(defender.rect):
        data = ATTACKS.get(attacker.attack_type, ATTACKS["light"])
        did_hit = defender.take_damage(
            data["damage"],
            data["stun"],
            data["knockback"],
            attacker.rect.centerx < defender.rect.centerx,
        )
        if did_hit:
            attacker.attacking = False
            attacker.attack_type = None
            attacker.attack_timer = 0


def make_state(p1, p2, winner, disconnected=False):
    return {
        "players": {
            "0": p1.to_dict(),
            "1": p2.to_dict(),
        },
        "winner": winner,
        "disconnected": disconnected,
    }


def step_fight(p1, p2, input1, input2, winner):
    if winner is not None:
        if input1.get("restart") or input2.get("restart"):
            p1.reset(200, 300, True)
            p2.reset(900, 300, False)
            winner = None
        return winner

    p1.face_opponent(p2)
    p2.face_opponent(p1)
    p1.move_from_input(input1)
    p2.move_from_input(input2)

    p1.apply_gravity()
    p2.apply_gravity()

    p1.update()
    p2.update()

    handle_combat(p1, p2)
    handle_combat(p2, p1)

    if p1.hp <= 0:
        winner = 1
    elif p2.hp <= 0:
        winner = 0
    return winner


def make_ai_input(ai, player, frame_count):
    inp = empty_input()
    distance = player.rect.centerx - ai.rect.centerx
    abs_distance = abs(distance)

    if ai.hit_stun > 0:
        return inp

    if abs_distance > 110:
        if distance > 0:
            inp["right"] = True
        else:
            inp["left"] = True
    elif abs_distance < 48:
        if distance > 0:
            inp["left"] = True
        else:
            inp["right"] = True

    if 62 <= abs_distance <= 145 and not ai.attacking:
        if frame_count % 42 == 0:
            inp["light"] = True
        elif frame_count % 86 == 0:
            inp["medium"] = True
        elif frame_count % 155 == 0:
            inp["heavy"] = True

    if player.attacking and abs_distance < 155 and frame_count % 3 != 0:
        inp["block"] = True

    if frame_count % 210 == 0 and ai.on_ground and abs_distance < 260:
        inp["jump"] = True

    return inp


def run_game_server(server):
    p1 = Fighter(200, 300, "joseph", True)
    p2 = Fighter(900, 300, "caesar", False)
    winner = None
    frame_duration = 1 / FPS
    send_duration = 1 / NET_FPS
    next_frame_time = time.perf_counter()
    next_send_time = next_frame_time

    while server.running:
        now = time.perf_counter()
        if now < next_frame_time:
            time.sleep(next_frame_time - now)
        next_frame_time += frame_duration

        if time.perf_counter() - next_frame_time > frame_duration:
            next_frame_time = time.perf_counter()

        inputs = server.get_inputs()

        if inputs[0].get("menu") or inputs[1].get("menu"):
            return "menu"

        if server.player_count() < 2:
            server.broadcast_state(make_state(p1, p2, winner, disconnected=True))
            return "menu"

        winner = step_fight(p1, p2, inputs[0], inputs[1], winner)

        now = time.perf_counter()
        if now >= next_send_time:
            server.broadcast_state(make_state(p1, p2, winner))
            next_send_time = now + send_duration

    return "menu"


def run_singleplayer_game():
    stop_menu_music()
    round_intro()
    player = Fighter(200, 300, "joseph", True)
    ai = Fighter(900, 300, "wamuu", False)
    winner = None
    frame_count = 0

    while True:
        clock.tick(FPS)
        frame_count += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

        player_input = get_local_input()

        if player_input["menu"]:
            return "menu"

        ai_input = make_ai_input(ai, player, frame_count)
        winner = step_fight(player, ai, player_input, ai_input, winner)

        state = make_state(player, ai, winner)
        draw_match(state, 0)

        if winner is not None:
            if winner == 0:
                draw_center("YOU WIN!", 430, True, YELLOW)
            else:
                draw_center("WAMUU WINS!", 430, True, YELLOW)

        draw_center("Single Player: Joseph vs. Wamuu", 675, False, GRAY)
        pygame.display.flip()


# =========================
# CLIENT LOOP
# =========================
def run_client_game(client):
    last_state_time = time.time()
    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.close()
                pygame.quit()
                quit()

        inp = get_local_input()

        try:
            client.send_input(inp)
        except Exception as e:
            message_screen("CONNECTION LOST", [str(e), "Press Enter to return to the menu"])
            wait_for_enter()
            return "menu"

        if client.error:
            message_screen("CONNECTION LOST", [str(client.error), "Press Enter to return to the menu"])
            wait_for_enter()
            return "menu"

        state = client.get_state()
        if state:
            last_state_time = time.time()
            draw_match(state, client.player_id)
            if state.get("disconnected") and inp["menu"]:
                return "menu"
        else:
            message_screen("WAITING FOR BATTLE DATA", ["The server is warming up the arena..."])

        if time.time() - last_state_time > 3:
            draw_center("Network delay...", 610, False, YELLOW)

        pygame.display.flip()

        if inp["menu"]:
            return "menu"


# =========================
# MENUS
# =========================
def wait_for_enter():
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return


def intro_screen():
    play_menu_music()
    timer = 120
    while timer > 0:
        clock.tick(FPS)
        timer -= 1
        handle_secret_image_toggle()
        draw_menu_background()

        scale = 1 + (120 - timer) * 0.002
        title_font = pygame.font.SysFont("arial", int(84 * scale), bold=True)
        title = title_font.render("JJBA2", True, WHITE)
        shadow = title_font.render("JJBA2", True, PINK)
        screen.blit(shadow, (WIDTH // 2 - shadow.get_width() // 2 + 7, 160 + 7))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 160))

        draw_center("THE SHOWDOWN", 275, False, RED)
        draw_center("A Ripple Warriors LAN Battle", 330, False, CYAN)
        if timer < 65:
            draw_center("Press Enter to skip", 610, False, GRAY)
        draw_secret_image_popup()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return


def round_intro():
    labels = ["3", "2", "1", "FIGHT!"]
    for label in labels:
        frames = 45 if label != "FIGHT!" else 60
        for frame in range(frames):
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            draw_stage()
            color = YELLOW if label == "FIGHT!" else WHITE
            draw_center(label, 260, True, color)
            draw_center("Joseph Joestar vs. Wamuu", 350, False, CYAN)
            pygame.display.flip()


def lobby_menu():
    play_menu_music()
    selected = 0
    options = ["Single Player", "Create LAN Lobby", "Join LAN Lobby", "Controls", "Exit"]

    while True:
        clock.tick(FPS)
        handle_secret_image_toggle()
        draw_menu_background()

        draw_text("JJBA2", 42, 52, True, WHITE)
        draw_text("JJBA2", 49, 59, True, PINK)
        draw_text("THE SHOWDOWN", 82, 132, False, RED)
        draw_small("v1.4.0", 18, 18, GRAY)

        for i, option in enumerate(options):
            rect = pygame.Rect(38, 250 + i * 72, 285, 58)
            draw_menu_button(option, rect, i == selected)

        draw_showdown_preview(360, 150, 590, 410)
        draw_lobby_side_panel()
        draw_secret_image_popup()

        draw_small("UP/DOWN  NAVIGATE", 38, 640, GRAY)
        draw_small("ENTER  CONFIRM", 38, 665, GRAY)
        draw_small("ESC  BACK", 38, 690, GRAY)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    if options[selected] == "Single Player":
                        return "singleplayer"
                    if options[selected] == "Create LAN Lobby":
                        return "host"
                    if options[selected] == "Join LAN Lobby":
                        return "join"
                    if options[selected] == "Controls":
                        controls_screen()
                    else:
                        pygame.quit()
                        quit()


def controls_screen():
    lines = [
        "Move: A/D or Left/Right",
        "Jump: W or Up",
        "Block: S or Down",
        "Ripple Jab: J or Numpad 1",
        "Bubble Cutter: K or Numpad 2",
        "Sunlight Overdrive: L or Numpad 3",
        "Restart after KO: R",
        "Menu: Esc",
        "",
        "Tap attacks. Held buttons will not auto-repeat.",
    ]
    while True:
        clock.tick(FPS)
        handle_secret_image_toggle()
        draw_menu_background()
        draw_center("CONTROLS", 95, True, YELLOW)
        for i, line in enumerate(lines):
            draw_center(line, 190 + i * 38, False, WHITE if line else GRAY)
        draw_center("Press Enter or Esc to return", 635, False, GRAY)
        draw_secret_image_popup()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                return


def create_lobby_flow():
    play_menu_music()
    server = LobbyServer()
    try:
        server.start()
    except Exception as e:
        message_screen("SERVER ERROR", [str(e), "Maybe port 5555 is already being used.", "Press ENTER"])
        wait_for_enter()
        return

    local_ip = get_local_ip()
    client = GameClient()

    try:
        client.connect("127.0.0.1")
    except Exception as e:
        server.stop()
        message_screen("HOST ERROR", [str(e), "Press ENTER"])
        wait_for_enter()
        return

    waiting = True
    while waiting:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                server.stop()
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                server.stop()
                client.close()
                return

        handle_secret_image_toggle()
        draw_menu_background()
        draw_center("LOBBY CREATED", 130, True, YELLOW)
        draw_center("Have Player 2 join using this IP:", 250)
        draw_center(local_ip, 310, True, WHITE)
        draw_center(f"Players Connected: {server.player_count()} / 2", 420)
        draw_center("Esc = cancel lobby", 540, False, GRAY)
        draw_lobby_side_panel(server.player_count())
        draw_secret_image_popup()
        pygame.display.flip()

        if server.player_count() >= 2:
            waiting = False

    def server_game_thread():
        run_game_server(server)

    stop_menu_music()
    threading.Thread(target=server_game_thread, daemon=True).start()
    run_client_game(client)
    server.stop()
    client.close()


def join_lobby_flow():
    play_menu_music()
    host_ip = text_input_screen("JOIN LOBBY")
    if not host_ip:
        return

    client = GameClient()
    try:
        message_screen("CONNECTING", [f"Trying {host_ip}:{PORT}..."])
        client.connect(host_ip)
    except Exception as e:
        message_screen("JOIN FAILED", [str(e), "Make sure both devices are on the same Wi-Fi network.", "Press Enter"])
        wait_for_enter()
        return

    stop_menu_music()
    run_client_game(client)
    client.close()


# =========================
# MAIN
# =========================
def main():
    intro_screen()
    while True:
        choice = lobby_menu()
        if choice == "singleplayer":
            run_singleplayer_game()
        elif choice == "host":
            create_lobby_flow()
        elif choice == "join":
            join_lobby_flow()


if __name__ == "__main__":
    main()
