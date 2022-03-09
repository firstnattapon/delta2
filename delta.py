import pandas as pd
import numpy as np
import matplotlib.pyplot as plt  
import ccxt
import datetime
import streamlit as st
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
st.set_option('deprecation.showPyplotGlobalUse', False)
plt.style.use('ggplot')

class  delta :
    def __init__(self ,  usd = 1000 ,  fix_value = 0.50 , fix_ap = 0.50 ,
                 p_data = 'ETH-PERP', timeframe = '4h'  , limit  = 1200):
        self.usd        = usd
        self.fix_value  = fix_value
        self.fix_ap = fix_ap
        self.p_data     = p_data
        self.timeframe  = timeframe
        self.limit = limit

    @property
    def get_data(self):
        exchange = ccxt.ftx({'apiKey': '', 'secret': '', 'enableRateLimit': True})
        ohlcv = exchange.fetch_ohlcv(self.p_data, self.timeframe, limit=self.limit)
        ohlcv = exchange.convert_ohlcv_to_trading_view(ohlcv)
        df = pd.DataFrame(ohlcv)
        df.t = df.t.apply(lambda x: datetime.datetime.fromtimestamp(x))
        df = df.set_index(df['t'])
        df = df[['c' , 'v']] 
        df = df.rename(columns={"c" : 'asset-price' , "v" : 'volume' })
        dfx = df['asset-price'].values
        dfv = df['volume'].values.astype(int)
        return dfx ,  df.index  ,  dfv

    def delta_pv (self):
        delta_price , _ , _ = self.get_data
        series  =  np.ones((len(delta_price)), dtype=int) # input
        cash = np.zeros(len(delta_price)) ; cash[0] = (self.usd * self.fix_value)
        qty = np.zeros(len(delta_price))  
        re = np.zeros(len(delta_price))  

        for  i , v in enumerate(qty): # qty
            if series[i] == 0 & i != 0 :
                qty[i] = qty[i-1]
            else : qty[i] = (self.usd * self.fix_value) / delta_price[i]
        qty_usd  = qty * delta_price

        for  i , v in enumerate(re): # re
            if series[i] == 0 & i != 0 :
                re[i] = 0
            else : re[i] = (qty[i-1]  * delta_price[i]) - cash[0]

        for  i , v in enumerate(cash): # cash
            if  i == 0 :
                pass
            else : cash[i] = cash[i-1] +  re[i]

        sumusd_pv = qty_usd + cash
        pv_change = ((sumusd_pv - sumusd_pv[0]) / sumusd_pv[0]) *100
        return pv_change  

    def delta_ap (self):
        delta_price , _ , _ = self.get_data
        ap_change = (((delta_price - delta_price[0]) /  delta_price[0]) * self.fix_ap) * 100
        return ap_change

    def  cf (self):
        _ ,  idx  , idv = self.get_data
        pv_change =   self.delta_pv()
        ap_change =  self.delta_ap()
        cf_change = pv_change  -  ap_change
        cf_usd =  self.usd * (cf_change / 100)
        dic = {'idx' : idx  , 'pv_change': pv_change , 'ap_change': ap_change 
               ,  'cf_change': cf_change , 'cf_usd': cf_usd , 'volume': idv }

        return  dic
   
D =  st.number_input('Pick a number', 0, 10)
