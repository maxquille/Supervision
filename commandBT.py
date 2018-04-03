#! /usr/bin/python
import RPi.GPIO as GPIO ## Import GPIO library
import time

GPIO.setwarnings(False)

GPIO.setmode(GPIO.BOARD) ## Use board pin numbering
GPIO.setup(7, GPIO.OUT) ## Setup GPIO Pin 7 to OUT
GPIO.output(7,True) ## Turn on GPIO pin 7
while True:
	print 'True'	
	GPIO.output(7,True) ## Turn on GPIO pin 7
	time.sleep(0.1)	
	print 'False'	
	GPIO.output(7,False) ## Turn on GPIO pin 7
	time.sleep(0.1)	


