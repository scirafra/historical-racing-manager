import pandas as pd
import random as rd
import teams as tm

CScontract=[]
DTcontract=[]
STcontract=[]


def load(name):
    global CScontract
    global DTcontract
    global STcontract
    CScontract = pd.read_csv(name+'CScontract.csv')
    DTcontract = pd.read_csv(name + 'DTcontract.csv')
    STcontract = pd.read_csv(name + 'STcontract.csv')

def save(name):
    if len(name)>0:
        STcontract.to_csv(name + 'STcontract.csv', index=False)
        DTcontract.to_csv(name + 'DTcontract.csv', index=False)
        CScontract.to_csv(name + 'CScontract.csv', index=False)
    else:
        print('Nezadal si meno')

def sign_contracts(active_series,dat,DTcontract,active_drivers,rules,STcontract):
    active_series = active_series.sort_values(by='reputation', ascending=True)
    active_series = active_series.reset_index(drop=True)
    # Step 1: Filter DTcontract to find drivers who have a contract in the given year
    contracted_drivers = DTcontract[(DTcontract['startYear'] <= dat.year) & (DTcontract['endYear'] >= dat.year)][
        'driverId']

    # Step 2: Identify drivers who don't have a contract in the given year
    non_contracted_drivers = active_drivers[~active_drivers['driverId'].isin(contracted_drivers)]
    ##print("Free", non_contracted_drivers)
    active_DTcontracts = DTcontract[(DTcontract['startYear'] <= dat.year) & (DTcontract['endYear'] >= dat.year)]
    #print("ACFTC",active_DTcontracts)
    x = 0
    for si in (active_series['seriesId']):
        active_rules = rules[
            (rules['startSeason'] <= dat.year) &
            (rules['endSeason'] >= dat.year)
            ]
        max_cars = active_rules[active_rules['seriesId'] == si]['maxCars']
        if len(max_cars)!=0:


            #print(si,max_cars)
            # Select the teamIds from STcontract where seriesId matches the current i
            teams_in_series = STcontract[STcontract['seriesId'] == si]['teamId']






            # Filter DTcontract to find active contracts for the selected teams

            active_contracts_per_team = active_DTcontracts[active_DTcontracts['teamId'].isin(teams_in_series)]
            #print("ACPT", active_contracts_per_team)
            # Group by teamId and count the number of active contracts
            contract_counts = active_contracts_per_team.groupby('teamId').size().reset_index(name='activeContracts')
            #print("CC",contract_counts)
            # Merge with all teams in the series to ensure all teams are included, even those with 0 contracts
            all_teams_in_series = pd.DataFrame(teams_in_series).merge(contract_counts, on='teamId', how='left').fillna(
                0)

            # Ensure activeContracts is an integer
            all_teams_in_series['activeContracts'] = all_teams_in_series['activeContracts'].astype(int)
            #print(all_teams_in_series)
            all_teams_in_series = pd.merge(all_teams_in_series, tm.teams, on='teamId')
            #human_teams = merged_teams[(merged_teams['ai'] == False)]
            #human_teams = human_teams.reset_index(drop=True)

            # Print the result
            #print(f"Active contracts for teams in seriesId {si}:")
            #print(all_teams_in_series)
            #print("\n")


            # !!!!!!!!!!!!!!!!!!!!!!!!!!!
            non_contracted_drivers = non_contracted_drivers.reset_index(drop=True)
            for i in range(max_cars.iloc[0]):
                for j in range(len(all_teams_in_series)):

                    if all_teams_in_series.iloc[j]['activeContracts'] == i and len(non_contracted_drivers) > 0:
                        if all_teams_in_series.iloc[j]['ai'] == False :
                            show_drivers=non_contracted_drivers[['driverId','forename','surname','year','reputation_race']]
                            show_drivers = show_drivers.sort_values(by='surname', ascending=True)
                            show_drivers = show_drivers.reset_index(drop=True)
                            print(show_drivers)
                            print(all_teams_in_series.iloc[j]['teamName'],dat.year)
                            while(True):

                                d = input("Which do you want ?")

                                if d.isdigit():
                                    d=int(d)
                                    if d>=0 and d<len(show_drivers):
                                        break

                            DTcontract.loc[len(DTcontract)] = [show_drivers.iloc[d]['driverId'],
                                                               all_teams_in_series.iloc[j]['teamId'], 25000, dat.year,
                                                               dat.year + rd.randint(0, 3)]
                            non_contracted_drivers = non_contracted_drivers[non_contracted_drivers['driverId'] != show_drivers.iloc[d]['driverId']]
                        else:
                            d=0
                            DTcontract.loc[len(DTcontract)] = [non_contracted_drivers.iloc[d]['driverId'],
                                                           all_teams_in_series.iloc[j]['teamId'], 25000, dat.year,
                                                           dat.year + rd.randint(0, 3)]
                            non_contracted_drivers = non_contracted_drivers.drop(d)
                        all_teams_in_series.at[j, 'activeContracts'] += 1

                        non_contracted_drivers = non_contracted_drivers.reset_index(drop=True)
                        x += 1
            #print('DT', DTcontract)
    return DTcontract