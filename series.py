import pandas as pd

series=[]
rules=[]

def load(name):
    global series
    global rules
    series = pd.read_csv(name+'series.csv')
    rules = pd.read_csv(name+'rules.csv')

def save(name):
    if len(name)>0:
        series.to_csv(name + 'series.csv', index=False)
        rules.to_csv(name + 'rules.csv', index=False)
    else:
        print('Nezadal si meno')