from .config import logger
from .menus import create_lobby_flow, join_lobby_flow, lobby_menu, intro_screen
from .gameplay import run_singleplayer_game
from .render import message_screen, wait_for_enter


def run_with_error_screen(label, action):
    """Run one game mode and return to the menu if it crashes."""
    try:
        return action()
    except Exception as exc:
        logger.exception("%s crashed", label)
        try:
            message_screen(
                "GAME ERROR",
                [
                    f"{label} crashed.",
                    str(exc),
                    "Press Enter to return to the menu.",
                ],
            )
            wait_for_enter()
        except Exception:
            logger.exception("Could not show crash message screen")
        return "menu"


def main():
    """Run the main game loop and route menu choices to the correct mode."""
    logger.info("JJBA2 The Showdown started")
    intro_screen()
    while True:
        choice = lobby_menu()
        if choice == "singleplayer":
            run_with_error_screen("Singleplayer", run_singleplayer_game)
        elif choice == "host":
            run_with_error_screen("Host lobby", create_lobby_flow)
        elif choice == "join":
            run_with_error_screen("Join lobby", join_lobby_flow)
