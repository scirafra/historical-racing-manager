import pandas as pd
import load as ld
import race as rc
import pandas as pd
import numpy as np
import contracts as ct
import drivers as dr
import mytime as mt
import series as se
import contracts as co
import random as rd

from datetime import datetime, timedelta
begin=1843
dat = datetime.strptime('01-01-'+str(begin), '%d-%m-%Y')

def sim_day(dat,days):
    #global races
    global drivers
    global active_drivers
    global DTcontract
    global results
    global stands
    for i in range(days):
        dat = dat + timedelta(days=1)

        if dat.day == 1 and dat.month == 1:
            if dat.year > 1930:
            #if dat.year > 1893:
                rc.plan_races(dat)

            dr.update_drivers(dat)
            #print('som tu',dat.year)
            dr.choose_active_drivers(dat)
            active_series = se.series[
            (se.series['startYear'] <= dat.year) &
            (se.series['endYear'] >= dat.year)
            ]
            series_ids = active_series['seriesId']
            #print(series_ids)

            for index in range(len(series_ids)):
                # Access by position with iloc
                rc.print_champ(dat.year - 1, series_ids.iloc[index])

            ct.sign_contracts(active_series, dat,co.DTcontract,dr.active_drivers,se.rules,co.STcontract)
            #print('iuy',dat.year,active_drivers)

    races_this_day=rc.races[rc.races['race_date']== dat].copy()

    #check if race day
    if len(races_this_day)>0:
        races_this_day[ 'trackAbility'] = 50
        x=0


        for i in range(len(races_this_day)):
            race_data,filtered_ps,current_rules=rc.prepare_race(races_this_day,i,dat)
            results,stands=rc.race(races_this_day.iloc[i],race_data,current_rules,filtered_ps)

    return dat





def sim_year(dat,years):
    for i in range(years*366):

        dat=sim_day(dat,1)


    return dat

