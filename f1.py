import load as ld
import race as rc
import drivers as dr
import mytime as mt

import time
from datetime import datetime, timedelta

# Assign the date to variable `dat`
start_time = time.time()
driver_each_year=2
begin=1843
end=2005



#transform data
dr.generate_drivers(begin,end,driver_each_year)
dr.drivers.to_csv('my_data/drivers.csv', index=False)

#load and set data
ld.load_all('my_data')
begin=15+dr.drivers['year'].min()
dat = datetime.strptime('01-01-'+str(begin), '%d-%m-%Y')
dr.choose_active_drivers(dat)



dat=mt.sim_year(dat,75)
print('aa ',dat)
#rc.plan_races(dat)
x=0



ld.save('ahoj')
ld.load_all('ahoj')
dat=mt.sim_year(dat,1)
end_time = time.time()

# Time taken in seconds
execution_time = end_time - start_time

print(f"Execution time: {execution_time} seconds")