#! /usr/bin/python
# -*- coding: utf-8 -*-
# 
# File: 
#	sendToGdrive.py
# 
# Description:
# 	Ce script permet d'envoyer un
# 	repertoire et son contenu sur
# 	un compte google Drive
# 
# 
# Ex:
#	python sendToGdrive.py -p alarm -d cam1_31_01_2017__09_22_01 -s cam1_31_01_2017__09_22_01
#
# MQ 30/01/2018
#

# Enable Python3 compatibility
from __future__ import (unicode_literals, absolute_import, print_function,
                        division)

""" Import general libraries"""
import time, sys, logging, os, ast, ConfigParser, io
from os import chdir, listdir, stat
from logging.handlers import RotatingFileHandler
from datetime import datetime
import subprocess
from subprocess import *
from threading import Timer
from argparse import ArgumentParser
import subprocess, threading,signal
import pygame
from threading import Thread
path_motion_event = "/tmp/motion_event.txt"


work_path = "/home/pi/supervision/sendToGdrive"
logger_path = "/home/pi/supervision/logs/sendToGdrive.log"
param_file_path = "/home/pi/supervision/param.ini"


""" Create logger class """
class logger(object):
	def __init__(self):
		self.log = logging.getLogger(__name__) 
	
	def create(self):
		""" Logger setting """
		self.log.setLevel(logging.DEBUG)
		self.file_handler = RotatingFileHandler(os.path.normpath(logger_path), 'a', 1000000, 1)
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


""" Global def """
def retrieve_parameters(log, file):
	name_came = None

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

class event(Thread):

	def __init__(self, log):
		Thread.__init__(self)
		self.log = log
		self.log.info("Start thread event")
		
	def run(self):
		pass
		
	def send_sms(self):
		pass
		
	def send_mail(self):
		pass
		
	def upload_file(self): 
		pass
	

def main():
	""" 
		Main
	"""
	
	""" Global variables """
	name_came = None
	
	""" Create logger """
	log = logger()
	log.create()
	log.info("")
	log.info("Start script")
	
	th_event = event(log)
	th_event.start()
	
	# Set alarme
	os.system('sleep 15 && echo "on" > ' + path_motion_event)
	
	sys.exit()
	
	# Send SMS
	os.system("wget 'https://smsapi.free-mobile.fr/sendmsg?user=36056523&pass=Pn77qalc2rwilN&msg=Alerte%20general%20!!!'")
	
	
	# Upload files to Gdrive
	upload_files(log, src_folder_name, number_event)
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	""" Retrieve parameter """
	name_came = retrieve_parameters(log, param_file_path)
	
	""" Script argument """
	if len(sys.argv) != 5:
		log.error("Error, argument not valid")
		sys.exit()

	args = parse_args()
	src_folder_name = args.source
	#dst_folder_name = args.destination
	#parent_folder_name = args.parent
	number_event = args.number
	
	log.info("Arguments: ")
	log.info("   src_folder_name: " + src_folder_name)
	#log.info("   parent_folder_name: " + parent_folder_name)
	#log.info("   dst_folder_name: " + dst_folder_name)
	log.info("   number_event: " + number_event)
	
	# Send SMS
	os.system("wget 'https://smsapi.free-mobile.fr/sendmsg?user=36056523&pass=Pn77qalc2rwilN&msg=Alerte%20general%20!!!'")
	pygame.mixer.init()
	pygame.mixer.music.load("/home/pi/supervision/music/2334.mp3")
	pygame.mixer.music.play()	
	# Alarm Actif
	os.system("echo " + alarm_local_actif + " > " + path_alarm_local_actif)
			
	time.sleep(5)
	pygame.mixer.music.stop()	
	# Upload the files    
	upload_files(log, src_folder_name, number_event)

	sys.exit()
	
if __name__ == "__main__":
    main()
































path_alarm_local_actif = "/tmp/alarm_local_actif.txt"
alarm_local_actif = "on"



class Command(object):
	def __init__(self, cmd):
		self.cmd = cmd
		self.process = None

	def run(self, timeout):
		self.out = None
		self.err = None
		def target():
			self.process = subprocess.Popen(self.cmd, stdout=PIPE, stderr=PIPE, shell=True, preexec_fn=os.setsid)
			self.out, self.err = self.process.communicate()
			
		thread = threading.Thread(target=target)
		thread.start()

		thread.join(timeout)
		
		if thread.is_alive():
			os.killpg(self.process.pid, signal.SIGTERM)
			thread.join()
			
		return self.process.returncode,self.out
		
def upload_files(log, src_folder_name, nbr):
	""" 
		Upload files in the local folder to Google Drive 
	"""
	
	# Enter the source folder
	try:
		chdir(os.path.join(work_path,src_folder_name))
	# Print error if source folder doesn't exist
	except OSError:
		log.error('Local folder ' + src_folder_name + ' is missing')
		sys.exit()
	
	
	up_to_date = False
	nb_try_uploading = 3

	while(up_to_date == False and nb_try_uploading >0):
		log.info('Uploading files in progress (1st time)...')
		command = Command("sudo /usr/local/bin/drive push -no-prompt -ignore-checksum -fix-clashes -ignore-conflict "+ nbr +"* ")
		rtr_code, out = command.run(timeout=120)
		log.info("Result command return code: '" + str(rtr_code) + "'")
		
		#if (rtr_code == 0 and (str(out).find('Everything is up-to-date') != -1) or str(out).find('100.00%') != -1):
		if (rtr_code == 0):
			log.info("Uploading files finished")
			up_to_date = True
	
		nb_try_uploading -= 1
	
	time.sleep(10)
	up_to_date = False
	nb_try_uploading = 3
	while(up_to_date == False and nb_try_uploading >0):
		log.info('Uploading files in progress (2nd times)...')
		command = Command("sudo /usr/local/bin/drive push -no-prompt -ignore-checksum -fix-clashes -ignore-conflict "+ nbr +"* ")
		rtr_code, out = command.run(timeout=120)
		log.info("Result command return code: '" + str(rtr_code) + "'")
		
		#if (rtr_code == 0 and (str(out).find('Everything is up-to-date') != -1) or str(out).find('100.00%') != -1):
		if (rtr_code == 0):
			log.info("Uploading files finished")
			up_to_date = True
	
		nb_try_uploading -= 1
		
	return

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
	if len(sys.argv) != 5:
		log.error("Error, argument not valid")
		sys.exit()

	args = parse_args()
	src_folder_name = args.source
	#dst_folder_name = args.destination
	#parent_folder_name = args.parent
	number_event = args.number
	
	log.info("Arguments: ")
	log.info("   src_folder_name: " + src_folder_name)
	#log.info("   parent_folder_name: " + parent_folder_name)
	#log.info("   dst_folder_name: " + dst_folder_name)
	log.info("   number_event: " + number_event)
	
	# Send SMS
	os.system("wget 'https://smsapi.free-mobile.fr/sendmsg?user=36056523&pass=Pn77qalc2rwilN&msg=Alerte%20general%20!!!'")
	pygame.mixer.init()
	pygame.mixer.music.load("/home/pi/supervision/music/2334.mp3")
	pygame.mixer.music.play()	
	# Alarm Actif
	os.system("echo " + alarm_local_actif + " > " + path_alarm_local_actif)
			
	time.sleep(5)
	pygame.mixer.music.stop()	
	# Upload the files    
	upload_files(log, src_folder_name, number_event)

	sys.exit()
	
if __name__ == "__main__":
    main()
