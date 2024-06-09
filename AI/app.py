import socket
import threading
import cv2
import numpy as np
import time
import requests
from flask import Flask, render_template, Response, jsonify, request
from ultralytics import YOLO

server_address = ('192.168.168.167', 8500)  # Raspberry Pi IP and port

client_socket = None
receive_thread = None
shutdown_flag = threading.Event()

model = YOLO('AI/model/detect_cat_v8.pt')
conf_threshold = 0.55  # Updated confidence threshold
raspberry_pi_ip = '192.168.168.167'  # Raspberry Pi IP address

bbox_colors = {
    'Orange': (0, 255, 0),  # Green for Orange
    'Niuniu': (255, 0, 0)  # Red for Niuniu
}

app = Flask(__name__, template_folder='templates')

# Global variable to store annotated frame and predictions
annotated_frame = None
predictions = []
current_cat = None

def setup_socket_client():
    global client_socket, receive_thread
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(server_address)
    print("Connected to server")

    receive_thread = threading.Thread(target=receive_messages, args=(client_socket, shutdown_flag))
    receive_thread.start()

def receive_messages(sock, shutdown_flag):
    global annotated_frame, predictions
    sock.settimeout(1)
    data = b""
    try:
        while not shutdown_flag.is_set():
            try:
                packet = sock.recv(1024)  # Use a smaller buffer size to reduce latency
                if not packet:
                    break
                data += packet

                frames = data.split(b"END_FRAME")

                for frame in frames[:-1]:
                    np_arr = np.frombuffer(frame, np.uint8)
                    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    if img is not None:
                        annotated_frame, predictions = process_frame(img)
                data = frames[-1]
            except socket.timeout:
                continue
    except Exception as e:
        if not shutdown_flag.is_set():
            print(f"Connection error: {e}")
    finally:
        sock.close()

def process_frame(frame):
    global current_cat
    results = model(frame)
    annotated_frame = frame.copy()
    predictions = []

    for result in results:
        for bbox in result.boxes.data:
            x1, y1, x2, y2, score, class_id = bbox
            if score >= conf_threshold:
                label = model.names[int(class_id)]
                predictions.append(f"{label}: {score:.2f}")
                color = bbox_colors.get(label, (255, 255, 255))  # Default to white if label not found
                cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(annotated_frame, f"{label} {score:.2f}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

                if score >= 0.55:
                    if current_cat != label:
                        send_command(f"cat_{label.lower()}")
                        current_cat = label

    if current_cat and not any(label in p for p in predictions):
        send_command('close')
        current_cat = None

    return annotated_frame, predictions

def send_command(command):
    requests.post(f'http://{raspberry_pi_ip}:5000/command', json={'command': command})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            if annotated_frame is not None:
                _, buffer = cv2.imencode('.jpg', annotated_frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)  # Reduce the sleep time to increase frame rate
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/predictions')
def get_predictions():
    return jsonify(predictions=predictions)

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video-file' not in request.files:
        return jsonify({'error': 'No video file part'}), 400
    file = request.files['video-file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    file.save('uploads/' + file.filename)
    return jsonify({'success': 'File uploaded successfully'}), 200

@app.route('/process_video', methods=['POST'])
def process_uploaded_video():
    video_path = 'uploads/' + request.files['video-file'].filename
    cap = cv2.VideoCapture(video_path)
    global annotated_frame, predictions

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        annotated_frame, predictions = process_frame(frame)

    cap.release()
    return jsonify({'success': 'Video processed successfully'}), 200

def main():
    global client_socket, receive_thread
    setup_socket_client()
    client_socket.sendall('start_video'.encode())

    flask_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000})
    flask_thread.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("Client disconnecting...")
        shutdown_flag.set()
    finally:
        client_socket.close()
        receive_thread.join()
        print("Client stopped gracefully")

if __name__ == "__main__":
    main()
