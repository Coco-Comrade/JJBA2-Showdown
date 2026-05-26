import pygame

from .config import *
from .data import *

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
        self.jump_buffer = 0
        self.coyote_timer = 0
        self.last_dx = 0

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
        self.jump_buffer = 0
        self.coyote_timer = 0
        self.last_dx = 0

    def face_opponent(self, opponent):
        if self.attacking or self.hit_stun > 0:
            return
        self.facing_right = self.rect.centerx <= opponent.rect.centerx

    def move_from_input(self, inp):
        if self.hp <= 0:
            self.remember_attack_buttons(inp)
            return

        if inp["jump"]:
            self.jump_buffer = JUMP_BUFFER_FRAMES
        elif self.jump_buffer > 0:
            self.jump_buffer -= 1

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
        self.last_dx = dx

        can_jump = (self.on_ground or self.coyote_timer > 0) and not self.attacking
        if self.jump_buffer > 0 and can_jump:
            self.vel_y = self.jump_power
            self.on_ground = False
            self.coyote_timer = 0
            self.jump_buffer = 0

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
            self.coyote_timer = COYOTE_FRAMES
        else:
            if self.on_ground:
                self.coyote_timer = COYOTE_FRAMES
            elif self.coyote_timer > 0:
                self.coyote_timer -= 1
            self.on_ground = False

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
            return pygame.Rect(
                self.rect.right,
                self.rect.y + data["y_offset"],
                data["range"],
                data["height"],
            )
        return pygame.Rect(
            self.rect.left - data["range"],
            self.rect.y + data["y_offset"],
            data["range"],
            data["height"],
        )

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
            "on_ground": self.on_ground,
            "last_dx": self.last_dx,
        }
