"""Client-side LAN connection code for joining or hosting a match."""

import json
import socket
import threading
import time

from .config import *
from .protocol import recv_message, send_message, tune_socket

class GameClient:
    """Connect to a lobby, send local input, and receive server state."""

    def __init__(self):
        """Create an unconnected game client with empty network state."""
        self.sock = None
        self.player_id = None
        self.latest_state = None
        self.error = None
        self.running = False
        self.receiver_thread = None
        self.lock = threading.Lock()
        self.last_sent_input = None
        self.last_input_send_time = 0
        self.selections = {0: None, 1: None}
        self.player_names = {"0": "PLAYER 1", "1": "PLAYER 2"}

    def connect(self, host_ip):
        """Connect to a lobby server and return the assigned player id."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tune_socket(self.sock)
            self.sock.settimeout(8)
            logger.info("Connecting to lobby at %s:%s", host_ip, PORT)
            self.sock.connect((host_ip, PORT))
            self.sock.settimeout(None)

            data = recv_message(self.sock)
            if data.get("type") == "full":
                raise ConnectionError("Lobby is full")
            if data.get("type") != "welcome" or "player_id" not in data:
                raise ConnectionError("Bad server response")

            self.player_id = int(data["player_id"])
            if self.player_id not in (0, 1):
                raise ConnectionError("Bad player id from server")

            selections = data.get("selections", {})
            if not isinstance(selections, dict):
                selections = {}
            self.selections = {int(pid): value for pid, value in selections.items()}

            player_names = data.get("player_names", {})
            if not isinstance(player_names, dict):
                player_names = {}
            self.player_names = {str(pid): value for pid, value in player_names.items()} or self.player_names
            self.running = True
            self.receiver_thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.receiver_thread.start()
            logger.info("Connected as player %s", self.player_id + 1)
            return self.player_id
        except Exception:
            self.close()
            raise

    def receive_loop(self):
        """Continuously receive state messages on a background thread."""
        while self.running:
            try:
                data = recv_message(self.sock)
                if data.get("type") == "state":
                    with self.lock:
                        self.latest_state = data["state"]
            except Exception as exc:
                if self.running:
                    self.error = exc
                    logger.info("Client receive loop stopped: %s", exc)
                self.running = False
                break

    def send_input(self, input_data):
        """Send the current input snapshot unless it is an unchanged repeat."""
        now = time.perf_counter()
        if input_data == self.last_sent_input and now - self.last_input_send_time < 0.1:
            return
        send_message(self.sock, {"type": "input", "input": input_data})
        self.last_sent_input = dict(input_data)
        self.last_input_send_time = now

    def select_character(self, character_key):
        """Tell the server which character this client chose in the lobby."""
        send_message(self.sock, {"type": "select", "character": character_key})
        self.selections[self.player_id] = character_key
        logger.info("Sent character selection: %s", character_key)

    def get_state(self):
        """Return a safe copy of the newest authoritative state from the server."""
        with self.lock:
            return json.loads(json.dumps(self.latest_state)) if self.latest_state else None

    def close(self):
        """Shut down and close the client socket."""
        self.running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception as exc:
                logger.debug("Client socket shutdown skipped: %s", exc)
            try:
                self.sock.close()
            except Exception as exc:
                logger.debug("Client socket close skipped: %s", exc)
            self.sock = None
