"""Host-side LAN lobby and authoritative match server code."""

import socket
import threading

from .config import *
from .data import *
from .input_state import empty_input
from .protocol import recv_message, send_message, tune_socket

class LobbyServer:
    """Accept two clients, store their inputs, and broadcast server state."""

    def __init__(self, host_character="joseph", player_names=None):
        """Create a lobby server with the host character already selected."""
        self.host = "0.0.0.0"
        self.port = PORT
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.inputs = {0: empty_input(), 1: empty_input()}
        self.selections = {0: host_character, 1: None}
        self.player_names = player_names or {"0": "PLAYER 1", "1": "PLAYER 2"}
        self.lock = threading.Lock()
        self.running = True
        self.started = False
        self.thread = None

    def start(self):
        """Bind the TCP socket, listen for players, and start accepting clients."""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(2)
        self.thread = threading.Thread(target=self.accept_loop, daemon=True)
        self.thread.start()
        logger.info("Lobby server started on %s:%s", self.host, self.port)

    def accept_loop(self):
        """Accept incoming clients and assign them Player 1 or Player 2."""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                tune_socket(conn)
                logger.info("Incoming lobby connection from %s:%s", *addr)

                with self.lock:
                    if len(self.clients) >= 2:
                        send_message(conn, {"type": "full"})
                        conn.close()
                        logger.info("Rejected connection because lobby is full")
                        continue

                    player_id = 0 if 0 not in self.clients else 1
                    self.clients[player_id] = conn
                    self.started = len(self.clients) == 2
                    logger.info("Assigned client to player %s", player_id + 1)

                send_message(
                    conn,
                    {
                        "type": "welcome",
                        "player_id": player_id,
                        "selections": self.selections,
                        "player_names": self.player_names,
                    },
                )

                thread = threading.Thread(
                    target=self.client_loop,
                    args=(conn, player_id),
                    daemon=True,
                )
                thread.start()

            except Exception as exc:
                if self.running:
                    logger.exception("Server accept loop stopped unexpectedly: %s", exc)
                break

    def client_loop(self, conn, player_id):
        """Receive one player's select/input messages until they disconnect."""
        while self.running:
            try:
                data = recv_message(conn)
                if data.get("type") == "input":
                    with self.lock:
                        self.inputs[player_id] = data["input"]
                elif data.get("type") == "select":
                    character_key = data.get("character")
                    with self.lock:
                        taken = [
                            value
                            for pid, value in self.selections.items()
                            if pid != player_id
                        ]
                        if character_key in CHARACTERS and character_key not in taken:
                            self.selections[player_id] = character_key
                            logger.info(
                                "Player %s selected %s",
                                player_id + 1,
                                character_key,
                            )
                        else:
                            logger.warning(
                                "Rejected character selection from player %s: %s",
                                player_id + 1,
                                character_key,
                            )
            except Exception as exc:
                logger.info("Player %s disconnected: %s", player_id + 1, exc)
                with self.lock:
                    if player_id in self.clients:
                        del self.clients[player_id]
                    self.inputs[player_id] = empty_input()
                    self.started = False
                break

    def get_inputs(self):
        """Return a thread-safe copy of the latest input for both players."""
        with self.lock:
            return {pid: dict(inp) for pid, inp in self.inputs.items()}

    def broadcast_state(self, state):
        """Send the official match state to every connected client."""
        with self.lock:
            client_items = list(self.clients.items())

        dead = []
        for pid, conn in client_items:
            try:
                send_message(conn, {"type": "state", "state": state})
            except Exception as exc:
                logger.info("Dropping player %s after send failure: %s", pid + 1, exc)
                dead.append(pid)

        if dead:
            with self.lock:
                for pid in dead:
                    if pid in self.clients:
                        del self.clients[pid]
                    self.inputs[pid] = empty_input()
                self.started = len(self.clients) == 2

    def player_count(self):
        """Return how many clients are currently connected to the lobby."""
        with self.lock:
            return len(self.clients)

    def characters_ready(self):
        """Return True when both player slots have selected a character."""
        with self.lock:
            return all(self.selections.get(pid) for pid in (0, 1))

    def get_characters(self):
        """Return the two selected characters, fixing duplicates if needed."""
        with self.lock:
            p1 = self.selections.get(0) or "joseph"
            p2 = self.selections.get(1) or "caesar"
        if p1 == p2:
            p2 = next(key for key in CHARACTER_ORDER if key != p1)
        return p1, p2

    def get_player_names(self):
        """Return a thread-safe copy of the generated player display names."""
        with self.lock:
            return dict(self.player_names)

    def stop(self):
        """Stop the server socket and close all active client connections."""
        self.running = False
        logger.info("Stopping lobby server")
        try:
            self.server_socket.close()
        except Exception as exc:
            logger.debug("Server socket close failed: %s", exc)
        with self.lock:
            for conn in self.clients.values():
                try:
                    conn.close()
                except Exception as exc:
                    logger.debug("Client socket close failed: %s", exc)
            self.clients.clear()
