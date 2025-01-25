import pandas as pd
import random as rd
import drivers as dr
import series as se
import teams as tm
import contracts as co
import time
from datetime import datetime, timedelta

results=[]
races=[]
driver_stands=[]
team_stands=[]
engine_stands=[]
chassi_stands=[]
pneu_stands=[]
stands=[]
pointSystem=[]

def load(name):



    global driver_stands
    global team_stands
    global engine_stands
    global chassi_stands
    global pneu_stands
    global stands
    global races
    global pointSystem
    global results
    driver_stands = pd.read_csv(name+'driver_stands.csv')
    team_stands = pd.read_csv(name + 'team_stands.csv')
    engine_stands = pd.read_csv(name + 'engine_stands.csv')
    chassi_stands = pd.read_csv(name + 'chassi_stands.csv')
    pneu_stands = pd.read_csv(name + 'pneu_stands.csv')
    stands = pd.read_csv(name + 'stands.csv')
    races = pd.read_csv(name+'races.csv')
    #print("Load races", races)
    races["race_date"] = pd.to_datetime(races["race_date"], format="%d-%m-%Y")
    pointSystem = pd.read_csv(name+'pointSystem.csv')
    results = pd.read_csv(name+'results.csv')
    #print("Load races",races)


def save(name):

    if len(name)>0:
        races.to_csv(name + 'craces.csv', index=False)
        driver_stands.to_csv(name + 'driver_stands.csv', index=False)
        team_stands.to_csv(name + 'team_stands.csv', index=False)
        engine_stands.to_csv(name + 'engine_stands.csv', index=False)
        chassi_stands.to_csv(name + 'chassi_stands.csv', index=False)
        pneu_stands.to_csv(name + 'pneu_stands.csv', index=False)
        stands.to_csv(name + 'stands.csv', index=False)
        pointSystem.to_csv(name + 'pointSystem.csv', index=False)
        results.to_csv(name + 'results.csv', index=False)

    else:
        print('Nezadal si meno')

def prepare_race(races_this_day,i,dat):
    ss = time.time()
    print("today race",races_this_day.name)
    active_DTcontracts = co.DTcontract[(co.DTcontract['startYear'] <= dat.year) & (co.DTcontract['endYear'] >= dat.year)]
    #print(active_DTcontracts)
    #print(c)
    filtered_DTcontracts = active_DTcontracts[active_DTcontracts['driverId'].isin(dr.active_drivers['driverId'])]
    #print(races_this_day.iloc[i]['seriesId'])
    teams_in_series = co.STcontract[co.STcontract['seriesId'] == races_this_day.iloc[i]['seriesId']]['teamId']
    #print("TIS", teams_in_series)
    # Filter DTcontract to find active contracts for the selected teams
    active_contracts_per_team = filtered_DTcontracts[filtered_DTcontracts['teamId'].isin(teams_in_series)]
    selected_for_race = pd.merge(active_contracts_per_team, dr.drivers[['driverId', 'ability']], on='driverId', how='left')

    selected_for_race = selected_for_race.reset_index(drop=True)
    #print("ACPT", active_contracts_per_team)
    # set data for race
    columns = ['driverId', 'ability', 'carId', 'carSpeedAbility', 'carCornerAbility', 'teamId','engineId','chassiId','pneuId']

    # Create DataFrame
    race_data = pd.DataFrame(columns=columns)

    for j in range(len(selected_for_race)):
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!
        race_data.loc[len(race_data)] = [selected_for_race.loc[j]['driverId'], selected_for_race.loc[j]['ability'], j,
                                         88, 55, selected_for_race.loc[j]['teamId'], selected_for_race.loc[j]['teamId'], selected_for_race.loc[j]['teamId'], selected_for_race.loc[j]['teamId']]
    #print('rules',dat)
    #print(races_this_day)
    race_data = race_data.sort_values(by='ability', ascending=False)
    race_data = race_data.reset_index(drop=True)
    current_rules = se.rules[
        (se.rules['seriesId'] == races_this_day.iloc[i]['seriesId']) & (se.rules['startSeason'] <= dat.year) & (
                    se.rules['endSeason'] >= dat.year)]
    current_rules = current_rules.reset_index(drop=True)
    #print(current_rules)
    filtered_ps = pointSystem[(pointSystem['psId'] == current_rules.loc[0]['psId'])]


    es = time.time()
    et = es - ss

    #print(f"Prepare race data Time: {et} seconds")
    return race_data, filtered_ps, current_rules

#!!!!TODO more drivers in 1 car, more drivers in results
def race(race,race_data,current_rules,ps): #,results,driver_stands
    global stands
    ss = time.time()

    x=[]
    for i in range(len(race_data)-1,-1,-1):
        x.append(i)
    res=[]
    rep=[]
    for i in range(len(race_data)-1):
        d=x[0]
        for j in range(1,len(x)):
            a=rd.randint(0, 9)
            if a<3:
                d=x[j]

        res.append(d)
        #dr.drivers.loc[dr.drivers['driverId'] == d, 'reputation_race'] += race['reputation'] // i
        rep.append(race_data.loc[d]['driverId'])
        #dr.active_drivers.loc[dr.active_drivers['driverId'] == d, 'reputation_race'] += race['reputation'] // len(res)
        #print(race['reputation'] // len(res))
        x.remove(d)
    dr.race_reputations(race['reputation'],rep)

    if len(x)==1:
        res.append(x[0])
    for i in range(len(res)):
        #raceId,driverId,teamId,carId,position
        results.loc[len(results)] =[race.loc['raceId'],race_data.loc[res[i]]['driverId'],race_data.loc[res[i]]['teamId'],race_data.loc[res[i]]['carId'],i+1]
    #print(x,res)
    #print('Results', results)
    #pointS
    sss = time.time()
    if race.loc['championship']:
        final = pd.DataFrame(columns=stands.columns).astype(stands.dtypes)
        prefiltered=stands[(stands['seriesId'] == race.loc['seriesId']) & (stands['year'] == race.loc['season']) ]
        for typ in ('driver', 'team', 'engine', 'chassi', 'pneu'):

            subject = race_data[[typ+'Id']].drop_duplicates()
            if typ=='driver':
                subject['cars'] = 1
            else:
                subject['cars'] = current_rules.iloc[0][typ+'Cts']
            subject['points'] = 0
            #drivers
            filtered_df = prefiltered[ (prefiltered['typ'] == typ)]

            # Get the row with the highest round
            this_round=filtered_df['round'].max()
            result_subject = filtered_df[filtered_df['round'] == this_round].copy()



            if len(result_subject )==0:

                for i in range(len(res)):


                    current_subject = race_data.loc[res[i]][typ+'Id']

                    subject.loc[(subject[typ+'Id'] == current_subject) & (subject['cars'] > 0), ['cars', 'points']] = \
                    subject.loc[(subject[typ+'Id'] == current_subject) & (subject['cars'] > 0), ['cars', 'points']] + [-1,
                                                                                                                   ps.iloc[
                                                                                                                            0][
                                                                                                                            i + 1]]


                subject['raceId'] = race.loc['raceId']
                subject['year'] = race.loc['season']
                subject['round'] = 1
                subject['position'] = 0
                subject['seriesId'] = race.loc['seriesId']
                subject['typ'] = typ
                subject.drop('cars', axis=1, inplace=True)



                sorted = subject.sort_values(by='points', ascending=False)
                sorted['position'] = range(1, len(subject) + 1)
                sorted.rename(columns={typ+'Id': 'subjectId'}, inplace=True)

                #final = pd.concat([final, sorted], ignore_index=True)




            else:

                for i in range(len(res)):


                    current_subject = race_data.loc[res[i]][typ+'Id']
                    subject.loc[(subject[typ+'Id'] == current_subject) & (subject['cars'] > 0), ['cars', 'points']] = subject.loc[(subject[typ+'Id'] == current_subject) & (subject['cars'] > 0), ['cars', 'points']] + [-1, ps.iloc[0][i + 1]]






                subject['raceId'] = race.loc['raceId']
                subject['year'] = race.loc['season']
                subject['round'] = this_round+1
                subject['position'] = 0
                subject['seriesId'] = race.loc['seriesId']
                subject['typ'] = typ
                subject.drop('cars', axis=1, inplace=True)
                #print('e',subject)





                subject['points'] += subject[typ+'Id'].map(result_subject.set_index('subjectId')['points']).fillna(0)
                new_entries = result_subject[~result_subject['subjectId'].isin(subject[typ+'Id'])]
                subject = pd.concat([subject, new_entries], ignore_index=True)
                subject['points'] = subject['points'].astype(int)
                sorted = subject.sort_values(by='points', ascending=False)
                sorted['position'] = range(1, len(subject) + 1)
                sorted.drop('subjectId', axis=1, inplace=True)
                sorted.rename(columns={typ + 'Id': 'subjectId'}, inplace=True)
                sorted['subjectId'] = sorted['subjectId'].astype(int)
                #print('c',sorted)
            final = pd.concat([final, sorted], ignore_index=True)
                #print(c)

        stands = pd.concat([stands, final], ignore_index=True)



        #print(merged_with_all_columns)
    #print(stands)

    es = time.time()
    et = es - sss

    #print(f"Points Time: {et} seconds")
    et = es - ss

    #print(f"Race Time: {et} seconds")

    return results, driver_stands

def plan_races(dat):
    global races
    ss = time.time()
    year=dat.year
    x=0
    a=0
    for j in range(364):
        if dat.strftime('%a') == 'Sun':
            x += 1
            if x % 3 == 0:
                a += 1
                filtered_series = se.series[
                    (se.series['startYear'] <= dat.year) &
                    (se.series['endYear'] >= dat.year)
                    ]
                for i in range(len(filtered_series)):
                    new_raceId = races['raceId'].max() + 1
                    if len(races)==0:
                        new_raceId=0
                    if i==len(filtered_series)-1 and x%6==0:
                        ch=False
                    else:
                        ch=True
                    new_row = {
                        'raceId': new_raceId,
                        'seriesId': filtered_series.iloc[i]['seriesId'],
                        'season': dat.year,
                        'trackId': 14,
                        'layoutId': 24,
                        'race_date': dat,
                        'name': 'Preteky '+filtered_series.iloc[i]['name'],
                        'championship': ch,
                        'reputation': 1000//filtered_series.iloc[i]['reputation'],
                        'reward': 1000000,
                    }

                    races.loc[len(races)] = new_row

                #x = 0

        dat = dat + timedelta(days=1)

    print(a,year)
    es = time.time()
    et = es - ss

    #print(f"Plan Race Time: {et} seconds")

def print_champ(year,series):

    for i in ('driver','team','engine','chassi','pneu'):
        #print(i)
        year_stands=stands[
                (stands['year'] == year) &
                (stands['typ'] == i) &
                (stands['seriesId'] == series)
                 ]
        if year_stands.empty:
            continue
            print("No data found for the specified year and seriesId.")
        else:
            max_round = year_stands['round'].max()

            # Filter rows that contain the highest round number
            highest_round_rows = year_stands[year_stands['round'] == max_round]
            highest_round_rows = highest_round_rows.sort_values(by='position', ascending=True)
            if i =='driver':
                merged_df = pd.merge(highest_round_rows, dr.drivers, left_on='subjectId', right_on='driverId')
                merged_df=merged_df[['forename','surname','points','position']]
            else:
                merged_df = pd.merge(highest_round_rows, tm.teams,  left_on='subjectId', right_on='teamId')
                merged_df = merged_df[['teamName', 'points', 'position']]
            #f_year_stands=year_stands[(year_stands['round']==highest_value_row)]
            #print(series,year)
            #print(merged_df)




