// PyBridge: TMInterface 2.x plugin that lets a Python program drive the car over a local TCP socket.
// Replaces the old (TMInterface < 2.0) Python client API.
//
// Protocol (all values little-endian):
//   plugin -> python (40 bytes): int type (1 = state, 2 = finish line crossed), int raceTimeMs,
//                                float x, y, z, vx, vy, vz, yaw, speedKmh
//   python -> plugin (20 bytes): int cmd (0 = drive, 1 = restart race, 2 = passive / you drive),
//                                float steer [-1,1], float throttle [-1,1], float gameSpeed, int stepPeriodMs
// After every state message the game is paused until Python answers.

const string HOST = "127.0.0.1";
const uint16 PORT = 8478;                 // must match PORT in config.py
const uint TIMEOUT_MS = 300000;           // give up waiting for Python after 5 minutes
const uint CMD_BYTES = 20;                // size of one python -> plugin message

Net::Socket@ server = null;               // listening socket
Net::Socket@ client = null;               // connected Python program (null = none)
bool restarting = false;                  // true while waiting for the countdown after a restart
bool wantGiveUp = false;                  // true = call sim.GiveUp() on the next OnRunStep
bool externalRestart = false;             // true = Python restarts via the end-screen menu (key presses), don't GiveUp
uint64 restartStart = 0;                  // Time::Now when the current restart was requested
bool controlling = false;                 // true = we apply Python's inputs, false = the human drives
int stepPeriod = 10;                      // send a state every this many ms of race time
float inSteer = 0.0f;                     // latest steering command from Python
float inThrottle = 0.0f;                  // latest throttle command from Python
float gameSpeed = 1.0f;                   // latest requested game speed

PluginInfo@ GetPluginInfo()
{
    auto info = PluginInfo();
    info.Name = "PyBridge";
    info.Author = "trackmania-ai";
    info.Version = "1.0.0";
    info.Description = "Socket bridge between TMInterface 2.x and the Python RL scripts";
    return info;
}

void Main()
{
    @server = Net::Socket();
    if (!server.Listen(HOST, PORT)) {
        log("PyBridge: could not listen on " + HOST + ":" + PORT);
        @server = null;
        return;
    }
    log("PyBridge: listening on " + HOST + ":" + PORT);
}

// Accept a new Python connection if one is waiting. Returns true when a new client was accepted.
bool PollAccept()
{
    if (server is null) return false;
    Net::Socket@ s = server.Accept(0);
    if (s is null) return false;
    s.NoDelay = true;
    @client = s;
    controlling = false;
    restarting = false;
    stepPeriod = 10;
    log("PyBridge: Python connected");
    return true;
}

void BeginRestart()
{
    restarting = true;
    restartStart = Time::Now;
}

void Render()
{
    PollAccept();                         // called every frame, so connections are picked up quickly
}

bool SendState(SimulationManager@ sim, bool finished)
{
    iso4 loc = sim.Dyna.CurrentState.Location;
    vec3 vel = sim.Dyna.CurrentState.LinearSpeed;
    float yaw = 0.0f;
    float pitch = 0.0f;
    float roll = 0.0f;
    loc.Rotation.GetYawPitchRoll(yaw, pitch, roll);

    int msgType = finished ? 2 : 1;
    int raceTime = sim.RaceTime;
    float speed = float(sim.PlayerInfo.DisplaySpeed);
    bool ok = client.Write(msgType);
    ok = client.Write(raceTime) && ok;
    ok = client.Write(loc.Position.x) && ok;
    ok = client.Write(loc.Position.y) && ok;
    ok = client.Write(loc.Position.z) && ok;
    ok = client.Write(vel.x) && ok;
    ok = client.Write(vel.y) && ok;
    ok = client.Write(vel.z) && ok;
    ok = client.Write(yaw) && ok;
    ok = client.Write(speed) && ok;
    return ok;
}

// Send the state, then block until Python answers. Returns true if the new inputs should be applied now.
bool Exchange(SimulationManager@ sim, bool finished)
{
    if (!SendState(sim, finished)) {
        log("PyBridge: lost connection to Python");
        @client = null;
        return false;
    }
    uint64 start = Time::Now;
    while (client.Available < CMD_BYTES) {
        if (PollAccept()) {               // Python was restarted: begin a fresh race for the new connection
            sim.GiveUp();
            BeginRestart();
            return false;
        }
        if (Time::Now - start > TIMEOUT_MS) {
            log("PyBridge: Python did not answer in time, disconnecting");
            @client = null;
            return false;
        }
    }
    int cmd = client.ReadInt32();
    inSteer = client.ReadFloat();
    inThrottle = client.ReadFloat();
    float speed = client.ReadFloat();
    stepPeriod = client.ReadInt32();
    if (stepPeriod < 10) stepPeriod = 10;
    if (speed != gameSpeed) {
        gameSpeed = speed;
        sim.SetSpeed(gameSpeed);
    }
    if (cmd == 1) {                       // restart the race
        // Don't call GiveUp() here: when we are inside the finish-line callback the race is still "finishing" in
        // this tick and the call is ignored. Defer it to the next regular OnRunStep, where GiveUp() is reliable.
        if (finished) {                   // finish-line case: Python presses Enter twice on the end screen itself
            externalRestart = true;
        } else {
            wantGiveUp = true;
        }
        BeginRestart();
        return false;
    }
    controlling = (cmd == 0);
    return true;
}

void ApplyInputs(SimulationManager@ sim)
{
    if (!controlling) return;
    sim.SetInputState(InputType::Up, inThrottle > 0.0f ? 1 : 0);
    sim.SetInputState(InputType::Down, inThrottle < -0.3f ? 1 : 0);
    float s = Math::Clamp(inSteer, -1.0f, 1.0f);
    sim.SetInputState(InputType::Steer, int(s * 65536.0f));
}

void OnRunStep(SimulationManager@ sim)
{
    if (client is null) return;
    int t = sim.RaceTime;
    if (wantGiveUp) {                     // restart requested by Python (possibly from the finish-line callback)
        wantGiveUp = false;
        sim.GiveUp();
        restartStart = Time::Now;
        return;
    }
    if (restarting) {                     // wait until the countdown of the new race starts
        if (t < 0) {
            restarting = false;
            externalRestart = false;
        } else if (!externalRestart && Time::Now - restartStart > 200) {   // still in the old race: GiveUp was ignored, try again
            sim.GiveUp();
            restartStart = Time::Now;
        }
        return;
    }
    if (t < 0) return;                    // countdown: inputs are ignored anyway
    if (t % stepPeriod == 0) {
        if (!Exchange(sim, false)) return;
    }
    ApplyInputs(sim);
}

void OnCheckpointCountChanged(SimulationManager@ sim, int current, int target)
{
    if (client is null) return;
    if (current == target) {              // last checkpoint = finish line
        // Let the game show its normal end screen; the Python side presses Enter twice to start the next attempt.
        Exchange(sim, true);
    }
}
