# AI lab

Where the decision and remediation models get built and tested, separate from the API.
Docker test machines run osquery. One is clean and one has (harmless) attacker activity
planted on it. We take snapshots of what osquery sees, run the models on them, and score
the models against an answer key.

## Quick start

```bash
cd ai
docker compose up -d --build     # start the test machines
./collect.sh                     # save osquery snapshots into snapshots/
docker compose run --rm ai       # run the models on the snapshots and score them
docker compose down              # stop everything when done
```

To use the real models, put your keys in `.env` in the **repo root** (copy `.env.example`).
Never commit it:

```
TYPESAFE_API_KEY=...   # decision model (Jev)
OPENAI_API_KEY=...     # remediation model
```

Without keys, the free fallbacks run instead: regex rules and a template script.
You can force them even with keys set:

```bash
docker compose run --rm -e DECISION_BACKEND=rules ai
docker compose run --rm -e REMEDIATION_BACKEND=template ai
docker compose run --rm ai python evaluate.py compromised   # just one machine
```

## What's here

| Path | What it is |
|---|---|
| `machines/Dockerfile` | A test computer: Ubuntu 24.04 + osquery 5.24.0. |
| `machines/clean.sh` | **web-01**: a normal web server (nginx, a Python app, a normal cron job, an admin SSH key). Anything flagged here is a false alarm. |
| `machines/compromised.sh` | **web-02**: the same server plus 9 planted attacks (list below). |
| `machines/listener.py` | **attacker**: catches the reverse shell. Never sends commands. |
| `queries.json` | The osquery queries we collect. Add one, run `./collect.sh`, done. |
| `collect.py`, `collect.sh` | Run the queries inside each machine and save `snapshots/<machine>.json`. |
| `snapshots/` | Saved osquery output. Commit these so anyone can run evals without Docker. |
| `expected/` | Answer keys: what should be flagged on each machine. |
| `decision.py` | Step 1, `decide()`: which rows are bad. Jev, or regex rules. |
| `remediation.py` | Step 2, `make_script()`: one multi-line fix script. OpenAI, or a template. |
| `evaluate.py` | Runs both steps and prints caught / missed / false alarms. |
| `results/` | Output of the last run, including the fix scripts. Not committed. |

## The planted attacks (web-02)

All harmless: the "malware" is `sleep`, cron isn't running, and the only network target
is the listener container.

| # | What | How it shows up in osquery |
|---|---|---|
| 1 | Reverse shell to the attacker | `processes` (`bash -i >& /dev/tcp/...`), `network_connections` (port 4444) |
| 2 | Crypto miner hidden in `/tmp/.x/kworkerd` | `processes` (`stratum+tcp://` in the command line) |
| 3 | Program that deleted itself after starting | `processes` (`on_disk = 0`) |
| 4 | Base64 command piped into `sh` | `processes` |
| 5 | Cron job that downloads and runs a script | `cron_jobs` |
| 6 | Hidden second root account `sysbackup` | `root_users` |
| 7 | Attacker's SSH key on root | `ssh_keys` (`hacker@kali`) |
| 8 | SUID copy of bash in `/var/tmp/.bash` | `temp_files` (mode `4755`) |
| 9 | Backdoor web server on port 31337 | `listening_ports`, `processes` (optional in the answer key) |

## How to improve the models

1. Change something:
   - prompts: `QUERY_HINTS` / `LABELS` in `decision.py`, `INSTRUCTIONS` in `remediation.py`
   - the confidence cutoff: `MIN_CONFIDENCE` in `decision.py`
   - the data: add a query to `queries.json`
2. Run `docker compose run --rm ai` and compare the score with the last run.
3. Read the fix script in `results/compromised.sh`. Would you approve it?

Keep both machines in every run. Catching more on web-02 doesn't help if web-01 starts
getting false alarms.

## Adding a new attack

1. Add it to `machines/compromised.sh` (keep it harmless).
2. Add a line to `expected/compromised.json` saying which query should catch it and a
   piece of text from the row (`contains`).
3. If no query sees it yet, add one to `queries.json`.
4. `docker compose up -d --force-recreate && ./collect.sh && docker compose run --rm ai`

## Later

- **Windows:** Docker on a Mac can't run Windows containers, so Windows testing needs the
  Windows VM.
- **Connecting to the API:** `server/decision.py` and `server/remediation.py` are older
  copies of these files. When the lab versions are good, they replace those.
- **Did the fix work?** A next step is to run the generated script on web-02, collect
  again, and check that the attacks are gone.
