"""This script collects a few relevant data sets, finds their columns
(if possible, automatically, in some cases manually due to the size
of the download) and then checks what the MIRA DKG search API returns
as matching entities."""
import pandas as pd

from mira.dkg.web_client import search_web


def sanitize(s):
    return s.replace('_', ' ').strip()


all_data_columns = []

# JHU daily case counts. Global, stratified by geography.
url = ('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/'
       'csse_covid_19_data/csse_covid_19_daily_reports/09-07-2022.csv')
df = pd.read_csv(url)
all_data_columns += [sanitize(c) for c in df.columns]

# CDC case surveillance. US, stratified by geography and demographics.
url = 'https://data.cdc.gov/api/views/n8mc-b4w4/rows.csv?accessType=DOWNLOAD'
# This is a really large table and only the columns matter so just adding
# them manually here
cols = ['case_month', 'res_state', 'state_fips_code', 'res_county',
        'county_fips_code', 'age_group', 'sex', 'race', 'ethnicity',
        'case_positive_specimen_interval', 'case_onset_interval', 'process',
        'exposure_yn', 'current_status', 'symptom_status', 'hosp_yn',
        'icu_yn', 'death_yn', 'underlying_conditions_yn']
all_data_columns += [sanitize(c) for c in cols]

# CDC rates by age/vaccination status. US stratified by
# demographics/vaccination status.
url = 'https://data.cdc.gov/api/views/3rge-nu2a/rows.csv?accessType=DOWNLOAD'
df = pd.read_csv(url)
all_data_columns += [sanitize(c) for c in df.columns]

# CDC vaccination data. Vaccines at the county level. Stratified by geography
# and age.
url = 'https://data.cdc.gov/api/views/8xkx-amqh/rows.csv?accessType=DOWNLOAD'
cols = ['Date', 'FIPS', 'MMWR_week', 'Recip_County', 'Recip_State',
        'Completeness_pct', 'Administered_Dose1_Recip',
        'Administered_Dose1_Pop_Pct', 'Administered_Dose1_Recip_5Plus',
        'Administered_Dose1_Recip_5PlusPop_Pct',
        'Administered_Dose1_Recip_12Plus',
        'Administered_Dose1_Recip_12PlusPop_Pct',
        'Administered_Dose1_Recip_18Plus',
        'Administered_Dose1_Recip_18PlusPop_Pct',
        'Administered_Dose1_Recip_65Plus',
        'Administered_Dose1_Recip_65PlusPop_Pct', 'Series_Complete_Yes',
        'Series_Complete_Pop_Pct', 'Series_Complete_5Plus',
        'Series_Complete_5PlusPop_Pct', 'Series_Complete_5to17',
        'Series_Complete_5to17Pop_Pct', 'Series_Complete_12Plus',
        'Series_Complete_12PlusPop_Pct', 'Series_Complete_18Plus',
        'Series_Complete_18PlusPop_Pct', 'Series_Complete_65Plus',
        'Series_Complete_65PlusPop_Pct', 'Booster_Doses',
        'Booster_Doses_Vax_Pct', 'Booster_Doses_5Plus',
        'Booster_Doses_5Plus_Vax_Pct', 'Booster_Doses_12Plus',
        'Booster_Doses_12Plus_Vax_Pct', 'Booster_Doses_18Plus',
        'Booster_Doses_18Plus_Vax_Pct', 'Booster_Doses_50Plus',
        'Booster_Doses_50Plus_Vax_Pct', 'Booster_Doses_65Plus',
        'Booster_Doses_65Plus_Vax_Pct', 'Second_Booster_50Plus',
        'Second_Booster_50Plus_Vax_Pct', 'Second_Booster_65Plus',
        'Second_Booster_65Plus_Vax_Pct', 'SVI_CTGY',
        'Series_Complete_Pop_Pct_SVI', 'Series_Complete_5PlusPop_Pct_SVI',
        'Series_Complete_5to17Pop_Pct_SVI', 'Series_Complete_12PlusPop_Pct_SVI',
        'Series_Complete_18PlusPop_Pct_SVI',
        'Series_Complete_65PlusPop_Pct_SVI', 'Metro_status',
        'Series_Complete_Pop_Pct_UR_Equity',
        'Series_Complete_5PlusPop_Pct_UR_Equity',
        'Series_Complete_5to17Pop_Pct_UR_Equity',
        'Series_Complete_12PlusPop_Pct_UR_Equity',
        'Series_Complete_18PlusPop_Pct_UR_Equity',
        'Series_Complete_65PlusPop_Pct_UR_Equity', 'Booster_Doses_Vax_Pct_SVI',
        'Booster_Doses_12PlusVax_Pct_SVI', 'Booster_Doses_18PlusVax_Pct_SVI',
        'Booster_Doses_65PlusVax_Pct_SVI', 'Booster_Doses_Vax_Pct_UR_Equity',
        'Booster_Doses_12PlusVax_Pct_UR_Equity',
        'Booster_Doses_18PlusVax_Pct_UR_Equity',
        'Booster_Doses_65PlusVax_Pct_UR_Equity', 'Census2019',
        'Census2019_5PlusPop', 'Census2019_5to17Pop', 'Census2019_12PlusPop',
        'Census2019_18PlusPop', 'Census2019_65PlusPop']
all_data_columns += [sanitize(c) for c in df.columns]

# CDC stay home orders. County level non-pharmaceutical interventions.
url = 'https://data.cdc.gov/api/views/y2iy-8irm/rows.csv?accessType=DOWNLOAD'
cols = ['State_Tribe_Territory', 'County_Name', 'FIPS_State', 'FIPS_County',
        'date', 'Order_code', 'Stay_at_Home_Order_Recommendation',
        'Express_Preemption', 'Source_of_Action', 'URL', 'Citation']
all_data_columns += [sanitize(c) for c in df.columns]

# We can now search all the column names and print some stats
for col in sorted(set(all_data_columns), key=lambda x: x.lower()):
    entities = search_web(col, limit=25, api_url='http://localhost:8771/')
    print(f'{col}: {len(entities)} entities found')
    for entity in entities[:5]:
        print(f' - {entity.id}, {entity.name}')
