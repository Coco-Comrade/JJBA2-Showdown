"""Generate JoJo-themed player names with local AI or a safe fallback."""

import json
import os
import random
import urllib.error
import urllib.request

from .config import logger

LOCAL_AI_URL = os.environ.get("JJBA2_LOCAL_AI_URL", "http://localhost:11434/api/generate")
LOCAL_AI_MODEL = os.environ.get("JJBA2_LOCAL_AI_MODEL", "llama3.2")


def _read_local_ai_timeout():
    """Read the local AI timeout safely, even if the environment value is bad."""
    try:
        return max(0.5, float(os.environ.get("JJBA2_LOCAL_AI_TIMEOUT", "3")))
    except ValueError:
        logger.warning("Bad JJBA2_LOCAL_AI_TIMEOUT value; using 3 seconds")
        return 3


LOCAL_AI_TIMEOUT = _read_local_ai_timeout()

FALLBACK_EPITHETS = (
    "Ripple",
    "Hamon",
    "Stardust",
    "Pillar",
    "Golden",
    "Crimson",
    "Sunlight",
    "Overdrive",
    "Bubble",
    "Battle",
    "Rose",
    "Azure",
)

FALLBACK_NOUNS = (
    "Joestar",
    "Zeppeli",
    "Crusader",
    "Tempest",
    "Requiem",
    "Phantom",
    "Vanguard",
    "Striker",
    "Oracle",
    "Comet",
    "Duelist",
    "Emperor",
)


def _fallback_name():
    """Build one dramatic JoJo-style name without calling the local AI server."""
    return f"{random.choice(FALLBACK_EPITHETS)} {random.choice(FALLBACK_NOUNS)}"


def _fallback_player_names():
    """Return two different fallback names for Player 1 and Player 2."""
    first = _fallback_name()
    second = _fallback_name()
    while second == first:
        second = _fallback_name()
    return {"0": first.upper(), "1": second.upper()}


def _clean_name(name):
    """Normalize one generated name so it is uppercase, short, and display-safe."""
    cleaned = "".join(ch for ch in name.upper() if ch.isalnum() or ch in " -'")
    cleaned = " ".join(cleaned.split())
    return cleaned[:24] or None


def _parse_names(text):
    """Extract two usable player names from the local AI response text."""
    text = text.strip()
    try:
        data = json.loads(text)
        names = data.get("names", data) if isinstance(data, dict) else data
        if isinstance(names, list) and len(names) >= 2:
            first = _clean_name(str(names[0]))
            second = _clean_name(str(names[1]))
            if first and second and first != second:
                return {"0": first, "1": second}
    except (TypeError, json.JSONDecodeError):
        pass

    lines = [
        line.strip(" -0123456789.:\t").strip()
        for line in text.splitlines()
        if line.strip()
    ]
    cleaned = [_clean_name(line) for line in lines]
    cleaned = [name for name in cleaned if name]
    if len(cleaned) >= 2 and cleaned[0] != cleaned[1]:
        return {"0": cleaned[0], "1": cleaned[1]}
    return None


def _ask_local_ai_for_names():
    """Ask the Ollama-compatible local API to generate two JoJo-themed names."""
    prompt = (
        "Generate exactly two short JoJo-themed arcade fighting game display "
        "names for Player 1 and Player 2. Make them dramatic and inspired by "
        "Ripple/Hamon, Pillar Men, stardust, poses, and over-the-top duel "
        "energy. Avoid real character full names. Each name must be 1 to 3 "
        "words and 24 characters or fewer. Return only JSON in this exact "
        "shape: {\"names\":[\"NAME ONE\",\"NAME TWO\"]}"
    )
    body = json.dumps(
        {
            "model": LOCAL_AI_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.95,
                "num_predict": 90,
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        LOCAL_AI_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=LOCAL_AI_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return _parse_names(payload.get("response", ""))


def generate_ai_player_names():
    """Return AI-generated player names, falling back locally if AI is unavailable."""
    try:
        names = _ask_local_ai_for_names()
        if names:
            logger.info(
                "Generated JoJo-style player names with local AI model %s",
                LOCAL_AI_MODEL,
            )
            return names
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        logger.info("Local AI name generation unavailable: %s", exc)

    names = _fallback_player_names()
    logger.info(
        "Using fallback JoJo-style player names: %s vs %s",
        names["0"],
        names["1"],
    )
    return names
