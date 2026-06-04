"""Handle the LAN socket protocol: length header plus pickled dictionaries."""

import pickle
import socket

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


def send_message(sock, data):
    """Send one dictionary as length#pickle_payload over a TCP socket."""
    if not isinstance(data, dict):
        raise TypeError("Protocol messages must be dictionaries")
    payload = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    header = str(len(payload)).encode("ascii") + MESSAGE_LENGTH_SEPARATOR
    sock.sendall(header + payload)


def tune_socket(sock):
    """Try to reduce input delay by disabling Nagle's algorithm on the socket."""
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception as exc:
        logger.debug("Could not set TCP_NODELAY: %s", exc)


def recv_exact(sock, byte_count):
    """Read exactly byte_count bytes or raise an error if the socket closes."""
    data = b""
    while len(data) < byte_count:
        chunk = sock.recv(byte_count - len(data))
        if not chunk:
            raise ConnectionError("Disconnected")
        data += chunk
    return data


def recv_message(sock):
    """Receive one length-prefixed pickle message and return its dictionary."""
    header = b""
    while MESSAGE_LENGTH_SEPARATOR not in header:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("Disconnected")
        header += chunk
        if len(header) > 12:
            raise ConnectionError("Message length header is too long")

    length_text = header[:-len(MESSAGE_LENGTH_SEPARATOR)].decode("ascii")
    if not length_text.isdigit():
        raise ConnectionError(f"Bad message length header: {length_text!r}")

    message_length = int(length_text)
    if message_length <= 0:
        raise ConnectionError(f"Bad message length: {message_length}")
    if message_length > MAX_MESSAGE_BYTES:
        raise ConnectionError(f"Message too large: {message_length} bytes")

    payload = recv_exact(sock, message_length)
    message = pickle.loads(payload)
    if not isinstance(message, dict):
        raise ConnectionError("Protocol message must be a dictionary")
    return message
