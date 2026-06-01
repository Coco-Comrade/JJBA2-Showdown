import logging
import os

import pygame

mixer_init_error = None
pygame.init()
try:
    pygame.mixer.init()
    pygame.mixer.music.set_volume(0.5)
except Exception as exc:
    mixer_init_error = exc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "jjba2_showdown.log")
# Use a local filename like "intro.mp3", or a direct audio-file URL ending in
# .mp3, .ogg, or .wav. Normal web pages/YouTube links will not play in Pygame.
MUSIC_SOURCE = "intro.mp3"
CHARACTER_SELECT_MUSIC_SOURCE = os.path.join(
    "assets", "music", "character_select.wav"
)
SWEETIE_IMAGE_FILE = os.path.join(BASE_DIR, "sweetie_fox.png")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("jjba2_showdown")
if mixer_init_error:
    logger.warning("Pygame mixer did not initialize: %s", mixer_init_error)

WIDTH = 1280
HEIGHT = 720
FPS = 60
NET_FPS = 30
GRAVITY = 1
GROUND_Y = 580
PORT = 5555
MESSAGE_LENGTH_SEPARATOR = b"#"
MAX_MESSAGE_BYTES = 1_000_000
JUMP_BUFFER_FRAMES = 7
COYOTE_FRAMES = 6

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
