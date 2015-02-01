#!/usr/bin/env python
""" iRWebStats class. Check examples.py for example usage. """
__author__ = "Jeyson Molina"
__email__ = "jjmc82@gmail.com"
__version__ = "1.0"


import urllib

try:
    import urllib.parse
    encode = urllib.parse.urlencode  # python3
except:
    encode = urllib.urlencode  # python2

import requests
import constants as ct
import datetime
import csv
import time
import json
import re
import io
from decimal import Decimal
from util import *

requests.packages.urllib3.disable_warnings()

class iRWebStats:
	global custid
	""" Use this class to connect to iRacing website and request some stats
		from drivers, races and series. It needs to be logged in the
		iRacing membersite so valid login crendentials (user, password)
		are required. Most  data is returned in JSON format and
		converted to python dicts. """

	def __init__(self, verbose=True):
		self.last_cookie = ''
		self.logged = False
		self.custid = 0
		self.verbose = verbose
		self.TRACKS, self.CARS, self.DIVISION, self.CARCLASS, self.CLUB = {},\
			{}, {}, {}, {}

	def __save_cookie(self):
		""" Saves the current cookie to disk from a successful login to avoid 
			future login procedures and save time. A cookie usually last  
			at least a couple of hours """

		#print("Saving cookie for future use")
		o = open('cookie.tmp', 'w')
		o.write(self.last_cookie)
		o.write('\r\n' + str(self.custid))
		o.close()

	def __load_cookie(self):
		""" Loads a previously saved cookie """

		try:
			o = open('cookie.tmp', 'r')
			self.last_cookie, self.custid = o.read().split('\r\n')
			o.close()
			return True
		except:
			return False

	def login(self, username='', password='', quiet=False):
		""" Log in to iRacing members site. If there is a valid cookie saved 
			then it tries to use it to avoid a new login request. Returns 
			True is the login was succesful and stores the customer id 
			(custid) of the current login in self.custid. """

		if self.logged:
			return True
		data = {"username": username, "password": password, 'utcoffset': 300,
				'todaysdate': ''}
		try:
			if not quiet:
				print("Loggin in...")
			# Check if there's a previous cookie
			if (self.__load_cookie() and self.__check_cookie()):
				#  If previous cookie is valid
				if not quiet:
					print("Previous cookie valid")
				self.logged = True
				# Load iracing info
				if not quiet:
					self.__get_irservice_info(self.__req(ct.URL_IRACING_HOME,
													 cookie=self.last_cookie))
				# TODO Should we cache this?
				return self.logged
			self.custid = ''
			r = self.__req(ct.URL_IRACING_LOGIN, grab_cookie=True)
			if r.find("<h2>iRacing Is Offline</h2>") > -1:
				print("iRacing is Offline, try again later")
				self.logged = False
			else:
				r = self.__req(ct.URL_IRACING_LOGIN2, data,
							   cookie=self.last_cookie, grab_cookie=True)

				if 'irsso_members' in self.last_cookie:
					ind = r.index('js_custid')
					custid = int(r[ind + 11: r.index(';', ind)])
					self.custid = custid
					self.logged = True
					if not quiet:
						self.__get_irservice_info(r)
					self.__save_cookie()
					if not quiet:
						print("Log in succesful")
				else:
					if not quiet:
						print("Invalid Login (user: %s).\n\rPlease check your credentials" % (username))
					self.logged = False

		except Exception as e:
			self.logged = False
		return self.logged

	def logout(self):
		self.logged = False  # TODO proper logout

	def __check_cookie(self):
		""" Checks the cookie by testing a request response"""

		r = parse(self.__req(ct.URL_DRIVER_COUNTS, cookie=self.last_cookie))
		if isinstance(r, dict):
			return True
		return False

	def __req(self, url, data=None, cookie=None, grab_cookie=False,
			  useget=False):
		""" Creates and sends the HTTP requests to iRacing site """

		# Sleep/wait to avoid flooding the service with requests
		time.sleep(ct.WAIT_TIME)  # 0.3 seconds
		h = ct.HEADERS.copy()
		if cookie is not None:  # Send the cookie
			h['Cookie'] = cookie
		elif len(self.last_cookie):
			h['Cookie'] = self.last_cookie

		if (data is None) or useget:
			try:
				req = requests.get(url, headers=h, params=data, verify=False)
			except requests.exceptions.ConnectionError as e:
				print("Unable to connect to iracing.com")
			except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as e:
				print("Timeout connecting to iracing.com")
				
		else:
			h['Content-Type'] = 'application/x-www-form-urlencoded;\
					charset=UTF-8'
			req = requests.post(url, data=data, headers=h, verify=False)
		if 'Set-Cookie' in req.headers and grab_cookie:
			self.last_cookie = req.headers['Set-Cookie']
		html = req.text
		return html

	def __get_irservice_info(self, resp):
		""" Gets general information from iracing service like current tracks, 
			cars, series, etc. Check self.TRACKS, self.CARS, self.DIVISION 
			, self.CARCLASS, self.CLUB. """

		print("Getting iRacing Service info (cars, tracks, etc.)")
		items = {"TRACKS":  "TrackListing", "CARS": "CarListing",
				 "CARCLASS":  "CarClassListing", "CLUBS": "ClubListing",
				 "SEASON": "SeasonListing", "DIVISION": "DivisionListing",
				 "YEARANDQUARTER": "YearAndQuarterListing"}
		for i in items:
			str2find = "var " + items[i] + " = extractJSON('"
			try:
				ind1 = resp.index(str2find)
				json_o = resp[ind1 + len(str2find): resp.index("');", ind1)]\
					.replace('+', ' ')
				o = json.loads(json_o)
				if i not in ("SEASON", "YEARANDQUARTER"):
					o = {ele['id']: ele for ele in o}
				setattr(self, i, o)  # i.e self.TRACKS = o

			except Exception as e:
				print(("Error ocurred. Couldn't get %s" % i))
		

	@logged_in
	def iratingchart(self, custid=None, category=ct.IRATING_ROAD_CHART):
		""" Gets the irating data of a driver using its custom id (custid) 
			that generates the chart located in the driver's profile. """

		r = self.__req(ct.URL_STATS_CHART % (custid, category),
					   cookie=self.last_cookie)
		return parse(r)

	@logged_in
	def driver_counts(self):
		""" Gets list of connected myracers and notifications. """

		r = self.__req(ct.URL_DRIVER_COUNTS, cookie=self.last_cookie)
		return parse(r)

	@logged_in
	def career_stats(self, custid=None):
		""" Gets career stats (top5, top 10, etc.) of driver (custid)."""

		r = self.__req(ct.URL_CAREER_STATS % (custid),
					   cookie=self.last_cookie)
		return parse(r)[0]

	@logged_in
	def yearly_stats(self, custid=None):
		""" Gets yearly stats (top5, top 10, etc.) of driver (custid)."""

		r = self.__req(ct.URL_YEARLY_STATS % (custid),
					   cookie=self.last_cookie)
		# tofile(r)
		return parse(r)

	@logged_in
	def cars_driven(self, custid=None):
		""" Gets list of cars driven by driver (custid)."""

		r = self.__req(ct.URL_CARS_DRIVEN % (custid),
					   cookie=self.last_cookie)
		# tofile(r)
		return parse(r)

	@logged_in
	def personal_best(self, custid=None, carid=0):
		""" Personal best times of driver (custid) using car 
			(carid. check self.CARS) set in official events."""

		r = self.__req(ct.URL_PERSONAL_BEST % (carid, custid),
					   cookie=self.last_cookie)
		return parse(r)

	@logged_in
	def driverdata(self, drivername):
		""" Personal data of driver  using its name in the request 
			(i.e drivername="Victor Beltran"). """

		r = self.__req(ct.URL_DRIVER_STATUS % (encode({
			'searchTerms': drivername})), cookie=self.last_cookie)
		# tofile(r)
		return parse(r)

	@logged_in
	def lastrace_stats(self, custid=None):
		""" Gets stats of last races (10 max?) of driver (custid)."""

		r = self.__req(ct.URL_LASTRACE_STATS % (custid),
					   cookie=self.last_cookie)
		return parse(r)

	@logged_in
	def driver_search(self, race_type=ct.RACE_TYPE_ROAD, location=ct.LOC_ALL,
					  license=(ct.LIC_ROOKIE, ct.ALL), irating=(0, ct.ALL),
					  ttrating=(0, ct.ALL), avg_start=(0, ct.ALL),
					  avg_finish=(0, ct.ALL), avg_points=(0, ct.ALL),
					  avg_incs=(0, ct.ALL), active=False,
					  sort=ct.SORT_IRATING, page=1, order=ct.ORDER_DESC):
		"""Search drivers using several search fields. A tuple represent a 
		   range (i.e irating=(1000, 2000) gets drivers with irating 
		   between 1000 and 2000). Use ct.ALL used in the lower or 
		   upperbound of a range disables that limit. Returns a tuple 
		   (results, total_results) so if you want all results you should 
		   request different pages (using page) until you gather all
		   total_results. Each page has 25 (ct.NUM_ENTRIES) results max."""

		lowerbound = ct.NUM_ENTRIES * (page - 1) + 1
		upperbound = lowerbound + ct.NUM_ENTRIES - 1
		search = 'null'
		friend = ct.ALL  # TODO
		studied = ct.ALL  # TODO
		recent = ct.ALL  # TODO

		active = int(active)
		# Data to POST
		data = {'custid': self.custid, 'search': search, 'friend': friend,
				'watched': studied, 'country': location, 'recent': recent,
				'category': race_type, 'classlow': license[0],
				'classhigh': license[1], 'iratinglow': irating[0],
				'iratinghigh': irating[1], 'ttratinglow': ttrating[0],
				'ttratinghigh': ttrating[1], 'avgstartlow': avg_start[0],
				'avgstarthigh': avg_start[1], 'avgfinishlow': avg_finish[0],
				'avgfinishhigh': avg_finish[1], 'avgpointslow': avg_points[0],
				'avgpointshigh': avg_points[1], 'avgincidentslow':
				avg_incs[0], 'avgincidentshigh': avg_incs[1],
				'lowerbound': lowerbound, 'upperbound': upperbound,
				'sort': sort, 'order': order, 'active': active}

		total_results, drivers = 0, {}

		try:
			r = self.__req(ct.URL_DRIVER_STATS, data=data,
						   cookie=self.last_cookie)
			res = parse(r)
			total_results = res['d']['33']

			header = res['m']
			f = res['d']['r'][0]
			if int(f['29']) == int(self.custid):  # 29 is custid
				drivers = res['d']['r'][1:]
			else:
				drivers = res['d']['r']
			drivers = format_results(drivers, header)

		except Exception as e:
			print("Error fetching driver search data. Error: %s" % e)

		return drivers, total_results

	def test(self, a, b=2, c=3):
		return a, b, c

	@logged_in
	def results_archive(self, custid=None, race_type=ct.RACE_TYPE_ROAD,
						event_types=ct.ALL, official=ct.ALL,
						license_level=ct.ALL, car=ct.ALL, track=ct.ALL,
						series=ct.ALL, season=(2014, 2, ct.ALL),
						date_range=ct.ALL, page=1, sort=ct.SORT_TIME,
						order= ct.ORDER_DESC):
		""" Search race results using various fields. Returns a tuple 
			(results, total_results) so if you want all results you should 
			request different pages (using page). Each page has 25 
			(ct.NUM_ENTRIES) results max."""

		format_ = 'json'
		lowerbound = ct.NUM_ENTRIES * (page - 1) + 1
		upperbound = lowerbound + ct.NUM_ENTRIES - 1
		#  TODO carclassid, seriesid in constants
		data = {'format': format_, 'custid': custid, 'seriesid': series,
				'carid': car, 'trackid': track, 'lowerbound': lowerbound,
				'upperbound': upperbound, 'sort': sort, 'order': order,
				'category': race_type, 'showtts': 0, 'showraces': 0,
				'showweek': 0, 'showops': 0, 'showofficial': 0,
				'showunofficial': 0, 'showrookie': 0, 'showclassa': 0,
				'showclassb': 0, 'showclassc': 0, 'showclassd': 0,
				'showpro': 0, 'showprowc': 0, }
		# Events
		ev_vars = {ct.EVENT_RACE: 'showraces', ct.EVENT_QUALY: 'showquals',
				   ct.EVENT_PRACTICE: 'showops', ct.EVENT_TTRIAL: 'showtts'}
		if event_types == ct.ALL:
			event_types = (ct.EVENT_RACE, ct.EVENT_QUALY, ct.EVENT_PRACTICE,
						   ct.EVENT_TTRIAL)

		for v in event_types:
			data[ev_vars[v]] = 1
		# Official, unofficial
		if official == ct.ALL:
			data['showofficial'] = 1
			data['showunoofficial'] = 1
		else:
			if ct.EVENT_UNOFFICIAL in official:
				data['showunofficial'] = 1
			if ct.EVENT_OFFICIAL in official:
				data['showofficial'] = 1

		# Season
		if date_range == ct.ALL:
			data['seasonyear'] = season[0]
			data['seasonquarter'] = season[1]
			if season[2] != ct.ALL:
				data['raceweek'] = season[2]
		else:
			# Date range
			tc = lambda s:\
				time.mktime(datetime.datetime.strptime(s, "%Y-%m-%d").timetuple()) * 1000
			data['starttime_low'] = Decimal(tc(date_range[0]))  # multiplied by 1000 | Fuzz wrapped this in Decimal to get it working in python 2.7
			data['starttime_high'] = Decimal(tc(date_range[1])) # Fuzz wrapped this in Decimal to get it working in python 2.7

		# License levels
		lic_vars = {ct.LIC_ROOKIE: 'showrookie', ct.LIC_A: 'showclassa',
					ct.LIC_B: 'showclassb', ct.LIC_C: 'showclassc',
					ct.LIC_D: 'showclassd', ct.LIC_PRO: 'showpro',
					ct.LIC_PRO_WC: 'showprowc'}

		if license_level == ct.ALL:
			license_level = (ct.LIC_ROOKIE, ct.LIC_A, ct.LIC_B, ct.LIC_C,
							 ct.LIC_D, ct.LIC_PRO, ct.LIC_PRO_WC)
		for v in license_level:
			data[lic_vars[v]] = 1
		
		r = self.__req(ct.URL_RESULTS_ARCHIVE, data=data,
					   cookie=self.last_cookie)
		res = parse(r)
		total_results, results = 0, []
		if len(res['d']):
			total_results = res['d']['46']
			results = res['d']['r']
			header = res['m']
			results = format_results(results, header)

		return results, total_results

	@logged_in
	def season_standings(self, season, carclass, club=ct.ALL, raceweek=ct.ALL,
						 division=ct.ALL, sort=ct.SORT_POINTS,
						 order=ct.ORDER_DESC, page=1):
		""" Search season standings using various fields. season, carclass 
			and club are ids.  Returns a tuple (results, total_results) so 
			if you want all results you should request different pages 
			(using page)  until you gather all total_results. Each page has
			25 results max."""

		lowerbound = ct.NUM_ENTRIES * (page - 1) + 1
		upperbound = lowerbound + ct.NUM_ENTRIES - 1

		data = {'sort': sort, 'order': order, 'seasonid': season,
				'carclassid': carclass, 'clubid': club, 'raceweek': raceweek,
				'division': division, 'start': lowerbound, 'end': upperbound}
		r = self.__req(ct.URL_SEASON_STANDINGS, data=data)
		res = parse(r)
		total_results = res['d']['27']
		results = res['d']['r']
		header = res['m']
		results = format_results(results, header)

		return results, total_results

	@logged_in
	def season_tt_standings(self, season, carclass, club=ct.ALL, raceweek=ct.ALL,
						 division=ct.ALL, sort=ct.SORT_POINTS,
						 order=ct.ORDER_DESC, page=1):
		""" Search season Time Trial standings using various fields. season, carclass 
			and club are ids.  Returns a tuple (results, total_results) so 
			if you want all results you should request different pages 
			(using page)  until you gather all total_results. Each page has
			25 results max."""

		lowerbound = ct.NUM_ENTRIES * (page - 1) + 1
		upperbound = lowerbound + ct.NUM_ENTRIES - 1

		data = {'sort': sort, 'order': order, 'seasonid': season,
				'carclassid': carclass, 'clubid': club, 'raceweek': raceweek,
				'division': division, 'start': lowerbound, 'end': upperbound}
		r = self.__req(ct.URL_SEASON_TT_STANDINGS, data=data)
		res = parse(r)
		total_results = res['d']['27']
		results = res['d']['r']
		header = res['m']
		results = format_results(results, header)

		return results, total_results

	@logged_in
	def season_tt_record(self, season, carclass, raceweek):
		""" Find the fastest time trial time for a seasonid and week num."""

		raceweek += 1
		data = {'seasonid': season, 'carclassid': carclass, 'raceweek': raceweek, 'start': 0, 'end': 1}
		r = self.__req(ct.URL_SEASON_TT_RES, data=data)
		res = parse(r)
		try:
			results = res['d']['r']
			header = res['m']
			results = format_results(results, header)
			record = results[0][u'besttime']

			return record
		except:
			return None

	@logged_in
	def season_qual_results(self, season, carclass, club=ct.ALL, raceweek=ct.ALL,
						 division=ct.ALL, sort=ct.SORT_POINTS,
						 order=ct.ORDER_DESC, page=1):
		""" Search season Qualifying standings using various fields. season, carclass 
			and club are ids.  Returns a tuple (results, total_results) so 
			if you want all results you should request different pages 
			(using page)  until you gather all total_results. Each page has
			25 results max."""

		lowerbound = ct.NUM_ENTRIES * (page - 1) + 1
		upperbound = lowerbound + ct.NUM_ENTRIES - 1

		data = {'sort': sort, 'order': order, 'seasonid': season,
				'carclassid': carclass, 'clubid': club, 'raceweek': raceweek,
				'division': division, 'start': lowerbound, 'end': upperbound}
		r = self.__req(ct.URL_SEASON_QUAL_RES, data=data)
		res = parse(r)
		print(res)
		total_results = res['d']['27']
		results = res['d']['r']
		header = res['m']
		results = format_results(results, header)

		return results, total_results

	@logged_in
	def season_qual_pole(self, season, carclass, raceweek):
		""" Find the fastest qualifying time for a seasonid and week num."""

		raceweek += 1
		data = {'seasonid': season, 'carclassid': carclass, 'raceweek': raceweek, 'start': 0, 'end': 1}
		r = self.__req(ct.URL_SEASON_QUAL_RES, data=data)
		res = parse(r)
		try:
			results = res['d']['r']
			header = res['m']
			results = format_results(results, header)
			pole = results[0][u'bestqualtime']

			return pole
		except:
			return None

	def last_series(self, userid):
		""" Returns stats for the last 3 series the driver has raced in """
		
		r = self.__req(ct.URL_LAST_SERIES % userid)
		res = parse(r)
		
		return res		

	@logged_in
	def my_season_standings(self, season, start=1, end=1):
		""" Returns the logged in user's current standing in a series, along 
			with the total number of drivers """

		r = self.__req(ct.URL_AGGREGATE_SEASON_STANDINGS % (season, start, end))
		res = parse(r)
		
		try:
			standing = res['custrow']
			total_drivers = res['rowcount']
		except:
			standing = 0
			total_drivers = 0

		return standing, total_drivers

	@logged_in
	def hosted_results(self, session_host=None, session_name=None,
					   date_range=None, sort=ct .SORT_TIME,
					   order=ct.ORDER_DESC, page=1):
		""" Search hosted races results using various fields. Returns a tuple
			(results, total_results) so if you want all results you should 
			request different pages (using page) until you gather all 
			total_results. Each page has 25 (ct.NUM_ENTRIES) results max."""

		lowerbound = ct.NUM_ENTRIES * (page - 1) + 1
		upperbound = lowerbound + ct.NUM_ENTRIES - 1

		data = {'sort': sort, 'order': order, 'lowerbound': lowerbound,
				'upperbound': upperbound}
		if session_host is not None:
			data['sessionhost'] = session_host
		if session_name is not None:
			data['sessionname'] = session_name

		if date_range is not None:
			# Date range
			tc = lambda s:\
				time.mktime(datetime.datetime.strptime(s, "%Y-%m-%d").
							timetuple()) * 1000
			data['starttime_lowerbound'] = tc(date_range[0])
			# multiplied by 1000
			data['starttime_upperbound'] = tc(date_range[1])

		r = self.__req(ct.URL_HOSTED_RESULTS, data=data)
		# tofile(r)
		res = parse(r)
		total_results = res['rowcount']
		results = res['rows']  # doesn't need format_results
		return results, total_results

	@logged_in
	def session_times(self, series_season, start, end):
		""" Gets Current and future sessions (qualy, practice, race) 
			of series_season """

		r = self.__req(ct.URL_SESSION_TIMES, data={'start': start, 'end': end,
					   'season': series_season}, useget=True)
		return parse(r)

	@logged_in
	def series_raceresults(self, season, raceweek):
		""" Gets races results of all races of season in specified raceweek """

		r = self.__req(ct.URL_SERIES_RACERESULTS, data={'seasonid': season,
					   'raceweek': raceweek})  # TODO no bounds?
		res = parse(r)
		header = res['m']
		results = res['d']
		results = format_results(results, header)
		return results

	@logged_in
	def event_results(self, subsession, sessnum=0):
		""" Gets the event results (table of positions, times, etc.). The
			event is identified by a subsession id. """
		r = self.__req(ct.URL_GET_EVENTRESULTS % (subsession, sessnum))\
				.encode('utf8')
		data = [x for x in csv.reader(io.StringIO(r), delimiter=',',
									  quotechar='"')]
		header_ev, header_res = data[0], data[3]
		event_info = dict(list(zip(header_ev, data[1])))
		results = [dict(list(zip(header_res, x))) for x in data[4:]]
		
		return event_info, results

	@logged_in
	def event_results2(self, subsession, custid):
		""" Get the event results from the web page rather than CSV. 
		Required to get ttRating for time trials """

		r = self.__req(ct.URL_GET_EVENTRESULTS2 % (subsession, custid),
					   cookie=self.last_cookie)
		
		resp = re.sub('\t+',' ',r)
		resp = re.sub('\r\r\n+',' ',resp)
		resp = re.sub('\s+',' ',resp)

		str2find = "var resultOBJ ="
		ind1 = resp.index(str2find)
		ind2 = resp.index("};", ind1) + 1
		resp = resp[ind1 + len(str2find): ind2].replace('+', ' ')

		ttitems = ("custid", "isOfficial", "carID", "avglaptime", "fastestlaptime", "fastestlaptimems", "fastestlapnum", "bestnlapstime", "bestnlapsnum", "lapscomplete", "incidents", "newttRating", "oldttRating", "sr_new", "sr_old", "reasonOutName")
		out = ""
		for ttitem in ttitems:
			ind1 = resp.index(ttitem)
			ind2 = resp.index(",", ind1) + 1
			out = out + resp[ind1: ind2]

		out = re.sub(r"{\s*(\w)", r'{"\1', out)
		out = re.sub(r",\s*(\w)", r',"\1', out)
		out = re.sub(r"(\w):", r'\1":', out)
		out = re.sub(r":\"(\d)\":", r':"\1:', out)
		out = re.sub(r"parseFloat\((\"\d\.\d\d\")\)", r'\1', out)

		out = out.strip().rstrip(',')
		out = "{\"" + out + "}"
		out = json.loads(out)

		return out

	@logged_in
	def past_series(self):
		""" Get a list of all past series """

		r = self.__req(ct.URL_GET_PASTSERIES,
					   cookie=self.last_cookie)
		
		start = r.find("var series")
		end = r.find("expandcollapseseries")
		resp = r[start:end]
		resp = re.sub('\t+',' ',resp)
		resp = re.sub('\r\r\n+',' ',resp)
		resp = re.sub('\s+',' ',resp)

		out = dict()
		pattern = "id:([0-9]*), name:\"([^\"]*)\", header_img"
		regex = re.compile(pattern, re.IGNORECASE)
		for match in regex.finditer(resp):
			out[match.group(1)] = match.group(2)

		return out

	def subsession_results(self, subsession, custid):
		""" Get the results for a time trial event from the web page. 
		"""

		r = self.__req(ct.URL_GET_SUBSESSRESULTS % (subsession, custid), useget=True)
		
		out = parse(r)['rows']
		
		return out

	def event_laps_single(self, subsession, custid, sessnum=0):
		""" Get the lap times for an event from the web page. 
		"""

		r = self.__req(ct.URL_GET_LAPS_SINGLE % (subsession, custid, sessnum),
					   cookie=self.last_cookie)
					   
		out = parse(r)

		return out

	def event_laps_all(self, subsession):
		""" Get the lap times for an event from the web page. 
		"""

		r = self.__req(ct.URL_GET_LAPS_ALL % subsession,
					   cookie=self.last_cookie)
					   
		out = parse(r)

		return out

	def best_lap(self, subsessionid, custid):
		""" Get the best lap time for a driver from an event. 
		"""
		
		laptime = self.event_laps_single(subsessionid, custid)['drivers'][0]['bestlaptime']
		
		return laptime

	def world_record(self, seasonyear, seasonquarter, carid, trackid, custid):
		""" Get the world record lap time for certain car in a season. 
		"""

		r = self.__req(ct.URL_GET_WORLDRECORD % (seasonyear, seasonquarter, carid, trackid, custid),
					   cookie=self.last_cookie)
		out = parse(r)
		
		subsessionid = out["d"]["r"][1]["17"]
		record_holder = out["d"]["r"][1]["26"]
		
		record = self.best_lap(subsessionid, record_holder)
		
		return record
	
if __name__ == '__main__':
    irw = iRWebStats()
    user, passw = ('username', 'password')
    irw.login(user, passw)
    print("Cars Driven", irw.cars_driven())  # example usage
