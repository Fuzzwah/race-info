#!python3

import re
import irsdk
from prettytable import PrettyTable
import constants as ct
from iRWebStats import iRWebStats

def median(mylist):
	sorts = sorted(mylist)
	length = len(sorts)
	if not length % 2:
		return (sorts[length // 2] + sorts[length // 2 - 1]) / 2.0
	return sorts[length // 2]

ir = irsdk.IRSDK()
irw = iRWebStats()

try:
	irw.login(cfg.config['Account']['username'], cfg.config['Account']['password'], quiet=True)
	web_api = True
	tab = PrettyTable(['#', 'Name', 'Q Time', 'License', 'iRating', 'Starts', 'S Pos', 'AvgFin', 'AvgInc'])
except:
	web_api = False
	tab = PrettyTable(['#', 'Name', 'Q Time', 'License', 'iRating'])
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
				print(drv_last_series)
				series_stats = False
				for s in drv_last_series:
					if s['seriesID'] == seriesid:
						series_stats = True
						row.append('{0: <6}'.format(s['starts']))
						row.append('{0: <6}'.format(s['position']))
						row.append('{0: <6}'.format(s['avgFinish']))
						avginc = "%.0f" % float(int(s['incidents']) // int(s['starts']))
						row.append('{0: <6}'.format(avginc))
				
				if not series_stats:
					row.append('{0: <6}'.format(""))
					row.append('{0: <6}'.format(""))
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
	table = re.sub("999.999", "       ", tab.get_string(sortby='Q Time'))
	print(table)
else:
	print("iRacing is not running")
