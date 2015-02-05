#!python3
#-*- coding: utf-8 -*-

import os
import re
import json
import irsdk
from prettytable import PrettyTable
import constants as ct
from iRWebStats import iRWebStats
import config as cfg
from collections import defaultdict
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--debug", action='store_true')
args = parser.parse_args()

debug = False
if args.debug:
    debug = True

def median(mylist):
	sorts = sorted(mylist)
	length = len(sorts)
	if not length % 2:
		return (sorts[length // 2] + sorts[length // 2 - 1]) / 2.0
	return sorts[length // 2]

ir = irsdk.IRSDK()
irw = iRWebStats()
print("                    ____                  ___        __                        ") 
print("                   |  _ \ __ _  ___ ___  |_ _|_ __  / _| ___                   ") 
print("                   | |_) / _` |/ __/ _ \  | || '_ \| |_ / _ \                  ") 
print("                   |  _ < (_| | (_|  __/  | || | | |  _| (_) |                 ") 
print("                   |_| \_\__,_|\___\___| |___|_| |_|_|  \___/                  ") 
print("                                                                               ")
print("                                                                               ")
print("                      v1.150205                                                ") 
print("                      Created by Robert \"Fuzzwah\" Crouch                     ") 
print("                      http://fuzzysracing.blogspot.com                         ")                                         
print("                                                                               ")
print("                                                                               ")

cfg.read("config.ini")
if cfg.config['password'] == '':
	cfg.config['username'] = str(input('Your iRacing username: '))
	cfg.config['password'] = str(input('Your iRacing password: '))
	
	cfg.config.write()
	print("                                 Config saved                                  ")
	print("                                                                               ")
	
if ir.startup():
	if len(ir['SessionInfo']['Sessions']) > 1:
		if ir['SessionInfo']['Sessions'][1]['SessionType'] == 'Race' or ir['SessionInfo']['Sessions'][2]['SessionType'] == 'Race':
			if debug:
				print("                                                                               ")
				print("                               *** DEBUG ON ***                                ")
				print("                           Dumping info to text files                          ")
				print("                                                                               ")
				json.dump(ir['SessionInfo'], open("SessionInfo.txt",'w'), sort_keys=True, indent=4, separators=(',', ': '))
				json.dump(ir['WeekendInfo'], open("WeekendInfo.txt",'w'), sort_keys=True, indent=4, separators=(',', ': '))
				json.dump(ir['QualifyResultsInfo'], open("QualifyResultsInfo.txt",'w'), sort_keys=True, indent=4, separators=(',', ': '))
				json.dump(ir['SessionInfo'], open("SessionInfo.txt",'w'), sort_keys=True, indent=4, separators=(',', ': '))
				json.dump(ir['DriverInfo'], open("DriverInfo.txt",'w'), sort_keys=True, indent=4, separators=(',', ': '))

			try:

				print("       Please wait, connecting to iracing.com to retrieve driver data")
				irw.login(cfg.config['username'], cfg.config['password'], quiet=True)
				
				web_api = True
				tab = PrettyTable(['ID', '#', 'Car', 'Name', 'License', 'iR', 'Races', 'SPos', 'AFin', 'AInc'])
				display = ['#', 'Car', 'Name', 'License', 'iR', 'Races', 'SPos', 'AFin', 'AInc']
			except:
				web_api = False
				tab = PrettyTable(['ID', '#', 'Car', 'Name', 'License', 'iRating'])
				display = ['#', 'Car', 'Name', 'License', 'iR']
				print("Unable to log into iRacing.com")	
			
			qualy_results = dict()

			seriesid = ir['WeekendInfo']['SeriesID']

			ir_total = defaultdict(lambda: 0)
			drv_count = defaultdict(lambda: 0)
			irs = dict()
			prev_car = ""
			mc = False
			my_car = ""
			count = 0

			for drv in ir['DriverInfo']['Drivers']:
				if drv['CarNumberRaw'] > 0:
					count += 1
					name = drv['AbbrevName'].split(', ')
					name = '{0: <17}'.format("%s %s" % (name[1], name[0][:17]))
					
					if irw.custid == drv['UserID']:
						my_car = drv['CarPath'][:3]
						name = ">%s<" % name[:15]

					row = ([int(drv['CarIdx']), drv['CarNumberRaw'], drv['CarPath'][:3].uppercase, name.encode('windows-1252', errors='replace').decode('windows-1252', errors='replace'), drv['LicString'], drv['IRating']])
					
					try:
						irs[drv['CarPath'][:3]] = list()
					except:
						print("blah")
					
					if web_api :
						drv_last_series = irw.last_series(drv['UserID'])
						series_stats = False
						for s in drv_last_series:
							if s['seriesID'] == seriesid and not series_stats:
								series_stats = True
								row.append(s['starts'])
								row.append(s['position'])
								row.append(s['avgFinish'])
								avginc = "%.0f" % float(int(s['incidents']) // int(s['starts']))
								row.append(avginc)
						
						if not series_stats:
							row.append('{0: <5}'.format(""))
							row.append('{0: <5}'.format(""))
							row.append('{0: <5}'.format(""))
							row.append('{0: <5}'.format(""))
					tab.add_row(row)
							
					ir_total[drv['CarPath'][:3]] += int(drv['IRating'])
					irs[drv['CarPath'][:3]].append(int(drv['IRating']))
					drv_count[drv['CarPath'][:3]] += 1
					if count > 1 and not prev_car == drv['CarPath'][:3]:
						mc = True
					prev_car = drv['CarPath'][:3]

			lines = count + 11
			os.system("mode con lines=%s" % lines)

			if my_car == "":
				my_car = prev_car
			
			#print("total ir: %s drv count: %s median ir: %s" % (ir_total[my_car], drv_count[my_car], median(irs[my_car])))
			sof = float(((int(ir_total[my_car]) / int(drv_count[my_car])) + int(median(irs[my_car]))) / 2)
			winner_pts = sof / 16
			pts_diff = (winner_pts / (drv_count[my_car] - 1))
			
			os.system('cls' if os.name == 'nt' else 'clear')
			print(" ")
			if mc:
				sof_my_car_string = " of %s:" % my_car.uppercase
				pts_my_car_string = " for %s:" % my_car.uppercase
			else:
				sof_my_car_string = ""
				pts_my_car_string = ""
			sof_string = 
			print("Approx SOF%s: %.0f" % (sof_my_car_string, sof))
			if ir['WeekendInfo']['WeekendOptions']['Unofficial'] == 0:
				if drv_count[my_car] > 4:
					print("Approx PTS%s: 1st: %.0f | 2nd: %.0f | 3rd: %.0f | 4th: %.0f | 5th: %.0f" % (pts_my_car_string, winner_pts, (winner_pts - pts_diff), (winner_pts - (pts_diff * 2)), (winner_pts - (pts_diff * 3)), (winner_pts - (pts_diff * 4))))
				elif drv_count[my_car] > 3:
					print("Approx PTS%s: 1st: %.0f | 2nd: %.0f | 3rd: %.0f | 4th: %.0f" % (pts_my_car_string, winner_pts, (winner_pts - pts_diff), (winner_pts - (pts_diff * 2)), (winner_pts - (pts_diff * 3))))
				elif drv_count[my_car] > 2:
					print("Approx PTS%s: 1st: %.0f | 2nd: %.0f | 3rd: %.0f" % (pts_my_car_string, winner_pts, (winner_pts - pts_diff), (winner_pts - (pts_diff * 2))))
				elif drv_count[my_car] > 1:
					print("Approx PTS%s: 1st: %.0f | 2nd: %.0f" % (pts_my_car_string, winner_pts, (winner_pts - pts_diff)))
				else:
					print("Approx PTS%s: 1st: %.0f" % (pts_my_car_string, winner_pts))
			else:
				print("Race is UNOFFICIAL, no PTS will be awarded")
				
			print(" ")

			tab.align['Name'] = 'l'
			tab.align['#'] = 'r'
			tab.align['iR'] = 'r'
			if web_api:
				tab.align['Races'] = 'r'
				tab.align['SPos'] = 'r'
				tab.align['AvgFin'] = 'r'
				tab.align['AvgInc'] = 'r'
				
			if not mc:
				display.pop(1)
				
			table = tab.get_string(sortby='ID', fields=display)
			print(table)
		else:
			print("*** ERROR *** This is not a race session")
			print("Race Info only generates details for races")
	else:
		print("*** ERROR *** This is not a race session")
		print("Race Info only generates details for races")
else:
	print("*** ERROR *** iRacing is not running")
	print("Join the race session first, then run Race Info")

print(" ")
input("Press Enter to close ...")



