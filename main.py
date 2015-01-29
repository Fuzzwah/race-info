#!python3
#-*- coding: utf-8 -*-

import re
import irsdk
from prettytable import PrettyTable
import constants as ct
from iRWebStats import iRWebStats
import config as cfg
from collections import defaultdict

def median(mylist):
	sorts = sorted(mylist)
	length = len(sorts)
	if not length % 2:
		return (sorts[length // 2] + sorts[length // 2 - 1]) / 2.0
	return sorts[length // 2]

ir = irsdk.IRSDK()
irw = iRWebStats()

cfg.read("config.ini")
if cfg.config['password'] == '':
	cfg.config['username'] = str(input('Your iRacing username: '))
	cfg.config['password'] = str(input('Your iRacing password: '))
	
	cfg.config.write()
	print("Config saved")
	
if ir.startup():
	if ir['SessionInfo']['Sessions'][1]['SessionType'] == 'Race' or ir['SessionInfo']['Sessions'][2]['SessionType'] == 'Race':
		try:
			irw.login(cfg.config['username'], cfg.config['password'], quiet=True)
			web_api = True
			tab = PrettyTable(['#', 'Car', 'Name', 'Q Time', 'License', 'iR', 'Races', 'SPos', 'AFin', 'AInc'])
			display = ['#', 'Car', 'Name', 'License', 'iR', 'Races', 'SPos', 'AFin', 'AInc']
		except:
			web_api = False
			tab = PrettyTable(['#', 'Car', 'Name', 'Q Time', 'License', 'iRating'])
			display = ['#', 'Car', 'Name', 'License', 'iR']
			print("Unable to log into iRacing.com")	
		
		qualy_results = dict()

		for res in ir['QualifyResultsInfo']['Results']:
			qualy_results[res['CarIdx']] = res['FastestTime']
			
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
				q_time = qualy_results[int(drv['CarIdx'])]
				if q_time == 0.0:
					q_time = 999.999
				name = drv['AbbrevName'].split(', ')
				name = "%s %s" % (name[1], name[0][:17])
				row = ([drv['CarNumberRaw'], drv['CarPath'][:3], name.encode('windows-1252', errors='replace').decode('windows-1252', errors='replace'), "%.3f" % float(q_time), drv['LicString'], drv['IRating']])
				
				try:
					irs[drv['CarPath'][:3]] = list()
				except:
					print("blah")
				if irw.custid == drv['UserID']:
					my_car = drv['CarPath'][:3]
				
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
		
		if my_car == "":
			my_car = prev_car
		
		#print("total ir: %s drv count: %s median ir: %s" % (ir_total[my_car], drv_count[my_car], median(irs[my_car])))
		sof = float(((int(ir_total[my_car]) / int(drv_count[my_car])) + int(median(irs[my_car]))) / 2)
		winner_pts = sof / 16
		pts_diff = (winner_pts / (drv_count[my_car] - 1))
		
		print(" ")
		print("Approx SOF: %.0f" % sof)
		if drv_count[my_car] > 4:
			print("Approx PTS: 1st: %.0f | 2nd: %.0f | 3rd: %.0f | 4th: %.0f | 5th: %.0f" % (winner_pts, (winner_pts - pts_diff), (winner_pts - (pts_diff * 2)), (winner_pts - (pts_diff * 3)), (winner_pts - (pts_diff * 4))))
		elif drv_count[my_car] > 3:
			print("Approx PTS: 1st: %.0f | 2nd: %.0f | 3rd: %.0f | 4th: %.0f" % (winner_pts, (winner_pts - pts_diff), (winner_pts - (pts_diff * 2)), (winner_pts - (pts_diff * 3))))
		elif drv_count[my_car] > 2:
			print("Approx PTS: 1st: %.0f | 2nd: %.0f | 3rd: %.0f" % (winner_pts, (winner_pts - pts_diff), (winner_pts - (pts_diff * 2))))
		elif drv_count[my_car] > 1:
			print("Approx PTS: 1st: %.0f | 2nd: %.0f" % (winner_pts, (winner_pts - pts_diff)))
		else:
			print("Approx PTS: 1st: %.0f" % (winner_pts))
			
		print(" ")

		tab.align['Name'] = 'l'
		tab.align['#'] = 'l'
		if web_api:
			tab.align['Races'] = 'r'
			tab.align['SPos'] = 'r'
			tab.align['AvgFin'] = 'r'
			tab.align['AvgInc'] = 'r'
			
		if not mc:
			display.pop(1)
			
		table = re.sub("999.999", "       ", tab.get_string(sortby='Q Time', fields=display))
		print(table)
	else:
		print("This is not a race session.")
else:
	print("iRacing is not running.")
