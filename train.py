import os
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from forza_gym_env import ForzaEnv

env = ForzaEnv()

# 1. Configurar el Callback para guardar checkpoints cada 10.000 pasos
# Los guardará en una carpeta llamada 'checkpoints'
checkpoint_callback = CheckpointCallback(
    save_freq=10000,
    save_path="./checkpoints/",
    name_prefix="ppo_forza_modelo"
)

# Ruta del último checkpoint generado para comprobar si existe
ultimo_checkpoint = "./checkpoints/ppo_forza_modelo_10000_steps.zip"

# 2. Lógica de carga o creación desde cero
# Si el archivo del checkpoint existe, reanudamos desde ahí
if os.path.exists(ultimo_checkpoint):
    print(f"Se ha encontrado un checkpoint válido: {ultimo_checkpoint}")
    print("Cargando modelo y reanudando el entrenamiento desde ese punto...")
    
    # Cargamos el modelo existente y le reconectamos nuestro entorno UDP del Forza
    model = PPO.load(ultimo_checkpoint, env=env)
else:
    print("No se han encontrado checkpoints anteriores. Iniciando entrenamiento desde cero...")
    
    # Si no hay archivos, creamos el modelo PPO con la configuración de exploración
    model = PPO(
        policy="MlpPolicy",
        env=env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.05,
        clip_range=0.2,
        verbose=1
    )

print("Todo listo. Arranca el circuito en el juego para empezar a procesar frames.")

# 3. Lanzar el aprendizaje pasando el callback en la lista
# Ponemos un total de pasos grande, ya que irá guardando cada 10.000
model.learn(total_timesteps=200000, callback=checkpoint_callback)

# Guardar el modelo final al terminar todos los pasos
model.save("ppo_forza_circuito_final")
env.close()