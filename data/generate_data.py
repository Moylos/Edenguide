
import numpy as np, pandas as pd
rng=np.random.default_rng(42)
t=pd.date_range("2026-01-01",periods=24*90,freq="h")
n=len(t); h=np.arange(n)
x1=20+5*np.sin(2*np.pi*h/24)+rng.normal(0,1,n)
x2=50+10*np.sin(2*np.pi*h/(24*7))+rng.normal(0,2,n)
x3=rng.uniform(0,10,n)
y=3.0+1.8*x1-0.4*x2+0.7*x3+0.002*h+rng.normal(0,1.5,n)
pd.DataFrame({"timestamp":t,"temperature":x1.round(3),"pressure":x2.round(3),"load":x3.round(3),"output":y.round(3)}).to_csv("data/sensors.csv",index=False)
print(n)
