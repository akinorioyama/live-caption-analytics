DB_NAME = "test.db"
import sqlite3
import pandas as pd
import datetime
import re

def log_load(session = "", start:datetime=None):

    kwargs = {}
    if session is not None:
        kwargs['session'] = [session,"="]
    if start is not None:
        kwargs['start'] = [start.strftime("%Y-%m-%d %H:%M:%S.%f"),">="]
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
    # find ones that were not find in logs and add them...
    df_final_not_found = pd.DataFrame([[row, df_sub[(df_sub['substart'] <= row['start']) & ((df_sub['end'] >= row['start']))]] for index, row in
                  df_log.iterrows() if
                  len(df_sub[(df_sub['substart'] <= row['start']) & ((df_sub['end'] >= row['start']))]) == 0])
    df_final = pd.concat([df_final,df_final_not_found])
    conn.close()
    # TODO: if a log is registered during the time when no utterance is available. Log should be still written
    #         so that that log will appear somewhere in between the captions
    return df_final


def session_load(session = "", start:datetime=None):

    kwargs = {}
    if session is not None:
        kwargs['session'] = [session,"="]
    if start is not None:
        kwargs['start'] = [start.strftime("%Y-%m-%d %H:%M:%S.%f"),">="]
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

    found_word = {}

    for index, log_details in df_log_combined.iterrows():
        log_line = log_details[0]
        log_located = log_details[1]
        # TODO: do not replace the same text
        # TODO: split text into chunks to replace only the relevant part

        if log_located.empty == True:
            temp_text = "<b>Looged item:" + log_line['logtype'] + "</b>"
            tmp_se = pd.Series([
                None,
                session,
                log_line['start'],
                log_line['start'],
                log_line['actor'],
                temp_text,
                ''
            ], index=df_caption.columns)
            df_caption = df_caption.append(tmp_se, ignore_index=True)

        for index, location_item in log_located.iterrows():
            df_lines = df_caption[df_caption['start'] == location_item['start']]
            if len(df_lines) == 0:
                continue
            # df_lines['text'] = df_lines['text'].str.replace(location_item['text'],
            #                                                 "("+ log_line['logtype'] +  ":" +str.lower(location_item['text']) + ")")
            temp_text = df_lines['text'].values[0]
            temp_text = temp_text.replace(".","")
            finding_word = log_line['text']
            finding_word = finding_word.replace(".","")
            finding_word = finding_word.replace(" ","")
            if str([finding_word,location_item['start']]) in found_word:
                continue
            found_word[str([finding_word,location_item['start']])] = True
            re_compile = re.compile(finding_word, re.IGNORECASE | re.MULTILINE)
            temp_text = re_compile.sub("<b>("+ log_line['logtype'] +  ":" +str.lower(finding_word) + ")</b>",temp_text)
            print(temp_text)
            df_lines['text'].values[0] = temp_text
            df_caption[df_caption['start'] == location_item['start']] = df_lines
    df_caption.sort_values(['start'], inplace=True)
    return df_caption

def get_delta(session="",start:datetime=None):
    df = session_load(session=session,start= start)
    return df