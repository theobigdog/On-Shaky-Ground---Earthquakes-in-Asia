# This file is intended to help shorten the associated Jupyter Notebook for my Capstone, On Shaky Ground - Earthquake Preparedness

import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX
import itertools


def make_ts(dataframe):
    return pd.Series(dataframe.set_index(dataframe['Date_Time'])['Magnitude'])

def load():
    df_countries = pd.read_csv('data/official_countries.csv')
    df_japan = df_countries[df_countries['Country'] == 'Japan'].reset_index(drop=True)
    df_japan = df_japan.drop('Unnamed: 0', axis=1)
    df_japan['Date_Time'] = pd.to_datetime(df_japan['Date_Time']).reset_index(drop=True)
    japan_ts = make_ts(df_japan)
    monthly_mean_japan = japan_ts.resample('QS').mean().ffill()
    return monthly_mean_japan, df_japan

def random_walk(train):
    rw = train.shift(1)
    rmse_rw = np.sqrt(mean_squared_error(train.dropna()[1:],rw.dropna()))
    return rmse_rw

def auto_ARIMA(train):
    p = d = q = range(0,3)
    pdq = list(itertools.product(p,d,q))
    seasonal_pdq = [(x[0],x[1],x[2],4) for x in list(itertools.product(p,d,q))]
    SARIMAX_dict3 = {'stats':[],'aic':[]} # Dictionary makes it easy to look through results when finished
    for param in pdq:
        for param_seasonal in seasonal_pdq:
            try:
                mod=SARIMAX(train,
                            order=param,
                            seasonal_order=param_seasonal,
                            enforce_stationarity=False,
                            enforce_invertibility=False)
                results = mod.fit(maxiter=200,method='nm',disp=False)
                SARIMAX_dict3['stats'].append('ARIMA{}x{}'.format(param,param_seasonal))
                SARIMAX_dict3['aic'].append(results.aic)
                print('ARIMA{}x{} - AIC:{}'.format(param,param_seasonal,results.aic))
            except: 
                print('Oops!')
                continue
    df_sar = pd.DataFrame(SARIMAX_dict3)
    df_sar.to_csv('data/SARIMAX_dict3.csv')

def RMSE(ts,mod):
    y_hat = mod.predict(typ='levels')
    return np.sqrt(mean_squared_error(ts,y_hat))
    
def RMSE_test(ts,mod,exo=None):
    y_hat = mod.predict(start=ts.index[0],end=ts.index[-1],exog=exo,typ='levels')
    return np.sqrt(mean_squared_error(ts,y_hat))

def fit_mod_jpn(endo, ordr, exo=None, season=(0,0,0,4)):
    return SARIMAX(endog=endo, exog=exo, order=ordr,seasonal_order=season, enforce_stationarity=False,
                    enforce_invertibility=False).fit(maxiter=200,method='nm',disp=False)

def generate_SARIMAX(df_japan, quarterly_mean, order, cutoff):
    # Setting up 3 more necessary Time-Series.
    quarterly_lat = (pd.Series(df_japan.set_index(df_japan['Date_Time'])['Latitude'])).resample('QS').mean().ffill()
    quarterly_long = (pd.Series(df_japan.set_index(df_japan['Date_Time'])['Longitude'])).resample('QS').mean().ffill()
    quarterly_dep = (pd.Series(df_japan.set_index(df_japan['Date_Time'])['Depth'])).resample('QS').mean().ffill()

    train = quarterly_mean[:cutoff]
    test = quarterly_mean[cutoff:]

    # Defining Exogenous Variables - All series need to match the train/test, so they are cut similarly here
    exo_lat = quarterly_lat[:cutoff]
    exo_lat_test = quarterly_lat[cutoff:]
    exo_long = quarterly_long[:cutoff]
    exo_long_test = quarterly_long[cutoff:]
    exo_dep = quarterly_dep[:cutoff]
    exo_dep_test = quarterly_dep[cutoff:]
    exo_lat_long = exo_long
    exo_lat_long_test = exo_long_test

    # Set up Lists for making models and printing summaries
    mod_list = ['Endo = Magnitude, Exo = Latitude:',
                'Endo = Magnitude, Exo = Longitude:',
                'Endo = Magnitude, Exo = Depth:',
                'Endo = Latitude, Exo = Longitude:']

    mod_train_list = [exo_lat, exo_long, exo_dep, exo_lat_long]
    mod_test_list = [exo_lat_test, exo_long_test, exo_dep_test, exo_lat_long_test]

    endos = [train,train,train,exo_lat]
    
    # Run the "baseline" model (no eXogneous)
    base_mod = fit_mod_jpn(train,order)
    # print('Base SARIMA Model, Endo = Magnitude Only','\np-values\n',round(base_mod.pvalues,2),'\nAIC:', round(base_mod.aic,3)) #Only the final model printed below
    # print('Train RMSE:',round(RMSE(train,base_mod),4),'\n','Test RMSE:',round(RMSE_test(test,base_mod),4),'\n')
    
    # Run the "individual" eXogenous models
    for mod in range(len(mod_list)):
        model = fit_mod_jpn(endos[mod],order,mod_train_list[mod])
    #     print(model.summary()) # These 3 lines commented out to save space - only final model (below) printed
        # print(mod_list[mod],'\np-values\n',round(model.pvalues,2),'\nAIC:',round(model.aic,3))
        # print('Train RMSE:',round(RMSE(train,model),4),'\n','Test RMSE:',round(RMSE_test(test,model,mod_test_list[mod]),4),'\n')

    # Make the lat_long array, fit it, test it, and print out the stats
    lat_long_array = np.array([[exo_lat][0],[exo_long][0]]).transpose()
    lat_long_test_array = np.array([[exo_lat_test][0],[exo_long_test][0]]).transpose()
    mod_magn_lat_long = fit_mod_jpn(train, order, lat_long_array)
    print('Endo = Magnitude, Exo = Latitude/Longitude Combo:','\np-values','\n',round(mod_magn_lat_long.pvalues,2),
      '\n','AIC:',round(mod_magn_lat_long.aic,3))
    print('Train RMSE:',round(RMSE(train,mod_magn_lat_long),4))
    final_japan_test_rmse = round(RMSE_test(test,mod_magn_lat_long,lat_long_test_array),4)
    print('Test RMSE:',final_japan_test_rmse)

print('Import Successful!')