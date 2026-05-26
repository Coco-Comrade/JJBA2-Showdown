# JJBA2: The Showdown

A local/LAN Pygame fighting game inspired by JoJo Part 2, with singleplayer AI and two-player lobby support.

## Run

Install Pygame, then run:

```bash
python jojo_lan_fighter.py
```

## Code Layout

- `jojo_lan_fighter.py` launches the game.
- `jjba2/config.py` initializes Pygame, logging, screen, fonts, and constants.
- `jjba2/data.py` contains characters, attacks, difficulties, and sprite metadata.
- `jjba2/protocol.py` contains LAN message framing and socket helpers.
- `jjba2/server.py` contains the lobby/game server.
- `jjba2/client.py` contains the LAN client.
- `jjba2/fighter.py` contains fighter movement, attack, damage, and state logic.
- `jjba2/gameplay.py` contains combat stepping, AI, singleplayer, and match loops.
- `jjba2/render.py` contains drawing, screens, music, and visual helpers.
- `jjba2/menus.py` contains menu and lobby flow.

## LAN Protocol

LAN messages are sent over TCP as a 4-byte big-endian payload length followed
by a UTF-8 JSON payload. The receiver reads exactly the 4-byte header first,
then exactly the announced payload length. Clients send character selections
and input snapshots; the host server sends lobby responses and authoritative
match state snapshots.

Optional local assets:

- `intro.mp3`, `intro.ogg`, or `intro.wav` for menu music
- `sweetie_fox.png` for the hidden easter egg image

The character select screen uses the bundled
`assets/music/character_select.wav` track.

Runtime logs are written to `logs/jjba2_showdown.log`. Local music, easter egg
images, downloaded music, logs, ZIPs, and PyCharm project files are ignored by
Git by default.
