"""Menu screens and lobby flows that connect UI choices to game modes."""

import threading

import pygame

from .ai_names import generate_ai_player_names
from .client import GameClient
from .config import *
from .data import *
from .gameplay import run_client_game, run_game_server, run_singleplayer_game
from .protocol import get_local_ip
from .render import *
from .server import LobbyServer

def lobby_menu():
    """Show the main menu and return the selected game mode."""
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
    """Display the controls page until the player presses Enter or Esc."""
    lines = [
        "Move: A/D or Left/Right",
        "Jump: W, Up, or Space",
        "Block: S, Down, or Shift",
        "Ripple Jab: J, U, or Numpad 1",
        "Bubble Cutter: K, I, or Numpad 2",
        "Sunlight Overdrive: L, O, or Numpad 3",
        "Restart after KO: R",
        "Menu: Esc",
        "",
        "Jumps have a short buffer and coyote time.",
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
    """Host a LAN lobby, wait for Player 2, then start the network match."""
    play_menu_music()
    host_character = character_select_screen("PLAYER 1 SELECT")
    if not host_character:
        return
    lan_password = password_input_screen("CREATE LAN PASSWORD", show_password=True)
    if not lan_password:
        return
    play_menu_music()
    message_screen("CREATING LOBBY", ["Generating player names..."])
    player_names = generate_ai_player_names()
    logger.info(
        "Creating lobby as %s with AI names %s vs %s",
        host_character,
        player_names.get("0", "PLAYER 1"),
        player_names.get("1", "PLAYER 2"),
    )

    server = LobbyServer(host_character, player_names, lan_password)
    try:
        server.start()
    except Exception as exc:
        logger.exception("Could not start lobby server")
        message_screen(
            "SERVER ERROR",
            [
                str(exc),
                "Maybe port 5555 is already being used.",
                "Press ENTER",
            ],
        )
        wait_for_enter()
        return

    local_ip = get_local_ip()
    client = GameClient()

    try:
        client.connect("127.0.0.1", lan_password)
    except Exception as exc:
        logger.exception("Host client could not connect to local server")
        server.stop()
        message_screen("HOST ERROR", [str(exc), "Press ENTER"])
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
                logger.info("Host cancelled lobby")
                server.stop()
                client.close()
                return

        handle_secret_image_toggle()
        draw_menu_background()
        draw_center("LOBBY CREATED", 130, True, YELLOW)
        draw_center("Have Player 2 join using this IP:", 238)
        draw_center(local_ip, 298, True, WHITE)
        draw_center("Encrypted UDP lobby", 390, False, CYAN)
        status = "Ready to fight" if server.characters_ready() else "Waiting for Player 2 choice"
        draw_center(f"Players Connected: {server.player_count()} / 2", 445)
        draw_center(status, 492, False, CYAN)
        draw_center("Esc = cancel lobby", 585, False, GRAY)
        draw_lobby_side_panel(server.player_count(), player_names)
        draw_secret_image_popup()
        pygame.display.flip()

        if server.player_count() >= 2 and server.characters_ready():
            waiting = False

    def server_game_thread():
        """Run the authoritative server match loop in the background."""
        run_game_server(server)

    stop_menu_music()
    p1_key, p2_key = server.get_characters()
    if not round_intro(CHARACTERS[p1_key]["name"], CHARACTERS[p2_key]["name"]):
        server.stop()
        client.close()
        return
    threading.Thread(target=server_game_thread, daemon=True).start()
    run_client_game(client)
    server.stop()
    client.close()


def join_lobby_flow():
    """Join another player's LAN lobby, choose a character, and play as client."""
    play_menu_music()
    host_ip = text_input_screen("JOIN LOBBY")
    if not host_ip:
        return
    lan_password = password_input_screen("ENTER LAN PASSWORD")
    if not lan_password:
        return

    client = GameClient()
    try:
        message_screen("CONNECTING", [f"Trying {host_ip}:{PORT}..."])
        client.connect(host_ip, lan_password)
    except Exception as exc:
        logger.exception("Could not join lobby at %s", host_ip)
        message_screen(
            "JOIN FAILED",
            [
                str(exc),
                "Make sure both devices are on the same Wi-Fi network.",
                "Press Enter",
            ],
        )
        wait_for_enter()
        return

    taken = [value for value in client.selections.values() if value]
    character_key = character_select_screen("PLAYER 2 SELECT", taken)
    if not character_key:
        client.close()
        return
    play_menu_music()
    try:
        client.select_character(character_key)
    except Exception as exc:
        logger.exception("Could not send character selection")
        message_screen("SELECT FAILED", [str(exc), "Press Enter"])
        wait_for_enter()
        client.close()
        return

    stop_menu_music()
    run_client_game(client)
    client.close()
