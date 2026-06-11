import socket
import struct

UDP_IP = "127.0.0.1"
UDP_PORT = 5123

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((UDP_IP, UDP_PORT))

print(f"Escuchando telemetria de Forza en {UDP_IP}:{UDP_PORT}...")

try:
    while True:
        data, addr = sock.recvfrom(1024)
        
        current_engine_rpm = struct.unpack('f', data[16:20])[0]
        
        speed_ms = struct.unpack('f', data[256:260])[0]
        speed_kmh = speed_ms * 3.6
        
        perfectdriveLine = struct.unpack('b', data[321:322])[0]
        
        slip_fl = abs(struct.unpack('f', data[180:184])[0])
        slip_fr = abs(struct.unpack('f', data[184:188])[0])
        slip_rl = abs(struct.unpack('f', data[188:192])[0])
        slip_rr = abs(struct.unpack('f', data[192:196])[0])

        angularVelY = round(struct.unpack('f', data[48:52])[0], 4)
        
        slip_delantero = (slip_fl + slip_fr) / 2
        slip_trasero = (slip_rl + slip_rr) / 2
        
        accel_x = round(struct.unpack('f', data[20:24])[0],4)
        accel_z = round(struct.unpack('f', data[28:32])[0],4)

        print(f"RPM: {current_engine_rpm:.0f} | Velocidad: {speed_kmh:.1f} km/h, LINE: {perfectdriveLine}, SLIP DEL: {slip_delantero:.2f}, SLIP TRAS: {slip_trasero:.2f}, ANG: {angularVelY}, Accel_x: {accel_x}, Accel_z: {accel_z}", end="\r")

except KeyboardInterrupt:
    print("\nDeteniendo receptor de telemetria.")
finally:
    sock.close()