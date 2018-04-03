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
import os, time, logging, sys, ConfigParser
from logging.handlers import RotatingFileHandler
from argparse import ArgumentParser
import socket, struct
import select

work_path = "/home/pi/supervision/"
logger_path = "/home/pi/supervision/logs/daemon_motion.log"
path_alarm_local_actif = "/tmp/alarm_local_actif.txt"

name_came = 'cam'
ip_cam = None
port_cam = None

alarm_sous_surveillance = "off"

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
		description="Script daemon supervision")
	parser.add_argument('-p', '--parameter', type=str, 
						help='Parameter file')

	return parser.parse_args()

def get_cam_name(log, path_file):
	try:
		fconfig = ConfigParser.ConfigParser()
		fconfig.read(path_file)
		name = fconfig.get("General", 'camera_name')
		return name
	
	except: 
		
		return "cam"
		
def retrieve_parameters(log, file):
	global ip_cam
	global port_cam
	file_backup = 'param_backup.ini'
	path_file = file
	
	try:
		with open(file): pass
	except:
		log.error("Parameter file is missing : '" + file + "' File by default '" + file_backup + "' is used.")
		path_file = os.path.join(work_path,file_backup)
	

	try:
		fconfig = ConfigParser.ConfigParser()
		fconfig.read(path_file)
		ip_cam = fconfig.get('Ip_cam', 'ip_static').strip()
		
		section = 'Supervision'
		path_items = fconfig.items(section)
		for key, path in path_items:
			if ("ipcam_slave" in key) or ("ipcam_master" in key):
				if path.split("/")[1].strip() == ip_cam:
					port_cam = int(path.split("/")[2].strip())
					return
				
		log.error("Impossible to find camera port in parameter file")
		sys.exit()
		
	except Exception as e:
		log.error("Parameter file is incorrect: " + str(e))
		sys.exit()

def start_stop_detection(log,state):
	if state == "off":
		urllib2.urlopen('http://127.0.0.1:8082/0/detection/pause')
		log.info("Send url request detection 'pause'")
	else:
		urllib2.urlopen('http://127.0.0.1:8082/0/detection/start')
		log.info("Send url request detection 'start'")
		
def main_loop(log):
	global alarm_sous_surveillance
	global ip_cam
	global port_cam
	alarm_local_actif = "off"
	
	# Kill motion process
	os.system("sudo killall motion")
	time.sleep(5)
	
	# Start motion process
	
	os.system("sudo motion")
	log.info("Start Motion process")
	time.sleep(2)
	
	os.system("echo " + alarm_local_actif + " > " + path_alarm_local_actif)
	os.system("sudo chown pi " + path_alarm_local_actif)	
	
	while True:
		try:
			urllib2.urlopen('http://127.0.0.1:8082/0/detection/pause')
			log.info("Init : Send url request detection 'pause'")
			break
			
		except:
			pass
	
	log.info("alarm_sous_surveillance = " + alarm_sous_surveillance)
	
	udp_frame_from_master_InTimeout = None
	
	while True:
	
		""" Receive socket from master """
		""" Bind socket """
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
			sock.bind((ip_cam, port_cam))
			sock.settimeout(5)
			
		except Exception as e:
			print "Error Bind socket : " + str(e)
			sys.exit()
			
		""" Get socket """
		try:
			data = sock.recv(2048)
			res = struct.unpack("B", data)
			if udp_frame_from_master_InTimeout == None or udp_frame_from_master_InTimeout == True:
				log.info("Receive UDP frame of master in progress ")
				
			if alarm_sous_surveillance == 'off' and \
				res[0] & 0x1 == 1:
				alarm_sous_surveillance = 'on'
				log.info("alarm_sous_surveillance = " + alarm_sous_surveillance)
				start_stop_detection(log,alarm_sous_surveillance)
				
			elif alarm_sous_surveillance == 'on' and \
				res[0] & 0x1 == 0:
				alarm_sous_surveillance = 'off'
				log.info("alarm_sous_surveillance = " + alarm_sous_surveillance)
				start_stop_detection(log,alarm_sous_surveillance)
				
			udp_frame_from_master_InTimeout = False
			
		except Exception as e:
			if udp_frame_from_master_InTimeout == None or udp_frame_from_master_InTimeout == False:
				alarm_sous_surveillance = 'off'
				log.error('Timeout on UDP frame master, force "alarm_sous_surveillance" = off')
				log.info("alarm_sous_surveillance = " + alarm_sous_surveillance)
				start_stop_detection(log,alarm_sous_surveillance)
				
			udp_frame_from_master_InTimeout = True
		
		
		""" Send socket to master """
		if udp_frame_from_master_InTimeout != True:
			""" Bind socket """
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
			
			""" Read from file """
			alarm_local_actif = open(path_alarm_local_actif, 'r').read().rstrip()
		
			""" Send UDP frame to master """
			payload = 0x0
			if alarm_local_actif == "on":
				mask = 1
				payload |= mask					
			
			hex = struct.pack("B", payload)
			#sock.sendto(hex, (defCamSupervSlave[slave]['ip'], int(defCamSupervSlave[slave]['port'])))
			
	sys.exit()

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

	main_loop(log)

		
if __name__ == "__main__":
    main()
