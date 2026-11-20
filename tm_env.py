"""Gymnasium environment that lets a neural network drive Trackmania through TMInterface."""  # module docstring
import numpy as np                                                      # array math
import gymnasium as gym                                                 # RL environment API
from gymnasium import spaces                                            # describes action / observation shapes
import config                                                           # shared settings
import keys                                                             # real key presses for the post-finish menu
from tmi_link import Link                                               # socket client for the PyBridge.as plugin
from track import Track, forward_vec, right_vec                         # racing-line geometry helpers


class TMEnv(gym.Env):                                                   # the environment PPO trains on
    def __init__(self):                                                 # constructor
        super().__init__()                                              # initialise gym.Env
        self.track = Track()                                            # load the recorded racing line
        self.action_space = spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)  # [steer, throttle]
        n_obs = 7 + 2 * config.N_LOOKAHEAD                              # 7 scalar features + look-ahead (x, z) pairs
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(n_obs,), dtype=np.float32)  # unbounded floats
        self.link = Link()                                              # socket to the plugin inside the game
        self.link.connect()                                             # wait until the game is ready
        self.idx = 0                                                    # index of the waypoint nearest to the car
        self.last_steer = 0.0                                           # previous steering command (part of observation)
        self.steps = 0                                                  # decisions made this episode
        self.stuck = 0                                                  # decisions without enough progress
        self.progress_ref = 0.0                                         # progress value at the last "not stuck" check
        self.bad_heading = 0                                            # counter for the yaw-convention sanity check
        self.pending = False                                            # True while the game is blocked waiting for our action
        self.prev_s = 0.0                                               # distance along the line at the previous step
        self.finished = False                                           # True if the last step ended on the finish line

    def _observe(self, raw):                                            # turn raw game values into the network input
        pos = np.array([raw["pos"][0], raw["pos"][2]])                  # horizontal position (x, z)
        vel = np.array([raw["vel"][0], raw["vel"][2]])                  # horizontal velocity (x, z) in m/s
        f, r = forward_vec(raw["yaw"]), right_vec(raw["yaw"])           # car's forward and right axes
        self.idx = self.track.nearest(pos, self.idx)                    # update nearest-waypoint index
        d = self.track.direction(self.idx)                              # direction of the racing line here
        heading_cos = float(np.dot(f, d))                               # 1 = pointing along the line
        heading_sin = float(np.dot(r, d))                               # sign tells which way the car is turned
        scalars = np.array([raw["speed"] / config.MAX_SPEED_KMH,        # speed scaled to about 0..1
                            np.dot(vel, f) / 80.0, np.dot(vel, r) / 80.0,  # forward / sideways velocity (m/s scaled)
                            self.track.lateral_offset(pos, self.idx) / config.MAX_OFFSET_M,  # distance from the line
                            heading_cos, heading_sin, self.last_steer], dtype=np.float32)  # heading error + last steer
        if raw["speed"] > 30 and np.dot(vel, f) < 0:                    # moving fast but "backwards" per yaw?
            self.bad_heading += 1                                       # count it
            if self.bad_heading == 20:                                  # after repeated evidence
                print("WARNING: yaw convention looks wrong; edit forward_vec() in track.py")  # tell the user how to fix it
        return np.concatenate([scalars, self.track.lookahead(pos, raw["yaw"], self.idx)])  # full observation vector

    def reset(self, seed=None, options=None):                           # start a new episode
        super().reset(seed=seed)                                        # let gym handle the seed
        if self.pending:                                                # game is blocked mid-episode waiting for us
            self.link.send_restart()                                    # tell it to restart the race (unblocks the game)
            self.pending = False                                        # the game is running again
            if self.finished:                                           # race ended on the finish screen: menus need keys
                keys.press_enter(config.ENTER_PRESSES)                  # Enter several times, as a human would
        self.finished = False                                           # clear the flag for the new episode
        while True:                                                     # keep going until we are at race time 0
            raw = self.link.recv_state()                                # wait for the game to report its state
            self.pending = True                                         # the game is now blocked waiting for our answer
            if raw["t"] == 0 and not raw["finished"]:                   # fresh start line, countdown just ended
                break                                                   # ready to race
            self.link.send_restart()                                    # otherwise ask the game to restart the race
            self.pending = False                                        # the game is running again
        self.idx, self.steps, self.stuck, self.last_steer = 0, 0, 0, 0.0  # clear episode bookkeeping
        self.progress_ref = 0.0                                         # reset the stuck-detection reference
        self.prev_s = 0.0                                               # distance along the line at the previous step
        return self._observe(raw), {}                                   # first observation, empty info dict

    def step(self, action):                                             # apply an action, return the result
        self.link.send_drive(float(action[0]), float(action[1]))        # send [steer, throttle] to the game
        self.last_steer = float(action[0])                              # remember it for the next observation
        self.pending = False                                            # the game is running again until its next decision
        raw = self.link.recv_state()                                    # wait until the next decision point
        self.pending = True                                             # the game is blocked again, waiting for us
        self.finished = bool(raw["finished"])                           # reset() must press Enter if the race finished
        obs = self._observe(raw)                                        # convert raw state to network input
        s = float(self.track.s[self.idx])                               # current progress along the line in metres
        reward = (s - self.prev_s) * 0.1 - 0.01                         # reward progress, tiny penalty per step (go fast)
        self.prev_s = s                                                 # store for the next step
        self.steps += 1                                                 # count this decision
        terminated = False                                              # episode ended because of success/failure
        if raw["finished"]:                                             # crossed the finish line
            reward += config.FINISH_BONUS                               # big reward
            terminated = True                                           # episode over
        elif abs(obs[3]) * config.MAX_OFFSET_M > config.MAX_OFFSET_M:   # too far from the racing line
            reward -= config.CRASH_PENALTY                              # punish it
            terminated = True                                           # episode over
        if s - self.progress_ref > config.MIN_PROGRESS_M:               # made real progress recently
            self.progress_ref, self.stuck = s, 0                        # reset the stuck counter
        else:                                                           # no real progress this step
            self.stuck += 1                                             # count it
            if self.stuck >= config.STUCK_STEPS and not terminated:     # stuck for too long
                reward -= config.CRASH_PENALTY                          # punish it
                terminated = True                                       # episode over
        truncated = self.steps >= config.MAX_EPISODE_STEPS              # time limit reached (not a failure per se)
        return obs, reward, terminated, truncated, {}                   # standard gymnasium 5-tuple
