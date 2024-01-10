# -*- coding: utf-8 -*-
"""
Created on Sun Jul 23 22:04:50 2023

@author: narju

THIS IS FOR CALCULATING SHORTING MARGIN ON VIA-METAL CMB STRUCTURES
Grouped by .*_grp column

"""

import pandas as pd
import numpy as np
# from scipy.optimize import curve_fit
# from win32com.client import Dispatch
import os
import re
import matplotlib.pyplot as plt

#%%
val='VALUE_ABS'
delta='TSDR_DELTA'
test='TEST_NAME'
tsdr='TSDR_TYPE'
vx='VX'
viasize='SDR_VIA_SIZE'
lot7='LOT7'
wfr='WAFER'
metalline='METAL_LINE'
xx='X'
yy='Y'

#%%
# jmpfile=r"C:\Users\narju\OneDrive - Intel Corporation\Documents\Device\804_Dispo\EVFT GIB V0 FLARE D318RWMA\v1m1_shorting.jmp"
incsv=r"C:\Users\narju\OneDrive - Intel Corporation\Documents\Device\804_Dispo\M1M2 fixes WW01 GCIB FT\D338R5M0_v1\sm.csv"
auto_grp = [lot7,wfr,viasize,vx,metalline,'LINE_WIDTH']
log_leakage_at_margin=-10
plot_switch = 0

#%%
def f(x, a, b, c):
    return a+b*(x-c)**4

def gs(y,d):

    x=y.index.values
    y=y.values
    
    # gaussian smoothing
    d2 = float(d**(-2))
    yout = np.array([0.]*len(x))
    for i, xi in enumerate(x):
        gaussnow = np.exp(- ((x - xi)**2 *d2))
        norm = 1/(np.sum(gaussnow))
        yout[i] = np.inner(gaussnow,y)*norm
    yout=pd.Series(yout, index=x)
    return yout

def intercepts(x,y,target):
    x_ints=[]
    for i in range(len(y)-1):
        if (y[i]>target and y[i+1]<target) or (y[i]<target and y[i+1]>target):
            #intercepts.extend(i)
            xi = x[i]+(target-y[i])*(x[i+1]-x[i])/(y[i+1]-y[i])
            x_ints.append(xi)
    return x_ints

def margin(yp, target, side='l'):
        if yp.values.min() > target: 
            margin=0
        else:
            margin = intercepts(yp.index.values, yp.values, target)
            if len(margin)==0: 
                if side=='l': margin=yp.index.min()
                elif side=='r': margin=yp.index.max()
            elif len(margin)>1:
                margin=0 
            else:
                margin=margin[0]
        return margin

# ints=intercepts(x,y0,0)
# print(ints)

#%% load the data file 
# jmp = Dispatch("JMP.Application")
# doc = jmp.OpenDocument(jmpfile)
# doc.SaveAs(outcsv)

d=pd.read_csv(incsv)

#%%
group = d.columns[d.columns.str.contains('_grp$', regex=True)].to_list()
 # this variable name is recycled below. bad idea to use same variable name. fix.
n_group=len(group)

if len(group)==0: 
    d["_grp"]=d[auto_grp].apply(lambda x: ','.join(x.astype(str)), axis=1)
    
d = d.loc[ d[test].apply(lambda x: bool(re.search('LOG_I2.*1.1', x)) ) ]

#%%
# if there are >1 _grp cols, pick which one

if len(group)>1:
    for i in zip(range(len(group)), group ):
        print(i)

    selection=input("select baseline: ")
    if selection.rstrip().isdigit(): 
        print(group[int(selection.rstrip())], " selected")
        group=group[int(selection.rstrip())]
elif len(group)==1: group=group[0]
else: group = '_grp'

# group='split' # bad idea to use same variable name 
# d[group]=d[tsdr]+','+d[vx]+','+d[viasize]+','+d[group1]

#%%
splits=pd.DataFrame(d[group].unique(), columns=[group])
splits.set_index([group], inplace=True)
splits['LEFT_MARGIN']=0
splits['RIGHT_MARGIN']=0

di=d.groupby([delta,group])[val].quantile(0.75)
di=di.reset_index()

#%%
for split in splits.index.values:
        try:
            idx = (di[group]==split) & (~di[val].isna())
            y=di.loc[idx].astype({delta: float})
            # y[delta]=y[delta].astype(float)
            y.set_index([delta], inplace=True)
            
            y=y[val]
            
            # CURVE_FIT
            y = gs(y, 1)
                    
            yp=y.loc[y.index<=0]
            l_margin=margin(yp, log_leakage_at_margin, side='l')
            
            yp=y.loc[y.index>=0]
            r_margin=margin(yp, log_leakage_at_margin, side='r')
            
            splits.loc[splits.index==split,'LEFT_MARGIN']=round(l_margin, 2)
            splits.loc[splits.index==split,'RIGHT_MARGIN']=round(r_margin, 2)
            
            if plot_switch:
                fig, ax = plt.subplots()
                plot_title=split+ ' Margin:' +' ('+"{:.2f}".format(l_margin)+', '+"{:.2f}".format(r_margin)+')'
                y.plot(ax=ax, title=plot_title)
        except:
            print(split, "had a problem")
    
splits['SHORTING_WINDOW']=splits['RIGHT_MARGIN']-splits['LEFT_MARGIN']
splits['SHORTING_MARGIN']=splits[['RIGHT_MARGIN','LEFT_MARGIN']].apply(lambda x: min(x.RIGHT_MARGIN, -x.LEFT_MARGIN), axis=1)
splits.reset_index(inplace=True)

#%% =d[lot7]+','+d[wfr].astype(str)+','+d[viasize]+','+d[vx]+','+d[metalline]
if n_group==0: splits[auto_grp]=splits['_grp'].str.split(',',expand=True)

#%%
#Write to disk
directory=os.path.dirname(incsv)
csvname=os.path.basename(incsv)
splits.to_csv(os.path.join(directory, csvname+'_short_margin.csv'), index=False)
