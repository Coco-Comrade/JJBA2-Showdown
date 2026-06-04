import pygame

def empty_input():
    """Create a blank input snapshot where every game action is released."""
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
    """Read the keyboard and convert pressed keys into the game's input format."""
    keys = pygame.key.get_pressed()
    inp = empty_input()
    inp["left"] = keys[pygame.K_a] or keys[pygame.K_LEFT]
    inp["right"] = keys[pygame.K_d] or keys[pygame.K_RIGHT]
    inp["jump"] = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]
    inp["block"] = keys[pygame.K_s] or keys[pygame.K_DOWN] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
    inp["light"] = keys[pygame.K_j] or keys[pygame.K_u] or keys[pygame.K_KP1]
    inp["medium"] = keys[pygame.K_k] or keys[pygame.K_i] or keys[pygame.K_KP2]
    inp["heavy"] = keys[pygame.K_l] or keys[pygame.K_o] or keys[pygame.K_KP3]
    inp["restart"] = keys[pygame.K_r]
    inp["menu"] = keys[pygame.K_ESCAPE]
