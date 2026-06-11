import gymnasium as gym
from gymnasium import spaces
import numpy as np
import socket
import struct
import vgamepad as vg
import time
import vgamepad as vg
import time
import vgamepad as vg00000

class ForzaEnv(gym.Env):
    def __init__(self):
        super(ForzaEnv, self).__init__()

        self.steps_in_episode = 0
        self.crashed = True

        # Configuración del Socket UDP
        self.UDP_IP = "127.0.0.1"
        self.UDP_PORT = 5123
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.UDP_IP, self.UDP_PORT))
        
        # Inicializar el mando virtual de Xbox
        self.gamepad = vg.VX360Gamepad()
        
        # Espacio de Acciones Continuas: 
        # Acción 0: Dirección del volante (-1.0 Izquierda a 1.0 Derecha)
        # Acción 1: Pedal acc
        # Acción 2: Pedal fren
        self.action_space = spaces.Box(
                low=np.array([-1.0, 0.0, 0.0], dtype=np.float32),
                high=np.array([1.0, 1.0, 1.0], dtype=np.float32),
                dtype=np.float32
            )
        # Espacio de Observaciones (Los 7 datos físicos que limpiamos)
        # [RPM, Velocidad, LINE, SLIP_DEL, SLIP_TRAS, ANG_VEL_Y, ACCEL_Z]
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, -127.0, 0.0, 0.0, -10.0, -50.0], dtype=np.float32),
            high=np.array([10000.0, 400.0, 127.0, 100.0, 100.0, 10.0, 50.0], dtype=np.float32),
            dtype=np.float32
        )

    def _get_telemetry(self):
        # Captura un paquete UDP del juego
        data, addr = self.sock.recvfrom(1024)
        
        current_engine_rpm = struct.unpack('f', data[16:20])[0]
        speed_ms = struct.unpack('f', data[256:260])[0]
        speed_kmh = speed_ms * 3.6
        perfectdriveLine = struct.unpack('b', data[321:322])[0]
        
        slip_fl = abs(struct.unpack('f', data[180:184])[0])
        slip_fr = abs(struct.unpack('f', data[184:188])[0])
        slip_rl = abs(struct.unpack('f', data[188:192])[0])
        slip_rr = abs(struct.unpack('f', data[192:196])[0])
        slip_delantero = (slip_fl + slip_fr) / 2
        slip_trasero = (slip_rl + slip_rr) / 2
        
        angular_vel_y = struct.unpack('f', data[48:52])[0]
        accel_z = struct.unpack('f', data[28:32])[0]
        
        state = np.array([current_engine_rpm, speed_kmh, perfectdriveLine, 
                          slip_delantero, slip_trasero, angular_vel_y, accel_z], dtype=np.float32)
        
        print(f"FRAME: {self.steps_in_episode} | RPM: {state[0]:4.0f} | Vel: {state[1]:5.1f} km/h | LINE: {int(state[2]):4d} | SLIP D/T: {state[3]:.2f}/{state[4]:.2f} | ANG Y: {state[5]:5.2f} | G_Z: {state[6]:5.2f}", end='\r')
        return state

    def step(self, action):
        
        # 1. Aplicar las acciones en el mando virtual
        steer_input = action[0]
        acc_input = action[1]
        brake_input = action[2]

        self.steps_in_episode += 1

        # Mapear el volante al stick izquierdo del mando de Xbox (-32768 a 32767)
        self.gamepad.left_joystick(x_value=int(steer_input * 32767), y_value=0)
        
        # Mapear acelerador y freno independientes basados en el valor continuo
        if acc_input > 0:
            self.gamepad.right_trigger(value=int(acc_input * 255))  # Acelerar
            self.gamepad.left_trigger(value=0)
        elif brake_input > 0:
            self.gamepad.left_trigger(value=int(abs(brake_input) * 255)) # Frenar
            self.gamepad.right_trigger(value=0)
            
        self.gamepad.update() # Envía los inputs al juego
        
        # 2. Leer el nuevo estado físico resultante
        state = self._get_telemetry()
        speed_kmh = state[1]
        perfectdriveLine = state[2]
        accel_z = state[6]
        
        # 3. Lógica de Recompensa Pura y detección de fin de episodio
        done = False
        truncated = False
        
        # Recompensa base: premiar ir rápido si estás en la línea
        desvio = abs(perfectdriveLine)/127
        reward = 20 * (1.0 - desvio) - (desvio)
        
        # Detecciones de fracaso
        if abs(perfectdriveLine) == 127 and self.steps_in_episode > 200:
            print("=== SALIDA CARRETERA ===")
            done = True
            self.crashed = True
            reward = -500.0
        elif accel_z < -40.0 and self.steps_in_episode > 200:
            print("=== CHOQUE ===")
            done = True
            self.crashed = True
            reward = -1000.0
        elif self.steps_in_episode > 600 and speed_kmh < 2.0 and acc_input > 0.5:
            done = True
            reward = -500.0
            self.crashed = True
            print("=== Coche atascado ===")

        info = {}
        return state, reward, done, truncated, info

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 1. Soltar mandos al instante
        self.gamepad.reset()
        self.gamepad.update()
        time.sleep(0.1)
        
        # 2. Secuencia exacta de botones para reiniciar la carrera en el Forza
        self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_START)
        self.gamepad.update()
        time.sleep(0.1)
        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_START)
        self.gamepad.update()
        time.sleep(0.6) # Un pelín más de margen para el menú
        
        self.gamepad.left_joystick(x_value=-32768, y_value=0)
        self.gamepad.update()
        time.sleep(0.2)
        self.gamepad.left_joystick(x_value=0, y_value=0)
        self.gamepad.update()
        time.sleep(0.6)
        
        self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        self.gamepad.update()
        time.sleep(0.1)
        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        self.gamepad.update()
        time.sleep(0.6)
        
        self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        self.gamepad.update()
        time.sleep(0.1)
        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        self.gamepad.update()
        
        print("Esperando 4 segundos a la pantalla de carga...")
        time.sleep(7.0)
        
        self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        self.gamepad.update()
        time.sleep(0.1)
        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        self.gamepad.update()
        
        print("Esperando 3 segundos finales para sincronizar la salida...")
        time.sleep(5.0)
        
        # 3. Limpieza absoluta del buffer de red para tirar a la basura los datos de cuando la IA pensaba
        self.sock.setblocking(False)
        while True:
            try:
                self.sock.recvfrom(1024)
            except BlockingIOError:
                break
        self.sock.setblocking(True)
        
        # 4. Ponemos todos los contadores de peligro a cero antes de dar luz verde
        self.steps_in_episode = 0
        self.crash_occurred = False 
        
        # 5. Devolver estado puro de la parrilla de salida
        state = self._get_telemetry()
        info = {}
        return state, info

    def close(self):
        self.sock.close()