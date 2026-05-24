# JJBA2: The Showdown

A local/LAN Pygame fighting game inspired by JoJo Part 2, with singleplayer AI and two-player lobby support.

## Run

Install Pygame, then run:

```bash
python jojo_lan_fighter.py
```

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
