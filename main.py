#!python3

import re
import irsdk
from prettytable import PrettyTable

def median(mylist):
	sorts = sorted(mylist)
	length = len(sorts)
	if not length % 2:
		return (sorts[length // 2] + sorts[length // 2 - 1]) / 2.0
	return sorts[length // 2]

tab = PrettyTable(['#', 'Name', 'Q Time', 'License', 'iRating'])

ir = irsdk.IRSDK()

if ir.startup():

	qualy_results = dict()

	for res in ir['QualifyResultsInfo']['Results']:
		qualy_results[res['CarIdx']] = res['FastestTime']

	ir_total = 0
	drv_count = 0
	irs = list()
	for drv in ir['DriverInfo']['Drivers']:
		if drv['CarNumberRaw'] > 0:
			q_time = qualy_results[int(drv['CarIdx'])]
			if q_time == 0.0:
				q_time = 999.999
			tab.add_row([drv['CarNumberRaw'], drv['UserName'], "%.3f" % float(q_time), drv['LicString'], drv['IRating']])
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
