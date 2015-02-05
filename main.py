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

# set up our API things
ir = irsdk.IRSDK() # interfaces with the local iRacing API
irw = iRWebStats() # interfaces with the iRacing.com website API

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
			ir_total = defaultdict(lambda: 0) 					# a dictionary for iRating totals per car, default to 0
			drv_count = defaultdict(lambda: 0) 					# a dictionary for driver totals per car, default to 0
			irs = dict() 										# a dictionary for all the iRatings
			prev_car = "" 										# we do a check against this later
			my_car = "" 										# blank var for our vehicle
			mc = False 											# set multiclass to false until proven otherwise
			count = 0 											# count of drivers, because the full list includes spectators and the pace car
			
			# lets run through each driver in the race
			for drv in ir['DriverInfo']['Drivers']:
				# this checks that the driver isn't a spectator or the pace car, lol
				if drv['CarNumberRaw'] > 0:
					count += 1 									# increase our total driver count by one
					name = drv['AbbrevName'].split(', ') 		# AbbrevName's are LastName, FirstInitial
					name = "%s %s" % (name[1], name[0][:15]) 	# if the lastname is over 15 chars in length, trim it
					name = '{0: <17}'.format(name) 				# pad all the names out to be 17 chars total
					
					# finally lets sort out any special chars so all names will be displayed correctly in the windows console
					name = name.encode('windows-1252', errors='replace').decode('windows-1252', errors='replace')
					
					if irw.custid == drv['UserID']:				# is this driver our user?
						my_car = drv['CarPath'][:3]				# then this is their car type
						name = ">%s<" % name[:15]				# wack > < around their name to highlight it

					# collect all the basic info up into a new row
					row = ([int(drv['CarIdx']), drv['CarNumberRaw'], drv['CarPath'][:3].uppercase, name, drv['LicString'], drv['IRating']])
					
					try:
						irs[drv['CarPath'][:3]] = list()		# try to make a new list for this type of car
					except:
						blah = 1								# if the car already has an entry, lets avoid an error
					
					# if we do have a connection to the website, lets do all this extra stuff
					if web_api :
						# get the last 3 series this driver has raced in
						drv_last_series = irw.last_series(drv['UserID'])
						series_stats = False
						for s in drv_last_series:
							# is the series which this race is part of one of those 3?
							if s['seriesID'] == seriesid and not series_stats:
								series_stats = True													# sweet it is!
								row.append(s['starts'])												# the number of starts they've had in the series
								row.append(s['position'])											# the driver's standing in the championship
								row.append(s['avgFinish'])											# the average finish position
								avginc = "%.0f" % float(int(s['incidents']) // int(s['starts']))	# average incidents per race
								row.append(avginc)
						
						# if we can't get this driver's stats for this series, blank out these cols in their row
						if not series_stats:
							row.append('{0: <5}'.format(""))
							row.append('{0: <5}'.format(""))
							row.append('{0: <5}'.format(""))
							row.append('{0: <5}'.format(""))
					
					# right, lets add the row to our table
					tab.add_row(row)
					
					ir_total[drv['CarPath'][:3]] += int(drv['IRating'])		# add this driver's iR to the total for their vehicle
					irs[drv['CarPath'][:3]].append(int(drv['IRating']))		# append this driver's iR to the list for their vehicle
					drv_count[drv['CarPath'][:3]] += 1						# driver count for this car
					if count > 1 and not prev_car == drv['CarPath'][:3]:	# if this isn't our first driver, is this car different from the last one?
						mc = True											# oh it is, then this is a multiclass race!
					prev_car = drv['CarPath'][:3]							# previous car is what the current car was, because we're done with this guy

			os.system("mode con lines=%s" % (count + 11))	# this sets the height of our window so it fits everything neatly
			
			# if my_car isn't set, we're a spectator so lets just set it to be what ever the final car was... just so we can test things
			if my_car == "":
				my_car = prev_car
			
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
				sof_my_car_string = " of %s:" % my_car.uppercase
				pts_my_car_string = " for %s:" % my_car.uppercase
			else:
				sof_my_car_string = ""
				pts_my_car_string = ""
				
			print("Approx SOF%s: %.0f" % (sof_my_car_string, sof)) 		# show the guestimated strength of field
			
			if ir['WeekendInfo']['WeekendOptions']['Unofficial'] == 0:	# only show points if this race went official
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
				print("Race is UNOFFICIAL, no PTS will be awarded")		# else tell them this isn't an official race, so no points for you
				
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
				
			if not mc:
				display.pop(1)	# if this isn't a multiclass event, don't show the car col
				
			table = tab.get_string(sortby='ID', fields=display)		# we sort by the CarIdx because its the grid order, but we don't show the ID
			print(table)											# display our table and bask in the love and admiration of the user... awwwww yisssss!
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
input("Press Enter to close ...") # go on, press it.... or click close... or alt-f4... whatever, I don't care



