import pandas as pd

def clean_dv(CIL_dv):
    """Isolate phases from application numbers in Demand Values report
    
    Args:
    - CIL_dv: Demand Values report (df)
    
    Returns:
    Demand Values report with separate columns for application number and phase"""
    
    #isolate phases from app numbers
    CIL_dv['Phase'] = CIL_dv['App No'].str[8]
    CIL_dv['App No'] = CIL_dv['App No'].str[0:6]
    
    return CIL_dv

def clean_sc(CIL_sc):
    """Creates new record for each demand reference in ScoreCard report, as they are currently listed together
    
    Args:
    - CIL_sc: ScoreCard report (df)
    
    Returns:
    ScoreCard report with a row for each demand ref"""
    
    #create list of individual demand refs
    CIL_sc['Demand Refs'] = CIL_sc.apply(lambda x: x['Demand Refs'].split(';') if pd.notnull(x['Demand Refs']) else x['Demand Refs'], axis=1)

    #create new record for each demand ref
    CIL_sc = CIL_sc.explode('Demand Refs')
    
    return CIL_sc
        

def merge_reports(df_dv, df_sc):
    """Merges Demand Values and ScoreCard data on payment reference fields
    
    Args:
    - df_dv: Demand Values dataframe with separate application numbers and phases
    - df_sc: ScoreCard dataframe with separate row for each demand ref
    
    Returns:
    Merged dataframe"""
    
    #merge on payment references
    CIL_full = df_dv.merge(df_sc, left_on='Payment Reference', right_on='Demand Refs')
    
    #drop records where different applications somehow had the same payment reference
    CIL_full.drop(index=CIL_full.loc[CIL_full['App No_x'] != CIL_full['App No_y']].index, inplace=True)
    
    return CIL_full

def filter_columns(df_full):
    """Extracts fields required for phase table in BuildUp schema
    
    Args:
    -df_full: Dataframe of merged CIL Demand Values and ScoreCard reports
    
    Returns:
    Dataframe with only relevant fields"""
    
    #list of columns needed from each report
    columns = ['App No_x', 'Phase', 'Commencement Date', 'Form 2 Rec', 'LN Date', 'Form 6 Rec']
    
    df_filtered = df_full[columns].copy().rename(columns={'App No_x': 'planning_ref_number'})
    
    return df_filtered