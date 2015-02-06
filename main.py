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

# set up our command line option for debugging
parser = argparse.ArgumentParser()
parser.add_argument("--debug", action='store_true')
args = parser.parse_args()

debug = False
if args.debug:
    debug = True

def median(mylist):
	""" Returns the median of a list of numbers """
	sorts = sorted(mylist)
	length = len(sorts)
	if not length % 2:
		return (sorts[length // 2] + sorts[length // 2 - 1]) / 2.0
	return sorts[length // 2]

# local iRacing API
ir = irsdk.IRSDK() 

# iRacing.com website API
irw = iRWebStats() 

# a pretty looking splash screen, because branding
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

# try to read in a config file
cfg.read("config.ini")
# if the password is blank, lets prompt the user for their details and save them
if cfg.config['password'] == '':
	cfg.config['username'] = str(input('Your iRacing username: '))
	cfg.config['password'] = str(input('Your iRacing password: '))
	
	cfg.config.write()
	print("                                 Config saved                                  ")
	print("                                                                               ")

# check if the local API can talk to the game, ie: is iRacing running	
if ir.startup():
	# check if there is more than one session, ie a race
	if len(ir['SessionInfo']['Sessions']) > 1:
		# check if the 2nd or 3rd (for series which have qualy, warmup then race) session is a race session
		if ir['SessionInfo']['Sessions'][1]['SessionType'] == 'Race' or ir['SessionInfo']['Sessions'][2]['SessionType'] == 'Race':
			# let the user know if we're in debug mode and dump the info files
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
				# let the user know we're connecting to the website
				print("       Please wait, connecting to iracing.com to retrieve driver data")
				irw.login(cfg.config['username'], cfg.config['password'], quiet=True)
				# if this worked then we'll set up the full table
				web_api = True
				tab = PrettyTable(['ID', '#', 'Car', 'Name', 'License', 'iR', 'Races', 'SPos', 'AFin', 'AInc'])
				display = ['#', 'Car', 'Name', 'License', 'iR', 'Races', 'SPos', 'AFin', 'AInc']
			except:
				# if it didn't work we'll set up only the minimal table
				web_api = False
				tab = PrettyTable(['ID', '#', 'Car', 'Name', 'License', 'iRating'])
				display = ['#', 'Car', 'Name', 'License', 'iR']
				print("Unable to log into iRacing.com")	
			
			seriesid = ir['WeekendInfo']['SeriesID']
			# a dictionary for iRating totals per car, default to 0
			ir_total = defaultdict(lambda: 0) 				
			# a dictionary for driver totals per car, default to 0	
			drv_count = defaultdict(lambda: 0) 					
			# a dictionary for all the iRatings
			irs = dict() 										
			# blank var for our vehicle
			my_car = "" 										
			# set multiclass to false until proven otherwise
			mc = False 											
			# count of drivers, because the full list includes spectators and the pace car
			count = 0 											
			
			# lets run through each driver in the race
			for drv in ir['DriverInfo']['Drivers']:
				# this checks that the driver isn't a spectator or the pace car, lol
				if drv['CarNumberRaw'] > 0:
					# increase our total driver count by one
					count += 1 							
								
					# do we have more than 1 car class?		
					if ir['WeekendInfo']['NumCarClasses'] > 1:
						# oh it is, then this is a multiclass race!	
						mc = True		
							
					# AbbrevName's are LastName, FirstInitial		
					name = drv['AbbrevName'].split(', ')
					# if this isn't a multiclass race we have an extra 4 chars
					if not mc:
						# if the lastname is over 19 chars in length, trim it
						name = "%s %s" % (name[1], name[0][:19]) 	
						# pad all the names out to be 21 chars total
						name = '{0: <21}'.format(name) 				
					else:
						# if the lastname is over 13 chars in length, trim it
						name = "%s %s" % (name[1], name[0][:13]) 	
						# pad all the names out to be 15 chars total
						name = '{0: <15}'.format(name) 				
						
					# finally lets sort out any special chars so all names will be displayed correctly in the windows console
					name = name.encode('windows-1252', errors='replace').decode('windows-1252', errors='replace')
					
					# is this driver our user?
					if irw.custid == drv['UserID']:		
						# then this is their car type		
						my_car = drv['CarPath'][:3]		
						# wack > < around their name to highlight it		
						name = ">%s<" % name[:15]				

					# collect all the basic info up into a new row
					row = ([int(drv['CarIdx']), drv['CarNumberRaw'], drv['CarPath'][:3].upper(), name, drv['LicString'], drv['IRating']])
					
					try:
						# try to make a new list for this type of car
						irs[drv['CarPath'][:3]] = list()		
					except:
						# if the car already has an entry, lets avoid an error
						blah = 1								
					
					# if we do have a connection to the website, lets do all this extra stuff
					if web_api :
						# get the last 3 series this driver has raced in
						drv_last_series = irw.last_series(drv['UserID'])
						series_stats = False
						for s in drv_last_series:
							# is the series which this race is part of one of those 3?
							if s['seriesID'] == seriesid and not series_stats:
								# sweet it is!
								series_stats = True		
								# the number of starts they've had in the series											
								row.append(s['starts'])	
								# the driver's standing in the championship											
								row.append(s['position'])		
								# the average finish position									
								row.append(s['avgFinish'])		
								# average incidents per race									
								avginc = "%.0f" % float(int(s['incidents']) // int(s['starts']))	
								row.append(avginc)
						
						# if we can't get this driver's stats for this series, blank out these cols in their row
						if not series_stats:
							row.append('{0: <5}'.format(""))
							row.append('{0: <5}'.format(""))
							row.append('{0: <5}'.format(""))
							row.append('{0: <5}'.format(""))
					
					# right, lets add the row to our table
					tab.add_row(row)
					
					# add this driver's iR to the total for their vehicle
					ir_total[drv['CarPath'][:3]] += int(drv['IRating'])	
					
					# append this driver's iR to the list for their vehicle	
					irs[drv['CarPath'][:3]].append(int(drv['IRating']))		
					
					# driver count for this car
					drv_count[drv['CarPath'][:3]] += 1	
					
			# this sets the height of our window so it fits everything neatly
			os.system("mode con lines=%s" % (count + 11))	
			
			# if my_car isn't set, we're a spectator so lets just set it to be what ever the final car was... just so we can test things
			if my_car == "":
				my_car = drv['CarPath'][:3]
			
			# strength of field math: we take the average and add it to the median and divide by 2 and we seem to get close enough
			sof = float(((int(ir_total[my_car]) / int(drv_count[my_car])) + int(median(irs[my_car]))) / 2)
			
			# the sof divided by 16 gets us pretty damn close to the winner's championship points gain
			winner_pts = sof / 16
			
			# this works out how the points step down each finishing position
			pts_diff = (winner_pts / (drv_count[my_car] - 1))
			
			# lets clear our splash screen and please wait message because we're ready to display our awesome table!
			os.system('cls' if os.name == 'nt' else 'clear')
			print(" ")
			
			# if this is multiclass, lets say which car we're talking about
			if mc:
				sof_my_car_string = " of %s:" % my_car.upper()
				pts_my_car_string = " for %s:" % my_car.upper()
			else:
				sof_my_car_string = ""
				pts_my_car_string = ""
			
			# show the guestimated strength of field
			print("Approx SOF%s: %.0f" % (sof_my_car_string, sof)) 		
			
			# only show points if this race went official
			if ir['WeekendInfo']['WeekendOptions']['Unofficial'] == 0:	
				# some logic to not show points for positions which don't exist
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
				# else tell them this isn't an official race, so no points for you
				print("Race is UNOFFICIAL, no PTS will be awarded")		
				
			print(" ")
			
			# set some nice alignments for our cols
			tab.align['Name'] = 'l'
			tab.align['#'] = 'r'
			tab.align['iR'] = 'r'
			if web_api:
				tab.align['Races'] = 'r'
				tab.align['SPos'] = 'r'
				tab.align['AvgFin'] = 'r'
				tab.align['AvgInc'] = 'r'
			
			# if this isn't a multiclass event, don't show the car col
			if not mc:
				display.pop(1)	
			
			# we sort by the CarIdx because its the grid order, but we don't show the ID
			table = tab.get_string(sortby='ID', fields=display)		
			# display our table and bask in the love and admiration of the user... awwwww yisssss!
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
# go on, press it.... or click close... or alt-f4... whatever, I don't care
input("Press Enter to close ...") 



