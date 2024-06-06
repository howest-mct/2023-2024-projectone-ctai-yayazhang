import socket
import cv2
from ultralytics import YOLO
import numpy as np
import streamlit as st

# Load the model
model = YOLO('AI/model/detect_cat_v8.pt')

# Streamlit configuration
st.set_page_config(page_title="Cat Detection", layout="wide")
st.title("Cat Detection")

conf_threshold = st.slider("Confidence Threshold", min_value=0.0, max_value=1.0, value=0.7)

# Placeholder for images and results
image_placeholder = st.empty()
results_placeholder = st.empty()

def setup_image_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8501))  # Bind to all interfaces
    server_socket.listen(1)
    client_socket, addr = server_socket.accept()
    print(f"Connected by {addr}")

    while True:
        # Receive image size first
        data = client_socket.recv(4)
        if not data:
            break
        img_size = int.from_bytes(data, byteorder='big')
        # Then receive the image
        img_data = b''
        while len(img_data) < img_size:
            packet = client_socket.recv(4096)
            if not packet:
                break
            img_data += packet

        # Convert bytes to image
        nparr = np.frombuffer(img_data, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Process image with YOLO model
        results = model(img_np)
        predictions = []
        for result in results:
            for bbox in result.boxes.data:
                x1, y1, x2, y2, score, class_id = bbox
                if score >= conf_threshold:
                    label = model.names[int(class_id)]
                    predictions.append(f"Class: {label}, Confidence: {score:.2f}")
                    cv2.rectangle(img_np, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                    cv2.putText(img_np, f"{label} {score:.2f}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

        # Display the image with Streamlit
        image_placeholder.image(img_np, channels="BGR")
        results_placeholder.text("\n".join(predictions))

    client_socket.close()

try:
    threading.Thread(target=setup_image_server).start()
except KeyboardInterrupt:
    print("Client shutting down")
