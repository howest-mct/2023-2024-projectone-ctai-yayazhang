import RPi.GPIO as GPIO
import time

SERVO_PIN = 18 
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(0)

def set_servo_angle(angle):
    duty = angle / 18 + 2
    GPIO.output(SERVO_PIN, True)
    servo.ChangeDutyCycle(duty)
    time.sleep(1)
    GPIO.output(SERVO_PIN, False)
    servo.ChangeDutyCycle(0)
    print(f"Servo moved to {angle} degrees")

try:
    while True:
        print("Rotating to 0 degrees")
        set_servo_angle(0)    # Test with 0 degree
        time.sleep(2)
        print("Rotating to 90 degrees")
        set_servo_angle(90)   # Test with 90 degrees
        time.sleep(2)
        print("Rotating to 180 degrees")
        set_servo_angle(180)  # Test with 180 degrees
        time.sleep(2)
except KeyboardInterrupt:
    print("Stopping")
finally:
    servo.stop()
    GPIO.cleanup()
