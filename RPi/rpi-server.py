import socket
import threading
import time
from RPi import GPIO
import cv2

# GPIO setup
SERVO_PIN = 18 
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo = GPIO.PWM(SERVO_PIN, 50) 
servo.start(0)

# Global vars
client_socket = None
server_socket = None
server_thread = None
shutdown_flag = threading.Event()

def set_servo_angle(angle):
    duty = angle / 18 + 2
    GPIO.output(SERVO_PIN, True)
    servo.ChangeDutyCycle(duty)
    time.sleep(1)
    GPIO.output(SERVO_PIN, False)
    servo.ChangeDutyCycle(0)
    print(f"Servo moved to {angle} degrees")

def setup_socket_server():
    global server_socket, server_thread, shutdown_flag
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8500))
    server_socket.settimeout(0.2)
    server_socket.listen(1)
    
    server_thread = threading.Thread(target=accept_connections, args=(shutdown_flag,), daemon=True)
    server_thread.start()

def accept_connections(shutdown_flag):
    global client_socket
    print("Accepting connections")
    while not shutdown_flag.is_set():
        try:
            client_socket, addr = server_socket.accept()
            print("Connected by", addr)
            client_thread = threading.Thread(target=handle_client, args=(client_socket, shutdown_flag,))
            client_thread.start()
        except socket.timeout:
            pass

def handle_client(sock, shutdown_flag):
    global cap
    try:
        while not shutdown_flag.is_set():
            data = sock.recv(1024)
            if not data:
                break
            message = data.decode(errors='ignore')
            print(f"Received from client: {message}")
            if message == 'start_video':
                cap = cv2.VideoCapture(0)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                send_video(sock)
            elif message == 'cat orange':
                set_servo_angle(120)  # Rotate to Orange Food
            elif message == 'cat niuniu':
                set_servo_angle(0)  # Rotate to Niuniu Food
            elif message == 'close':
                set_servo_angle(60)  # Rotate to Close (Open Shade)
    except socket.timeout:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cap' in globals():
            cap.release()
        sock.close()

def send_video(sock):
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            _, buffer = cv2.imencode('.jpg', frame)
            sock.sendall(buffer.tobytes() + b"END_FRAME")
    except Exception as e:
        print(f"Error sending video frame: {e}")

try:
    setup_socket_server()
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    print("Server shutting down")
    shutdown_flag.set()
finally:
    server_thread.join()
    server_socket.close()
    servo.stop()
    GPIO.cleanup()
