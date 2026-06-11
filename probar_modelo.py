import time
from stable_baselines3 import PPO
from forza_gym_env import ForzaEnv

env = ForzaEnv()

print("Cargando el modelo entrenado ppo_forza_circuito.zip...")
model = PPO.load("checkpoints/ppo_forza_modelo_160000_steps", env=env)

print("Modelo cargado con éxito.")
print("Entra al circuito en Forza Horizon 6, colócate en la pista y pulsa Ctrl+C en la consola si quieres parar.")
time.sleep(3)

state, info = env.reset()

try:
    while True:
        action, _states = model.predict(state, deterministic=True)
        
        state, reward, done, truncated, info = env.step(action)
        
        if done or truncated:
            env.gamepad.reset()
            env.gamepad.update()
            
            env.sock.setblocking(False)
            while True:
                try:
                    env.sock.recvfrom(1024)
                except BlockingIOError:
                    break
            env.sock.setblocking(True)
            
            env.steps_in_episode = 0
            state = env._get_telemetry()

except KeyboardInterrupt:
    print("\nPrueba finalizada por el usuario. Soltando controles...")
finally:
    env.gamepad.reset()
    env.gamepad.update()
    env.close()