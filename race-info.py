#!python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
import traceback
from itertools import groupby, count
from math import exp, log
from tkinter import Tk, Toplevel, Label, HORIZONTAL, W, E, LEFT
from tkinter.font import Font
from tkinter.messagebox import askyesno, showerror
from tkinter.simpledialog import askstring
from tkinter.ttk import Treeview, Progressbar

import irsdk
import keyring
import requests
from keyring.backends import Windows

import config as cfg
from ir_webstats.ir_webstats.client import iRWebStats

denom = 1600 / log(2)

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


def score(pos, compet, scenario):
    posiR = [placement['iR'] for placement in scenario if placement['place'] == pos][0]
    competiR = [placement['iR'] for placement in scenario if placement['place'] == compet][0]
    return ((1 - exp(-posiR / denom)) * (exp(-competiR / denom))) / (
            (1 - exp(-competiR / denom)) * (exp(-posiR / denom)) + (1 - exp(-posiR / denom)) * (
        exp(-competiR / denom)))


def fudge(place, scenario):
    return ((len(scenario)) / 2 - place) / 100


def ir_Delta(place, scenario):
    return (len(scenario) - place - (sum(map(lambda c: score(place, c, scenario), range(1, len(scenario) + 1))) - 0.5) - fudge(place, scenario)) * 200 / len(scenario)


def get_name(drv, ddb, irw, cls):
    global my_cls
    tags = []
    name = drv["UserName"]

    # is this driver our user?
    if irw.custid == str(drv['UserID']):
        # then this is their car type
        my_cls = cls
        tags.append('user')

    if ddb:
        # is this a real-world driver?
        trimmedName = re.search('([A-Za-zÀ-ž ]*)', name).group(1).rstrip()
        r = requests.get(f'https://www.driverdb.com/autocomp/?term={trimmedName}')
        if r.status_code == 200 and len(r.text):
            tags.append('ddb')

    return name, tags


def build_row(drv, progress, ddb, irw, cls, web_api, seriesid, classPos, rowIdx):
    (name, tags) = get_name(drv, ddb, irw, cls)
    # collect all the basic info up into a new row
    row = ([classPos, cls, name, drv['LicString'], drv['IRating']])

    # if we do have a connection to the website, lets do all this extra stuff
    if web_api:
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
                avginc = f"{float(int(s['incidents']) // int(s['starts'])):.0f}"
                row.append(avginc)

        # if we can't get this driver's stats for this series, blank out these cols in their row
        if not series_stats:
            for _ in range(4):
                row.append('')

    progress['value'] = rowIdx
    progress.winfo_toplevel().update()
    return row, tags


def add_iRcolumn(tab, drv_by_class, custID):
    # Show the expected change in iRating for finishing in each position
    iRDelta = []
    for (cls, cls_drivers) in drv_by_class.items():
        if my_cls != cls:
            iRDelta.extend([''] * len(cls_drivers))
            continue
        iRmap = {drv['UserID']: drv['IRating'] for drv in cls_drivers}
        for finPos in range(1, len(cls_drivers) + 1):
            scenario = [{'place': finPos, 'iR': iRmap[custID]}] + \
                       [{'place': pos, 'iR': iR} for (pos, iR) in
                        zip([pos for pos in range(1, len(cls_drivers) + 1) if pos != finPos],
                            [iR for (custId, iR) in iRmap.items() if
                             custId != custID])]
            iRDelta.append(int(ir_Delta(finPos, scenario)))

    # just make sure the order is right (should be since rows were generated by class)
    for (row, delta) in zip(tab.get_children(), iRDelta):
        tab.set(row, 'iRDelta', delta)


def printSOFpoints(mc, drv_by_class, unofficial):
    res = ''
    # iR totals by class
    ir_total = {cls: sum([drv['IRating'] for drv in drivers]) for (cls, drivers) in drv_by_class.items()}
    # iRs by class
    irs = {cls: [drv['IRating'] for drv in drivers] for (cls, drivers) in drv_by_class.items()}
    # driver count by class
    drv_count = {cls: len(drivers) for (cls, drivers) in drv_by_class.items()}

    # strength of field math: we take the average and add it to the median and divide by 2 and we seem to get close enough
    sof = float(((int(ir_total[my_cls]) / int(drv_count[my_cls])) + int(median(irs[my_cls]))) / 2)

    # the sof divided by 16 gets us pretty damn close to the winner's championship points gain
    winner_pts = sof / 16

    # this works out how the points step down each finishing position
    pts_diff = (winner_pts / (drv_count[my_cls] - 1))

    # show the guestimated strength of field
    res += f'Approx SOF' + (f' of {my_cls}' if mc else '') + f': {sof:.0f}\n'

    # only show points if this race went official
    if not unofficial:
        res += f'Approx PTS' + (f' for {my_cls}: ' if mc else ': ') + ' | '.join(
            [f'{pos + 1}: {winner_pts - pts_diff * pos:.0f}' for pos in range(0, drv_count[my_cls])[:5]])
    else:
        # else tell them this isn't an official race, so no points for you
        res += 'Race is UNOFFICIAL, no PTS will be awarded'

    return res


def main():
    # local iRacing API
    ir = irsdk.IRSDK()

    # iRacing.com website API
    irw = iRWebStats(verbose=False)

    # create UI frame
    root = Tk()
    root.title('Race Info')
    root.withdraw()  # hide for now

    # get/store credentials & preferences
    cfg.read("config.ini")
    keyring.set_keyring(Windows.WinVaultKeyring())
    if cfg.config['ddb'] == '':
        cfg.config['ddb'] = askyesno('DriverDb', 'Check if drivers are on DriverDB.com?')
    if cfg.config['username'] == '':
        cfg.config['username'] = askstring('iRacing Login', 'Username')
        pw = askstring('iRacing Login', 'Password', show='*')
        keyring.set_password('race-info', cfg.config['username'], pw)
    else:
        pw = keyring.get_password('race-info', cfg.config['username'])
    cfg.config.write()

    # check if the local API can talk to the game, ie: is iRacing running
    if ir.startup():
        if any(['Race' == ses['SessionType'] for ses in ir['SessionInfo']['Sessions']]):
            # if we're in debug mode, dump the info files
            if debug:
                json.dump(ir['SessionInfo'], open("SessionInfo.txt", 'w'), sort_keys=True, indent=4,
                          separators=(',', ': '))
                json.dump(ir['WeekendInfo'], open("WeekendInfo.txt", 'w'), sort_keys=True, indent=4,
                          separators=(',', ': '))
                json.dump(ir['QualifyResultsInfo'], open("QualifyResultsInfo.txt", 'w'), sort_keys=True, indent=4,
                          separators=(',', ': '))
                json.dump(ir['DriverInfo'], open("DriverInfo.txt", 'w'), sort_keys=True, indent=4,
                          separators=(',', ': '))

            try:
                # let the user know we're connecting to the website
                irw.login(cfg.config['username'], pw)
                web_api = True
            except:
                # if it didn't work we'll set up only the minimal table
                web_api = False

            seriesid = ir['WeekendInfo']['SeriesID']
            # is it multiclass?
            mc = ir['WeekendInfo']['NumCarClasses'] > 1
            # Split into classes first
            drv_by_class = {cls: [drv for drv in list(group) if drv['CarNumberRaw']] for cls, group in
                            groupby(ir['DriverInfo']['Drivers'], key=lambda drv: drv['CarClassShortName']) if
                            cls or not mc}
            if not drv_by_class:
                showerror(title='Multiclass Replay', message='Not supported for replay of a multiclass race session')
                exit(1)
            # total drivers
            cnt = sum([len(drivers) for drivers in drv_by_class.values()])
            # process all the drivers
            popup = Toplevel(root)
            progress = Progressbar(popup, orient=HORIZONTAL, length=200, mode='determinate')
            progress['maximum'] = cnt
            Label(popup, text='Getting driver information...').pack(anchor=W)
            progress.pack()
            counter = count(0)
            rows_tags = [build_row(drv, progress, 'True' == cfg.config['ddb'], irw, cls, web_api,
                              seriesid, classPos,
                              next(counter)) for (cls, cls_drivers) in drv_by_class.items() for (drv, classPos) in
                    zip(cls_drivers, range(1, len(cls_drivers) + 1))]

            # Table creation
            core_cols = ['#', 'Class', 'Name', 'License', 'iR']
            webapi_cols = ['Races', 'SPos', 'AFin', 'AInc']
            display = core_cols + (webapi_cols if web_api else []) + ['iRDelta']
            sofpoints = Label(root,
                              text=printSOFpoints(mc, drv_by_class, ir['WeekendInfo']['WeekendOptions']['Unofficial']),
                              anchor=W, justify=LEFT)
            tab = Treeview(root, show=["headings"], height=cnt)
            tab["columns"] = display
            tab.tag_configure('user', background='#FFF3B3')
            tab.tag_configure('ddb', background='#7CFC00')
            for (row, tags) in rows_tags:
                tab.insert("", 'end', values=row, tags=tags)
            add_iRcolumn(tab, drv_by_class, int(irw.custid))
            for col in display:
                tab.column(col, anchor=E if 'Name' != col else W, width=min([int(Font().measure(['W'] * 84) * .62), max(
                    [Font().measure(col),
                     *[Font().measure(str(tab.item(row)['values'][display.index(col)])) for row in
                       tab.get_children()]])]))
                tab.heading(col, text=col)
            sofpoints.pack(anchor=W)
            tab.pack()
            tab.bind('<Control-c>', lambda _e: root.clipboard_clear() or root.clipboard_append(
                '\n'.join([','.join(tab["columns"]),
                           *(','.join(['"' + str(i) + '"' for i in tab.item(r)['values']]) for r in
                             tab.get_children())])))
            popup.withdraw()
            root.deiconify()
            root.mainloop()
        else:
            showerror(title='This is not a race session', message='Race Info only generates details for races')
    else:
        showerror(title='iRacing is not running', message='Join the race session first, then run Race Info')


if __name__ == "__main__":
    try:
        main()
    except :
        showerror(title='Exception', message=traceback.format_exc())
