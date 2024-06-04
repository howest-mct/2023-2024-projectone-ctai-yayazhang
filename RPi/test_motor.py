import RPi as GPIO
from time import sleep

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(18, GPIO.OUT)

servo_pwm = GPIO.PWM(18, 50)
servo_pwm.start(0)

def set_servo_angle(angle):
    duty_cycle = 2.5 + (angle / 18.0)
    servo_pwm.ChangeDutyCycle(duty_cycle)
    sleep(0.5) 
    servo_pwm.ChangeDutyCycle(0) 

try:
    current_angle = 0
    set_servo_angle(current_angle) 
    print("Press and hold GPIO 21 to toggle the servo motor between 0 and 180 degrees.")
    while True:
        if GPIO.input(21) == GPIO.LOW:
            print("Button pressed, moving servo motor")
            current_angle = 180 if current_angle == 0 else 0 
            set_servo_angle(current_angle)
            sleep(0.5)
        else:
            sleep(0.1) 

except KeyboardInterrupt:
    print("Program stopped by user")
finally:
    servo_pwm.stop()
    GPIO.cleanup()
