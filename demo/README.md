# Boombox demo

A live demo of Boombox catching and closing a reverse shell. Everything runs in Docker on
your machine:

- **victim**: an Ubuntu machine with osquery, a reverse shell to the attacker that
  reconnects every 5 seconds, and a small Boombox client (`client.py`) that polls every
  20 seconds and runs approved fixes.
- **attacker**: the machine the reverse shell connects to. You type into it.

| File | What it does |
|---|---|
| `start.sh` | Fresh start: empties the database, starts Boombox, the victim and the attacker |
| `victim-screen.sh` | Shows the victim's "hacked screen" |
| `attacker-listen.sh` | The attacker's listener; the reverse shell connects here |
| `funny-messages.txt` | The line to paste into the attacker shell to post cowsay messages |
| `stop.sh` | Stops everything |
| `compose.yaml`, `Dockerfile`, `victim.sh`, `client.py` | How the two machines are built |

## Live demo, in order

Use two terminals (or panes), both in this folder.

1. **Any terminal:** `./start.sh`
2. **Victim terminal:** `./victim-screen.sh`. It stays blank until the attacker posts
   something. That's expected.
3. **Attacker terminal:** `./attacker-listen.sh`. Within 5 seconds you'll see
   `Connection received`. Press Enter to get the `root@demo-web-01:/#` prompt: you're now
   controlling the victim. Try `whoami` or `hostname`.
4. **Attacker terminal:** paste the line from `funny-messages.txt` and press Enter.
   Animals with "HACKED!" messages appear in the victim terminal every 3 seconds.
5. **Browser:** open http://localhost. Within about a minute a fix appears under
   "Awaiting review" (refresh if needed). Open it, show the explanation and the script,
   then click **Approve & deploy**.
6. **Watch both terminals.** Within about 20 seconds the animals stop, and the attacker
   terminal drops back to your own prompt: the connection is closed.

To run it again: `./start.sh`, then start from step 2. When you're done: `./stop.sh`.

## During the demo, don't

- **Press Ctrl+C in the attacker terminal** once connected: that closes the connection
  yourself instead of letting Boombox do it.
- **Use the arrow keys in the attacker terminal:** the shell has no history, so they just
  print `^[[A`. Retype commands instead.
- **Start the victim screen after the messages:** it only shows what comes after it starts.

The AI keys (`TYPESAFE_API_KEY`, `OPENAI_API_KEY`) must be in the repo root's `.env`.
