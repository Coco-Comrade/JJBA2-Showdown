"""Gameplay loops for combat, singleplayer, and LAN matches."""

import random
import time

import pygame

from .ai_names import generate_ai_player_names
from .config import *
from .data import *
from .fighter import Fighter
from .input_state import empty_input, get_local_input
from .render import (
    character_select_screen,
    difficulty_select_screen,
    draw_center,
    draw_match,
    message_screen,
    round_intro,
    stop_menu_music,
    wait_for_enter,
)

def handle_combat(attacker, defender):
    """Check whether one fighter's active attack hits the other fighter."""
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


def make_state(p1, p2, winner, disconnected=False, player_names=None):
    """Build the full match-state dictionary used by rendering and networking."""
    return {
        "players": {
            "0": p1.to_dict(),
            "1": p2.to_dict(),
        },
        "player_names": player_names or {"0": "PLAYER 1", "1": "PLAYER 2"},
        "winner": winner,
        "disconnected": disconnected,
    }


def step_fight(p1, p2, input1, input2, winner):
    """Run one authoritative frame of fighting logic and return the winner."""
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


def make_ai_input(ai, player, frame_count, difficulty_key="hard"):
    """Create a CPU input snapshot based on distance, danger, and difficulty."""
    inp = empty_input()
    difficulty = DIFFICULTIES.get(difficulty_key, DIFFICULTIES["hard"])
    distance = player.rect.centerx - ai.rect.centerx
    abs_distance = abs(distance)

    if ai.hit_stun > 0:
        return inp

    attack_box = player.get_attack_box()
    danger_close = player.attacking and abs_distance < difficulty["block_range"]

    if danger_close and ai.on_ground and frame_count % difficulty["block_chance_mod"] == 0:
        inp["block"] = True

    if abs_distance > difficulty["approach"]:
        if distance > 0:
            inp["right"] = True
        else:
            inp["left"] = True
    elif abs_distance < difficulty["retreat"] and not ai.attacking:
        if distance > 0:
            inp["left"] = True
        else:
            inp["right"] = True

    if attack_box and attack_box.colliderect(ai.rect.inflate(70, 30)) and ai.on_ground and frame_count % difficulty["block_chance_mod"] == 0:
        inp["block"] = True

    if 45 <= abs_distance <= 170 and not ai.attacking:
        if abs_distance > 118 and frame_count % difficulty["heavy_rate"] in (0, 1):
            inp["heavy"] = True
        elif abs_distance > 82 and frame_count % difficulty["medium_rate"] in (0, 1):
            inp["medium"] = True
        elif frame_count % difficulty["light_rate"] in (0, 1, 2):
            inp["light"] = True

    if player.hp <= 35 and abs_distance < 190 and not ai.attacking and frame_count % max(8, difficulty["heavy_rate"] // 2) in (0, 1):
        inp["heavy"] = True

    if frame_count % difficulty["jump_rate"] == 0 and ai.on_ground and abs_distance < 300:
        inp["jump"] = True

    return inp


def run_game_server(server):
    """Run the host's authoritative LAN match loop and broadcast state updates."""
    p1_key, p2_key = server.get_characters()
    player_names = server.get_player_names()
    logger.info("Starting LAN match: %s vs %s", p1_key, p2_key)
    p1 = Fighter(200, 300, p1_key, True)
    p2 = Fighter(900, 300, p2_key, False)
    winner = None
    frame_duration = 1 / FPS
    send_duration = 1 / NET_FPS
    next_frame_time = time.perf_counter()
    next_send_time = next_frame_time
    server.broadcast_state(make_state(p1, p2, winner, player_names=player_names))

    while server.running:
        now = time.perf_counter()
        if now < next_frame_time:
            time.sleep(next_frame_time - now)
        next_frame_time += frame_duration

        if time.perf_counter() - next_frame_time > frame_duration:
            next_frame_time = time.perf_counter()

        inputs = server.get_inputs()

        if inputs[0].get("menu") or inputs[1].get("menu"):
            server.broadcast_state(
                make_state(p1, p2, winner, disconnected=True, player_names=player_names)
            )
            logger.info("LAN match ended by menu input")
            return "menu"

        if server.player_count() < 2:
            server.broadcast_state(
                make_state(p1, p2, winner, disconnected=True, player_names=player_names)
            )
            logger.info("LAN match ended because a player disconnected")
            return "menu"

        winner = step_fight(p1, p2, inputs[0], inputs[1], winner)

        now = time.perf_counter()
        if now >= next_send_time:
            server.broadcast_state(make_state(p1, p2, winner, player_names=player_names))
            next_send_time = now + send_duration

    return "menu"


def run_singleplayer_game():
    """Run a local singleplayer match against the rule-based CPU fighter."""
    player_key = character_select_screen("SINGLE PLAYER SELECT")
    if not player_key:
        return "menu"
    difficulty_key = difficulty_select_screen()
    if not difficulty_key:
        return "menu"
    ai_key = random.choice([key for key in CHARACTER_ORDER if key != player_key])
    logger.info(
        "Starting singleplayer match: %s vs %s on %s",
        player_key,
        ai_key,
        difficulty_key,
    )
    message_screen("PREPARING MATCH", ["Generating fighter names..."])
    player_names = generate_ai_player_names()
    stop_menu_music()
    if not round_intro(CHARACTERS[player_key]["name"], CHARACTERS[ai_key]["name"]):
        return "menu"
    player = Fighter(200, 300, player_key, True)
    ai = Fighter(900, 300, ai_key, False)
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
            logger.info("Singleplayer match exited to menu")
            return "menu"

        ai_input = make_ai_input(ai, player, frame_count, difficulty_key)
        winner = step_fight(player, ai, player_input, ai_input, winner)

        state = make_state(player, ai, winner, player_names=player_names)
        draw_match(state, 0)

        if winner is not None:
            if winner == 0:
                draw_center("YOU WIN!", 430, True, YELLOW)
            else:
                draw_center(f"{CHARACTERS[ai_key]['name'].upper()} WINS!", 430, True, YELLOW)

        draw_center(
            f"Single Player: {CHARACTERS[player_key]['name']} vs. {CHARACTERS[ai_key]['name']} - {DIFFICULTIES[difficulty_key]['label']}",
            675,
            False,
            GRAY,
        )
        pygame.display.flip()


# =========================
# CLIENT LOOP
# =========================
def run_client_game(client):
    """Run the local client loop that sends input and draws server state."""
    logger.info("Starting client game loop")
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
        except Exception as exc:
            logger.warning("Could not send input: %s", exc)
            message_screen(
                "CONNECTION LOST",
                [str(exc), "Press Enter to return to the menu"],
            )
            wait_for_enter()
            return "menu"

        if inp["menu"]:
            logger.info("Client returned to menu")
            return "menu"

        state = client.get_state()
        if state:
            last_state_time = time.time()
            draw_match(state, client.player_id)
            if state.get("disconnected") and inp["menu"]:
                return "menu"
        else:
            message_screen("WAITING FOR BATTLE DATA", ["The server is warming up the arena..."])

        if client.error:
            if state and state.get("disconnected"):
                draw_center("Press Esc to return to the menu", 390, False, WHITE)
            else:
                message_screen(
                    "CONNECTION LOST",
                    [str(client.error), "Press Enter to return to the menu"],
                )
                wait_for_enter()
                return "menu"

        if time.time() - last_state_time > 3:
            draw_center("Network delay...", 610, False, YELLOW)

        pygame.display.flip()

