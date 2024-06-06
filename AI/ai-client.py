import socket
import threading
import cv2
import numpy as np
from ultralytics import YOLO
import streamlit as st
import queue

# Connect to Raspberry Pi
server_address = ('192.168.168.167', 8500)
client_socket = None
receive_thread = None
shutdown_flag = threading.Event()
frame_queue = queue.Queue()

def setup_socket_client():
    global client_socket, receive_thread
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(server_address)
    print("Connected to server")

    receive_thread = threading.Thread(target=receive_video_stream, args=(client_socket, shutdown_flag, frame_queue))
    receive_thread.start()

def receive_video_stream(sock, shutdown_flag, frame_queue):
    sock.settimeout(1)
    data = b''
    try:
        while not shutdown_flag.is_set():
            try:
                packet = sock.recv(4096)
                if not packet:
                    break
                data += packet
                a = data.find(b'\xff\xd8')
                b = data.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = data[a:b+2]
                    data = data[b+2:]
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    frame_queue.put(frame)
            except socket.timeout:
                continue
    except Exception as e:
        if not shutdown_flag.is_set():
            print(f"Connection error: {e}")
    finally:
        sock.close()

def process_frame(frame, sock):
    results = model(frame)
    annotated_frame = frame.copy()
    predictions = []

    global current_state, cat_detected
    cat_detected = False
    for result in results:
        for bbox in result.boxes.data:
            x1, y1, x2, y2, score, class_id = bbox
            if score >= conf_threshold:
                label = model.names[int(class_id)]
                predictions.append(f"Class: {label}, Confidence: {score:.2f}")
                cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                cv2.putText(annotated_frame, f"{label} {score:.2f}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

                if label == 'Orange' and score >= 0.6:
                    if current_state != 'cat orange':
                        sock.sendall('cat orange'.encode())
                        current_state = 'cat orange'
                        st.session_state['feeder_status'] = "Feeder Status: Opening for Cat Orange"
                    cat_detected = True
                elif label == 'Niuniu' and score >= 0.6:
                    if current_state != 'cat niuniu':
                        sock.sendall('cat niuniu'.encode())
                        current_state = 'cat niuniu'
                        st.session_state['feeder_status'] = "Feeder Status: Opening for Cat Niuniu"
                    cat_detected = True

    if not cat_detected and current_state != 'close':
        sock.sendall('close'.encode())
        current_state = 'close'
        st.session_state['feeder_status'] = "Feeder Status: Closed"

    annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    st.session_state['annotated_frame'] = annotated_frame
    st.session_state['predictions'] = predictions

# Initialize Streamlit session state
if 'frame' not in st.session_state:
    st.session_state['frame'] = None
if 'annotated_frame' not in st.session_state:
    st.session_state['annotated_frame'] = None
if 'predictions' not in st.session_state:
    st.session_state['predictions'] = []
if 'feeder_status' not in st.session_state:
    st.session_state['feeder_status'] = "Feeder Status: Closed"

# Call socket client
setup_socket_client()

# Load the model
model = YOLO('AI/model/detect_cat_v9.pt')

# Page configuration
st.set_page_config(page_title="Cat Detection", layout="wide")
st.title("Cat Detection")

# Threshold slider
conf_threshold = st.slider("Confidence Threshold", min_value=0.0, max_value=1.0, value=0.5)

image_placeholder = st.empty()
results_placeholder = st.empty()
feeder_status = st.empty()

# Initial states
current_state = 'close'
cat_detected = False

# Main loop to update Streamlit UI
while True:
    if not frame_queue.empty():
        frame = frame_queue.get()
        if frame is not None:
            process_frame(frame, client_socket)

    if st.session_state['annotated_frame'] is not None:
        image_placeholder.image(st.session_state['annotated_frame'], channels="RGB")
    
    if st.session_state['predictions']:
        results_placeholder.text("\n".join(st.session_state['predictions']))

    feeder_status.text(st.session_state['feeder_status'])
