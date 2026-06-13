"""Handle the encrypted raw UDP LAN protocol for dictionary messages."""

import hashlib
import hmac
import pickle
import secrets
import socket

from .config import *

PROTOCOL_MAGIC = b"JJBA2UDP1"
NONCE_BYTES = 16
TAG_BYTES = 32
KEY_SALT = b"jjba2-showdown-lan-v1"
KEY_ROUNDS = 100_000


def get_local_ip():
    """Return the best LAN IP to show other players."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        logger.info("Detected LAN IP: %s", ip)
        return ip
    except Exception as exc:
        logger.debug("UDP LAN IP detection failed: %s", exc)
        try:
            ip = socket.gethostbyname(socket.gethostname())
            logger.info("Detected hostname IP: %s", ip)
            return ip
        except Exception as fallback_exc:
            logger.warning("Falling back to localhost IP: %s", fallback_exc)
            return "127.0.0.1"
    finally:
        if s:
            s.close()


def derive_lan_key(password):
    """Turn the lobby password into a fixed-size encryption/authentication key."""
    if not isinstance(password, str) or not password.strip():
        raise ValueError("A LAN password is required")
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.strip().encode("utf-8"),
        KEY_SALT,
        KEY_ROUNDS,
        dklen=32,
    )


def make_keystream(key, nonce, byte_count):
    """Build a SHA-256 byte stream used to hide the pickle payload."""
    output = bytearray()
    counter = 0
    while len(output) < byte_count:
        output.extend(
            hashlib.sha256(
                key + b"stream" + nonce + counter.to_bytes(4, "big")
            ).digest()
        )
        counter += 1
    return bytes(output[:byte_count])


def xor_bytes(left, right):
    """XOR two byte strings of equal length."""
    return bytes(a ^ b for a, b in zip(left, right))


def pack_message(data, key):
    """Serialize, encrypt, and authenticate one protocol dictionary."""
    if not isinstance(data, dict):
        raise TypeError("Protocol messages must be dictionaries")

    payload = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ConnectionError(f"Message too large: {len(payload)} bytes")

    nonce = secrets.token_bytes(NONCE_BYTES)
    ciphertext = xor_bytes(payload, make_keystream(key, nonce, len(payload)))
    tag = hmac.new(key, PROTOCOL_MAGIC + nonce + ciphertext, hashlib.sha256).digest()
    return PROTOCOL_MAGIC + nonce + tag + ciphertext


def unpack_message(packet, key):
    """Verify, decrypt, and unpickle one UDP packet into a dictionary."""
    min_size = len(PROTOCOL_MAGIC) + NONCE_BYTES + TAG_BYTES + 1
    if len(packet) < min_size:
        raise ConnectionError("UDP packet is too short")
    if len(packet) > MAX_MESSAGE_BYTES + min_size:
        raise ConnectionError(f"UDP packet is too large: {len(packet)} bytes")
    if not packet.startswith(PROTOCOL_MAGIC):
        raise ConnectionError("Bad UDP protocol header")

    offset = len(PROTOCOL_MAGIC)
    nonce = packet[offset:offset + NONCE_BYTES]
    offset += NONCE_BYTES
    tag = packet[offset:offset + TAG_BYTES]
    ciphertext = packet[offset + TAG_BYTES:]

    expected = hmac.new(
        key,
        PROTOCOL_MAGIC + nonce + ciphertext,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(tag, expected):
        raise ConnectionError("Bad LAN password or corrupted UDP packet")

    payload = xor_bytes(ciphertext, make_keystream(key, nonce, len(ciphertext)))
    message = pickle.loads(payload)
    if not isinstance(message, dict):
        raise ConnectionError("Protocol message must be a dictionary")
    return message


def send_message(sock, data, addr, key):
    """Send one encrypted dictionary as a raw UDP datagram."""
    sock.sendto(pack_message(data, key), addr)


def recv_message(sock, key):
    """Receive one encrypted UDP datagram and return its dictionary plus address."""
    packet, addr = sock.recvfrom(MAX_MESSAGE_BYTES + 128)
    return unpack_message(packet, key), addr
