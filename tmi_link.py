"""Socket client for the PyBridge.as plugin (TMInterface 2.x has no Python client API anymore)."""  # module docstring
import socket                                                           # plain TCP connection to the plugin
import struct                                                           # pack / unpack the binary messages
import time                                                             # wait between connection attempts
import config                                                           # shared settings

STATE = struct.Struct("<ii" + "f" * 8)                                  # type, time, pos xyz, vel xyz, yaw, speed
COMMAND = struct.Struct("<ifffi")                                       # cmd, steer, throttle, game speed, step period

CMD_DRIVE, CMD_RESTART, CMD_PASSIVE = 0, 1, 2                           # what the plugin should do after a state


class Link:                                                             # one connection to the game
    def __init__(self):                                                 # constructor
        self.sock = None                                                # set by connect()

    def connect(self):                                                  # block until the plugin accepts us
        printed = False                                                 # only print the waiting message once
        while True:                                                     # retry until the game is ready
            try:                                                        # try to open the TCP connection
                self.sock = socket.create_connection((config.HOST, config.PORT), timeout=2)  # plugin listens here
                self.sock.settimeout(None)                              # from now on block until data arrives
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # no batching delay
                print("Connected to TMInterface (PyBridge plugin).")     # tell the user it worked
                return                                                  # done
            except OSError:                                             # game not running / plugin not loaded
                if not printed:                                         # first failure only
                    print(f"Waiting for the PyBridge plugin on {config.HOST}:{config.PORT} ... "
                          "(start the game via TMLoader with TMInterface 2.x)")  # hint
                    printed = True                                      # don't spam
                time.sleep(1.0)                                         # try again in a second

    def _recv_exact(self, n):                                           # read exactly n bytes
        buf = b""                                                       # collected bytes
        while len(buf) < n:                                             # until we have all of them
            chunk = self.sock.recv(n - len(buf))                        # next piece
            if not chunk:                                               # connection closed by the game
                raise ConnectionError("TMInterface closed the connection")  # stop the script cleanly
            buf += chunk                                                # append it
        return buf                                                      # full message

    def recv_state(self):                                               # wait for the next car state
        v = STATE.unpack(self._recv_exact(STATE.size))                  # decode the 40 bytes
        return dict(finished=(v[0] == 2), t=v[1], pos=list(v[2:5]), vel=list(v[5:8]),  # raw values like before
                    yaw=v[8], speed=v[9])                               # heading and km/h

    def _send(self, cmd, steer=0.0, throttle=0.0, period=None):         # send one command
        period = config.DECISION_MS if period is None else period       # default decision interval
        self.sock.sendall(COMMAND.pack(cmd, steer, throttle, config.GAME_SPEED, period))  # 20 bytes

    def send_drive(self, steer, throttle):                              # let the AI drive
        self._send(CMD_DRIVE, steer, throttle)                          # apply these inputs

    def send_restart(self):                                             # restart the race
        self._send(CMD_RESTART)                                         # plugin calls GiveUp

    def send_passive(self, period):                                     # human drives, we only watch
        self._send(CMD_PASSIVE, period=period)                          # no inputs applied
