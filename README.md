# JJBA2: The Showdown

A local/LAN Pygame fighting game inspired by JoJo Part 2, with singleplayer AI and two-player lobby support.

## Project Summary

JJBA2: The Showdown is a Python/Pygame arcade fighting game. It supports:

- Singleplayer against a rule-based CPU fighter.
- Two-player LAN matches with a host lobby.
- A server-authoritative network model where clients send input and the host
  server sends back the official match state.
- Encrypted raw UDP messages for pickle dictionary game packets.
- Local AI-generated JoJo-themed player display names through an
  Ollama-compatible local API.

For NotebookLM or other study tools, the most important files are:

- `README.md` for the project overview.
- `jjba2/protocol.py` for the LAN message protocol.
- `jjba2/server.py` and `jjba2/client.py` for networking.
- `jjba2/fighter.py` and `jjba2/gameplay.py` for combat logic.
- `jjba2/ai_names.py` for local AI name generation.
- `jjba2/render.py` and `jjba2/menus.py` for UI and flow.

## Run

Install Pygame, then run:

```bash
python jojo_lan_fighter.py
```

Or on Windows, double-click:

```text
run_game.bat
```

## Code Layout

- `jojo_lan_fighter.py` launches the game.
- `jjba2/config.py` initializes Pygame, logging, screen, fonts, and constants.
- `jjba2/data.py` contains characters, attacks, difficulties, and sprite metadata.
- `jjba2/ai_names.py` generates JoJo-themed player names with a local AI model.
- `jjba2/protocol.py` contains encrypted UDP packet helpers.
- `jjba2/server.py` contains the lobby/game server.
- `jjba2/client.py` contains the LAN client.
- `jjba2/fighter.py` contains fighter movement, attack, damage, and state logic.
- `jjba2/gameplay.py` contains combat stepping, AI, singleplayer, and match loops.
- `jjba2/render.py` contains drawing, screens, music, and visual helpers.
- `jjba2/menus.py` contains menu and lobby flow.

## LAN Protocol

LAN messages are still Python dictionaries serialized with `pickle`, but they
are now sent as raw UDP datagrams instead of TCP streams. UDP already preserves
packet boundaries, so the protocol no longer needs the old `length#` header.

Each UDP packet contains:

```text
magic_header + nonce + hmac_tag + encrypted_pickle_payload
```

For example, the decrypted logical message still looks like:

```python
{"type": "input", "input": {...}}
```

The host and joining player must type the same LAN password. The game derives a
key from that password, encrypts the pickled dictionary, and verifies an HMAC
tag before unpickling. Clients send `join`, character selections, and input
snapshots; the host server sends lobby responses and authoritative match state
snapshots.

Because the game uses UDP, firewalls must allow UDP port `5555` on the host PC.
If the passwords do not match, the packet authentication fails and the lobby
will not accept the message.

## AI Player Names

The game can ask a local AI model to create short JoJo-themed display names
for Player 1 and Player 2. By default it calls an Ollama-compatible local API:
`http://localhost:11434/api/generate` with model `llama3.2`.

Set `JJBA2_LOCAL_AI_URL` or `JJBA2_LOCAL_AI_MODEL` to use a different local
server or model. LAN names are generated when the host creates a lobby, so they
can appear before the fight starts. This does not call OpenAI or any paid
external API. If the local model is not running, the game falls back to local
JoJo-themed names so matches still start normally.

### Local AI Setup

The GitHub repo includes the code that talks to a local AI API, but it does not
include the AI server or model files. Each player who wants local AI-generated
names needs to install and run a local model server.

Recommended setup with Ollama:

1. Install Ollama from the official website.
2. Open a terminal and download the default model:

```bash
ollama pull llama3.2
```

3. Make sure Ollama is running. Its local API should be available at:

```text
http://localhost:11434/api/generate
```

4. Launch the game. When the host creates a LAN lobby, the game asks the local
   model for two JoJo-themed player names.

To use a different model:

```powershell
$env:JJBA2_LOCAL_AI_MODEL="mistral"
python jojo_lan_fighter.py
```

To use a different local endpoint:

```powershell
$env:JJBA2_LOCAL_AI_URL="http://localhost:11434/api/generate"
python jojo_lan_fighter.py
```

If Ollama is not installed or not running, the game still works. It simply uses
the built-in fallback name generator.

Optional local assets:

- `intro.mp3`, `intro.ogg`, or `intro.wav` for menu music
- `sweetie_fox.png` for the hidden easter egg image

The character select screen uses the bundled
`assets/music/character_select.wav` track.

Runtime logs are written to `logs/jjba2_showdown.log`. Local music, easter egg
images, downloaded music, logs, ZIPs, and PyCharm project files are ignored by
Git by default.
