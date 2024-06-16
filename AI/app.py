import threading
import time
import socket
import cv2
import numpy as np
import requests
import streamlit as st
from ultralytics import YOLO

# Initialize configurations
server_address = ('192.168.168.167', 8500)
model = YOLO('AI/model/detect_cat_v9.pt')
conf_threshold = 0.55
raspberry_pi_ip = '192.168.168.167'
bbox_colors = {'Orange': (0, 255, 0), 'Niuniu': (255, 0, 0)}

# global variables
client_socket = None
receive_thread = None
shutdown_flag = threading.Event()
annotated_frame = None
predictions = []
current_cat = None
last_detection_time = 0
door_open = False
stop_stream_flag = threading.Event()
cat_detection_queue = []

door_state_lock = threading.Lock()

def setup_socket_client():
    global client_socket, receive_thread
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(server_address)
    receive_thread = threading.Thread(target=receive_messages, args=(client_socket, shutdown_flag))
    receive_thread.start()

def close_socket_client():
    global client_socket, shutdown_flag, receive_thread
    shutdown_flag.set()
    if client_socket:
        client_socket.close()
    if receive_thread:
        receive_thread.join()
    client_socket = None
    shutdown_flag.clear()

def receive_messages(sock, shutdown_flag):
    global annotated_frame, predictions
    sock.settimeout(1)
    data = b""
    try:
        while not shutdown_flag.is_set():
            try:
                packet = sock.recv(1024)
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
    global current_cat, conf_threshold, last_detection_time, door_open, cat_detection_queue
    results = model(frame)
    annotated_frame = frame.copy()
    predictions = []
    detected = False
    current_time = time.time()
    for result in results:
        for bbox in result.boxes.data:
            x1, y1, x2, y2, score, class_id = bbox
            if score >= conf_threshold:
                label = model.names[int(class_id)]
                predictions.append(f"{label}: {score:.2f}")
                color = bbox_colors.get(label, (255, 255, 255))
                cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(annotated_frame, f"{label} {score:.2f}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                detected = True
                cat_detection_queue.append((label, current_time))

    # Filter out old detections
    cat_detection_queue = [cat for cat in cat_detection_queue if current_time - cat[1] <= 2]

    if detected:
        with door_state_lock:
            if not door_open and cat_detection_queue:
                first_detected_cat = cat_detection_queue[0][0]
                if current_cat != first_detected_cat:
                    send_command(f"cat_{first_detected_cat.lower()}")
                    current_cat = first_detected_cat
                    last_detection_time = current_time
                    door_open = True
                    threading.Timer(2.0, lambda: close_door()).start()
    return annotated_frame, predictions

def close_door():
    global door_open, current_cat, cat_detection_queue
    with door_state_lock:
        send_command('close')
        door_open = False
        # Do not reset current_cat to allow for new detection logic

def send_command(command):
    requests.post(f'http://{raspberry_pi_ip}:5000/command', json={'command': command})

# Initialize Streamlit session state
if 'stream_started' not in st.session_state:
    st.session_state.stream_started = False
if 'predictions' not in st.session_state:
    st.session_state.predictions = "None"
if 'door_state' not in st.session_state:
    st.session_state.door_state = "Closed"

def start_laptop_camera_stream(image_placeholder, info_placeholder, door_state_placeholder):
    st.session_state.stream_started = True
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("Error: Could not open video stream from laptop camera.")
        return
    while st.session_state.stream_started:
        ret, frame = cap.read()
        if not ret:
            st.error("Error: Could not read frame from laptop camera.")
            break
        annotated_frame, predictions = process_frame(frame)
        image_placeholder.image(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB), channels="RGB")
        st.session_state.predictions = predictions
        st.session_state.door_state = f"Food Door: {'Open for ' + (current_cat if current_cat else '') if door_open else 'Closed'}"
        info_placeholder.text(f"Predictions: {st.session_state.predictions}")
        door_state_placeholder.text(st.session_state.door_state)
        time.sleep(0.1)
    cap.release()

def start_rpi_camera_stream(image_placeholder, info_placeholder, door_state_placeholder):
    st.session_state.stream_started = True
    setup_socket_client()
    client_socket.sendall('start_video'.encode())
    while st.session_state.stream_started:
        if annotated_frame is not None:
            image_placeholder.image(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB), channels="RGB")
            st.session_state.predictions = predictions
            st.session_state.door_state = f"Food Door: {'Open for ' + (current_cat if current_cat else '') if door_open else 'Closed'}"
            info_placeholder.text(f"Predictions: {st.session_state.predictions}")
            door_state_placeholder.text(st.session_state.door_state)
        time.sleep(0.1)
    if client_socket:
        client_socket.sendall('stop_video'.encode())
    close_socket_client()

def process_uploaded_video(video_path, image_placeholder, info_placeholder, door_state_placeholder):
    st.session_state.stream_started = True
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        st.error("Error: Could not open uploaded video file.")
        return
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        annotated_frame, predictions = process_frame(frame)
        image_placeholder.image(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB), channels="RGB")
        st.session_state.predictions = predictions
        st.session_state.door_state = f"Food Door: {'Open for ' + (current_cat if current_cat else '') if door_open else 'Closed'}"
        info_placeholder.text(f"Predictions: {st.session_state.predictions}")
        door_state_placeholder.text(st.session_state.door_state)
    cap.release()
    st.sidebar.success("Video processed successfully")

def main():
    global conf_threshold

    st.markdown("<h1 style='text-align: center;'>Cat Detection and Control System</h1>", unsafe_allow_html=True)

    # Slider for confidence threshold
    threshold = st.slider('Confidence Threshold', min_value=0.0, max_value=1.0, value=conf_threshold, key="confidence_threshold")
    if threshold != conf_threshold:
        conf_threshold = threshold

    # Default placeholders for detection results
    st.write("### Detection Results")
    image_placeholder = st.empty()
    info_placeholder = st.empty()
    door_state_placeholder = st.empty()
    
    info_placeholder.text(f"Predictions: {st.session_state.predictions}")
    door_state_placeholder.text(st.session_state.door_state)

    # Sidebar options
    selected_option = st.sidebar.radio("Select Input Source", ["Laptop Camera", "Raspberry Pi Camera", "Upload Video"])

    if selected_option == "Laptop Camera" and not st.session_state.stream_started:
        st.sidebar.button('Start Laptop Camera Stream', on_click=lambda: start_laptop_camera_stream(image_placeholder, info_placeholder, door_state_placeholder), key="start_laptop")
        st.sidebar.button('Stop Video Stream', on_click=lambda: st.session_state.update(stream_started=False), key="stop_laptop")

    if selected_option == "Raspberry Pi Camera" and not st.session_state.stream_started:
        st.sidebar.button('Start Raspberry Pi Camera Stream', on_click=lambda: start_rpi_camera_stream(image_placeholder, info_placeholder, door_state_placeholder), key="start_rpi")
        st.sidebar.button('Stop Video Stream', on_click=lambda: st.session_state.update(stream_started=False), key="stop_rpi")

    if selected_option == "Upload Video":
        uploaded_file = st.sidebar.file_uploader("Upload Video", key="upload_video")
        if uploaded_file is not None:
            video_path = 'uploads/' + uploaded_file.name
            with open(video_path, 'wb') as f:
                f.write(uploaded_file.read())
            st.sidebar.success("File uploaded successfully")
            st.sidebar.button('Process Uploaded Video', on_click=lambda: process_uploaded_video(video_path, image_placeholder, info_placeholder, door_state_placeholder), key="process_upload")

if __name__ == "__main__":
    main()
