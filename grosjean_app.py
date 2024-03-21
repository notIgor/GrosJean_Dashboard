import pandas as pd
import numpy as np
import gspread as gs
from google.oauth2.service_account import Credentials
import plotly.express as px
import seaborn as sns
import streamlit as st

url = "https://docs.google.com/spreadsheets/d/1htnZuo6YkMOcCLOlP7n4h51jD8hDhARID_iz_ay9O8U/edit#gid=0"
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
]

@st.cache_data
def load_data(url,scopes):
    skey = st.secrets["connection_gspread"]
    credentials = Credentials.from_service_account_info(
        skey,
        scopes=scopes,
    )
    client = gs.authorize(credentials)
    sh = client.open_by_url(url)
    df = pd.DataFrame(sh.worksheet('CAMPIONATO PILOTI').get_all_records())
    disdf = pd.DataFrame(sh.worksheet('CAMPIONATO DISTRUTTORI').get_all_values())
    tdf = pd.DataFrame(sh.worksheet('Track_DB').get_all_records())
    penalty_df = pd.DataFrame(sh.worksheet('LOS SBINNADORES').get_all_values())
    crash_df = pd.DataFrame(sh.worksheet('IL PREDESBINNATO').get_all_values())
    return df, disdf, penalty_df, crash_df, tdf

df, disdf, penalty_df, crash_df, tdf = load_data(url,scopes)
#function to reindex dataset to get the kpi's values
def reindex_dataframe(dataframe):
    dataframe.drop(dataframe.columns[:2],axis=1,inplace=True)
    dataframe.columns = dataframe.iloc[0]
    dataframe = dataframe[1:]
    dataframe.set_index(['PILOTI'],inplace=True)
    return dataframe

#driver championship dataframe
df = df.drop(df.columns[:1],axis=1)

#distructor championship
disdf = reindex_dataframe(disdf)
disdf.drop(disdf.index[17:],axis=0,inplace=True)


#penalty count
penalty_df = reindex_dataframe(penalty_df)

#crashes count
crash_df = reindex_dataframe(crash_df)


#function to clean missing values from csv and fixing the half point problem in Monza
@st.cache_data
def clean_missing(df):
    df.replace('', pd.NA, inplace = True)
    df.fillna(method='ffill', limit = 1, inplace=True)
    df.fillna(0, inplace=True)
    df = df.apply(pd.to_numeric, errors='ignore')
    condition = df['Monza'] > 100
    df.loc[condition, 'Monza'] /= 10
    condition1 = df['TOTALE PILOTA'] > 1000
    df.loc[condition1, 'TOTALE PILOTA'] /= 10
    return df


#cleaning the main dataframe 
df = clean_missing(df)

#dropping sum columns cause we are going to do a cumsum anyway
columns_to_drop = ['TEAM','TOTALE PILOTA', 'TOTALE SCUDERIA', 'xP']
dcdf = df.drop(columns = columns_to_drop)
dcdb = df.drop(columns = columns_to_drop)

#applying function to df then Transposing the data and resetting the column names and melting the dataset
@st.cache_data
def transpose_and_melt(dataframe):
    dataframe= dataframe.T.reset_index()
    dataframe.columns = dataframe.iloc[0]
    dataframe = dataframe.drop(0)
    dataframe = dataframe.rename(columns={'PILOTI':'Race'})
    dataframe.iloc[:, 1:]= dataframe.iloc[:, 1:].cumsum()
    dataframe = dataframe.melt('Race', var_name= 'Driver', value_name='Points')
    return dataframe

dcdf = transpose_and_melt(dcdf)  

df = df.sort_values(by='TOTALE PILOTA', ascending=False)
df['Position'] = range(1, len(df) + 1)



#setting indexes to the driver column to research values in the function
df.set_index(['PILOTI'],inplace = True)
dcdb.set_index(['PILOTI'],inplace = True)




#function to get the data to display into the dashboard
def get_kpi(driver):
    team = df.loc[driver,'TEAM']
    total_points = str(df.loc[driver,'TOTALE PILOTA'])
    position = str(df.loc[driver,'Position'])
    pole = str((tdf['pole'] == driver).sum())
    fastlap = str((tdf['fastest_lap'] == driver).sum())
    damage = disdf.loc[driver,'TOTALE PILOTA']
    wins = str((dcdb.loc[driver] >= 25).sum())
    podiums = str((dcdb.loc[driver] >= 15).sum())
    penalty = penalty_df.loc[driver,'TOTALE PILOTA']
    crashes = crash_df.loc[driver,'TOTALE PILOTA']

    return [team,total_points,position,pole,fastlap,damage,wins,podiums,penalty,crashes]




st.header("Grosjean Drivers' Dashboard")

select_driver = st.selectbox('Select a driver', df.index)

#creating some boxes to display the kpis in filling them
kpi_values = get_kpi(select_driver)
columns = st.columns(5)
titles = ['Team','Punti','Ranking','Pole','Fast Lap','Danni','Vittorie','Podi','Penalità','Sbinnate']
for i, (title , kpi) in enumerate(zip(titles,kpi_values)):
    columns[i % 5].subheader(title)
    columns[i % 5].write(kpi)

#plotting the championship progress of the driver
fig = px.line(dcdf[dcdf['Driver'] == select_driver], x='Race', y='Points', title='Season Progress', markers=True, hover_data={'Points': True})
fig.update_layout(hovermode='x', showlegend=False)
st.plotly_chart(fig)
