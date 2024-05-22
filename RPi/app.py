import threading
import queue

# Bluez gatt uart service (SERVER)
from bluetooth_uart_server.bluetooth_uart_server import ble_gatt_uart_loop

import RPi.GPIO as GPIO
import time
import smbus2

### ---------------- make a class of this -------------------###





class LCD:


  I2C_ADDR  = 0x27 # I2C device address
  LCD_WIDTH = 16   # Maximum characters per line
  LCD_CHR = 1 # bit value for bit0; sets mode - Sending data
  LCD_CMD = 0 # bit value for bit0; bit0 sets mode - Sending command
  LCD_LINE_1 = 0x80 | 0x0   # Instruction to go to beginning of line 1
  LCD_LINE_2 = 0x80 | 0x40    # Instruction to go to beginning of line 2
  LCD_BACKLIGHT = 0x08 # Data bit value to turn backlight on
  ENABLE =  0x04 # Enable bit value
  # ENABLE_LOW =
  E_PULSE = 0.0002
  E_DELAY = 0.0002
  BOX = 0b11011011


  def __init__(self) -> None:
    self.i2c = smbus2.SMBus(1)
    self.lcd_init()

  def send_byte_with_e_toggle(self, bits):
    time.sleep(self.E_DELAY)
    # send data with E bit HIGH
    self.i2c.write_byte(self.I2C_ADDR, bits | self.ENABLE)
    time.sleep(self.E_PULSE)
    self.i2c.write_byte(self.I2C_ADDR, bits)
    time.sleep(self.E_DELAY)
    # latch the data

  def lcd_init(self):
    self.send_byte_with_e_toggle(0x30) # 8-bit
    self.send_byte_with_e_toggle(0x30) # 8-bit
    self.send_byte_with_e_toggle(0x20) # 4-bit

    self.send_instruction(0x0C) # Display on
    self.send_instruction(0x28) # 2-lines and 5x7 pixels
    self.send_instruction(0x01) # clear
    time.sleep(self.E_DELAY)


  def send_bits(self,bits,mode):
    # isolating the MSN
    # OR with mode to set the required mode
    bits_high = mode | (bits & 0xF0) | self.LCD_BACKLIGHT
    # isolating the LSN
    bits_low = mode | ((bits << 4) & 0xF0) | self.LCD_BACKLIGHT
    self.send_byte_with_e_toggle(bits_high)
    time.sleep(self.E_DELAY)
    self.send_byte_with_e_toggle(bits_low)
    time.sleep(self.E_DELAY)


  def send_instruction(self, value):
    self.send_bits(value, self.LCD_CMD)
    time.sleep(0.01)

  def send_char(self, value):
    bits = ord(value)
    self.send_bits(bits, self.LCD_CHR)
    time.sleep(0.01)

  def send_string(self, msg, line):
    if len(msg) <= self.LCD_WIDTH:
      if line == 1:
        self.send_instruction(self.LCD_LINE_1)
      elif line == 2:
        self.send_instruction(self.LCD_LINE_2)

      else:
        raise ValueError("Invalid line")

      for char in msg:
        self.send_char(char)

    else:
      self.display_scrolling_string(msg, line)

  def clear(self):
    self.send_instruction(0x01)
    time.sleep(self.E_DELAY)

  def display_scrolling_string(self, message, line):

    # Calculate the number of scroll positions needed
    scroll_positions = len(message) - self.LCD_WIDTH + 1

    # Continuously scroll the string
    while True:
      for position in range(scroll_positions):
        # Send the portion of the string to be displayed
        start_index = position
        end_index = start_index + self.LCD_WIDTH
        self.send_string(message[start_index:end_index], line)
        time.sleep(0.5)  # Adjust scrolling speed

  def set_ddram(self, ddram, msg):
    self.send_instruction(0x80 | ddram)
    for char in msg:
      self.send_char(char)

  def segment_string(self, msg):
    words = msg.split(" ")
    l1 = ''
    l2 = ''
    for word in words:
      if len(l1) + len(word) + 1 < 16:
        l1 += word + " "
      elif len(l1) + len(word) > 16:
        l2 += word + " "
      elif len(l1) + len(word) == 16:
        l1 += word
      elif len(l2) + len(word) +1 <= 16 and len(l1) == 16:
        l2 += word + " "

    self.send_string(l1,1)
    self.send_string(l2,2)

def main():
    i = 0
    rx_q = queue.Queue()
    tx_q = queue.Queue()
    device_name = "yaya-zhang" # TODO: replace with your own (unique) device name
    threading.Thread(target=ble_gatt_uart_loop, args=(rx_q, tx_q, device_name), daemon=True).start()
    while True:
        try:
            incoming = rx_q.get(timeout=1) # Wait for up to 1 second 
            if incoming:
                print("In main loop: {}".format(incoming))
        except Exception as e:
            pass # nothing in Q 

        # if i%5 == 0: # Send some data every 5 iterations
        #     tx_q.put("test{}".format(i))
        # i += 1
if __name__ == '__main__':
    main()


