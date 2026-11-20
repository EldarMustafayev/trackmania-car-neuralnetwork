"""Drive the map yourself once; this script records your racing line as waypoints."""  # module docstring
import numpy as np                                                      # numpy to store the waypoints
from tmi_link import Link                                               # socket client for the PyBridge plugin
import config                                                           # shared settings


def main():                                                             # record one run
    link = Link()                                                       # connection to the game
    link.connect()                                                      # wait for the plugin
    print("Connected. Drive the map; recording stops at the finish line.")  # tell the user what to do
    points = []                                                         # list of recorded [x, y, z] positions
    while True:                                                         # one iteration per state from the game
        raw = link.recv_state()                                         # game is paused until we answer
        if raw["finished"]:                                             # finish line crossed
            np.save(config.WAYPOINT_FILE, np.array(points, dtype=np.float32))  # write the waypoints to disk
            print(f"Saved {len(points)} waypoints to {config.WAYPOINT_FILE}")  # confirm to the user
            link.send_restart()                                         # auto restart: put the car back on the start line
            return                                                      # done
        link.send_passive(config.RECORD_STEP_MS)                        # let the human keep driving
        pos = np.array(raw["pos"])                                      # current car position in world coordinates
        if not points or np.linalg.norm(pos - points[-1]) >= config.WAYPOINT_SPACING:  # moved far enough?
            points.append(pos)                                          # store this position as a new waypoint


if __name__ == "__main__":                                              # only run when executed directly
    main()                                                              # connect to the game and record
