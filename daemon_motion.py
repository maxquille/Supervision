#! /usr/bin/python
# -*- coding: utf-8 -*-
# 
# File: 
#	daemon_motion.py
# 
# Description:
# 	
# 
# 
# Ex:
#	python daemon_motion.py
#
# MQ 30/01/2018
#
import urllib2
from threading import Thread
import os, time, logging, sys, ConfigParser
from logging.handlers import RotatingFileHandler
from argparse import ArgumentParser
import socket, struct
import select
from datetime import date, datetime, timedelta
import pygame
import RPi.GPIO as GPIO ## Import GPIO library

logger_path = "/home/pi/supervision/logs/daemon_motion.log"
path_motion_event = "/tmp/motion_event.txt"
param_file_name = "param.ini"
motion_conf_path_original = "/etc/motion/motion_original.conf"
motion_conf_path = "/etc/motion/motion.conf"

""" Global def """
def retrieve_parameters(log, file):
	name_came = None
	ip_cam = None
	port_cam = None
	ip_cam_master = None
	port_cam_master = None

	try:
		with open(file): pass
	except:
		log.error("Parameter file is missing : " + file)
		sys.exit()

	try:
		fconfig = ConfigParser.ConfigParser()
		fconfig.read(file)
		
		name_came = fconfig.get('General', 'camera_name').strip()
		ip_cam = fconfig.get('Ip_cam', 'ip_static').strip()

		section = 'Supervision'
		ip_cam_master = fconfig.get(section, 'ipcam_master').strip().split("/")[0].strip()
		port_cam_master = fconfig.get(section, 'ipcam_master').strip().split("/")[1].strip()

		path_items = fconfig.items(section)
		for key, path in path_items:
			if ("ipcam_slave" in key) or ("ipcam_master" in key):
				if path.split("/")[0].strip() == ip_cam:
					if ("ipcam_master" in key):
						port_cam = int(path.split("/")[2].strip())
					else:
						port_cam = int(path.split("/")[1].strip())
	
					return name_came, ip_cam, port_cam, ip_cam_master, port_cam_master
		
		log.error("Impossible to find camera port in parameter file")
		sys.exit()
		
	except Exception as e:
		log.error("Parameter file is incorrect: " + str(e))
		sys.exit()

""" Class """
class logger(object):
	def __init__(self):
		self.log = logging.getLogger(__name__) 
	
	def create(self):
		""" Logger path """ 
		self.pathlogger = logger_path

		""" Logger setting """
		self.log.setLevel(logging.DEBUG)
		self.file_handler = RotatingFileHandler(os.path.normpath(self.pathlogger), 'a', 1000000, 1)
		self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
		self.file_handler.setLevel(logging.DEBUG)
		self.file_handler.setFormatter(self.formatter)
		self.log.addHandler(self.file_handler)
		self.gsteam_handler = logging.StreamHandler() # création d'un second handler qui va rediriger chaque écriture de log sur la console
		self.gsteam_handler.setFormatter(self.formatter)
		self.gsteam_handler.setLevel(logging.DEBUG)
		self.log.addHandler(self.gsteam_handler)
	
	def info(self, string):
		self.log.info(string)
	
	def warning(self, string):
		self.log.warning(string)
	
	def error(self, string):
		self.log.error(string)
	
	def debug(self, string):
		self.log.debug(string)	

""" Class Thread """
class motion(Thread):

	def __init__(self, log):
		Thread.__init__(self)
		self.current_detection = None
		self.detection_cmd = None
		self.log = log
		self.log.info("Start thread motion")
		
	def run(self):
		while True:
			if self.current_detection != self.detection_cmd:
				self.manage_detection(self.detection_cmd) 
			time.sleep(1)
			
	def set_detection(self):
		self.detection_cmd = 'on' 
		return

	def clear_detection(self):
		self.detection_cmd = 'off'
		return
		
	def manage_detection(self, status):
		i = 0
		while i<3:
			try:
				if status == 'on':
					urllib2.urlopen('http://127.0.0.1:8082/0/detection/start')
				else:
					urllib2.urlopen('http://127.0.0.1:8082/0/detection/pause')
				
				state = urllib2.urlopen('http://127.0.0.1:8082/0/detection/status').read()
					
				if status == 'off': 
					if "Detection status PAUSE" in state:
						self.current_detection = self.detection_cmd
						return
				else:
					if "Detection status ACTIVE" in state:
						self.current_detection = self.detection_cmd
						return
			except:
				pass
			
			time.sleep(2)
			i += 1

		self.log.error("Thread motion: Unable to set or clear motion detection.")
		os.system('sudo killall python')

	def get_detection(self):
		return self.current_detection

	def get_on_event_detection(self):
		try:
			return open(path_motion_event, 'r').read().strip()
		except:
			return "off"
			
class receive_udp(Thread):

	def __init__(self, log, addr, port):
		Thread.__init__(self)
		self.detection_cmd = 'off'
		self.alarme_active_cmd = 'off'
		self.log = log
		self.log.info("Thread receive_udp: Start thread")
		
		""" Bind socket """
		try:
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
			self.sock.bind((str(addr), int(port)))
			self.sock.settimeout(5)
			log.debug("Thread receive_udp: Bind socket success on " + str(addr) + ':' + str(port))

		except Exception as e:
			log.error("Thread receive_udp: Error Bind socket on " + str(addr) + ':' + str(port) + ' ' + str(e))
			sys.exit()
			
	def run(self):
		udp_frame_from_master_InTimeout = None
		
		while True:
			try:
				data = self.sock.recv(2048)
				res = struct.unpack("B", data)
				if udp_frame_from_master_InTimeout == None or udp_frame_from_master_InTimeout == True:
					self.log.info("Thread receive_udp: Receive UDP frame from master in progress.")
				
				if res[0] & 0x1 == 1:
					self.detection_cmd = 'on'
				elif res[0] & 0x1 == 0:
					self.detection_cmd = 'off'
				
				if res[0] >> 1 & 0x1  == 1:
					self.alarme_active_cmd = 'on'
				elif res[0] >> 1 & 0x1 == 0:
					self.alarme_active_cmd = 'off'
					
				udp_frame_from_master_InTimeout = False
				
				# print res[0]
				# print 'detection_cmd:' + self.detection_cmd
				# print 'alarme_active_cmd:' + self.alarme_active_cmd
				
			except Exception as e:
				if udp_frame_from_master_InTimeout == None or udp_frame_from_master_InTimeout == False:
					self.detection_cmd = 'off'
					self.alarme_active_cmd = 'off'
					self.log.error('Thread receive_udp: Timeout on UDP frame master. ' + str(e))

				udp_frame_from_master_InTimeout = True

	def get_detection_cmd(self):
		return self.detection_cmd

	def get_alarme_active_cmd(self):
		return self.alarme_active_cmd

class send_udp(Thread):

	def __init__(self, log, addr, port):
		Thread.__init__(self)
		self.detection_status = 'off'
		self.alarme_active_status = 'off'
		self.log = log
		self.addr = addr
		self.port = int(port)
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP

	def run(self):
		while True:
		
			""" Make payload """
			payload = 0x0
			if self.detection_status == "on":
				mask = 1
				payload |= mask
			if self.alarme_active_status == "on":
				mask = 1 << 1
				payload |= mask
			
			""" Send frame """
			hex = struct.pack("B", payload)
			self.sock.sendto(hex, (self.addr, self.port))
			time.sleep(1)	

	def set_detection_status(self, status):
		self.detection_status = str(status)

	def set_alarme_active_status(self, status):
		self.alarme_active_status = str(status)
		
class alarme(Thread):

	def __init__(self, log):
		Thread.__init__(self)
		self.current_status = 'off'
		self.log = log
		self.log.info("Start thread alarme")
		self.date_start = datetime.now()
		self.date_end = datetime.now()
		self.alarme_is_actif = False
		pygame.mixer.init()
		pygame.mixer.music.set_volume(1)
		try:
			pygame.mixer.music.load("/home/pi/supervision/music/2334.mp3")
		except:
			log.error("Thread alarme: Load music failed")
		GPIO.setwarnings(False)
		GPIO.setmode(GPIO.BOARD) ## Use board pin numbering
		GPIO.setup(7, GPIO.OUT) ## Setup GPIO Pin 7 to OUT
		GPIO.output(7,True) ## Turn on GPIO pin 7
		self.gpio_state = True
		
	def run(self):
	
		while True:
			time.sleep(0.4)
			
			#Timeout
			if self.current_status == 'on' and datetime.now() > self.date_end and self.alarme_is_actif == True:
				self.alarme_is_actif = False
				pygame.mixer.music.stop()
				self.log.info('Thread alarme: Stop alarme after timeout.')
			
			self.manage_gpio()
			
			
				
	def set(self):
		self.current_status = 'on'
		self.alarme_is_actif = True
		self.date_start = datetime.now()
		self.date_end = self.date_start + + timedelta(minutes=0, seconds=15) #Timeout
		# Play alarm music
		try:
			pygame.mixer.music.play(loops=-1, start=0.0) #Infinit loop
		except:
			pass
		
		return
		
	def clear(self):
		open(path_motion_event, 'w').write("off")
		self.current_status = 'off'
		self.alarme_is_actif = False
		self.date_start = datetime.now()
		self.date_end = datetime.now()
		# Stop alarm music
		try:
			pygame.mixer.music.stop()
		except:
			pass
		return
	
	def get_status(self):
		return self.current_status

	def manage_gpio(self):
		if self.alarme_is_actif == True:
			if self.gpio_state == True:
				GPIO.output(7,False) ## Turn off
				self.gpio_state = False
			else:
				GPIO.output(7,True) ## Turn ons
				self.gpio_state = True
		else:
			GPIO.output(7,True) ## Turn on
		
def main():
	
	""" Create logger """
	log = logger()
	log.create()
	log.info("")
	log.info("Start script")
	
	open(path_motion_event, 'w').write("off")
	
	""" Global variables """
	name_came = None
	ip_cam = None
	port_cam = None
	ip_cam_master = None
	port_cam_master = None
	
	""" Retrieve parameter """
	name_came, ip_cam, port_cam, ip_cam_master, port_cam_master = retrieve_parameters(log, param_file_name)
	
	""" Create and start thread """
	t_r_udp = receive_udp(log, ip_cam, int(port_cam))

	t_s_udp = send_udp(log, ip_cam_master, int(port_cam_master))
	t_motion = motion(log)
	t_alarme = alarme(log)

	t_r_udp.start()
	t_s_udp.start()
	t_motion.start()
	t_alarme.start()
	
	# Kill motion process
	os.system("sudo killall motion >/dev/null 2>&1")
	time.sleep(2)
	
	# Start motion process
	try:
		file = open(motion_conf_path_original,'r').read().replace("$CAM$",name_came)
		open(motion_conf_path,'w').write(file)
		
	except Exception as e:
		log.error("Impossible to create motion.conf : " + str(e))
		sys.exit()
	
	os.system("sudo motion >/dev/null 2>&1")
	log.info("Start Motion process")
	t_motion.clear_detection()
	
	""" Init variable for manage detection and alarme """
	current_detection_status = 'off'
	current_alarme_status = 'off'

	""" Main loop """
	while True:
	
		""" Manage detection """
		if t_r_udp.get_detection_cmd() == 'on' and current_detection_status == 'off':
			t_motion.set_detection()
			current_detection_status = 'on'
			t_s_udp.set_detection_status(current_detection_status)
			log.info("Detection_status new state : " + current_detection_status)
			
		elif t_r_udp.get_detection_cmd() == 'off' and current_detection_status == 'on':
			t_motion.clear_detection()
			current_detection_status = 'off'
			t_s_udp.set_detection_status(current_detection_status)
			log.info("Detection_status new state : " + current_detection_status)
		
		""" Manage alarme status """
		current_alarme_status = t_alarme.get_status()
		
		if t_r_udp.get_alarme_active_cmd() == 'off' and t_motion.get_on_event_detection() == 'off' and current_alarme_status == 'on':
			t_alarme.clear()
			current_alarme_status = 'off'
			t_s_udp.set_alarme_active_status(current_alarme_status)
			log.info("Alarme_active_status new state : " + current_alarme_status)
		
		if current_detection_status == 'off' and current_alarme_status == 'on':
			t_alarme.clear()
			current_alarme_status = 'off'
			t_s_udp.set_alarme_active_status(current_alarme_status)
			log.info("Alarme_active_status new state : " + current_alarme_status)

		if current_detection_status == 'on' and t_r_udp.get_alarme_active_cmd() == 'on' and current_alarme_status == 'off':
			t_alarme.set()
			current_alarme_status = 'on'
			t_s_udp.set_alarme_active_status(current_alarme_status)
			log.info("Alarme_active_status new state : " + current_alarme_status)

		if current_detection_status == 'on' and t_motion.get_on_event_detection() == 'on' and current_alarme_status == 'off':
			t_alarme.set()
			current_alarme_status = 'on'
			t_s_udp.set_alarme_active_status(current_alarme_status)
			log.info("Alarme_active_status new state : " + current_alarme_status)
		
		print "boucle"
		time.sleep(1)


if __name__ == "__main__":
    main()
