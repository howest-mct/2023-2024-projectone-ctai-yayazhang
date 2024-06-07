import socket
import threading
import cv2
from ultralytics import YOLO
import tempfile
import streamlit as st
import numpy as np

# Connect to Raspberry Pi
server_address = ('192.168.168.167', 8500)
client_socket = None
receive_thread = None
shutdown_flag = threading.Event()

# setup client socket and connect to server
def setup_socket_client():
    global client_socket, receive_thread
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(server_address)
    print("Connected to server")

    receive_thread = threading.Thread(target=receive_messages, args=(client_socket, shutdown_flag))
    receive_thread.start()

# receive messages from server
def receive_messages(sock, shutdown_flag):
    sock.settimeout(1) # set timeout for socket receive
    counter = 0
    try:
        while not shutdown_flag.is_set():
            try:
                # receive data from server
                data = sock.recv(1024)
                if not data:
                    break
                print("Received from server:", data.decode(errors='ignore'))
                counter += 1

                # send response back to server
                response = "{} message(s) received".format(counter)
                sock.sendall(response.encode())
            except socket.timeout:
                continue
    except Exception as e:
        if not shutdown_flag.is_set():
            print(f"Connection error: {e}")
    finally:
        sock.close()

# Call socket client socket connection
setup_socket_client()

# Load the model
model = YOLO('AI/model/detect_cat_v9.pt')

# streamlit page configuration
st.set_page_config(page_title="Cat Detection", layout="wide")
st.title("Cat Detection")

# Threshold slider
conf_threshold = st.slider("Confidence Threshold", min_value=0.0, max_value=1.0, value=0.5)

# Placeholders for displaying video and results
image_placeholder = st.empty()
results_placeholder = st.empty()
feeder_status = st.empty()

# Initial states for cat detection and feeder status
current_state = 'close'
cat_detected = False

# process video from a local camera or file
def process_video(video_source, conf_threshold, frame_skip=5):
    global current_state, cat_detected

    # open the video source (webcame or file)
    cap = cv2.VideoCapture(video_source)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # set buffer size to 1 to reduce latency
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read() # read frame from video source
        if not ret:
            break

        frame_count += 1
        if frame_count % frame_skip != 0:
            continue # skip frames to reduce processing load

        # Inference
        results = model(frame)
        annotated_frame = frame.copy()
        predictions = []

        # Check if any cat is detected with confidence above threshold
        cat_detected = False
        for result in results:
            for bbox in result.boxes.data:
                x1, y1, x2, y2, score, class_id = bbox
                if score >= conf_threshold:
                    label = model.names[int(class_id)]
                    predictions.append(f"Class: {label}, Confidence: {score:.2f}")

                    # draw bounding box and label on the frame
                    cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                    cv2.putText(annotated_frame, f"{label} {score:.2f}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

                    # send command to feeder based on detection result
                    if label == 'Orange' and score >= 0.6:
                        if current_state != 'cat orange':
                            client_socket.sendall('cat orange'.encode())
                            current_state = 'cat orange'
                            feeder_status.text("Feeder Status: Opening for Cat Orange")
                        cat_detected = True
                    elif label == 'Niuniu' and score >= 0.6:
                        if current_state != 'cat niuniu':
                            client_socket.sendall('cat niuniu'.encode())
                            current_state = 'cat niuniu'
                            feeder_status.text("Feeder Status: Opening for Cat Niuniu")
                        cat_detected = True

        if not cat_detected and current_state != 'close':
            client_socket.sendall('close'.encode())
            current_state = 'close'
            feeder_status.text("Feeder Status: Closed")

        # display annotated frome and prediction results
        annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        image_placeholder.image(annotated_frame, channels="RGB")
        results_placeholder.text("\n".join(predictions))

    cap.release()

# process video reveived from pi over a socket
def process_video_from_socket(sock, conf_threshold, frame_skip=5):
    global current_state, cat_detected

    frame_count = 0
    data = b""

    while True:
        try:
            packet = sock.recv(4096) # receive data from socket
            if not packet:
                break
            data += packet

            # frame seprarate by a delimiter "END_FRAME"
            frames = data.split(b"END_FRAME")

            for frame in frames[:-1]:
                frame_count += 1
                if frame_count % frame_skip != 0:
                    continue # skip frames to reduce processing load

                # Decode frame from received data
                np_arr = np.frombuffer(frame, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if img is None:
                    continue

                # Inference
                results = model(img)
                annotated_frame = img.copy()
                predictions = []

                # Check if any cat is detected with confidence above threshold
                cat_detected = False
                for result in results:
                    for bbox in result.boxes.data:
                        x1, y1, x2, y2, score, class_id = bbox
                        if score >= conf_threshold:
                            label = model.names[int(class_id)]
                            predictions.append(f"Class: {label}, Confidence: {score:.2f}")

                            # draw bounding box and label on the frame
                            cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                            cv2.putText(annotated_frame, f"{label} {score:.2f}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

                            # send command to feeder based on detection result
                            if label == 'Orange' and score >= 0.6:
                                if current_state != 'cat orange':
                                    client_socket.sendall('cat orange'.encode())
                                    current_state = 'cat orange'
                                    feeder_status.text("Feeder Status: Opening for Cat Orange")
                                cat_detected = True
                            elif label == 'Niuniu' and score >= 0.6:
                                if current_state != 'cat niuniu':
                                    client_socket.sendall('cat niuniu'.encode())
                                    current_state = 'cat niuniu'
                                    feeder_status.text("Feeder Status: Opening for Cat Niuniu")
                                cat_detected = True

                if not cat_detected and current_state != 'close':
                    client_socket.sendall('close'.encode())
                    current_state = 'close'
                    feeder_status.text("Feeder Status: Closed")
                
                # display annotated frome and prediction results
                annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                image_placeholder.image(annotated_frame, channels="RGB")
                results_placeholder.text("\n".join(predictions))

            data = frames[-1]  # Keep the last incomplete frame
        except Exception as e:
            print(f"Error receiving video frame: {e}")
            break

# select video source
st.sidebar.title("Video Source")
source = st.sidebar.radio("Choose the video source", ("External Camera", "Webcam", "Upload"))

# process video based on selected source
if source == "Raspberry Pi Camera":
    client_socket.sendall('start_video'.encode())
    process_video_from_socket(client_socket, conf_threshold)
elif source == "Webcam":
    process_video(0, conf_threshold)
else:
    uploaded_file = st.sidebar.file_uploader("Upload a video", type=["mp4"])
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name
        
        process_video(tmp_file_path, conf_threshold)
