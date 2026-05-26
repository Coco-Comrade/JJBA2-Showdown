import json
import os
import random
import urllib.error
import urllib.request

from .config import logger

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_NAME_MODEL = os.environ.get("OPENAI_NAME_MODEL", "gpt-5-mini")

LOCAL_EPITHETS = (
    "Ripple",
    "Hamon",
    "Crimson",
    "Pillar",
    "Stardust",
    "Golden",
    "Overdrive",
    "Caesar",
    "Rose",
    "Sunlight",
    "Battle",
    "Azure",
)

LOCAL_NOUNS = (
    "Joestar",
    "Zeppeli",
    "Tempest",
    "Phantom",
    "Crusader",
    "Vanguard",
    "Duelist",
    "Oracle",
    "Striker",
    "Emperor",
    "Comet",
    "Requiem",
)


def _local_name():
    return f"{random.choice(LOCAL_EPITHETS)} {random.choice(LOCAL_NOUNS)}"


def local_player_names():
    first = _local_name()
    second = _local_name()
    while second == first:
        second = _local_name()
    return {"0": first.upper(), "1": second.upper()}


def _extract_response_text(response):
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    parts = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(part for part in parts if part)


def _parse_names(text):
    text = text.strip()
    try:
        data = json.loads(text)
        names = data.get("names", data)
        if isinstance(names, list) and len(names) >= 2:
            return {"0": str(names[0]).upper()[:24], "1": str(names[1]).upper()[:24]}
    except json.JSONDecodeError:
        pass

    lines = [
        line.strip(" -0123456789.:\t").strip()
        for line in text.splitlines()
        if line.strip()
    ]
    if len(lines) >= 2:
        return {"0": lines[0].upper()[:24], "1": lines[1].upper()[:24]}
    return None


def generate_ai_player_names():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return local_player_names()

    prompt = (
        "Generate exactly two short JoJo-themed arcade fighting game player "
        "names. Make them dramatic, punchy, and inspired by Ripple/Hamon, "
        "Pillar Men, stardust, poses, and over-the-top anime duel energy. "
        "Do not use real copyrighted character full names. Each name must be "
        "1 to 3 words and 24 characters or fewer. Return only JSON like "
        "{\"names\":[\"NAME ONE\",\"NAME TWO\"]}."
    )
    request_body = json.dumps(
        {
            "model": OPENAI_NAME_MODEL,
            "input": prompt,
            "max_output_tokens": 80,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=request_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
        names = _parse_names(_extract_response_text(payload))
        if names:
            logger.info("Generated AI player names with %s", OPENAI_NAME_MODEL)
            return names
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        logger.info("AI name generation fell back to local names: %s", exc)

    return local_player_names()
