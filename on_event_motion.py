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
logger_path = "/home/pi/supervision/logs/on_event_motion.log"

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

class class_event(object):

	def __init__(self, log, name, path, event):
		self.log = log
		self.cam_name = name
		self.picture_storage = path
		self.event_number = event
		
	def send_sms(self):
		os.system("curl 'https://smsapi.free-mobile.fr/sendmsg?user=36056523&pass=Pn77qalc2rwilN&msg=Detection%20mouvement%20sur%20"+ self.cam_name +"%20!' >/dev/null 2>&1 &")
		#sself.log.info("class_event: send SMS")
		
	def send_mail(self):
		self.log.info("class_event: send Mail")
		os.system('(echo "Alerte" | mail -s "Detection mouvement sur ' + self.cam_name + ' !" mquille.supervision@gmail.com)&')
		
	def upload_file(self):
		self.log.info("class_event: upload pictures to GoogleDrive")
			
		command = Command("sudo /usr/local/bin/drive push -no-prompt -ignore-checksum -fix-clashes -ignore-conflict "+ self.picture_storage)

		rtr_code, out = command.run(timeout=120)
		self.log.info("Result command return code (1/2): '" + str(rtr_code) + "'")
		
		if rtr_code == 255:
			self.log.error('class_event : Error with upload Gdrive(255)')
			sys.exit()
		
		time.sleep(10)
		
		rtr_code, out = command.run(timeout=120)
		self.log.info("Result command return code (2/2): '" + str(rtr_code) + "'")
		
		if rtr_code == 255:
			self.log.error('class_event : Error with upload Gdrive(255)')
			sys.exit()
		
		return
	
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
	
def main():
	""" 
		Main
	"""
	
	""" Global variables """
	picture_storage = None
	name_came = None
	event_number = None
	
	""" Create logger """
	log = logger()
	log.create()
	log.info("")
	log.info("Start script")
	
	""" Script argument """
	if len(sys.argv) != 3:
		log.error("Error, argument not valid")
		sys.exit()
	
	picture_storage = str(sys.argv[1])
	event_number = str(sys.argv[2])
	name_came = picture_storage.split('/')[len(picture_storage.split('/'))-1]
	
	log.info("Args: " + sys.argv[1] + " " + sys.argv[2])
	
	""" Create event class """
	event = class_event(log, name_came, picture_storage, event_number)
	
	# Set alarme
	os.system('(sleep 4 && echo "on" > ' + path_motion_event + ')&')

	# Send SMS
	event.send_sms()
	
	# Send Mail
	event.send_mail()
	
	# Upload files
	event.upload_file()
	
	sys.exit()

	
if __name__ == "__main__":
    main()





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
