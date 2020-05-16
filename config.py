#!python3

import os
import configobj

cfg_file = "config.ini"

if not os.path.isfile(cfg_file):

	config = configobj.ConfigObj()
	config.filename = cfg_file

	config['username'] = ''
	config['ddb'] = ''

	config.write()

def read(f="config.ini"):
	global config

	# try to read in the config
	try:
		config = configobj.ConfigObj(f)
		
	except (IOError, KeyError, AttributeError) as e:
		print("Unable to successfully read config file")
