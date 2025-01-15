import pandas as pd
import numpy as np
import random as rd

drivers=[]
active_drivers=[]

def load(name):
    global drivers
    drivers = pd.read_csv(name+'drivers.csv')

def save(name):
    if len(name)>0:
        drivers.to_csv(name + 'drivers.csv', index=False)
    else:
        print('Nezadal si meno')




ability_lim=69

data_types = {'raceId': 'int', 'year': 'int', 'round': 'int', 'circuitId': 'int', 'seriesID': 'int', 'name': 'str', 'date': 'str'}
# Create an empty DataFrame with specified columns and data types
transform_races = pd.DataFrame({col: pd.Series(dtype=dt) for col, dt in data_types.items()})


def choose_active_drivers(dat):
    global active_drivers
    active_drivers = drivers[(dat.year - drivers['year'] > (14)) & (drivers['ability'] > 35)]
    active_drivers = active_drivers.sort_values(by='ability', ascending=False)
    active_drivers = active_drivers.reset_index(drop=True)



def custom_sort(row):
    return tuple(-row.get(pos, 0) for pos in sorted(aq['position'].unique()))

def reassign_positions(group):
    group = group.sort_values(by='position').reset_index(drop=True)
    group['position'] = range(1, len(group) + 1)
    return group

def generate_new_drivers(year, needed_count,df,nationality_weights,x):
    new_drivers = []
    for _ in range(needed_count):
        nationality = np.random.choice(nationality_weights.index, p=nationality_weights.values)
        forename = "X"+df[df['nationality'] == nationality]['forename'].sample(1).values[0]
        surname = "x"+df[df['nationality'] == nationality]['surname'].sample(1).values[0]

        # Create a new driverId (incremental)
        new_driverId = df['driverId'].max() + 1 + x if len(df) > 0 else 1
        x += 1
        new_drivers.append({
            'driverId': new_driverId,
            'forename': forename,
            'surname': surname,
            'year': year,
            'dob': str(year) + '-01-01',  # Dummy date of birth, modify as needed
            'nationality': nationality
        })

    return pd.DataFrame(new_drivers)

def generate_drivers(begin_year,end_year,drivers_per_year):
    global drivers

    df = pd.read_csv('original/drivers.csv')
    df9 = pd.read_csv('original/results.csv')
    df3 = pd.read_csv('original/races.csv')

    #filter indy 500
    merged_df = pd.merge(df9, df3, on='raceId')
    indy_500_drivers = merged_df[merged_df['name'] == 'Indianapolis 500']['driverId'].unique()
    other_races_drivers = merged_df[merged_df['name'] != 'Indianapolis 500']['driverId'].unique()
    drivers_to_remove = set(indy_500_drivers) - set(other_races_drivers)
    filtered_drivers_df = df[~df['driverId'].isin(drivers_to_remove)]
    df=filtered_drivers_df



    #results driver correct
    max_rounds = df3.groupby('year')['round'].max().reset_index()
    result = pd.merge(df3, max_rounds, on=['year', 'round'])
    result_sorted = result.sort_values(by='year')
    df4 = pd.read_csv('original/driver_standings.csv')
    df4['seriesId'] = 1
    aa = pd.merge(df4, result_sorted, on=['raceId'])
    aa=aa[['driverId','position','year']]
    ab=pd.merge(aa, df, on=['driverId'])
    ab=ab[['driverId','code','surname','year','position']]

    ab2 = ab.groupby('year').apply(reassign_positions).reset_index(drop=True)
    ab = ab2.sort_values(by=['year','position'], ascending=[True,True])
    aq = ab[ab['year'] < 2050]

    #driver sorting
    position_counts = aq.pivot_table(index='driverId', columns='position', aggfunc='size', fill_value=0)

    sorted_df = position_counts.sort_values(by=position_counts.columns.tolist(), ascending=[False]*len(position_counts.columns))
    sorted_df = sorted_df.reset_index()
    dr = pd.merge(sorted_df,df, on=['driverId'])
    dr['year']=dr['dob'].str.slice(0, 4)
    dr['year']=dr['year'].astype('int64')
    dr=dr[dr['year']>1800]
    missing_driver_ids = df[~df['driverId'].isin(dr['driverId'])]

    # Filter df to keep only rows with missing driverId values
    new_rows = missing_driver_ids.copy()

    # Use .loc to set new columns
    new_rows.loc[:, 'year'] = new_rows['dob'].str.slice(0, 4)
    new_rows.loc[:, 'year'] = new_rows['year'].astype('int64')
    # Step 3: Append these new rows to dr
    dr = pd.concat([dr, new_rows], ignore_index=True)

    #give ability
    good = dr.groupby('year').head(drivers_per_year)
    good=good[['driverId','forename','surname','year','dob','nationality']]
    if begin_year==0:
        min_year = dr['year'].min()
    else:
        min_year = begin_year
    if end_year == 0:
        max_year = dr['year'].max()
    else:
        max_year = end_year
    print(min_year,'-',max_year)
    all_years = pd.Series(range(min_year, max_year + 1))
    driver_counts = dr.groupby('year').size().reindex(all_years, fill_value=0)
    years_with_fewer_than_two_drivers = driver_counts[driver_counts < drivers_per_year]
    nationality_counts = df['nationality'].value_counts()

    nationality_weights = nationality_counts / nationality_counts.sum()

    new_drivers_list = []
    x=0
    for year in years_with_fewer_than_two_drivers.index:

        needed_count = drivers_per_year - years_with_fewer_than_two_drivers[year]

        new_drivers_df = generate_new_drivers(year, needed_count,df,nationality_weights,x)
        print(year, needed_count,new_drivers_df)
        x+=needed_count
        new_drivers_list.append(new_drivers_df)
    new_drivers_df = pd.concat(new_drivers_list, ignore_index=True)
    final = pd.concat([good, new_drivers_df], ignore_index=True)
    #final=good #olny made drivers
    final = final.reset_index(drop=True)

    final['ability'] = 0
    final['ability_original'] = 0
    final['ability_best'] = 0

    # Initialize variables
    x = 1
    index = 0
    total_drivers = len(final)

    # Assign values using the while loop
    while index < total_drivers:
        # Determine the range for current x
        end_index = min(index + x, total_drivers)
        # Assign value x to the next x drivers
        final.loc[index:end_index-1, 'ability'] = ability_lim-x
        final.loc[index:end_index - 1, 'ability_original'] = ability_lim - x
        final.loc[index:end_index-1, 'ability_best'] = ability_lim-x
        # Move the index forward by x positions
        index = end_index
        # Increase x by 1 for the next group of drivers
        x += 1

    #print(final.head(60))
    print(final.tail(60))
    drivers=final
    #print(len(final))
    #return final

po=[4,4,3,3,3,2,2,2,2,1,1,1,1,1,0,0,-1,-1,-1,-1,-1,-2,-2,-2,-2,-3,-3,-3,-4,-4,-5,-6,-7,-8,-9,-10,-11,-12,-13]
#po = [7, 6, 5,4,3,2,1]


def calculate_adjustment(row, po, position,year):
    index = year - row['year']
    if index < 0 or index >= len(po):
        return 0  # No adjustment if year is out of range in po

    adjustment = po[index]
    if position == 'first':
        return adjustment
    elif position == 'second':
        return adjustment - 1
    elif position == 'third':
        return adjustment - 2

def update_drivers(dat):
    global drivers
    for i in range(13):

        filtered_drivers = drivers[
            (dat.year - drivers['year'] > (15+3*i)) &
            (dat.year - drivers['year'] < (19+3*i)) &
            (drivers['ability'] > 35)
            ]
        if len(filtered_drivers)>0:
            filtered_drivers = filtered_drivers.sort_values(by='ability', ascending=False)
            filtered_drivers = filtered_drivers.reset_index(drop=True)

            n = len(filtered_drivers)
            a = n // 3
            remainder = n % 3

            a1 = 1 if remainder == 2 else 0
            a2 = 1 if remainder == 1 else 0

            # Assign positions to the drivers
            positions = ['first'] * (a + a1) + ['second'] * (a + a2) + ['third'] * (n - 2 * a - a1 - a2)
            filtered_drivers['position'] = positions


            for i in range(len(filtered_drivers)):
                position = filtered_drivers.loc[i, 'position']
                adjustment = calculate_adjustment(filtered_drivers.loc[i], po, position,dat.year-16)
                filtered_drivers.at[i, 'ability'] += adjustment #rd.randint(adjustment-2,adjustment)
                filtered_drivers['ability_best'] = filtered_drivers.apply(lambda row: max(row['ability'], row['ability_best']), axis=1)

            filtered_drivers.drop(columns=['position'], inplace=True)
            #print(filtered_drivers)
            # Drop the 'position' column as it's no longer needed

            filtered_drivers = filtered_drivers[['driverId', 'ability','ability_best']]
            drivers = drivers.set_index('driverId')
            filtered_drivers = filtered_drivers.set_index('driverId')
            drivers.update(filtered_drivers)
            drivers = drivers.reset_index()




