import socket
import threading
import time
from flask import Flask, Response, request
import cv2
from RPi import GPIO

# Initialize the camera
camera = cv2.VideoCapture(0)

# Set lower latency settings if available
camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
camera.set(cv2.CAP_PROP_FPS, 30)

# GPIO setup for the stepper motor
GPIO.setmode(GPIO.BCM)  # Set the GPIO mode
control_pins = [19, 13, 6, 5]
for pin in control_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, 0)

# Stepper motor step sequence
step_sequence = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1]
]

def rotate_stepper(steps, delay=0.001, direction='clockwise'):
    if direction == 'counterclockwise':
        step_sequence.reverse()

    for _ in range(abs(steps)):
        for step in step_sequence:
            for pin in range(4):
                GPIO.output(control_pins[pin], step[pin])
            time.sleep(delay)

    if direction == 'counterclockwise':
        step_sequence.reverse()  # Reset sequence to original

# GPIO setup for LEDs
LED_RED = 5
LED_GREEN = 6
LED_BLUE = 13
GPIO.setup(LED_RED, GPIO.OUT)
GPIO.setup(LED_BLUE, GPIO.OUT)
GPIO.setup(LED_GREEN, GPIO.OUT)

GPIO.output(LED_GREEN, True)

app = Flask(__name__)

# Global vars 
client_socket = None
server_socket = None
server_thread = None
shutdown_flag = threading.Event()

current_position = 'center'

def set_stepper_position(position):
    global current_position

    if position == 'cat_orange' and current_position != 'right':
        if current_position == 'left':
            rotate_stepper(256, direction='clockwise')  # Move from left to center
        rotate_stepper(256, direction='clockwise')  # Move from center to right
        current_position = 'right'
    elif position == 'cat_niuniu' and current_position != 'left':
        if current_position == 'right':
            rotate_stepper(256, direction='counterclockwise')  # Move from right to center
        rotate_stepper(256, direction='counterclockwise')  # Move from center to left
        current_position = 'left'
    elif position == 'close' and current_position != 'center':
        if current_position == 'right':
            rotate_stepper(256, direction='counterclockwise')  # Move from right to center
        elif current_position == 'left':
            rotate_stepper(256, direction='clockwise')  # Move from left to center
        current_position = 'center'

def turn_led_red():
    GPIO.output(LED_GREEN, False)
    GPIO.output(LED_RED, True)
    print("LED turned red")

def turn_led_green():
    GPIO.output(LED_RED, False)
    GPIO.output(LED_GREEN, True)
    print("LED turned green")

@app.route('/video_feed')
def video_feed():
    def generate_frames():
        while True:
            success, frame = camera.read()
            if not success:
                break
            else:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/command', methods=['POST'])
def command():
    global current_state
    data = request.json
    command = data.get('command')
    print(f"Received command: {command}")

    if command == 'cat_orange':
        set_stepper_position('cat_orange')
        current_state = 'cat orange'
    elif command == 'cat_niuniu':
        set_stepper_position('cat_niuniu')
        current_state = 'cat niuniu'
    elif command == 'close':
        set_stepper_position('close')
        current_state = 'close'
    return '', 204

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
    try:
        while not shutdown_flag.is_set():
            data = sock.recv(512) 
            if not data:
                break
            message = data.decode(errors='ignore')
            print(f"Received from client: {message}")
            if message == 'start_video':
                send_video(sock)
            elif message == 'cat_orange':
                set_stepper_position('cat_orange')
            elif message == 'cat_niuniu':
                set_stepper_position('cat_niuniu')
            elif message == 'close':
                set_stepper_position('close')
    except socket.timeout:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()

def send_video(sock):
    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                break
            _, buffer = cv2.imencode('.jpg', frame)
            sock.sendall(buffer.tobytes() + b"END_FRAME")
    except Exception as e:
        print(f"Error sending video frame: {e}")

###### MAIN PART ######
try:
    setup_socket_server()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    print("Server shutting down")
    shutdown_flag.set()
finally:
    server_thread.join()
    server_socket.close()
    GPIO.cleanup()
