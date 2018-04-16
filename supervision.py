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
# MQ 30/01/2018
#

""" Import general libraries"""
import time, sys, logging, os, ConfigParser, io
from logging.handlers import RotatingFileHandler
from datetime import datetime
from argparse import ArgumentParser
from collections import defaultdict
import socket, struct
import netifaces as ni

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
	
