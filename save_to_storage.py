DB_NAME = "test.db"
import sqlite3
import pandas as pd
import datetime

def log_load(session = "", start:datetime=None):

    kwargs = {}
    if session is not None:
        kwargs['session'] = [session,"="]
    if start is not None:
        kwargs['start'] = [start.strftime("%Y-%m-%d %H:%M:%S"),">="]
    if len(kwargs) == 0:
        where_clause = ""
    else:
        where_clause = 'WHERE ' + ' AND '.join([k + ' %s "%s"' % (kwargs[k][1],kwargs[k][0]) for k in kwargs.keys()])

    sql_string_log = \
        'select * from log ' + \
        where_clause

    sql_string_caption_sub = \
        'select * from caption_sub ' + \
        where_clause


    dbname = DB_NAME
    conn = sqlite3.connect(dbname)

    df_log = pd.read_sql(sql_string_log, conn)
    df_sub = pd.read_sql(sql_string_caption_sub, conn)
    df_final = pd.DataFrame([[row, df_sub[(df_sub['substart'] <= row['start']) & ((df_sub['end'] >= row['start']))]] for index, row in
                  df_log.iterrows() if
                  len(df_sub[(df_sub['substart'] <= row['start']) & ((df_sub['end'] >= row['start']))]) > 0])
    conn.close()
    # TODO: if a log is registered during the time when no utterance is available. Log should be still written
    #         so that that log will appear somewhere in between the captions
    return df_final


def session_load(session = "", start:datetime=None):

    kwargs = {}
    if session is not None:
        kwargs['session'] = [session,"="]
    if start is not None:
        kwargs['start'] = [start.strftime("%Y-%m-%d %H:%M:%S"),">="]
    if len(kwargs) == 0:
        where_clause = ""
    else:
        where_clause = 'WHERE ' + ' AND '.join([k + ' %s "%s"' % (kwargs[k][1],kwargs[k][0]) for k in kwargs.keys()])

    sql_string = \
        'select * from caption ' + \
        where_clause

    print(sql_string)
    dbname = DB_NAME
    conn = sqlite3.connect(dbname)

    df = pd.read_sql(sql_string, conn)

    conn.close()

    return df

def prepare_document_raw(df):

    for index, row in df.iterrows():
        print(row['session'],"\t",row['start'],"\t",row['actor'],"\t",row['text'])

def prepare_document(df):

    from flask import render_template
    text = render_template('caption.html', df=df)
    return text

def get_caption_html(session="",start:datetime=None):

    df = session_load(session=session,start= start)
    html = prepare_document(df)
    return html

def get_blending_logs(session="",start:datetime=None,df_caption:pd.DataFrame=None):

    df_log_combined = log_load(session=session,start=start)
    if len(df_caption) == 0:
        return df_caption
    import re
    for index, log_details in df_log_combined.iterrows():
        log_line = log_details[0]
        log_located = log_details[1]
        for index, location_item in log_located.iterrows():
            df_lines = df_caption[df_caption['start'] == location_item['start']]
            if len(df_lines) == 0:
                continue
            # df_lines['text'] = df_lines['text'].str.replace(location_item['text'],
            #                                                 "("+ log_line['logtype'] +  ":" +str.lower(location_item['text']) + ")")
            temp_text = df_lines['text'].values[0]
            if log_line['text'] == "no text":
                re_compile = re.compile(location_item['text'],re.IGNORECASE)
                temp_text = re_compile.sub("<b>("+ log_line['logtype'] +  ":" +str.lower(location_item['text']) + ")</b>",temp_text)
            else:
                re_compile = re.compile(log_line['text'], re.IGNORECASE)
                temp_text = re_compile.sub("<b>("+ log_line['logtype'] +  ":" +str.lower(location_item['text']) + ")</b>",temp_text)
            print(temp_text)
            df_lines['text'].values[0] = temp_text
            df_caption[df_caption['start'] == location_item['start']] = df_lines
    return df_caption

def get_delta(session="",start:datetime=None):
    df = session_load(session=session,start= start)
    return df