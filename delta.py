import pandas as pd
import numpy as np
import matplotlib.pyplot as plt  
import pandas_datareader  as pdr
import ccxt
import streamlit as st
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
from datetime import datetime
st.set_option('deprecation.showPyplotGlobalUse', False)

st.write("DB username:", st.secrets["db_username"])
st.write("DB password:", st.secrets["db_password"])
st.write("My cool secrets:", st.secrets["my_cool_secrets"]["things_i_like"])

class  delta :
    def __init__(self , usd = 1000 , fix_value = 0.50, pair_data = 'SRM-PERP', timeframe = '1h' , limit  = 2500):
        self.usd    = usd
        self.fix_value  = fix_value
        self.pair_data = pair_data
        self.timeframe = timeframe
        self.limit = limit
        
    def get_data(self):
        exchange = ccxt.ftx({'apiKey': '', 'secret': '', 'enableRateLimit': True})
        ohlcv = exchange.fetch_ohlcv(self.pair_data, self.timeframe, limit=self.limit)
        ohlcv = exchange.convert_ohlcv_to_trading_view(ohlcv)
        df = pd.DataFrame(ohlcv)
        df.t = df.t.apply(lambda x: datetime.fromtimestamp(x))
        df = df.set_index(df['t']);
        df = df.drop(['t'], axis=1)
        df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df = df.drop(['open', 'high' , 'low' , 'volume'] , axis=1) 
        df = df.dropna()
        return df

    def  mkt (self):
        mkt_data  = self.get_data()
        mkt_data['cash_mkt']     = np.nan ; mkt_data.iloc[0, 1]  = (self.usd * self.fix_value) ; mkt_data['cash_mkt']  = mkt_data.iloc[0, 1]
        mkt_data['amount_mkt']  = mkt_data.iloc[0, 2] = ((self.usd * self.fix_value) / mkt_data.iloc[0, 0])  ; mkt_data['amount_mkt']  = mkt_data.iloc[0, 2]
        mkt_data['asset_value_mkt'] = (mkt_data['amount_mkt'] * mkt_data['close'])
        mkt_data['sumusd_mkt'] = (mkt_data['asset_value_mkt']  + mkt_data['cash_mkt'])
        mkt_data['change_mkt'] =  ((mkt_data['sumusd_mkt'] - mkt_data.iloc[0, 4]) / mkt_data.iloc[0, 4]) * 100
        return mkt_data

    def  nav (self):
        nav_data = self.mkt()
        nav_data['amount_nav'] =    (self.usd * self.fix_value)  /  nav_data['close']
        nav_data['re_nav'] = (nav_data['amount_nav'].shift()* nav_data['close']) -  (self.usd * self.fix_value) 
        nav_data['cash_nav'] =  np.nan ; nav_data = nav_data.fillna(0) 

        for i in range(len(nav_data['cash_nav'])):
            if i == 0 :
                 nav_data.iloc[i, 8] =   (self.usd * self.fix_value) 
            else:
                nav_data.iloc[i, 8] =   ( nav_data.iloc[i, 7] + nav_data.iloc[i - 1, 8])

        nav_data['asset_value_nav'] =  ( nav_data['close']*nav_data['amount_nav'] ) 
        nav_data['sumusd_nav']  = (nav_data['cash_nav'] +  nav_data['asset_value_nav'] )
        nav_data['pvnav_change']  = (( nav_data['sumusd_nav'] - nav_data.iloc[0 , 10] ) / nav_data.iloc[0 , 10]) *100

        return nav_data

    def cf (self):
        cf_data = self.nav()
        cf_data['cf_usd'] =   (cf_data['sumusd_nav']  - cf_data['sumusd_mkt'])
        cf_data['cf_change'] =  (cf_data['cf_usd'] /  cf_data.iloc[0 , 10]) *100
        cf_data['0'] = 0
        return cf_data
    
#  streamlit

col1, col2 , col3 , col4 , col5   = st.beta_columns(5)
pair_data = col1.text_input("pair_data", "CRV/USD")
fix_value = float(col2.text_input("fix_value", "0.5" ))
invest =  int(col3.text_input("invest" , "1000"))
timeframe = col4.text_input("timeframe", "1h")
limit = int(col5.text_input("limit", "2500"))

delta_A = delta(usd = invest , fix_value = fix_value , pair_data = pair_data , timeframe =  timeframe  , limit  = limit)
delta_A= delta_A.cf()

_ = delta_A[['cf_change' ,'change_mkt' ,'0' ]] ; _.columns = ['1: cf_%', '2: mkt_%' , "3: zero_line"] 
st.line_chart(_)
_ = delta_A[[ 'pvnav_change', 'change_mkt' , '0' ]] ; _.columns = ['1: pv_%', '2: mkt_%' , "3: zero_line"] 
st.line_chart(_)

st.write('index        :' , len(delta_A) )
st.write('')
st.write( 'cf_usd      :'    ,  round(float(delta_A['cf_usd'][-1]) , 2 ) ,'$')
st.write('')
st.write( 'cf_change :'  , round(delta_A['cf_change'][-1] , 2),'%')

_, _ , head , _ ,   = st.beta_columns(4) 
head.write('เริ่ม')
st.dataframe(delta_A.head(1))
_, _ , tail , _ ,   = st.beta_columns(4)
tail.write('ล่าสุด')
st.dataframe(delta_A.tail(1))
