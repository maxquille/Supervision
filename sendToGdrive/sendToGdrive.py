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

work_path = "/home/pi/supervision/sendToGdrive"

logger_path = "/home/pi/supervision/logs/sendToGdrive.log"

param_file = "/home/pi/supervision/param.ini"

path_alarm_actif = "/tmp/alarm_actif.txt"
alarm_actif = "on"

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
		description="Upload local folder to Google Drive")
	parser.add_argument('-s', '--source', type=str, 
						help='Folder to upload')
	#parser.add_argument('-d', '--destination', type=str, 
	#					help='Destination Folder in Google Drive')
	#parser.add_argument('-p', '--parent', type=str, 
	#					help='Parent Folder in Google Drive')
	parser.add_argument('-n', '--number', type=str, 
						help='Event detection number')
						
	return parser.parse_args()

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
	
	# Alarm Actif
	os.system("echo " + alarm_actif + " > " + path_alarm_actif)
			
	time.sleep(5)
	# Upload the files    
	upload_files(log, src_folder_name, number_event)

	sys.exit()
	
if __name__ == "__main__":
    main()
