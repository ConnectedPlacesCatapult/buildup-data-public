import os
from dotenv import load_dotenv
import pandas as pd
import hmac, hashlib
import time
import base64
import requests
import ntplib
import numpy as np
import geopy
from convertbng.util import convert_bng, convert_lonlat
from scipy.spatial import cKDTree
from APIClient import APIClass

#Set up .env variables
load_dotenv()

def get_data(database:str, table:str, page=1, optional_param='', optional_param_value=''):
    """"Uses the Tascomi API client to request data
    
    Required args:
    - database (str): can be 'planning' (Tascomi Planning) or 'build' (Tascomi BC)
    - table (str): any available table according to Tascomi API documentation
    
    Optional args:
    - optional_param (str): any field from table
    - optional_param_value: possible value for field
    
    Returns:
    - DataFrame of response data"""
    
    #set up keys and columns to extract
    if database == 'planning':
        public_key = os.getenv('tascomi_planning_public').encode('latin-1')
        private_key = os.getenv('tascomi_planning_private').encode('latin-1')
        
        if table == 'applications':
            columns = ['id', 'planning_portal_reference',
                       'application_reference_number',
                       'decision_type_id', 
                       'site_address_description',
                       'dtf_location_id',
                       'proposal', 'received_date',
                       'decision_issued_date']
        
        elif table == 'dtf_locations':
            columns = ['id',
                        'uprn',
                        'usrn',
                        'lpi_key',
                       'pao_text',
                        'postcode',
                        'x_coordinate',
                        'y_coordinate',
                        'blpu_logical_status_code', 'lpi_logical_status_code']
    
    elif database == 'build':
        public_key = os.getenv('tascomi_build_public').encode('latin-1')
        private_key = os.getenv('tascomi_build_private').encode('latin-1')
        
        if table == 'applications':
            columns = ['id', 'application_number',
                       'description',
                        'dtf_location_id',
                       'received_date',
                       'valid_date',
                        'decision_date',
                        'started_date',
                        'completed_date',
                        'site_description']
        
        elif table == 'dtf_locations':
            columns = ['id',
                        'uprn',
                        'usrn',
                        'lpi_key',
                       'pao_text',
                        'postcode',
                        'x_coordinate',
                        'y_coordinate',
                        'blpu_logical_status_code', 'lpi_logical_status_code']
        
        elif table == 'inspections':
            columns = ['application_id', 'inspected_date']
    
    #construct request URI
    if optional_param != '':
        optional_param = f"{optional_param}={optional_param_value}&"
        
    request_uri = f"https://waltham-forest-{database}.tascomi.com/rest/v1/{table}?{optional_param}page={page}"
    request_method = 'GET'
    
    #API request object
    req = APIClass(public_key=public_key, private_key=private_key, request_uri=request_uri, request_method=request_method)

    #send request
    req.sendRequest()
    
    #show dataframe
    if req.status_code == 200:
        df = pd.DataFrame(req.json) #convert results to df
        if columns:
            df = df[columns].copy() #filter out irrelevant columns
        return df

#### CLEANING FUNCTIONS FOR PLANNING AND BC ####

def clean_dates(apps, dates):
    """ Converts date columns from str to datetime
    Args:
    - apps: data frame of applications
    - dates: list of date columns
    
    Returns:
    Dataframe with dates as datetime columns
    """
    
    #convert date columns
    for d in dates:
        apps[d] = pd.to_datetime(apps[d], format="%Y-%m-%d %H:%M:%S", errors='coerce')
    
    #return applications data frame
    return apps

def locate_apps(apps:pd.DataFrame, database:str):
    """Finds coordinates of locations in new planning applications - held in Tascomi Planning/BC 'dtf_locations' table
    
    Args:
    - apps: dataframe of applications with dtf_location_id field
    - database: 'planning' or 'build', depending on what applications have been loaded in
    
    Returns:
    Dataframe of applications with coordinate and address information attached"""
    
    #load in locations
    locations = pd.concat([get_data(database, 'dtf_locations', optional_param='id', optional_param_value=x) for x in apps['dtf_location_id'].tolist()])
    
    #merge applications and locations
    df = apps.merge(locations, left_on='dtf_location_id', right_on='id', how='left').rename(columns={'id_x': f"{database}_id"})
    
    #return df
    return df

def join_inspections(row:pd.Series, inspections:pd.DataFrame):
    """Adds new BC inspections for a scheme
    
    Args:
    - row: row from schemes table, with Building Control application ID attached
    - inspections: dataframe with new inspections from the day
    
    Returns:
    Row with new site visits appended to list"""
    
    bc_id = row['bc_id']
    m = inspections['application_id'] == bc_id
    row['wf_bc_site_visits'].append(inspections.loc[m, 'inspected_date'].iloc[0])
    
    return row

def geocode_address(row):
    """Finds coordinates for schemes with text addresses, but no coordinates
    
    Args:
    - row: row from applications, with address information from location merging step
    
    Returns:
    - row with easting/northing coordinates in appropriate fields"""
    
    #input pao_text into geocoder
    location = geolocator.geocode(row['pao_text'])
    
    #find BNG coordinates
    if location:
        bng = convert_bng(location.longitude, location.latitude)
        row['x_coordinate'] = bng[0][0]
        row['y_coordinate'] = bng[1][0]
    
    return row

def filter_bc(bc_apps):
    
    #filter table
    mask = bc_apps['application_number'].str.contains(r'IN|PA|FP')
    bc_apps = bc_apps.loc[mask].copy()
    
    return bc_apps

def nearest_bc_apps(row, candidates, results_dict, k=3):
    """Finds k (default 3) nearest new BC applications to a planning application
    
    Args:
    - row: planning application with coordinates
    - candidates: dataframe of new BC applications, filtered to relevant application types and with coordinates
    - k - default 3, number of nearest neighbours to find
    - results_dict - empty dictionary to hold potential matches, set up at start of script and structured as below
    
    {
        'planning_id': [],
        'bc_dist': [],
        'bc_id': []
    }
    
    """
    
    try:
        #Convert coordinates to numpy arrays
        bc_array = np.array(list(zip(candidates.x_coordinate, candidates.y_coordinate)))
        
        #Construct cKDTree of BC applications
        tree = cKDTree(bc_array)
    
        #Query tree to find k closest BC apps
        dist, idx = tree.query([row.x_coordinate, row.y_coordinate], k=k)
    
        #Find original index of BC candidate
        bc_idx = [candidates.loc[ix, 'build_id'] for ix in idx]
    
        #Add lists of results to matches_dict
        planning_id = np.repeat(row['planning_id'], k)
        results_dict['planning_id'].extend(planning_id)
        results_dict['bc_dist'].extend(dist)
        results_dict['bc_id'].extend(bc_idx)
        
    except ValueError:
        #print(row['proposal'], row['planning_id'], row['decision_issued_date'])
        results_dict['planning_id'].append(row['planning_id'])
        results_dict['bc_dist'].append(None)
        results_dict['bc_id'].append(None)