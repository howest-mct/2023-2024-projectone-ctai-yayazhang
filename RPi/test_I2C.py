import smbus
import time

# Initialize I2C (SMBus)
bus = smbus.SMBus(1)

# The address of the I2C device (example address)
DEVICE_ADDRESS = 0x48

def scan_i2c_bus():
    print("Scanning I2C bus...")
    for device in range(128):
        try:
            bus.write_byte(device, 0)
            print(f"Found device at address: {hex(device)}")
        except OSError:
            pass

def read_device(address):
    try:
        value = bus.read_byte(address)
        print(f"Read value: {value} from address: {hex(address)}")
    except OSError as e:
        print(f"Failed to read from address {hex(address)}: {e}")

try:
    scan_i2c_bus()
    time.sleep(1)
    read_device(DEVICE_ADDRESS)
except KeyboardInterrupt:
    print("Program interrupted")
finally:
    print("Program ended")
