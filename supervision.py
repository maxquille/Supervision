#! /usr/bin/python
# -*- coding: utf-8 -*-
# 
# File: 
#	supervision.py
# 
# Description:
# 	
# 
# 
# Ex:
#	python supervision.py
#
# MQ 06/08/2018
#

import urllib2
from threading import Thread
import os, time, logging, sys, ConfigParser
from logging.handlers import RotatingFileHandler
from argparse import ArgumentParser
from collections import defaultdict
import socket, struct
import select
from datetime import date, datetime, timedelta
import pygame
import RPi.GPIO as GPIO ## Import GPIO library

logger_path = "/home/pi/supervision/logs/supervision.log"
param_file_name = "/home/pi/supervision/param.ini"
path_change_detection = "/tmp/state_detection.txt"

""" Global def """
def retrieve_parameters(log, file):
	name_came = None
	ip_cam = None
	ip_cam_master = None
	cam_list = defaultdict(list)
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
				cam_list[key] = {}
				cam_list[key]['ip'] = path.split("/")[0].strip()
				if ("ipcam_master" in key):
					cam_list[key]['port'] = int(path.split("/")[2].strip())
				else:
					cam_list[key]['port'] = int(path.split("/")[1].strip())
				
		
		return name_came, ip_cam, ip_cam_master, cam_list, port_cam_master
		
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


class check_detection_state(Thread):

	def __init__(self, log):
		Thread.__init__(self)
		self.log = log
		GPIO.setwarnings(False)
		GPIO.setmode(GPIO.BOARD) ## Use board pin numbering
		GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # key detection Input
		GPIO.setup(21, GPIO.OUT) # Led Green Output
		GPIO.setup(23, GPIO.OUT) # Led Red Output
		GPIO.output(21,False)
		GPIO.output(23,False)
		self.gpio_state = True
		self.key_state = self.read_key_state()
		self.detection_alarme_old = '';
		self.detection_alarme = "off" 					# Init à off (modifier les 2 lignes)
		open(path_change_detection , 'w').write("0") 	# Init à off (modifier les 2 lignes)
		self.log.info("Thread check_detection_state: Start thread")
		
	def read_key_state(self):
		return int(GPIO.input(13))
	
	def key_state_change(self):
		key_state_temp = self.read_key_state()
		if key_state_temp != self.key_state:
			self.log.info("Thread check_detection_state: new state detected on GPIO.")
			self.key_state = key_state_temp
			return True
		else:
			return False		
	
	def send_mail(self, state):
		self.log.info("check_detection_state: send Mail alarm " + state)
		if state == "off" and self.detection_alarme_old != '':
			os.system('(echo "Desactivation alarme" | mail -s "Desactivation alarme !" mquille.supervision@gmail.com)&')
		
		elif state == "on" and self.detection_alarme_old != '':
			os.system('(echo "Activation alarme" | mail -s "Activation alarme !" mquille.supervision@gmail.com)&')
			
	def new_state(self, state):
		self.log.info("Thread check_detection_state: traitement new state " + state)
		if (state == "on"):
			GPIO.output(21,True) # Red Led
			GPIO.output(23,False) # Green Led
			#self.send_mail(state)
			
		elif (state == "off"):
			GPIO.output(21,False) # Red Led
			GPIO.output(23,True) # Green Led
			self.send_mail(state)
			
	def get_status(self):
		return self.detection_alarme
		
	def run(self):
		while True:
			
			if self.key_state_change():
				if self.detection_alarme == "off":
					self.detection_alarme = "on"
					open(path_change_detection , 'w').write("1")
				else:
					open(path_change_detection , 'w').write("0")
					self.detection_alarme = "off"
					
			state_file_temp = open(path_change_detection , 'r').read().strip()
			if (state_file_temp == '1' and self.detection_alarme == "off"):
				self.log.info("Thread check_detection_state: new state detected on file")
				self.detection_alarme = "on"
				
			elif (state_file_temp == '0' and self.detection_alarme == "on"):
				self.log.info("Thread check_detection_state: new state detected on file")
				self.detection_alarme = "off"
			
			if self.detection_alarme_old != self.detection_alarme:
				self.new_state(self.detection_alarme)
				self.detection_alarme_old = self.detection_alarme
				
				
			time.sleep(0.5)		

class send_udp(Thread):
	def __init__(self, log, list_cam):
		Thread.__init__(self)
		self.detection_status = 'off'
		self.alarme_active_status = 'off'
		self.log = log
		self.list_cam = list_cam
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
		self.log.info("Thread send_udp: Start thread")
		
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
			for cam in self.list_cam:
				self.sock.sendto(hex, (self.list_cam[cam]['ip'], int(self.list_cam[cam]['port'])))
			time.sleep(1)

	def set_detection_status(self, status):
		self.detection_status = str(status)

	def set_alarme_active_status(self, status):
		self.alarme_active_status = str(status)

class receive_udp(Thread):

	def __init__(self, log, list_cam, port):
		Thread.__init__(self)
		self.log = log
		self.list_cam = list_cam
		for cam in self.list_cam:
			self.list_cam[cam]['detection_cmd'] = "error"
			self.list_cam[cam]['alarme_active_cmd'] = "error"
			self.list_cam[cam]['recv_udp_timeout'] = None
			
		self.log.info("Thread receive_udp: Start thread")
		
		""" Bind socket """
		try:
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
			self.sock.bind(('', int(port)))
			self.sock.settimeout(5)
			log.debug("Thread receive_udp: Bind socket success on port :" + str(port))

		except Exception as e:
			log.error("Thread receive_udp: Error Bind socket on port :" + str(port) + ' ' + str(e))
			sys.exit()
	
	def run(self):
		
		while True:
			try:
				data = self.sock.recv(2048)
				res = struct.unpack("B", data)
				if self.list_cam['ipcam_master']['recv_udp_timeout'] == None or self.list_cam['ipcam_master']['recv_udp_timeout'] == True:
					self.log.info("Thread receive_udp: Receive UDP frame from cam:" + self.list_cam['ipcam_master']['ip'] + " in progress.")
				
				if res[0] & 0x1 == 1:
					self.list_cam['ipcam_master']['detection_cmd'] = 'on'
				elif res[0] & 0x1 == 0:
					self.list_cam['ipcam_master']['detection_cmd'] = 'off'
				
				if res[0] >> 1 & 0x1  == 1:
					self.list_cam['ipcam_master']['alarme_active_cmd'] = 'on'
				elif res[0] >> 1 & 0x1 == 0:
					self.list_cam['ipcam_master']['alarme_active_cmd'] = 'off'
					
				self.list_cam['ipcam_master']['recv_udp_timeout'] = False
				
				print self.list_cam['ipcam_master']
				
			except Exception as e:
				if self.list_cam['ipcam_master']['recv_udp_timeout'] == None or self.list_cam['ipcam_master']['recv_udp_timeout'] == False:
					self.list_cam['ipcam_master']['detection_cmd'] = 'error'
					self.list_cam['ipcam_master']['alarme_active_cmd'] = 'error'
					self.log.error('Thread receive_udp: Timeout on UDP frame from cam:'+ self.list_cam['ipcam_master']['ip'] + " / "+ str(e))

				self.list_cam['ipcam_master']['recv_udp_timeout'] = True
		
def main():
	
	""" Create logger """
	log = logger()
	log.create()
	log.info("")
	log.info("Start script")
	
	""" Global variables """
	name_came = None
	ip_cam = None
	ip_cam_master = None
	cam_list = defaultdict(list)
	port_cam_master = None
	
	""" Retrieve parameter """
	name_came, ip_cam, ip_cam_master, cam_list, port_cam_master = retrieve_parameters(log, param_file_name)
	
	os.system("sudo /usr/bin/python /home/pi/supervision/daemon_motion.py > /dev/null 2>&1 &")
	
	if ip_cam == ip_cam_master:
		t_check_detection_state = check_detection_state(log)
		t_send_udp = send_udp(log, cam_list)
		t_receive_udp = receive_udp(log, cam_list, port_cam_master)
		
		t_check_detection_state.start()
		t_send_udp.start()
		t_receive_udp.start()
		
		i=0
		while True:
			i += 1
			t_send_udp.set_detection_status(t_check_detection_state.get_status())
			#if i == 15:
			#	t_send_udp.set_alarme_active_status('on')
			time.sleep(0.3)
		
	exit()














if __name__ == "__main__":
    main()


























work_path = "/home/pi/supervision/"
logger_path = "/home/pi/supervision/logs/supervision.log"
path_alarm_sous_surveillance = "/tmp/alarm_sous_surveillance.txt"
path_alarm_general_actif = "/tmp/alarm_genaral_actif.txt"

defIpCam = defaultdict(list)
defCamSupervSlave = defaultdict(list)

cam_IsMaster = False
alarm_sous_surveillance = "off"
alarm_general_actif = "off"
interface = "wlan0"

""" Create logger class """
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
		
def parse_args():
	""" 
	Parse arguments
	"""

	parser = ArgumentParser(
		description="Script main supervision")
	parser.add_argument('-p', '--parameter', type=str, 
						help='Parameter file')

	return parser.parse_args()

def retrieve_parameters(log, file):
	global cam_IsMaster
	file_backup = 'param_backup.ini'
	path_file = file
	
	try:
		with open(file): pass
	except:
		log.error("Paramter file is missing : '" + file + "' File by default '" + file_backup + "' is used.")
		path_file = os.path.join(work_path,file_backup)
	
	section = 'Ip_cam'
	try:
		fconfig = ConfigParser.ConfigParser()
		fconfig.read(path_file)
		defIpCam['dhcp_actif'] = fconfig.getboolean(section, 'dhcp_actif')
		defIpCam['ip_static'] = fconfig.get(section, 'ip_static')
		defIpCam['routers_static'] = fconfig.get(section, 'routers_static')
		defIpCam['domain_name_servers_static'] = fconfig.get(section, 'domain_name_servers_static')
		
		section = 'Supervision'
		cam_IsMaster = fconfig.getboolean(section, 'cam_IsMaster')
		path_items = fconfig.items(section)

		for key, path in path_items:
			if ("ipcam_slave" in key) or ("ipcam_master" in key):
				defCamSupervSlave[key] = {}
				defCamSupervSlave[key]['name'] = path.split("/")[0].strip()
				defCamSupervSlave[key]['ip'] = path.split("/")[1].strip()
				defCamSupervSlave[key]['port'] = path.split("/")[2].strip()
				defCamSupervSlave[key]['isAlive'] = False

		return

	except Exception as e:
		log.error("Paramter file is incorrect: " + str(e))
		sys.exit()
	
def init_wlan0(log):
	if (defIpCam['dhcp_actif'] == True):
		os.system('sudo cp /etc/dhcpcd_original.conf /etc/dhcpcd.conf')
		log.debug('Update dhcpcd.conf with wlan0 in dhcp mode.')

	else:
		os.system('sudo cp /etc/dhcpcd_original.conf /etc/dhcpcd.conf')
		os.system('sudo echo "interface wlan0" >> /etc/dhcpcd.conf')
		os.system('sudo echo "static ip_address="' + defIpCam['ip_static'] + ' >> /etc/dhcpcd.conf')
		os.system('sudo echo "static routers="' + defIpCam['routers_static'] + ' >> /etc/dhcpcd.conf')
		os.system('sudo echo "static domain_name_servers="' + defIpCam['domain_name_servers_static'] + ' >> /etc/dhcpcd.conf')
		log.debug('Update dhcpcd.conf with wlan0 in static mode (ip:' + defIpCam['ip_static'] + ').')
		
	log.debug('Restart wlan0 interface.')
	os.system('sudo ifconfig wlan0 down')
	os.system('sudo ifconfig wlan0 up')
	time.sleep(3)

def toggle_alarm_surv():
	return False
	
def main_loop(log):
	global alarm_sous_surveillance
	global alarm_general_actif
	global interface
	
	os.system("echo " + alarm_sous_surveillance + " > " + path_alarm_sous_surveillance)
	os.system("echo " + alarm_general_actif + " > " + path_alarm_general_actif)
	os.system("sudo chown pi " + path_alarm_sous_surveillance)	
	os.system("sudo chown pi " + path_alarm_general_actif)	

	
	# Wait during if up
	if_wlan0_up = False
	while if_wlan0_up == False:
		try:
			#for debug eth0 => wlan0
			ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
			#for debug
			#ip = defIpCam['ip_static']
			if ip == defIpCam['ip_static']: if_wlan0_up = True
			
		except:
			pass
		
	""" Bind socket """
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
	sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
	sock2.bind((defIpCam['ip_static'], 50001))
		
	while True:
		""" Read if toggle alarm_sous_surveillance is required """
		if toggle_alarm_surv():
			if alarm_sous_surveillance == "off":
				alarm_sous_surveillance = "on"
	
			else:
				alarm_sous_surveillance = "off"

			os.system("echo " + alarm_sous_surveillance + " > " + path_alarm_sous_surveillance)
			log.info("New detection state : " + alarm_sous_surveillance)
		
		""" Read from file """
		alarm_sous_surveillance = open(path_alarm_sous_surveillance, 'r').read().rstrip()
		alarm_general_actif = open(path_alarm_general_actif, 'r').read().rstrip()

		""" Send UDP frame to slave """
		payload = 0x00
		if alarm_sous_surveillance == "on":
			mask = 1
			payload |= mask
			
		if alarm_general_actif == "on":
			mask = 1 << 1
			payload |= mask
				
		
		for slave in defCamSupervSlave:
			hex = struct.pack("B", payload)
			sock.sendto(hex, (defCamSupervSlave[slave]['ip'], int(defCamSupervSlave[slave]['port'])))
		
		""" Wait UDP from slave """
		""" Bind socket """
		print 'reception'
		print sock2.recv(2048)
		
		time.sleep(1)

def main():
	""" 
		Main
	"""
	
	""" Create logger """
	log = logger()
	log.create()
	log.info("")
	log.info("")
	log.info("********************")
	log.info("*** Start script ***")
	log.info("********************")
	
	""" Script argument """
	if len(sys.argv) != 3:
		log.error("Error, argument not valid")
		sys.exit()

	args = parse_args()
	name_parameter_file= args.parameter
	retrieve_parameters(log,name_parameter_file)
	init_wlan0(log)
	
	log.info("Start script daemon_motion.py")
	os.system("sleep 5 && sudo /usr/bin/python /home/pi/supervision/daemon_motion.py -p " + name_parameter_file + " &")
	
	""" Cam is master """
	if cam_IsMaster == True:
		log.info("Camera is master")
		main_loop(log)
		
	else:
		os.info("Camera is slave")
		
if __name__ == "__main__":
    main()
	
