from RPi import GPIO
from time import sleep
import smbus


i2c = smbus.SMBus(1)
pin = 18
GPIO.setup(pin, GPIO.OUT)

pwm = GPIO.PWM(pin, 50)
pwm.start(7)

a6_command = 0b1011
ADC_adr = 0x48

def read_joystick():
  i2c.write_byte(ADC_adr, (a6_command << 4 | 0x4))
  analog_val = i2c.read_byte(ADC_adr)/ 25.5 + 3
  return analog_val

try:
  while True:
    pwm.ChangeDutyCycle(read_joystick())

except KeyboardInterrupt:
    print("Interrupted by user")
finally:
    GPIO.cleanup()
    print("Pins off")