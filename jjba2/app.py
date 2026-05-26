from .config import logger
from .menus import create_lobby_flow, join_lobby_flow, lobby_menu, intro_screen
from .gameplay import run_singleplayer_game


def main():
    logger.info("JJBA2 The Showdown started")
    intro_screen()
    while True:
        choice = lobby_menu()
        if choice == "singleplayer":
            run_singleplayer_game()
        elif choice == "host":
            create_lobby_flow()
        elif choice == "join":
            join_lobby_flow()
