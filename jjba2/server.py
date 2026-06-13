"""Host-side UDP lobby and authoritative match server code."""

import socket
import threading
import time

from .config import *
from .data import *
from .input_state import empty_input, normalize_input
from .protocol import derive_lan_key, recv_message, send_message


class LobbyServer:
    """Track two UDP clients, store their inputs, and broadcast server state."""

    def __init__(self, host_character="joseph", player_names=None, password=""):
        """Create a UDP lobby server with the host character already selected."""
        self.host = "0.0.0.0"
        self.port = PORT
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.addr_to_player = {}
        self.last_seen = {}
        self.inputs = {0: empty_input(), 1: empty_input()}
        self.selections = {0: host_character, 1: None}
        self.player_names = player_names or {"0": "PLAYER 1", "1": "PLAYER 2"}
        self.crypto_key = derive_lan_key(password)
        self.lock = threading.Lock()
        self.running = True
        self.started = False
        self.thread = None

    def start(self):
        """Bind the UDP socket and start receiving lobby/game datagrams."""
        self.server_socket.bind((self.host, self.port))
        self.thread = threading.Thread(target=self.accept_loop, daemon=True)
        self.thread.start()
        logger.info("UDP lobby server started on %s:%s", self.host, self.port)

    def accept_loop(self):
        """Receive UDP packets, assign players, and process player messages."""
        while self.running:
            try:
                data, addr = recv_message(self.server_socket, self.crypto_key)
                self.cleanup_stale_clients()
                if addr not in self.addr_to_player:
                    self.register_client(addr, data)
                    continue

                player_id = self.addr_to_player[addr]
                with self.lock:
                    self.last_seen[player_id] = time.time()
                self.handle_client_message(player_id, data)
            except Exception as exc:
                if self.running:
                    logger.info("Ignored bad UDP packet: %s", exc)

    def register_client(self, addr, data):
        """Assign a new UDP address to an open player slot after a join packet."""
        if data.get("type") != "join":
            logger.warning("Ignoring first packet without join from %s:%s", *addr)
            return

        with self.lock:
            if len(self.clients) >= 2:
                is_full = True
                player_id = None
                selections = {}
                player_names = {}
            else:
                is_full = False
                player_id = 0 if 0 not in self.clients else 1
                self.clients[player_id] = addr
                self.addr_to_player[addr] = player_id
                self.last_seen[player_id] = time.time()
                self.started = len(self.clients) == 2
                selections = dict(self.selections)
                player_names = dict(self.player_names)

        if is_full:
            send_message(self.server_socket, {"type": "full"}, addr, self.crypto_key)
            logger.info("Rejected UDP join from %s:%s because lobby is full", *addr)
            return

        send_message(
            self.server_socket,
            {
                "type": "welcome",
                "player_id": player_id,
                "selections": selections,
                "player_names": player_names,
            },
            addr,
            self.crypto_key,
        )
        logger.info("Assigned UDP client %s:%s to player %s", *addr, player_id + 1)

    def handle_client_message(self, player_id, data):
        """Apply one validated UDP message from an already registered client."""
        if data.get("type") == "join":
            with self.lock:
                addr = self.clients.get(player_id)
                selections = dict(self.selections)
                player_names = dict(self.player_names)
            if addr:
                send_message(
                    self.server_socket,
                    {
                        "type": "welcome",
                        "player_id": player_id,
                        "selections": selections,
                        "player_names": player_names,
                    },
                    addr,
                    self.crypto_key,
                )
            return

        if data.get("type") == "input":
            with self.lock:
                self.inputs[player_id] = normalize_input(data.get("input"))
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

    def cleanup_stale_clients(self):
        """Remove UDP clients that stopped sending packets for too long."""
        now = time.time()
        stale = []
        with self.lock:
            for player_id, seen_at in list(self.last_seen.items()):
                if now - seen_at > UDP_CLIENT_TIMEOUT:
                    stale.append(player_id)
            for player_id in stale:
                self.drop_player_locked(player_id)
        for player_id in stale:
            logger.info("Player %s timed out", player_id + 1)

    def drop_player_locked(self, player_id):
        """Remove one player while the server lock is already held."""
        addr = self.clients.pop(player_id, None)
        if addr in self.addr_to_player:
            del self.addr_to_player[addr]
        self.last_seen.pop(player_id, None)
        self.inputs[player_id] = empty_input()
        self.selections[player_id] = None
        self.started = False

    def get_inputs(self):
        """Return a thread-safe copy of the latest input for both players."""
        with self.lock:
            return {pid: dict(inp) for pid, inp in self.inputs.items()}

    def broadcast_state(self, state):
        """Send the official match state to every connected UDP client."""
        self.cleanup_stale_clients()
        with self.lock:
            client_items = list(self.clients.items())

        dead = []
        for pid, addr in client_items:
            try:
                send_message(
                    self.server_socket,
                    {"type": "state", "state": state},
                    addr,
                    self.crypto_key,
                )
            except Exception as exc:
                logger.info("Dropping player %s after send failure: %s", pid + 1, exc)
                dead.append(pid)

        if dead:
            with self.lock:
                for pid in dead:
                    self.drop_player_locked(pid)
                self.started = len(self.clients) == 2

    def player_count(self):
        """Return how many clients are currently connected to the lobby."""
        self.cleanup_stale_clients()
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
        """Stop the UDP server socket and forget all active clients."""
        self.running = False
        logger.info("Stopping UDP lobby server")
        try:
            self.server_socket.close()
        except Exception as exc:
            logger.debug("Server socket close failed: %s", exc)
        with self.lock:
            self.clients.clear()
            self.addr_to_player.clear()
            self.last_seen.clear()
