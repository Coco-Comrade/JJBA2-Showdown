import json
import socket
import struct

from .config import *

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


def send_json(sock, data):
    payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
    header = struct.pack("!I", len(payload))
    sock.sendall(header + payload)


def tune_socket(sock):
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception as exc:
        logger.debug("Could not set TCP_NODELAY: %s", exc)


def recv_exact(sock, byte_count):
    data = b""
    while len(data) < byte_count:
        chunk = sock.recv(byte_count - len(data))
        if not chunk:
            raise ConnectionError("Disconnected")
        data += chunk
    return data


def recv_json(sock):
    header = recv_exact(sock, MESSAGE_HEADER_BYTES)
    message_length = struct.unpack("!I", header)[0]
    if message_length > MAX_MESSAGE_BYTES:
        raise ConnectionError(f"Message too large: {message_length} bytes")

    payload = recv_exact(sock, message_length)
    return json.loads(payload.decode("utf-8"))
