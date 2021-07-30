import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt  
import pandas_datareader  as pdr
import ccxt
import streamlit as st
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
from datetime import datetime
st.set_option('deprecation.showPyplotGlobalUse', False)
import datetime
plt.style.use('ggplot')
from stqdm import stqdm

class  delta :
    def __init__(self , usd = 1000 , fix_value = 0.50, p_data = 'CAKE-PERP', timeframe = '15m'  , max  = 1535  
                 , limit  = 5000 , series_num = None , minimum_re = 0.005 , start_end = [182 , 196] , mode = 'mode2'):
        self.usd        = usd
        self.fix_value  = fix_value
        self.p_data     = p_data
        self.timeframe  = timeframe
        self.limit      = limit
        self.mode       = mode
        if      self.mode   == 'mode1':     self.series_num = [ i for i in range(max)]
        elif    self.mode   == 'mode2':     self.series_num = np.array(np.unique([np.around( x * max) for x in series_num]))
        else:pass
        self.minimum_re = minimum_re
        self.start_end = start_end

    def get_data(self):
        exchange = ccxt.ftx({'apiKey': '', 'secret': '', 'enableRateLimit': True})
        ohlcv = exchange.fetch_ohlcv(self.p_data, self.timeframe, limit=self.limit)
        ohlcv = exchange.convert_ohlcv_to_trading_view(ohlcv)
        df = pd.DataFrame(ohlcv)
        df.t = df.t.apply(lambda x: datetime.datetime.fromtimestamp(x))
        df = df.set_index(df['t'])
        df.t = df.index.dayofyear
        df = df.loc[df.t >= self.start_end[0]]
        df = df.loc[df.t <= self.start_end[1]]
        df = df.drop(['t'], axis=1)
        df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df = df.drop(['open', 'high' , 'low' , 'volume'] , axis=1) 
        df = df.dropna()
        return df

    def series(self):
        idx_close = 0 ; idx_perdit = 3  ;  idx_diff = 2 ; idx_index  = 1
        series  = self.get_data()
        series['index'] =np.array([ i for i in range(len(series))])
        series['perdit'] =series['index'].apply(func= (lambda x : np.where( x in self.series_num , 1 , 0)))
        return series

    def  nav (self):
        idx_amount = 3 ; idx_close = 0 ; idx_perdit = 2  ;  idx_re = 5  ;  idx_cash = 6 
        
        nav_data = self.series()
        nav_data['amount'] =  np.nan
        for i in range(len(nav_data)): # amount
            if i == 0 :
                nav_data.iloc[i, idx_amount] =   (self.usd * self.fix_value)  / nav_data.iloc[i, idx_close]
            else :

                  nav_data.iloc[i, idx_amount] =   np.where(nav_data.iloc[i, idx_perdit] == 1  and
                                                            (abs((nav_data.iloc[i-1, idx_amount] * nav_data.iloc[i, idx_close]) - (self.usd * self.fix_value)) 
                                                             / (self.usd * self.fix_value)) >= self.minimum_re,
                                                            (self.usd * self.fix_value) / nav_data.iloc[i , idx_close] ,  nav_data.iloc[i-1, idx_amount])                    
                
        nav_data['asset_value'] =  (nav_data['close']*nav_data['amount']) 

        nav_data['re'] =  np.nan
        for i in range(len(nav_data)): # re
            if i == 0 :
                nav_data.iloc[i, idx_re] =    0
            else :
                nav_data.iloc[i, idx_re] =    np.where(nav_data.iloc[i, idx_perdit] == 1 and 
                                                  (abs((nav_data.iloc[i-1, idx_amount] * nav_data.iloc[i, idx_close]) - (self.usd * self.fix_value)) 
                                                  / (self.usd * self.fix_value)) >= self.minimum_re
                                                  , (nav_data.iloc[i-1, idx_amount] * nav_data.iloc[i, idx_close]) -  (self.usd * self.fix_value) , 0)

        nav_data['cash'] =  np.nan
        for i in range(len(nav_data)): # cash
            if i == 0 :
                nav_data.iloc[i, idx_cash] =    (self.usd * self.fix_value)
            else :
                nav_data.iloc[i, idx_cash] =   (nav_data.iloc[i-1, idx_cash] + nav_data.iloc[i, idx_re] )

        nav_data['sumusd'] =  (nav_data['cash'] + nav_data['asset_value'])

        return nav_data

    def  mkt (self):
        idx_close = 0 ; idx_cashmkt = 9
        mkt_data  = self.nav()
        mkt_data[':'] = ':'
        mkt_data['cash_mkt'] =  (self.usd * self.fix_value)
        mkt_data['amount_mkt'] =   (mkt_data.iloc[0, idx_cashmkt]  / mkt_data.iloc[0, idx_close])
        mkt_data['assetvalue_mkt'] =  mkt_data['close'] * mkt_data['amount_mkt']
        mkt_data['sumusd_mkt'] = (mkt_data['assetvalue_mkt']  + mkt_data['cash_mkt'])

        return mkt_data

    def cf (self):
        idx_sumusd = 7 
        cf_data = self.mkt()
        cf_data[' : '] = ' : '
        cf_data['cf_usd'] =   cf_data['sumusd']  - cf_data['sumusd_mkt']
        cf_data['cf_change'] =  (cf_data['cf_usd'] /  cf_data.iloc[0 , idx_sumusd]) * 100

        return cf_data

    def change (self):
        idx_sumusd = 7  ; idx_sumusdmkt = 12
        change_data = self.cf()
        change_data['  :  '] = '  :  '
        change_data['price_change'] =   ((change_data['sumusd_mkt'] - change_data.iloc[0, idx_sumusdmkt]) / change_data.iloc[0, idx_sumusdmkt]) * 100
        change_data['pv_change']  = ((change_data['sumusd'] - change_data.iloc[0 , idx_sumusd] ) / change_data.iloc[0 , idx_sumusd]) *100

        return change_data

    def  final (self):
        idx_amount = 3 ; idx_close = 0 ; idx_perdit = 2  ;  idx_re = 5  ;  idx_cash = 6 

        final = self.change()
        final['   :   '] = '   :   '
        final['zero_line'] =  0
        final['start_usd'] =  self.usd
        final['t'] =    final.index.dayofyear
        
        for i in range(len(final)): 
            final['diff'] = (abs((final.iloc[i-1, idx_amount] * final.iloc[i, idx_close]) - (self.usd * self.fix_value)) 
                    / (self.usd * self.fix_value))

        return final
    
def getpair ():
    exchange = ccxt.ftx({'apiKey': '', 'secret': '', 'enableRateLimit': True})
    e = exchange.load_markets()
    pair_x   = [i for i in e if i[-1] == 'P']
    pair_x   = [i for i in pair_x if i[-9:] != 'BULL/USDT']
    pair_x   = [i for i in pair_x if i[-9:] != 'BEAR/USDT']
    pair_x   = [i for i in pair_x if i[-9:] != 'DOWN/USDT']
    pair_x   = [i for i in pair_x if i[-7:] != 'UP/USDT']
    return pair_x
pair_x = getpair()

#  streamlit
col2 , col3 , col4 , col5  , col6 = st.beta_columns(5)
fix_value = float(col2.text_input("fix_value", "0.5" ))
invest =  int(col3.text_input("invest" , "1000"))
timeframe = col4.text_input("timeframe", "15m")
max = int(col5.text_input("max" , "1535"))
minimum_re = float(col6.text_input("minimum_re" , "0.005"))

col7, col8 , col9   = st.beta_columns(3)
pair_data = col7.selectbox('pair_data', pair_x , 5 )    
start = col8.date_input('start' , datetime.date(2021,7,15)) ; start = int(start.timetuple().tm_yday) #; st.sidebar.write(start)
end = col9.date_input('end', datetime.date(2021,7,31)) ; end =  int(end.timetuple().tm_yday) #; st.sidebar.write(end)

col10 , col11 = st.beta_columns(2)
with col10.beta_expander("Feigenbaum "):
    linear_x = st.checkbox("linear", value = False)
    
    if linear_x :
        mode = 'mode1'
        y = None
    else:
        d_λ =  float(st.text_input("λ" , "3.90"))
        d_X0 =  float(st.text_input("X0" , "0.50"))
        d_N =  int(st.text_input("N" , "1000"))
        λ = st.slider('λ', min_value=0.0 , max_value=4.0 , value= d_λ  , format="%.3f" )
        X0 = st.slider('X0', min_value=0.0 , max_value=1.0 , value=d_X0  , format="%.2f" )    
        N = st.slider('N', min_value=0 , max_value=20000 , value=d_N) 

        y = [] ; x = X0 ; mu = λ ; num = int(N)
        for it in range(num):
            x = mu * x * (1.0 - x)
            y.append(x)
        mode = 'mode2'
    
# if x == 0.8749972636024641 and y[-1] == 0.8749972636024641 :
if 1 :
#     st.success('Success')
    
    delta_x = delta(usd = invest , minimum_re = minimum_re , fix_value = fix_value , max = max , 
                    p_data = pair_data , timeframe =  timeframe , series_num = y , start_end =[start , end] , mode = mode ) 
    delta_A= delta_x.final()

    with col11.beta_expander("expander"):
        options  = st.radio('options', 
                            ['cashflow_hold',
                             'rebalancing',
                             'cf_change vs price_change vs port-value_change',
                             'port-value_change vs price_change',
                             'amount_hold vs amount_mkt' ,
                             'asset-value_hold vs asset-value_mkt' ,
                             'cash_hold vs cash_mkt' ,
                             'sumusd_hold vs sumusd_mkt'] ,index=2 )

    if options == 'cashflow_hold':plot = ['cf_change' , 'zero_line']
    elif options == 'rebalancing':plot = ['re' , "zero_line"]
    elif options == 'cf_change vs price_change vs port-value_change' :plot = ['cf_change' ,'price_change', 'pv_change' , "zero_line"]
    elif options == 'port-value_change vs price_change':plot = ['pv_change' ,'price_change' , "zero_line"]
    elif options == 'amount_hold vs amount_mkt':plot = ['amount' ,'amount_mkt']
    elif options == 'asset-value_hold vs asset-value_mkt':plot = ['asset_value' ,'assetvalue_mkt']
    elif options == 'cash_hold vs cash_mkt':plot = ['cash' ,'cash_mkt']
    elif options == 'sumusd_hold vs sumusd_mkt':plot = ['sumusd' ,'sumusd_mkt' , "start_usd"]

    try: next_re = [i for i in  [i if i > delta_A['index'][-1] else None for i in delta_x.series_num] if i != None][0]
    except IndexError: next_re = None
        
    st.write('index :' , delta_A['index'][-1] , 
             '   ,   next_re :' , next_re ,
             '   ,   start :' , start , '   ,   end :' , end ,
             '   ,   perdit :',delta_A['perdit'][-1] ,'   ,   re :' ,
             round(delta_A['re'][-1] , 2) , '   ,   diff :' , round(delta_A['diff'][-1] , 4 ))

    # plot
    plt.subplots(figsize=(12, 8))
    
    for i in plot:
        plt.plot(delta_A[i] ,label =i)
   
    data_vl = delta_A[delta_A['index'].isin(delta_x.series_num)] ; vline = data_vl.index
    for vl in vline:
        plt.axvline(x=vl , ymin=0.0, ymax=0.50, color='k', alpha = 0.25)
        
    per_dit = data_vl[data_vl['re'] != 0 ] ; per_dit = per_dit.index
    for pd in per_dit:
        plt.axvline(x=pd , ymin=0.50 , ymax=1.00, color='k' , alpha = 0.25 )
        
    plt.legend()
    st.pyplot()
    # end_plot

    st.write('cf_change :'  , round(delta_A['cf_change'][-1] , 2),'%','   ,   cf_usd :',  round(float(delta_A['cf_usd'][-1]) , 2 ) ,'$')
    st.write('amount :'  , round(delta_A['amount'][-1] , 2) , '   ,   amount_mkt :',  round(delta_A['amount_mkt'][-1] , 2)  )
    st.write('sumusd :'  , round(delta_A['sumusd'][-1] , 2) , '   ,   sumusd_mkt :',  round(delta_A['sumusd_mkt'][-1] , 2)  )

    with st.beta_expander("data"):
        _, _ , head , _ ,   = st.beta_columns(4) 
        head.write('เริ่ม')
        st.dataframe(delta_A.head(1))
        _, _ , tail , _ ,   = st.beta_columns(4)
        tail.write('ล่าสุด')
        st.dataframe(delta_A.tail(1))
        _, _ , re , _ ,   = st.beta_columns(4)
        st.dataframe(delta_A[['close', 'perdit'  , 're']].tail(10))
        
    with st.beta_expander("series_num"):
        np.set_printoptions(threshold=sys.maxsize)
        st.code(delta_x.series_num)
        
    st.stop()

else:
    st.stop()        
