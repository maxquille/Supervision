#! /usr/bin/python
# -*- coding: utf-8 -*-
# 
# File: 
#	autoConnOpenVPN.py
# 
# Description:

# 
# 
# Ex:
#	
#
# MQ 06/12/2018
#

import pyping, os, time

def restart_service():
	print ("Restart service python")
	os.system("sleep 3 && /bin/sh /etc/rc.local &")
	os.system("pkill python")
	time.sleep(5)
	

def main():
	""" 
		Main
	"""

	""" Global variables """

	while True:
		try:
			r = pyping.ping("172.27.224.1")
			
			print int(r.ret_code)
			if int(r.ret_code) != 0:
				while int(r.ret_code) != 0:
					# wait openVpn become 
					os.system("service openvpn restart")
					time.sleep(30)
					r = pyping.ping("172.27.224.1") 
					print int(r.ret_code) 
				
				restart_service()
				
		except:
			pass
				
	
if __name__ == "__main__":
    main()