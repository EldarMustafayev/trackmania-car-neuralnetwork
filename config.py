"""Central settings shared by every script."""  # module docstring
HOST = "127.0.0.1"                  # where the PyBridge.as plugin listens (inside the game)
PORT = 8478                         # must match PORT in plugin/PyBridge.as
RECORD_STEP_MS = 20                 # while recording, the game reports the car every 20 ms (< 2 m at 300 km/h)
WAYPOINT_FILE = "waypoints.npy"     # file where the recorded racing line is stored
WAYPOINT_SPACING = 2.0              # metres between recorded waypoints
DECISION_MS = 50                    # the AI picks a new action every 50 ms of game time (20 Hz)
GAME_SPEED = 6.0                    # game speed multiplier while training (try 4.0 once things work)
N_LOOKAHEAD = 10                    # how many upcoming waypoints the network can "see"
LOOKAHEAD_STRIDE = 4                # use every 4th waypoint ahead (4 * 2 m = 8 m between look-ahead points)
MAX_SPEED_KMH = 300.0               # used to scale the speed observation into roughly 0..1
MAX_OFFSET_M = 12.0                 # leaving the racing line by more than this ends the episode
STUCK_STEPS = 60                    # this many decisions without progress (3 s) ends the episode
MIN_PROGRESS_M = 2.0                # progress smaller than this over STUCK_STEPS counts as "stuck"
MAX_EPISODE_STEPS = 2400            # hard cap per episode (2400 * 50 ms = 120 s)
FINISH_BONUS = 100.0                # reward for crossing the finish line
CRASH_PENALTY = 30                  # penalty for leaving the line or getting stuck
GAME_WINDOW_TITLE = "Trackmania"    # exact title of the game window (focused before pressing Enter after a finish)
FINISH_MENU_DELAY_S = 1.0           # wait this long after the finish before pressing Enter (end screen must be up)
ENTER_PRESSES = 3

                 # how many times Enter is pressed after a finish
ENTER_GAP_S = 1                   # pause between the Enter presses
MODEL_DIR = "models"               # folder where trained models are saved
