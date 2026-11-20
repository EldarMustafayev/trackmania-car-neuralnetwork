"""Geometry of the racing line: progress, offset and look-ahead points (no game needed)."""  # module docstring
import math                                                             # sin/cos for the car's local frame
import numpy as np                                                      # array math
import config                                                           # shared settings


def forward_vec(yaw):                                                   # unit vector the car points along, in (x, z)
    return np.array([math.sin(yaw), math.cos(yaw)])                     # assumes yaw 0 = +Z; swap here if the heading check warns


def right_vec(yaw):                                                     # unit vector pointing to the car's right, in (x, z)
    return np.array([math.cos(yaw), -math.sin(yaw)])                    # forward vector rotated by 90 degrees


class Track:                                                            # 
    def __init__(self, path=config.WAYPOINT_FILE):                      # 
        wp = np.load(path)                                              # loads the data of location
        self.xz = wp[:, [0, 2]].astype(np.float64)                      # finds segments using diff, length using norm
        seg = np.linalg.norm(np.diff(self.xz, axis=0), axis=1)          # 
        self.s = np.concatenate([[0.0], np.cumsum(seg)])                # makes a distance from the origin array
        self.n = len(self.xz)                                           # number of checkpoints
        self.length = float(self.s[-1])                                 # start to finish distance

    def nearest(self, pos_xz, idx):                                     # find the closest waypoint near the last known index
        lo = max(0, idx - 5)                                            # allows a jitter of 5 checkpoints
        hi = min(self.n, idx + 40)                                      # look at most 40 checkpoints ahead
        d = np.linalg.norm(self.xz[lo:hi] - pos_xz, axis=1)             # distance from car to each candidate waypoint
        return lo + int(np.argmin(d))                                   # index of the closest candidate

    def direction(self, idx):                                           # unit direction of the line at waypoint idx
        j = min(idx + 1, self.n - 1)                                    # next waypoint (clamped at the end)
        i = max(j - 1, 0)                                               # the waypoint before it
        v = self.xz[j] - self.xz[i]                                     # direction vector between them
        return v / (np.linalg.norm(v) + 1e-9)                           # normalise to length 1

    def lateral_offset(self, pos_xz, idx):                              # signed distance of the car from the line
        d = self.direction(idx)                                         # line direction here
        r = np.array([d[1], -d[0]])                                     # line's right-hand normal
        return float(np.dot(pos_xz - self.xz[idx], r))                  # project the car offset onto that normal

    def lookahead(self, pos_xz, yaw, idx):                              # upcoming waypoints in the car's own frame
        f, r = forward_vec(yaw), right_vec(yaw)                         # car's forward and right axes
        out = []                                                        # collected look-ahead coordinates
        for k in range(1, config.N_LOOKAHEAD + 1):                      # for each look-ahead point
            j = min(idx + k * config.LOOKAHEAD_STRIDE, self.n - 1)      # waypoint index (clamped at the finish)
            rel = self.xz[j] - pos_xz                                   # vector from car to that waypoint
            out += [np.dot(rel, r) / 100.0, np.dot(rel, f) / 100.0]     # (right, forward) in units of 100 m
        return np.array(out, dtype=np.float32)                          # flat array of 2 * N_LOOKAHEAD numbers
