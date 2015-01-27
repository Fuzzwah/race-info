#!python3

import re
import irsdk
from prettytable import PrettyTable
import constants as ct
from iRWebStats import iRWebStats
import config as cfg

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
	
try:
	irw.login(cfg.config['username'], cfg.config['password'], quiet=True)
	web_api = True
	tab = PrettyTable(['#', 'Name', 'Q Time', 'License', 'iR', 'Races', 'SPos', 'AvgFin', 'AvgInc'])
	display = ['#', 'Name', 'License', 'iR', 'Races', 'SPos', 'AvgFin', 'AvgInc']
except:
	web_api = False
	tab = PrettyTable(['#', 'Name', 'Q Time', 'License', 'iRating'])
	display = ['#', 'Name', 'License', 'iR']
	print("Unable to log into iRacing.com")

if ir.startup():

	qualy_results = dict()

	for res in ir['QualifyResultsInfo']['Results']:
		qualy_results[res['CarIdx']] = res['FastestTime']
		
	seriesid = ir['WeekendInfo']['SeriesID']

	ir_total = 0
	drv_count = 0
	irs = list()
	
	for drv in ir['DriverInfo']['Drivers']:
		if drv['CarNumberRaw'] > 0:
			q_time = qualy_results[int(drv['CarIdx'])]
			if q_time == 0.0:
				q_time = 999.999
			row = ([drv['CarNumberRaw'], drv['UserName'], "%.3f" % float(q_time), drv['LicString'], drv['IRating']])
			
			if web_api:
				drv_last_series = irw.last_series(drv['UserID'])
				series_stats = False
				for s in drv_last_series:
					if s['seriesID'] == seriesid:
						series_stats = True
						row.append(s['starts'])
						row.append(s['position'])
						row.append(s['avgFinish'])
						avginc = "%.0f" % float(int(s['incidents']) // int(s['starts']))
						row.append(avginc)
				
				if not series_stats:
					row.append('{0: <5}'.format(""))
					row.append('{0: <5}'.format(""))
					row.append('{0: <6}'.format(""))
					row.append('{0: <6}'.format(""))
					
			tab.add_row(row)
					
			ir_total += int(drv['IRating'])
			irs.append(int(drv['IRating']))
			drv_count += 1

	sof = float(((int(ir_total) / int(drv_count)) + int(median(irs))) / 2)
	winner_pts_est = sof / 16
	
	print(" ")
	print("Approx SOF: %.0f" % sof)
	print("Est winner PTS: %.0f" % winner_pts_est)
	print(" ")

	tab.align['Name'] = 'l'
	table = re.sub("999.999", "       ", tab.get_string(sortby='Q Time', fields=display))
	print(table)
else:
	print("iRacing is not running")
