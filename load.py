import pandas as pd
import teams as tm
import drivers as dr
import race as rc
import series as se
import contracts as co




def save(name):
    if len(name)>0:
        name=name + '/'
        rc.save(name)
        co.save(name)
        tm.save(name)
        se.save(name)
        dr.save(name)
    else:
        print('Nezadal si meno')

def load_all(name):
    if len(name)>0:
        name = name + '/'
        se.load(name)
        co.load(name)
        rc.load(name)
        tm.load(name)
        dr.load(name)
    else:
        print('Nezadal si meno')