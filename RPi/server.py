import socket
import cv2
import numpy as np

def send_images():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('192.168.168.10', 8501))  # IP address and port of the laptop

    cap = cv2.VideoCapture(0)  # 0 for default camera, change if using a different camera
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        _, buffer = cv2.imencode('.jpg', frame)
        jpg_as_text = np.array(buffer).tobytes()

        # Send image size first
        client_socket.sendall(len(jpg_as_text).to_bytes(4, byteorder='big'))
        # Then send the image
        client_socket.sendall(jpg_as_text)

    cap.release()
    client_socket.close()

if __name__ == "__main__":
    send_images()
