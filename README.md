# Trackmania AI

A neural-network driver for Trackmania, trained with reinforcement learning (PPO from stable-baselines3).
The AI learns to follow a racing line you record yourself on a single map.

## How it works

- `plugin/PyBridge.as` is a TMInterface 2.x plugin. It opens a local TCP socket (`127.0.0.1:8478`) and
  pauses the game after every state update until Python replies.
- `tmi_link.py` is the Python client for that socket.
- `record_waypoints.py` records your own run as waypoints (`waypoints.npy`).
- `tm_env.py` is a Gymnasium environment built on those waypoints.
- `train.py` trains the model and `evaluate.py` lets you watch it drive.
- `keys.py` presses Enter to restart the race after a finish, since TMInterface cannot navigate menus.
- `config.py` holds every setting.

## Requirements

- Windows (the game and `pydirectinput` need it)
- Trackmania with [TMInterface 2.x](https://donadigo.com/tminterface/), started through TMLoader
- Python 3.10 or newer

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Install the plugin by copying `plugin/PyBridge.as` into TMInterface's plugins folder
(usually `Documents\TMInterface\Plugins`). Then start the game through TMLoader with TMInterface and
enable **PyBridge** in the TMInterface plugin list.

## Usage

Start the game and load the map you want to train on. Every script waits for the plugin until it connects.

### 1. Record a racing line

```powershell
python record_waypoints.py
```

Drive the map yourself once. Recording stops at the finish line and saves `waypoints.npy`.
The repo already ships a `waypoints.npy` for one map. Re-record it if you use a different map.

### 2. Train

```powershell
python train.py
```

- Models are saved to `models/`: a snapshot every 20,000 steps and the latest as `ppo_tm.zip`.
- If `models/ppo_tm.zip` exists, training resumes from it. Delete it to start from scratch.
- Press `Ctrl+C` to stop. The latest model is saved first.
- Keep the game window titled "Trackmania" and don't click away. Enter presses are sent to it after each finish.

### 3. Watch the AI drive

```powershell
python evaluate.py
```

Runs 5 episodes with the saved model and prints reward and progress for each.

## Settings (`config.py`)

| Setting | Meaning |
| --- | --- |
| `GAME_SPEED` | Game speed multiplier during training (lower it if the car behaves oddly) |
| `DECISION_MS` | How often the AI picks an action, in ms of game time |
| `MAX_OFFSET_M` | Distance from the racing line that ends an episode |
| `FINISH_BONUS`, `CRASH_PENALTY` | Reward shaping |
| `GAME_WINDOW_TITLE` | Window title used to focus the game |
| `PORT` | Must match `PORT` in `plugin/PyBridge.as` |

## Docker

A `Dockerfile` is included. It installs the dependencies and runs `train.py`, but training needs the Windows
game running, so Docker is mainly useful for reproducing the Python environment.

```bash
docker build -t trackmania-ai .
```
