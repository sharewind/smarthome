# -*- coding: utf-8 -*-

try:
  import RPi.GPIO as GPIO
except RuntimeError:
  print("Error importing RPi.GPIO!\n")
  print("This is probably because you need superuser privileges.\n")
  print("You can achieve this by using 'sudo' to run your script.\n")

PIN_1 = 8
PIN_2 = 10
PIN_3 = 12
PIN_4 = 16

def init():
	GPIO.setmode(GPIO.BOARD)
	GPIO.setwarnings(False)
	GPIO.setup(PIN_1, GPIO.OUT, initial = GPIO.LOW)
	GPIO.setup(PIN_2, GPIO.OUT, initial = GPIO.LOW)
	GPIO.setup(PIN_3, GPIO.OUT, initial = GPIO.LOW)
	GPIO.setup(PIN_4, GPIO.OUT, initial = GPIO.LOW)

def open():
	GPIO.output(PIN_1, GPIO.HIGH)
	GPIO.output(PIN_2, GPIO.HIGH)
	GPIO.output(PIN_3, GPIO.HIGH)
	GPIO.output(PIN_4, GPIO.HIGH)

def close():
	GPIO.output(PIN_1, GPIO.LOW)
	GPIO.output(PIN_2, GPIO.LOW)
	GPIO.output(PIN_3, GPIO.LOW)
	GPIO.output(PIN_4, GPIO.LOW)
