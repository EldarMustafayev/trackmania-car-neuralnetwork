"""Watch the trained model drive the map."""                             # module docstring
import os                                                               # file path helpers
from stable_baselines3 import PPO                                       # PPO class (used for loading)
from tm_env import TMEnv                                                # our Trackmania environment
import config                                                           # shared settings

if __name__ == "__main__":                                              # only run when executed directly
    env = TMEnv()                                                       # create env (waits for the game connection)
    model = PPO.load(os.path.join(config.MODEL_DIR, "ppo_tm.zip"), device="cpu")  # load the trained network
    for episode in range(5):                                            # run five attempts
        obs, _ = env.reset()                                            # restart the race
        done, total = False, 0.0                                        # episode flag and reward counter
        while not done:                                                 # until the episode ends
            action, _ = model.predict(obs, deterministic=True)          # network picks the best action (no exploration)
            obs, reward, terminated, truncated, _ = env.step(action)    # apply it in the game
            total += reward                                             # accumulate reward
            done = terminated or truncated                              # stop when the episode ends
        print(f"Episode {episode}: reward {total:.1f}, progress {env.track.s[env.idx]:.0f}/{env.track.length:.0f} m")  # report result
