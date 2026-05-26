from .config import *

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
    "kars": {
        "name": "Kars",
        "title": "Pillar Genius",
        "color": (185, 40, 210),
        "accent": (120, 245, 255),
        "aura": (210, 80, 255),
        "speed": 6,
        "jump": -21,
    },
    "stroheim": {
        "name": "Stroheim",
        "title": "Cyborg Soldier",
        "color": (105, 165, 195),
        "accent": (245, 245, 245),
        "aura": (160, 220, 255),
        "speed": 5,
        "jump": -18,
    },
}
CHARACTER_ORDER = ("joseph", "caesar", "lisa", "wamuu", "kars", "stroheim")

SPRITE_ANIMATIONS = {
    "joseph": {
        "folder": "joseph8",
        "idle": 4,
        "walk": 4,
        "jump": 1,
        "block": 2,
        "light": 3,
        "medium": 3,
        "heavy": 3,
        "hit": 2,
        "ko": 3,
        "height": 152,
    }
}
sprite_cache = {}

DIFFICULTIES = {
    "easy": {
        "label": "Easy",
        "description": "Slower reactions, fewer blocks",
        "approach": 125,
        "retreat": 36,
        "block_range": 110,
        "block_chance_mod": 4,
        "light_rate": 30,
        "medium_rate": 48,
        "heavy_rate": 85,
        "jump_rate": 210,
    },
    "normal": {
        "label": "Normal",
        "description": "Balanced arcade pressure",
        "approach": 110,
        "retreat": 40,
        "block_range": 140,
        "block_chance_mod": 3,
        "light_rate": 20,
        "medium_rate": 34,
        "heavy_rate": 60,
        "jump_rate": 150,
    },
    "hard": {
        "label": "Hard",
        "description": "Fast pressure and smarter blocks",
        "approach": 88,
        "retreat": 34,
        "block_range": 175,
        "block_chance_mod": 2,
        "light_rate": 12,
        "medium_rate": 18,
        "heavy_rate": 26,
        "jump_rate": 95,
    },
    "ultimate": {
        "label": "Ultimate",
        "description": "Very mean. Very JoJo.",
        "approach": 76,
        "retreat": 28,
        "block_range": 210,
        "block_chance_mod": 1,
        "light_rate": 8,
        "medium_rate": 13,
        "heavy_rate": 18,
        "jump_rate": 70,
    },
}
DIFFICULTY_ORDER = ("easy", "normal", "hard", "ultimate")

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
