import os
import urllib.parse
import urllib.request

import pygame

from .config import *
from .data import *

music_error_printed = False
current_music_file = None
sweetie_image = None
sweetie_popup_open = False
prev_c_and_p = False

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


def draw_text_in_rect(
    text,
    rect,
    base_font=None,
    color=WHITE,
    align="center",
    bold=False,
    min_size=12,
):
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


def draw_character_portrait(character_key, rect, flip=False):
    sprite_data = SPRITE_ANIMATIONS.get(character_key)
    if sprite_data:
        path = os.path.join(BASE_DIR, "assets", "sprites", sprite_data["folder"], "idle", "0.png")
        image = load_sprite_image(path)
        if image:
            image_width = int(image.get_width() * rect.height / image.get_height())
            image = pygame.transform.scale(image, (image_width, rect.height))
            if flip:
                image = pygame.transform.flip(image, True, False)
            crop = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            crop.blit(image, (rect.centerx - rect.x - image.get_width() // 2, 0))
            screen.blit(crop, rect.topleft)
            return

    char = CHARACTERS[character_key]
    pygame.draw.rect(screen, char["color"], rect.inflate(-16, -10), border_radius=4)
    pygame.draw.circle(screen, (235, 190, 150), rect.center, rect.height // 4)


def draw_arcade_hud(state):
    p1 = state["players"]["0"]
    p2 = state["players"]["1"]
    player_names = state.get("player_names", {})
    p1_name = player_names.get("0", "PLAYER 1")
    p2_name = player_names.get("1", "PLAYER 2")
    c1 = CHARACTERS[p1.get("character_key", "joseph")]
    c2 = CHARACTERS[p2.get("character_key", "caesar")]

    pygame.draw.rect(screen, (26, 21, 70), (0, 0, WIDTH, 104))
    pygame.draw.rect(
        screen,
        (245, 202, 42),
        (12, 14, WIDTH - 24, 46),
        border_radius=3,
    )
    pygame.draw.rect(
        screen,
        (95, 55, 18),
        (18, 20, WIDTH - 36, 34),
        3,
        border_radius=3,
    )
    pygame.draw.polygon(
        screen,
        (232, 190, 35),
        [
            (WIDTH // 2 - 72, 8),
            (WIDTH // 2 + 72, 8),
            (WIDTH // 2 + 48, 88),
            (WIDTH // 2 - 48, 88),
        ],
    )
    pygame.draw.rect(
        screen,
        (18, 29, 88),
        (WIDTH // 2 - 32, 24, 64, 48),
        border_radius=4,
    )
    draw_text_in_rect(
        "40",
        pygame.Rect(WIDTH // 2 - 26, 28, 52, 40),
        big_font,
        YELLOW,
        bold=True,
        min_size=24,
    )

    draw_text(p1_name, 72, 2, False, YELLOW, 250)
    right_label = render_fitted(p2_name, font, YELLOW, 250)
    screen.blit(right_label, (WIDTH - 72 - right_label.get_width(), 2))

    left_portrait = pygame.Rect(18, 34, 72, 62)
    right_portrait = pygame.Rect(WIDTH - 90, 34, 72, 62)
    pygame.draw.rect(screen, (41, 24, 75), left_portrait)
    pygame.draw.rect(screen, (41, 24, 75), right_portrait)
    pygame.draw.rect(screen, YELLOW, left_portrait, 3)
    pygame.draw.rect(screen, YELLOW, right_portrait, 3)
    draw_character_portrait(p1.get("character_key", "joseph"), left_portrait)
    draw_character_portrait(p2.get("character_key", "caesar"), right_portrait, True)

    left_bar = pygame.Rect(112, 42, 382, 18)
    right_bar = pygame.Rect(WIDTH - 494, 42, 382, 18)
    pygame.draw.rect(screen, (90, 23, 38), left_bar)
    pygame.draw.rect(screen, (90, 23, 38), right_bar)
    pygame.draw.rect(
        screen,
        (74, 236, 120),
        (
            left_bar.x,
            left_bar.y,
            int(left_bar.width * p1["hp"] / 100),
            left_bar.height,
        ),
    )
    right_hp_width = int(right_bar.width * p2["hp"] / 100)
    pygame.draw.rect(
        screen,
        (74, 236, 120),
        (
            right_bar.right - right_hp_width,
            right_bar.y,
            right_hp_width,
            right_bar.height,
        ),
    )
    pygame.draw.rect(screen, WHITE, left_bar, 2)
    pygame.draw.rect(screen, WHITE, right_bar, 2)

    draw_small(c1["name"].upper(), 112, 64, WHITE, 240)
    p2_name = small_font.render(c2["name"].upper(), True, WHITE)
    screen.blit(p2_name, (right_bar.right - p2_name.get_width(), 64))
    draw_small("STAND", WIDTH - 370, 76, YELLOW, 140)


def draw_stage():
    screen.fill(NIGHT)
    pygame.draw.rect(screen, (28, 24, 48), (0, 0, WIDTH, HEIGHT))
    pygame.draw.circle(screen, (240, 215, 95), (WIDTH // 2, 120), 62)

    for i in range(7):
        x = 100 + i * 190
        pygame.draw.polygon(
            screen,
            (36, 32, 64),
            [(x, 220), (x + 70, 220), (x + 42, GROUND_Y)],
        )
        pygame.draw.line(
            screen,
            (85, 75, 110),
            (x, 220),
            (x + 42, GROUND_Y),
            2,
        )

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


def load_sprite_image(path):
    if path in sprite_cache:
        return sprite_cache[path]
    try:
        image = pygame.image.load(path).convert_alpha()
        bounds = image.get_bounding_rect()
        if bounds.width > 0 and bounds.height > 0:
            image = image.subsurface(bounds).copy()
        sprite_cache[path] = image
        return image
    except Exception as exc:
        logger.debug("Could not load sprite %s: %s", path, exc)
        sprite_cache[path] = None
        return None


def sprite_animation_name(p):
    if p["hp"] <= 0:
        return "ko"
    if p["hit_stun"] > 0 or p["hit_cooldown"] > 0:
        return "hit"
    if p["blocking"]:
        return "block"
    if p["attacking"] and p["attack_type"]:
        return p["attack_type"]
    if not p.get("on_ground", True):
        return "jump"
    if abs(p.get("last_dx", 0)) > 0:
        return "walk"
    return "idle"


def draw_character_sprite(p, rect, facing_right):
    sprite_data = SPRITE_ANIMATIONS.get(p.get("character_key"))
    if not sprite_data:
        return False

    anim = sprite_animation_name(p)
    frame_count = sprite_data.get(anim, sprite_data["idle"])
    tick = pygame.time.get_ticks() // 110
    frame_number = tick % frame_count
    path = os.path.join(
        BASE_DIR,
        "assets",
        "sprites",
        sprite_data["folder"],
        anim,
        f"{frame_number}.png",
    )
    image = load_sprite_image(path)
    if image is None:
        return False

    target_height = sprite_data.get("height", 152)
    if anim == "ko":
        target_height = int(target_height * 0.75)
    scale = target_height / image.get_height()
    target_size = (max(1, int(image.get_width() * scale)), target_height)
    image = pygame.transform.scale(image, target_size)
    if not facing_right:
        image = pygame.transform.flip(image, True, False)

    draw_x = rect.centerx - image.get_width() // 2
    draw_y = rect.bottom - image.get_height() + 4
    screen.blit(image, (draw_x, draw_y))

    if p["blocking"]:
        shield_x = rect.right + 10 if facing_right else rect.left - 32
        pygame.draw.ellipse(screen, BLUE, (shield_x, rect.y + 20, 26, 100), 4)
    return True


def draw_fighter_from_state(p):
    char = CHARACTERS[p.get("character_key", "joseph")]
    rect = pygame.Rect(p["x"], p["y"], 80, 160)
    facing_right = p["facing_right"]
    pulse = pygame.time.get_ticks() // 80

    draw_aura(rect, char["aura"], facing_right, pulse)

    if draw_character_sprite(p, rect, facing_right):
        if p["combo_text_timer"] > 0:
            draw_small("ORA!", rect.centerx - 18, rect.y - 62, char["accent"])
        return

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
        pygame.draw.polygon(
            screen,
            char["accent"],
            [
                (rect.right - 4, scarf_y),
                (rect.right + 42, scarf_y + 12),
                (rect.right - 4, scarf_y + 24),
            ],
        )
    else:
        pygame.draw.polygon(
            screen,
            char["accent"],
            [
                (rect.left + 4, scarf_y),
                (rect.left - 42, scarf_y + 12),
                (rect.left + 4, scarf_y + 24),
            ],
        )

    if p["blocking"]:
        shield_x = rect.right + 10 if facing_right else rect.left - 32
        pygame.draw.ellipse(screen, BLUE, (shield_x, rect.y + 20, 26, 100), 4)

    if p["attacking"]:
        attack_type = p["attack_type"]
        phase = p.get("attack_phase")
        data = ATTACKS.get(attack_type, ATTACKS["light"])
        atk_color = char["accent"] if phase == "active" else GRAY
        if facing_right:
            atk = pygame.Rect(
                rect.right,
                rect.y + data["y_offset"],
                data["range"],
                data["height"],
            )
        else:
            atk = pygame.Rect(
                rect.left - data["range"],
                rect.y + data["y_offset"],
                data["range"],
                data["height"],
            )
        pygame.draw.rect(screen, atk_color, atk, 3, border_radius=4)
        if phase == "active":
            pygame.draw.circle(
                screen,
                atk_color,
                atk.center,
                max(16, data["height"] // 2),
                2,
            )

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

    draw_arcade_hud(state)
    player_name = state.get("player_names", {}).get(str(player_id), f"PLAYER {player_id + 1}")
    draw_center(f"You are {player_name}", 104, False, WHITE, 360)

    if p1.get("attacking") and p1.get("attack_type"):
        draw_small(ATTACKS[p1["attack_type"]]["label"], 112, 86, c1["accent"], 260)
    if p2.get("attacking") and p2.get("attack_type"):
        label = ATTACKS[p2["attack_type"]]["label"]
        img = small_font.render(label, True, c2["accent"])
        screen.blit(img, (WIDTH - 112 - img.get_width(), 86))

    if state.get("disconnected"):
        draw_center("OPPONENT DISCONNECTED", 240, True, YELLOW)
        draw_center("Press Esc to return to the menu", 340)
        return

    if state["winner"] is not None:
        winner = state["winner"] + 1
        winner_name = state.get("player_names", {}).get(str(state["winner"]), f"PLAYER {winner}")
        draw_center(f"{winner_name} WINS!", 240, True, YELLOW)
        draw_center("Press R to restart", 330)
        draw_center("Press Esc to return to the menu", 370)


def load_sweetie_image():
    global sweetie_image
    if sweetie_image is not None:
        return sweetie_image
    try:
        img = pygame.image.load(SWEETIE_IMAGE_FILE).convert()
        sweetie_image = pygame.transform.smoothscale(img, (675, 360))
    except Exception as exc:
        logger.debug("Sweetie image unavailable: %s", exc)
        sweetie_image = None
    return sweetie_image


def handle_secret_image_toggle():
    global sweetie_popup_open, prev_c_and_p
    keys = pygame.key.get_pressed()
    c_and_p = keys[pygame.K_c] and keys[pygame.K_p]
    if c_and_p and not prev_c_and_p:
        sweetie_popup_open = not sweetie_popup_open
    prev_c_and_p = c_and_p


def play_music(source, volume=0.5):
    global current_music_file, music_error_printed
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            pygame.mixer.music.set_volume(volume)
        music_file = get_music_file(source)
        if not music_file:
            return
        if not os.path.exists(music_file):
            if not music_error_printed:
                logger.warning("Music file not found: %s", music_file)
                music_error_printed = True
            return
        if current_music_file != music_file:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1)
            current_music_file = music_file
            logger.info("Playing music: %s", music_file)
        elif not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)
            logger.info("Restarted music loop: %s", music_file)
    except Exception as exc:
        if not music_error_printed:
            logger.warning("Could not play music: %s", exc)
            logger.warning(
                "Try converting the soundtrack to .ogg or .wav if this "
                "Pygame build cannot play MP3 files."
            )
            music_error_printed = True


def play_menu_music():
    play_music(MUSIC_SOURCE, 0.5)


def play_character_select_music():
    play_music(CHARACTER_SELECT_MUSIC_SOURCE, 0.55)


def stop_menu_music():
    global current_music_file
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            logger.info("Stopped menu music")
        current_music_file = None
    except Exception as exc:
        logger.debug("Music stop skipped: %s", exc)


def get_music_file(source):
    global music_error_printed
    source = source.strip()
    parsed = urllib.parse.urlparse(source)
    is_url = parsed.scheme in ("http", "https")

    if not is_url:
        if os.path.isabs(source):
            return source
        return os.path.join(BASE_DIR, source)

    ext = os.path.splitext(parsed.path)[1].lower()
    if ext not in (".mp3", ".ogg", ".wav"):
        if not music_error_printed:
            logger.warning(
                "Music URL must point directly to an .mp3, .ogg, or .wav file."
            )
            logger.warning(
                "A YouTube, Spotify, or normal webpage link will not work in "
                "Pygame."
            )
            music_error_printed = True
        return None

    cached_file = os.path.join(BASE_DIR, "downloaded_intro" + ext)
    if os.path.exists(cached_file):
        return cached_file

    logger.info("Downloading music file: %s", source)
    urllib.request.urlretrieve(source, cached_file)
    return cached_file


def draw_gold_frame(rect, thickness=3):
    pygame.draw.rect(screen, BLACK, rect, border_radius=3)
    pygame.draw.rect(screen, (205, 150, 25), rect, thickness, border_radius=3)
    pygame.draw.rect(
        screen,
        (70, 45, 15),
        rect.inflate(-10, -10),
        1,
        border_radius=3,
    )

    for sx, sy in [
        (rect.left, rect.top),
        (rect.right - 18, rect.top),
        (rect.left, rect.bottom - 18),
        (rect.right - 18, rect.bottom - 18),
    ]:
        pygame.draw.line(
            screen,
            YELLOW,
            (sx + 3, sy + 3),
            (sx + 15, sy + 3),
            2,
        )
        pygame.draw.line(
            screen,
            YELLOW,
            (sx + 3, sy + 3),
            (sx + 3, sy + 15),
            2,
        )


def draw_menu_background():
    screen.fill((5, 3, 9))

    for i in range(0, WIDTH, 34):
        pygame.draw.line(
            screen,
            (32, 7, 45),
            (i, 0),
            (WIDTH - i // 2, HEIGHT),
            1,
        )
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
        pygame.draw.rect(
            screen,
            (255, 200, 30),
            rect.inflate(14, 14),
            3,
            border_radius=4,
        )
        pygame.draw.rect(
            screen,
            (95, 52, 8),
            rect.inflate(8, 8),
            2,
            border_radius=4,
        )

    draw_gold_frame(rect, 3)
    inner = rect.inflate(-10, -10)
    fill = (45, 13, 52) if selected else (18, 14, 28)
    pygame.draw.rect(screen, fill, inner, border_radius=3)

    if selected:
        pygame.draw.polygon(
            screen,
            YELLOW,
            [
                (rect.left + 18, rect.centery),
                (rect.left + 31, rect.centery - 10),
                (rect.left + 31, rect.centery + 10),
            ],
        )

    label_rect = rect.inflate(-54 if selected else -28, -14)
    if selected:
        label_rect.x += 18
    draw_text_in_rect(
        text.upper(),
        label_rect,
        font,
        WHITE if selected else (175, 170, 185),
        min_size=15,
    )


def draw_video_panel(x, y, w, h, title="SWEETIE FOX", show_close=False):
    panel = pygame.Rect(x, y, w, h)
    draw_gold_frame(panel, 3)
    draw_text_in_rect(
        title,
        pygame.Rect(x + 45, y + 8, w - 90, 34),
        font,
        WHITE,
        min_size=14,
    )

    if show_close:
        close = pygame.Rect(panel.right - 36, panel.top + 8, 26, 26)
        pygame.draw.rect(screen, BLACK, close)
        pygame.draw.rect(screen, YELLOW, close, 2)
        draw_small("X", close.x + 7, close.y + 3, WHITE)

    img = load_sweetie_image()
    image_rect = pygame.Rect(x + 5, y + 55, w - 10, h - 115)
    if img:
        fitted = pygame.transform.smoothscale(
            img,
            (image_rect.width, image_rect.height),
        )
        screen.blit(fitted, image_rect.topleft)
    else:
        pygame.draw.rect(screen, (28, 12, 40), image_rect)
        draw_center("Missing sweetie_fox.png", y + 170, False, RED, w - 40)
        draw_center("Put the image in your game folder", y + 215, False, WHITE, w - 40)

    pygame.draw.rect(screen, BLACK, (x + 5, y + h - 58, w - 10, 53))
    draw_small(
        "SBR EP 2 Gyro Teaches Johnny How To Roll Balls",
        x + 20,
        y + h - 47,
        WHITE,
        w - 115,
    )
    draw_small("(Cosplay Sweetie Fox)", x + 20, y + h - 22, WHITE, w - 115)
    draw_small("20:08", x + w - 75, y + h - 35, WHITE)


def draw_secret_image_popup():
    if not sweetie_popup_open:
        return

    draw_video_panel(330, 145, 675, 470, title="SWEETIE FOX", show_close=True)


def draw_showdown_preview(x, y, w, h):
    panel = pygame.Rect(x, y, w, h)
    draw_gold_frame(panel, 3)
    draw_text_in_rect(
        "BATTLE TENDENCY",
        pygame.Rect(x + 20, y + 8, w - 40, 38),
        font,
        WHITE,
        min_size=15,
    )

    arena = pygame.Rect(x + 16, y + 58, w - 32, h - 86)
    pygame.draw.rect(screen, (16, 12, 30), arena)
    pygame.draw.rect(screen, (65, 42, 75), arena, 2)
    pygame.draw.circle(screen, (238, 208, 82), (arena.centerx, arena.y + 55), 42)
    pygame.draw.rect(
        screen,
        (82, 55, 35),
        (arena.x, arena.bottom - 62, arena.width, 62),
    )
    pygame.draw.line(
        screen,
        YELLOW,
        (arena.x, arena.bottom - 62),
        (arena.right, arena.bottom - 62),
        3,
    )

    for i in range(5):
        pillar_x = arena.x + 42 + i * 105
        pygame.draw.polygon(
            screen,
            (42, 35, 65),
            [
                (pillar_x, arena.y + 95),
                (pillar_x + 42, arena.y + 95),
                (pillar_x + 25, arena.bottom - 62),
            ],
        )

    joseph = pygame.Rect(arena.x + 115, arena.bottom - 182, 70, 120)
    caesar = pygame.Rect(arena.right - 185, arena.bottom - 182, 70, 120)
    pygame.draw.circle(screen, CYAN, (joseph.centerx, joseph.y + 35), 42, 2)
    pygame.draw.circle(screen, YELLOW, (caesar.centerx, caesar.y + 35), 42, 2)
    pygame.draw.rect(screen, RED, joseph, border_radius=4)
    pygame.draw.rect(screen, GREEN, caesar, border_radius=4)
    pygame.draw.ellipse(
        screen,
        (235, 190, 150),
        (joseph.x + 16, joseph.y - 24, 38, 38),
    )
    pygame.draw.ellipse(
        screen,
        (235, 190, 150),
        (caesar.x + 16, caesar.y - 24, 38, 38),
    )
    pygame.draw.polygon(
        screen,
        CYAN,
        [
            (joseph.right - 3, joseph.y + 30),
            (joseph.right + 36, joseph.y + 42),
            (joseph.right - 3, joseph.y + 54),
        ],
    )
    pygame.draw.polygon(
        screen,
        YELLOW,
        [
            (caesar.left + 3, caesar.y + 30),
            (caesar.left - 36, caesar.y + 42),
            (caesar.left + 3, caesar.y + 54),
        ],
    )

    versus = big_font.render("VS", True, PINK)
    screen.blit(versus, (arena.centerx - versus.get_width() // 2, arena.centery - 35))
    draw_small("JOSEPH JOESTAR", arena.x + 58, arena.bottom - 42, CYAN, 185)
    draw_small("CAESAR ZEPPELI", arena.right - 220, arena.bottom - 42, YELLOW, 185)


def draw_lobby_side_panel(players=1):
    panel = pygame.Rect(960, 25, 295, 445)
    draw_gold_frame(panel, 3)
    draw_text_in_rect(
        "LOBBY",
        pygame.Rect(990, 42, 235, 42),
        font,
        YELLOW,
        align="left",
        min_size=16,
    )
    pygame.draw.line(screen, (185, 130, 25), (990, 95), (1228, 95), 2)
    draw_text_in_rect(
        "STATUS: WAITING",
        pygame.Rect(990, 112, 238, 28),
        small_font,
        WHITE,
        align="left",
        min_size=11,
    )
    draw_text_in_rect(
        f"PLAYERS: {players} / 2",
        pygame.Rect(990, 147, 238, 28),
        small_font,
        WHITE,
        align="left",
        min_size=11,
    )
    draw_text_in_rect(
        "HOST: YOU",
        pygame.Rect(990, 182, 238, 28),
        small_font,
        WHITE,
        align="left",
        min_size=11,
    )
    draw_text_in_rect(
        f"PORT: {PORT}",
        pygame.Rect(990, 217, 238, 28),
        small_font,
        WHITE,
        align="left",
        min_size=11,
    )

    p1 = pygame.Rect(980, 262, 255, 90)
    pygame.draw.rect(screen, (70, 10, 13), p1, border_radius=3)
    pygame.draw.rect(screen, RED, p1, 2, border_radius=3)
    draw_text_in_rect(
        "PLAYER 1",
        pygame.Rect(995, 278, 150, 32),
        font,
        RED,
        align="left",
        min_size=14,
    )
    draw_text_in_rect(
        "YOU",
        pygame.Rect(995, 322, 150, 24),
        small_font,
        WHITE,
        align="left",
        min_size=11,
    )
    pygame.draw.rect(screen, RED, (1170, 292, 32, 48), border_radius=4)
    pygame.draw.circle(screen, (235, 190, 150), (1186, 284), 15)

    p2 = pygame.Rect(980, 372, 255, 72)
    p2_color = GREEN if players >= 2 else GRAY
    pygame.draw.rect(screen, (18, 18, 24), p2, border_radius=3)
    pygame.draw.rect(screen, p2_color, p2, 2, border_radius=3)
    draw_text_in_rect(
        "PLAYER 2",
        pygame.Rect(995, 384, 165, 30),
        font,
        p2_color,
        align="left",
        min_size=14,
    )
    draw_text_in_rect(
        "READY" if players >= 2 else "WAITING",
        pygame.Rect(995, 420, 165, 24),
        small_font,
        BLUE,
        align="left",
        min_size=11,
    )


def draw_character_card(character_key, rect, selected=False, locked=False):
    char = CHARACTERS[character_key]
    fill = (42, 16, 52) if selected else (18, 14, 28)
    if locked:
        fill = (24, 24, 30)
    pygame.draw.rect(screen, fill, rect, border_radius=4)
    pygame.draw.rect(
        screen,
        char["accent"] if not locked else GRAY,
        rect,
        3 if selected else 2,
        border_radius=4,
    )

    body = pygame.Rect(rect.centerx - 22, rect.y + 32, 44, 72)
    if character_key in SPRITE_ANIMATIONS and not locked:
        preview = pygame.Rect(rect.centerx - 45, rect.y + 18, 90, 94)
        draw_character_portrait(character_key, preview)
    else:
        pygame.draw.circle(screen, char["aura"], (body.centerx, body.y + 20), 35, 2)
        pygame.draw.rect(
            screen,
            char["color"] if not locked else GRAY,
            body,
            border_radius=4,
        )
        pygame.draw.ellipse(
            screen,
            (235, 190, 150),
            (body.x + 8, body.y - 22, 28, 28),
        )

    draw_text_in_rect(
        char["name"].upper(),
        pygame.Rect(rect.x + 10, rect.y + 112, rect.width - 20, 26),
        font,
        WHITE if not locked else GRAY,
        min_size=14,
    )
    draw_text_in_rect(
        char["title"],
        pygame.Rect(rect.x + 10, rect.y + 140, rect.width - 20, 24),
        small_font,
        char["accent"] if not locked else GRAY,
        min_size=11,
    )
    if locked:
        draw_text_in_rect(
            "TAKEN",
            pygame.Rect(rect.x + 10, rect.y + 8, rect.width - 20, 24),
            small_font,
            RED,
            min_size=12,
        )


def character_select_screen(title, unavailable=None):
    play_character_select_music()
    unavailable = set(unavailable or [])
    available = [key for key in CHARACTER_ORDER if key not in unavailable]
    selected = 0

    while True:
        clock.tick(FPS)
        handle_secret_image_toggle()
        draw_menu_background()
        draw_center(title, 70, True, YELLOW)
        draw_center("Choose your fighter", 145, False, CYAN)

        for index, key in enumerate(CHARACTER_ORDER):
            row = index // 4
            col = index % 4
            rect = pygame.Rect(90 + col * 285, 215 + row * 195, 235, 165)
            is_locked = key in unavailable
            is_selected = available and key == available[selected]
            draw_character_card(key, rect, is_selected, is_locked)

        draw_center("Left/Right = change    Enter = select    Esc = back", 660, False, GRAY)
        draw_secret_image_popup()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if not available:
                    continue
                if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(available)
                elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(available)
                elif event.key == pygame.K_RETURN:
                    return available[selected]


def difficulty_select_screen():
    play_menu_music()
    selected = 1

    while True:
        clock.tick(FPS)
        handle_secret_image_toggle()
        draw_menu_background()
        draw_center("DIFFICULTY", 88, True, YELLOW)
        draw_center("Choose how badly the AI wants to win", 160, False, CYAN)

        for index, key in enumerate(DIFFICULTY_ORDER):
            data = DIFFICULTIES[key]
            rect = pygame.Rect(405, 235 + index * 88, 470, 62)
            draw_menu_button(data["label"], rect, index == selected)
            desc_rect = pygame.Rect(rect.x + 18, rect.bottom + 2, rect.width - 36, 22)
            draw_text_in_rect(data["description"], desc_rect, small_font, GRAY, min_size=12)

        draw_center("Up/Down = change    Enter = select    Esc = back", 650, False, GRAY)
        draw_secret_image_popup()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                    selected = (selected - 1) % len(DIFFICULTY_ORDER)
                elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
                    selected = (selected + 1) % len(DIFFICULTY_ORDER)
                elif event.key == pygame.K_RETURN:
                    return DIFFICULTY_ORDER[selected]


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


def round_intro(p1_name="Joseph Joestar", p2_name="Wamuu"):
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
            draw_center(f"{p1_name} vs. {p2_name}", 350, False, CYAN)
            pygame.display.flip()
