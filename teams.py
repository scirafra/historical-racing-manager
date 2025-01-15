import pandas as pd

teams=[]

def load(name):
    global teams
    teams = pd.read_csv(name+'teams.csv')

def save(name):
    if len(name)>0:
        teams.to_csv(name + 'teams.csv', index=False)
    else:
        print('Nezadal si meno')