import datetime
import sqlite3
import pandas as pd

DB_NAME = "main.db"
DB_NAME_SITE = "site.db"
DB_NAME_LOG = "log.db"
DB_NAME_AUTH = "session_auth.db"
REL_SESSION_GRANTED_ID = "grant_authorized"
allowed_function_list = ['get_default_sample_1',
                         'get_vacab_acknowledge_use',
                         'get_vacab_sugestion',
                         'get_vocab_coverage',
                         'get_turn_taking',
                         'get_vocab_frequency',
                         'get_word_per_second',
                         'get_issued_prompts',
                         'get_vocab_frequency_short',
                         'get_all_frozen_captions']

def mask_email_address(useremail:str=""):
    if useremail != "":
        account_email = useremail.split('@')[0][0] + "(not stored)" + \
                        useremail.split('@')[0][-2:]
    else:
        account_email = "No email provided"
    return account_email

def list_session_subscribing_only(google_userid:str="",email:str="",start_str:str="",end_str:str=""):
    df_session_internal_codelist = None
    # start_str = request.form.get("start_date",None)
    # end_str = request.form.get("end_date",None)
    try:
        dbname = DB_NAME
        conn = sqlite3.connect(dbname)
        where_clause_string = ""
        if start_str != '':
            where_clause_string += " and created_on >= '" + start_str + "'"
        if end_str != '':
            time_int = datetime.datetime.strptime(end_str,"%Y-%m-%d")
            time_int = time_int + datetime.timedelta(hours=23,minutes=59,seconds=59)
            end_str_int = time_int.strftime("%Y-%m-%d %H:%M:%S")

            where_clause_string += " and created_on <= '" + end_str_int + "'"

        # df_session_internal_codelist = pd.read_sql("SELECT * from session_internal_code where"
        #                                        " owner = '" + google_userid + "'"
        #                                        + where_clause_string
        #                                        , conn)
        dbname_subscribing = DB_NAME_AUTH
        conn_subscribing = sqlite3.connect(dbname_subscribing)
        df_session_internal_codelist_subscribing = pd.read_sql("SELECT id,session_id_parent,email from session_internal_mapping where"
                                               " email = '" + email + "' and "
                                               " connection_type = '" + REL_SESSION_GRANTED_ID  + "'"
                                               , conn_subscribing)
        if len(df_session_internal_codelist_subscribing) != 0:
            list_of_subscribing = ', '.join(str(i) for i in df_session_internal_codelist_subscribing['session_id_parent'].values)
            df_session_internal_codelist_to_merge = pd.read_sql("SELECT * from session_internal_code where"
                                                   " session_id in (" + list_of_subscribing + ")"
                                                   , conn)
            df_session_internal_codelist = pd.merge(df_session_internal_codelist_subscribing,df_session_internal_codelist_to_merge,right_on='session_id',left_on='session_id_parent',how="left")
            # df_session_internal_codelist = pd.concat([df_session_internal_codelist,df_session_internal_codelist_to_merge])
        conn_subscribing.close()
        conn.close()
        if len(df_session_internal_codelist) == 0:
            df_session_internal_codelist = pd.DataFrame()
            df_session_internal_codelist.columns=['id','external_session_name']

    except Exception as e:
        print(e)
    return df_session_internal_codelist


def list_session(google_userid:str="",email:str="",start_str:str="",end_str:str=""):
    df_session_internal_codelist = None
    # start_str = request.form.get("start_date",None)
    # end_str = request.form.get("end_date",None)
    try:
        dbname = DB_NAME
        conn = sqlite3.connect(dbname)
        where_clause_string = ""
        if start_str != '':
            where_clause_string += " and created_on >= '" + start_str + "'"
        if end_str != '':
            time_int = datetime.datetime.strptime(end_str,"%Y-%m-%d")
            time_int = time_int + datetime.timedelta(hours=23,minutes=59,seconds=59)
            end_str_int = time_int.strftime("%Y-%m-%d %H:%M:%S")

            where_clause_string += " and created_on <= '" + end_str_int + "'"

        df_session_internal_codelist = pd.read_sql("SELECT * from session_internal_code where"
                                               " owner = '" + google_userid + "'"
                                               + where_clause_string
                                               , conn)
        dbname_subscribing = DB_NAME_AUTH
        conn_subscribing = sqlite3.connect(dbname_subscribing)
        df_session_internal_codelist_subscribing = pd.read_sql("SELECT session_id_parent from session_internal_mapping where"
                                               " owner = '" + google_userid + "' and "
                                               " connection_type = '" + REL_SESSION_GRANTED_ID  + "'"
                                               , conn_subscribing)
        if len(df_session_internal_codelist_subscribing) != 0:
            list_of_subscribing = ', '.join(str(i) for i in df_session_internal_codelist_subscribing['session_id_parent'].values)
            df_session_internal_codelist_to_merge = pd.read_sql("SELECT * from session_internal_code where"
                                                   " session_id in (" + list_of_subscribing + ")"
                                                   , conn)
            df_session_internal_codelist = pd.concat([df_session_internal_codelist,df_session_internal_codelist_to_merge])
        conn_subscribing.close()
        conn.close()
        if len(df_session_internal_codelist) == 0:
            df_session_internal_codelist = pd.DataFrame()
            df_session_internal_codelist.columns=['id','external_session_name']

    except Exception as e:
        print(e)
    return df_session_internal_codelist

def build_calling_function(userid:str,section:str):
    list_functions = []
    frequency = 10
    # 'from'
    # 'to' \
    # 'function_name'
    dbname = DB_NAME_AUTH
    conn = sqlite3.connect(dbname)
    section_code = section.replace("/","")

    df_functions_db = pd.read_sql("SELECT * from calling_function where "
                                  "owner = '" + userid + "' AND " +
                                  "area = '" + section_code + "'"
                                  , conn)
    conn.close()
    conn.close()

    if len(df_functions_db) == 0:
        return None, None

    if sum(df_functions_db[df_functions_db['end'] != ""]['end']) <= 0:
        return None, None

    df_functions_db[df_functions_db['end'] != ""].sort_values('start', inplace=True)
    frequency = max(df_functions_db[df_functions_db['end'] != ""]['end'])
    df_functions_sorted = df_functions_db[df_functions_db['end'] != ""].sort_values('start')
    df_functions_sorted.drop(['id','owner','area'],axis=1, inplace=True)
    df_functions_sorted.columns = ['function_name','from','to']
    json_pre_string = df_functions_sorted.T.to_json()
    from flask import json
    jsoned_string = [ json.loads(line.T.to_json()) for index, line in df_functions_sorted.iterrows()]
    ret_value = {'function_list': jsoned_string }
    return ret_value, frequency

