"""
Caption analytics

Usage:
  main.py <host> <port> <debug>
  main.py -h | --help
  main.py --version

  <host>:
  <port>:
  <debug>: DEBUG to keep the incoming data

Examples:
  main.py 0.0.0.0 443

Options:
  -h --help     Show this screen.
  --version     Show version.
"""

import datetime
import sqlite3

import numpy as np
from docopt import docopt

from flask import Flask, request, jsonify,json
from flask_cors import CORS
from flask import render_template
import pandas as pd
from vocab_suggest import vocab_calculate_all
from vocab_suggest import get_stats_for_levels_db
from vocab_suggest import vocab_result_save
from vocab_suggest import vocab_result_load
from vocab_suggest import get_frequently_used_words
from vocab_suggest import suggest_words
from vocab_suggest import extract_words_from_response
from vocab_suggest import remove_stopwords_entry
from save_to_storage import get_caption_html
from save_to_storage import get_delta
from save_to_storage import get_blending_logs
from json import JSONDecodeError
import config_settings
DB_NAME = "main.db"
DB_NAME_SITE = "site.db"
DB_NAME_LOG = "log.db"

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
CORS(app)

def is_correct_session_access_code(session_string="", option_settings=""):

    #  - ip and username will not work due to users not sending any data to server
    # 1: with json access_key
    # read session_access_code and grant action if correct



    return True, None

@app.route('/prompt_check',methods=['POST','GET'])
def return_prompt_options():
    data_received = request.get_data().decode('utf-8')
    data_json = json.loads(data_received)
    username = data_json['username']
    session_string = data_json['transcriptId']
    print("username:",username)
    option_settings = data_json['option_settings']

    config_server_security_granted, message_json = config_settings.get_full_access_settings()
    if config_server_security_granted is None:
        # use error text
        return message_json
    elif config_server_security_granted != True:
        # true: fullaccess granted
        is_granted, message_json = is_correct_session_access_code(session_string=session_string, option_settings=option_settings)
        if is_granted != True:
            return  message_json

    df_session_vocab_to_cover, df_session_vocab_to_suggest, df_session_vocab_to_avoid = \
        get_session_settings(username=username,session_string=session_string)
    df_session_vocab_to_cover_all, df_session_vocab_to_suggest_all, df_session_vocab_to_avoid_all = \
        get_session_settings(username="all",session_string=session_string)

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)

    df_session_caption = pd.read_sql("SELECT * FROM caption where " + \
                                  " session = '" + session_string + "'"
                                  , conn)
    df_session_prompt = pd.read_sql("SELECT * FROM session_prompt_log where " + \
                                  " session = '" + session_string + "'"
                                  , conn)
    conn.commit()
    conn.close()
    df_vocab_avoid = None
    if df_session_vocab_to_avoid is not None:
        df_vocab_avoid_for_user = pd.DataFrame(list(df_session_vocab_to_avoid['value'].str.split(":")))
    if df_session_vocab_to_avoid_all is not None:
        df_vocab_avoid = pd.DataFrame(list(df_session_vocab_to_avoid_all['value'].str.split(":")))
    if df_vocab_avoid is not None:
        df_vocab_avoid = pd.concat([df_vocab_avoid,df_vocab_avoid_for_user])
    if df_vocab_avoid is not None and len(df_vocab_avoid) > 0:
        df_vocab_avoid.columns=['vocab','frequency','interval']
    else:
        df_vocab_avoid = pd.DataFrame()
    if df_session_vocab_to_suggest_all is not None:
        df_vocab_suggest = pd.DataFrame(list(df_session_vocab_to_suggest_all['value'].str.split(":")))
        if df_vocab_suggest is not None and len(df_vocab_suggest) > 0:
            df_vocab_suggest.columns=['vocab','frequency','interval']
    # TODO: merge check all and specific user
    for index, item in df_vocab_avoid.iterrows():
        df_hit = df_session_caption['text'].str.contains(item['vocab'] ,case=False)
        if len(df_hit) != 0:
            import re
            df_hit2 = df_session_caption[df_session_caption['text'].str.contains(item['vocab'], case=False)]['text'].apply(lambda s: len(re.findall(item['vocab'],s)))
            df_hit_index = df_session_caption[df_session_caption['text'].str.contains(item['vocab'], case=False)]['text'].apply(lambda s: len(re.findall(item['vocab'],s)))
            df_hit_re_index = df_session_caption['text'].apply(lambda s: len(re.findall(item['vocab'], s, flags=re.IGNORECASE)))
            max_end = df_session_caption[df_hit_re_index > 0]['end'].max()
            print(df_hit2.sum())
            num_of_occurance = df_hit_re_index.sum()
            # history of alert to avoid duplicate notice. Should be through history.
            if num_of_occurance >= int(item['frequency']):
                if num_of_occurance == int(item['frequency']):
                    if len(df_session_prompt[
                        (df_session_prompt['key'] == 'vocab_to_avoid') & (df_session_prompt['value'] == item['vocab']) &
                        (df_session_prompt['triggering_criteria'] == str(num_of_occurance))]) == 0:
                        data_show = {"notification": {"text": "Avoid the specific word"},
                                     "heading": f"You have used {item['vocab']} for {num_of_occurance} times.<br>",
                                     "prompt_options": "Yes<br>,No<br>,Maybe",
                                     "setting":
                                         {"duration": 3000}
                                     }
                        df_new = pd.DataFrame(columns=['session','start','key','value','triggering_criteria'])
                        tmp_se = pd.Series({
                            'session': session_string,
                            'start': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'key': 'vocab_to_avoid',
                            'value': item['vocab'],
                            'triggering_criteria': str(num_of_occurance)
                        }, index=df_new.columns)
                        df_new = df_new.append(tmp_se, ignore_index=True)
                        dbname = DB_NAME
                        conn = sqlite3.connect(dbname)
                        df_new.to_sql('session_prompt_log', conn, if_exists='append', index=False)
                        conn.commit()
                        conn.close()

                        return jsonify(data_show)
                elif ( (num_of_occurance - (int(item['frequency']))) % int(item['interval'])) == 0:
                    if len(df_session_prompt[
                        (df_session_prompt['key'] == 'vocab_to_avoid') & (df_session_prompt['value'] == item['vocab']) &
                        (df_session_prompt['triggering_criteria'] == str(num_of_occurance))])== 0:
                        data_show = {"notification": {"text": "Avoid the specific word"},
                                     "heading": f"You have used {item['vocab']} for {num_of_occurance} times.<br>",
                                     "prompt_options": "Yes<br>,No<br>,Maybe",
                                     "setting":
                                         {"duration": 3000}
                                     }
                        df_new = pd.DataFrame(columns=['session','start','key','value','triggering_criteria'])
                        tmp_se = pd.Series({
                            'session': session_string,
                            'start': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'key': 'vocab_to_avoid',
                            'value': item['vocab'],
                            'triggering_criteria': str(num_of_occurance)
                        }, index=df_new.columns)
                        df_new = df_new.append(tmp_se, ignore_index=True)
                        dbname = DB_NAME
                        conn = sqlite3.connect(dbname)
                        df_new.to_sql('session_prompt_log', conn, if_exists='append', index=False)
                        conn.commit()
                        conn.close()


                        return jsonify(data_show)

        else:
            print(f"no hit for {item['vocab']}")

            # session_start = datetime.datetime(2020, 9, 10, 0, 0, 0)
            # session_start_string = session_start.strftime("%Y-%m-%d %H:%M:%S.%f")
    # if (0 <= (datetime.datetime.now().second % 15) <= 0):
    #
    #     data_show = {"notification": {"text": "no data exists from Meet"},
    #                  "heading": "Would you like to volunteer to answer the question? Choose an option from the prompt.<br>",
    #                  "prompt_options": "Yes<br>,No<br>,Maybe",
    #                  "setting":
    #                      {"duration": 3000}
    #                  }
    #     return jsonify(data_show)
    # elif (7 <= (datetime.datetime.now().second % 10) <= 7):
    #
    #     data_show = {"notification": {"text": "no data exists from Meet"},
    #                  "heading": "'You know' is repetitively used. Avoid using the phrase.<br>",
    #                  "prompt_options": "Ok,<br>Not necessary",
    #                  "setting":
    #                      {"duration": 3000}
    #                  }
    #     return jsonify(data_show)
    #
    # else:
    data_show = {"notification": {"text": "no data exists from Meet"},
                 "heading": "no data",
                 "prompt_options": "",
                 "setting":
                     {"duration": 10}
                 }
    return jsonify(data_show)

@app.route('/caption',methods=['POST','GET'])
def return_caption():
    received_second = request.args.get('seconds')
    received_session = request.args.get('session')
    received_ip_address = request.remote_addr
    if received_second is None:
        text = get_caption_html(session=received_session, start=None)
    else:
        if received_second == "0":
            df = get_delta(session=received_session, start=None)
        else:
            start_time = datetime.datetime.now() - datetime.timedelta(seconds=10, minutes=0)
            df = get_delta(session=received_session, start=start_time)
            if len(df) == 0:
                print("reread with an extended time")
                start_time = datetime.datetime.now() - datetime.timedelta(seconds=0, minutes=2)
                df = get_delta(session=received_session, start=start_time)
        df = get_blending_logs(session=received_session,start=None,df_caption=df)
        text = df.to_json(orient="records")
        # TODO: authorization mechanism has to be implemented
        #  (although it could be already a little challenging to know the meeting id)
        # if (received_ip_address in df['actor_ip'].values) == True:
        #     text = df.to_json(orient="records")
        # else:
        #     data = [
        #         {
        #             'actor':'Not authorized',
        #             'start': 'Not in',
        #             'session': 'Not authorized session',
        #             'text': 'Not authorized',
        #         }
        #     ]
        #     text = jsonify(data)

    return text

@app.route('/log',methods=['POST','GET'])
def receive_log():
    data = request.get_data().decode('utf-8')
    # print("Log",data)
    data_json = json.loads(data)
    username = data_json['username']
    print("username:",username)

    if len(data_json['text']) == 0:
        data = [{"name": "no data exists",
                 "duration": 0}]
        return jsonify( data)
    input_text = data_json['text']
    logtype = data_json['logtype']
    logtime = data_json['logtime']
    date_string_iso = data_json['date']
    # date_string = (datetime.datetime.fromisoformat(date_string_iso.split(".")[0]) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    date_string = (datetime.datetime.fromisoformat(str(date_string_iso).replace("Z","")) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S.%f")
    if logtime is not None:
        logtime_string = (datetime.datetime.fromisoformat(str(logtime).replace("Z","")) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S.%f")
        date_string = logtime_string
    session_id  = data_json['transcriptId']

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    conn.execute("INSERT INTO log ( session , start , actor , text, logtype ) values ( " + \
                 "'" + session_id + "'," + \
                 "'" + date_string + "'," +\
                 "'" + username + "'," + \
                 "'" + input_text + "'," +
                 "'" + logtype + "'" + \
                 " )")
    conn.commit()
    conn.close()

    data = [{"name": "update",
             "duration": 0}]
    return jsonify(data)

    return data
@app.route('/',methods=['POST','GET'])
def return_heartbeat():
    data = request.get_data().decode('utf-8')
    data_json = json.loads(data)
    username = data_json['username']
    user_ip_address = request.remote_addr
    print(f"username:{username}(at {user_ip_address})")

    if len(data_json['transcript']) == 0:
        data = [{"name": "no data exists",
                 "duration": 0}]
        return jsonify( data)
    # print(data_json)
    # print(data_json['transcript'])
    # print(data_json['transcriptId'])
    session_string = data_json['transcriptId']
    print(data_json['transcript'])
    df = pd.DataFrame(data_json['transcript'])
    df.columns = ['dateStart','dateEnd',
                  'actor','text']
    df['start'] = pd.to_datetime(df['dateStart'].str.replace("Z","")) + datetime.timedelta(hours=9)
    df['end'] = pd.to_datetime(df['dateEnd'].str.replace("Z","")) + datetime.timedelta(hours=9)
    df['dif'] = df['end'] - df['start']
    df['session'] = session_string
    df['actor_ip'] = user_ip_address

    # if (datetime.datetime.now().second % 4 == 0):
    #     sequence = int(datetime.datetime.now().second / 4) + int(datetime.datetime.now().minute * 60 / 4) + \
    #                int(datetime.datetime.now().hour * 3600 / 4) + int(datetime.datetime.now().day * 86400 / 4)
    #     # sending_text = df['text'][-1:].to_string().encode('utf-8')
    #     sending_text = str(sequence).encode('utf-8') + \
    #                    str.join("\n", [str.join(" ", df['text'][-1:].to_string().split(" ")[a:a + 8]) for a in
    #                                    range(0, len(df['text'][-1:].to_string().split(" ")), 8)]).encode('utf-8')
    #     url =  "http://API call"
    #     url += f"&seq={sequence}&lang=en-US"
    #     import requests
    #     post_data_to_endpoint = sending_text
    #     return_object = requests.post(url, data=post_data_to_endpoint)
    #     print(f"endpoint response ({sending_text})",return_object.text,return_object.status_code)
    #
    # print("df in /",df)
    # print(df.columns)
    df.drop(['dateStart','dateEnd','dif'],axis=1, inplace=True)
    # df.drop(['time','timeEnd','year','month','day','hour','min','sec',
    #               'yearend', 'monthend', 'dayend', 'hourend', 'minend', 'secend','dif'
    #               ],axis=1,inplace=True)
    # print(df.columns)
    df.columns=['actor','text','start','end','session','actor_ip']
    if 'log_incoming_message' in globals():
        if log_incoming_message == "DEBUG":
            df_incoming = df.copy()
            df_incoming.drop(['text','actor_ip'],axis=1, inplace=True)
            df_incoming['received_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            df_incoming['json'] = data
            insert_incoming_log(df=df_incoming)

    # print("df in / after",df)
    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    # df_existing = pd.read_sql("SELECT * FROM caption where session = '" + session_string + "'"
    #                           " order by id limit 3",  #older captions are not needed
    #                           conn)
    caption_start = df['start'].min()
    caption_start_string = caption_start.strftime("%Y-%m-%d %H:%M:%S.%f")
    df_existing = pd.read_sql("SELECT * FROM caption where session = '" + session_string + "'" + \
                                  " and start >= '" + caption_start_string + "'"
                                  , conn)

    df_existing['start'] = pd.to_datetime(df_existing['start'],format="%Y-%m-%d %H:%M:%S.%f")
    df_existing['end'] = pd.to_datetime(df_existing['end'],format="%Y-%m-%d %H:%M:%S.%f")

    if len(df_existing) != 0:
        caption_sub_start = df_existing['start'].min()
        caption_sub_start_string = caption_sub_start.strftime("%Y-%m-%d %H:%M:%S.%f")
        df_existing_sub = pd.read_sql("SELECT * FROM caption_sub where session = '" + session_string + "'" + \
                                      " and start >= '" + caption_sub_start_string + "'"
                                      , conn)
    else:
        df_existing_sub = pd.read_sql("SELECT * FROM caption_sub where session = '" + session_string + "'"
                                      , conn)
    df_existing_sub['start'] = pd.to_datetime(df_existing_sub['start'],format="%Y-%m-%d %H:%M:%S.%f")
    df_existing_sub['end'] = pd.to_datetime(df_existing_sub['end'],format="%Y-%m-%d %H:%M:%S.%f")

    conn.commit()
    conn.close()

    df, df_existing, df_existing_sub, df_existing_sub_new = \
        record_captions(df = df,
                        df_existing = df_existing,
                        df_existing_sub = df_existing_sub)

    update_captions_to_db(df = df,
                          df_existing = df_existing,
                          df_existing_sub = df_existing_sub,
                          df_existing_sub_new=df_existing_sub_new)
    # read last vocab_aggregate
    #   find caption larger than max in vocab_aggregate, but not max of df
    df_vocab = vocab_calculate_all(session_string=session_string, since_last_update = True, include_last_record=False)
    #TODO: last record needs processing after the session close
    vocab_result_save(df=df_vocab ,db_target_name="vocab_aggregate")

    data = [{"name": "data received",
             "duration": 0}]
    return jsonify(data)

def record_captions(df:pd.DataFrame=None,df_existing:pd.DataFrame=None,df_existing_sub:pd.DataFrame=None):

    columns_sub=['session','start','substart','end','actor','text']
    df_existing_sub_new = pd.DataFrame(columns=columns_sub)

    df_remove_list = []
    df_existing_remove_list = []
    for index, row in df.iterrows():
        # to skip processing (no update needed)
        df_to_remove_index = ((df_existing['start'] == row['start']) & (df_existing['end'] == row['end']) & \
                              (df_existing['actor'] == row['actor']) & (df_existing['session'] == row['session']) &
                              (df_existing['text'] == row['text']))
        # df_to_remove_index = ((row['start'].isin(df_existing['start']))&(row['end'].isin(df_existing['end']))& \
        #             (row['actor'].isin(df_existing['actor']))&(row['session'].isin(df_existing['session']))&
        #             (row['text'].isin(df_existing['text'])))
        if len(df_existing[df_to_remove_index]):
            df_remove_list.append(index)
            df_existing = df_existing[-df_to_remove_index]
    df.drop(index=df_remove_list, inplace=True)
    df_remove_list = []

    df_update_list = []
    # only the end time is updated
    for index, row in df.iterrows():
        # to skip processing (update of the time needed)
        #   TODO: should the caption_sub be updated
        df_to_update_index = ((df_existing['start'] == row['start']) & (df_existing['end'] != row['end']) & \
                              (df_existing['actor'] == row['actor']) & (df_existing['session'] == row['session']) &
                              (df_existing['text'] == row['text']))
        # df_to_remove_index = ((row['start'].isin(df_existing['start']))&(row['end'].isin(df_existing['end']))& \
        #             (row['actor'].isin(df_existing['actor']))&(row['session'].isin(df_existing['session']))&
        #             (row['text'].isin(df_existing['text'])))
        if len(df_existing[df_to_update_index]) != 0:
            # df_existing[df_to_update_index]['end'][0], df['end'][0], df_existing.iloc[1, :], df_to_update_index, \
            # df_existing[df_to_update_index].index, df_existing.iloc[
            try:
                df_existing.iloc[df_existing[df_to_update_index].index, df_existing.columns.get_loc('end')] = pd.Series(
                    row['end'])
            except IndexError as e:
                print("DEBUG: index 3 is out of bounds for axis 0 with size 3")
            #     df_existing[df_to_update_index].index, df_existing.columns.get_loc('end')], pd.Series(row['end'])
            df_update_list.append(index)
            # update table entry and dataframe
            # df_existing[df_to_update_index]



    # replace pairs
    maketrans_str = {'.': '',
                     ',': '',
                     '?': '',
                     '!': '',
                     }
    maketrans_pairs = str.maketrans(maketrans_str)

    def front_loading_parts(row_words:list=[],existing_words:list=[]):

        def word_n_gram(words, N):
            result = []
            for it, c in enumerate(words):
                if it + N > len(words):
                    return result
                result.append(words[it: it + N])

        n_gram_row = word_n_gram(row_words, 3)
        n_gram_exist = word_n_gram(existing_words, 3)
        # if row or exist are not in sufficient length, use what?
        front_load_part_string = ""
        front_load_part = None
        front_load_latter_part = None
        if len(n_gram_row) == 0 or len(n_gram_exist) == 0:
            print("shorter than length = 3")
        if len(n_gram_row) == 0:
            return front_load_part_string, front_load_part, front_load_latter_part
        if n_gram_row[0] in n_gram_exist:
            found_new_in_past = [i for i, x in enumerate(n_gram_exist) if x == n_gram_row[0]]
            found_new_in_past = found_new_in_past[0]
            # copy first i items to new
            front_load_part = existing_words[:found_new_in_past]
            front_load_latter_part = existing_words[found_new_in_past:]

            row_words_to_front_load = row['text'].split(" ")
            found_past_in_new = [[i, t, n_gram_row[i], n_gram_exist[t]] for i, x in enumerate(n_gram_row) for t in
                                 range(0, len(n_gram_exist) - 1, 1) if x == n_gram_exist[t]]

            start_position = 0
            for exist_item in front_load_part:
                start_position += re.search(exist_item, existing_row['text'][start_position:],
                                            flags=re.IGNORECASE).end()
                front_load_part_string = existing_row['text'][:start_position]
        return front_load_part_string, front_load_part, front_load_latter_part

    def reconstruct_from_list(row_original_text = "", existing_words:list = [],):

        delta_text = ""
        for exist_item in existing_words:
            re_compile = re.compile(exist_item, re.IGNORECASE | re.MULTILINE)
            row_original_text_in = row_original_text
            row_original_text = re_compile.sub("", row_original_text, 1)
            if row_original_text_in != row_original_text:
                # trailing space or characters must be removed.
                if len(row_original_text) != 0 and row_original_text[0] in ['.', '?', ',']:
                    row_original_text = row_original_text[1:]
                row_original_text = row_original_text.lstrip()

        delta_text = row_original_text
        delta_text = delta_text.lstrip()

        return delta_text

    if len(row['text'].split(" ")) >= 5:
        print("now check")

    for index, row in df.iterrows():

        df_to_duplicate_index_sub = ((df_existing_sub['start'] == row['start'])& \
                    (df_existing_sub['actor'] == row['actor'])&(df_existing_sub['session'] == row['session']))

        if (df_to_duplicate_index_sub.sum()) > 0:
            df_original_lines_w_id = df_existing_sub[df_to_duplicate_index_sub]
            df_original_lines_w_id.drop(['id'], axis=1, inplace=True)
            df_dup_lines = df_original_lines_w_id[df_original_lines_w_id.duplicated()]
            if len(df_dup_lines) > 3:
                print("check here")
        # to skip processing (no update needed)
        df_to_compare_index = ((df_existing['start'] == row['start'])& \
                    (df_existing['actor'] == row['actor'])&(df_existing['session'] == row['session']))

        if len(df_existing[df_to_compare_index]) == 0:
            if row['start'] == row['end']:
                print(                row['start'], # substart
                    row['end'])
                # the very first cap
                row['end'] = row['end'] + datetime.timedelta(microseconds=10000)
            tmp_se = pd.Series([
                row['session'],
                row['start'],
                row['start'], # substart
                row['end'],
                row['actor'],
                row['text']
            ], index=df_existing_sub_new.columns)
            df_existing_sub_new = df_existing_sub_new.append(tmp_se, ignore_index=True)
            continue
        elif len(df_existing[df_to_compare_index]) >= 2:
            print("more than one line")

        is_found_in_the_pattern_1 = False
        is_found_in_the_pattern_2 = False
        import re
        # find with new in old string
        #   0) all parts match
        #   1) first part in old match new => extend to the last part
        #   2) first part is different => add existing parts to the current part

        #   1) first part in old match new => extend to the last part
        row_words = row['text'].translate(maketrans_pairs).replace('  ', ' ').upper().rstrip().split(" ")
        for index_existing, existing_row in df_existing[df_to_compare_index].iterrows():

            existing_words = existing_row['text'].translate(maketrans_pairs).replace('  ', ' ').upper().rstrip().split(" ")
            #   0) all parts match
            if (existing_words == row_words) == True:
                is_found_in_the_pattern_1 = True
                is_found_in_the_pattern_2 = True
                df_remove_list.append(index)  # no additional entry needed in df
                df_existing_remove_list.append(index_existing)  # no additional entry needed in df
                break

            #   1) first part in old match new => extend to the last part
            # existing_words = existing_row['text'].translate(maketrans_pairs).replace('  ', ' ').upper().rstrip().split(" ")

            # overwrite with new one + delta to be added to sub by deleting the old one and
            # find last part of existing one and find additional text to add to a new caption_sub
            delta_text = None

            frontload_string, frontload_former_part, frontload_latter_part\
                = front_loading_parts(row_words=row_words, existing_words=existing_words)

            if (frontload_latter_part == row_words) == True:
                # no need to add to sub
                is_found_in_the_pattern_1 = True
                is_found_in_the_pattern_2 = True
                df_remove_list.append(index)  # no additional entry needed in df
                df_existing_remove_list.append(index_existing)  # no additional entry needed in df
                break

            if (existing_words == row_words[:len(existing_words)]) == True:
                # first word part match
                delta_text = reconstruct_from_list(row['text'], existing_words)
                if len(delta_text) > 50:
                    print("do sometihng")

            # first two words have to match
            if delta_text is None and (existing_words[1:2]==row_words[1:2]):

                s_row = set(row_words)
                s_exist = set(existing_words)

                s_subset = s_exist.issubset(s_row)

                if s_subset == True:

                    row_original_text = row['text']
                    for exist_item in existing_words:
                        re_compile = re.compile(exist_item + " ", re.IGNORECASE | re.MULTILINE)
                        # found_segments = re_compile.search(row['text'][0:40])
                        row_original_text = re_compile.sub("",row_original_text,1)
                    delta_text = row_original_text
                    delta_text = delta_text.lstrip()
                    if len(delta_text) > 50:
                        print("do sometihng")

                else:
                    # tolerate smaller differences
                    #("You know. It's my day off. So, good job. Let's see. Mike, what's",
                    # "You know. It's my day off. So, good job. let's see, what  ")
                    # (existing_row['text'])
                    # That's such a, that's such a bless. Because I have to. I have to reproduce the program. To see what is going in on. and this is only happened, when The. Text. Rolled up and the older text are hidden. Otherwise, it's not going to happen. That's only the chance. I have. When? It's closed. It's the only. Part of the, Part of the difference. I'm going to I'm sight.
                    #              Because that's That's the <<thing that the thing>> supergor
                    # (existing)
                    # finding_word: '<<thing that the thing>> supergor'
                    # (new, incoming)
                    # clean_row_text: That's such a that's such a bless Because I have to I have to reproduce the program To see what is going in on and this is only happened when The Text Rolled up and the older text are hidden Otherwise it's not going to happen That's only the chance I have When It's closed It's the only Part of the Part of the difference I'm going to I'm sight
                    #              Because that's that's the <<thing that the thing>>
                    s_difference = s_row.difference(s_exist)
                    magic_number = 3
                    if len(s_difference) < magic_number:
                        # TODO: no retroactive changes to past caption_sub
                        # TODO: always frontload texts that are not included in row['text']
                        #frontload_string, frontload_former_part, frontload_latter_part
                        if frontload_latter_part is None:
                            delta_text = reconstruct_from_list(row['text'], existing_words)
                        elif (frontload_latter_part) == 0:
                            delta_text = reconstruct_from_list(row['text'], existing_words)
                        else:
                            delta_text = reconstruct_from_list(row['text'], frontload_latter_part)
                        if len(delta_text) > 50:
                            print("do sometihng")
                    else:
                        print("do something")
                        # TODO: too much different

            if delta_text is not None:

                df_existing.at[index_existing, "text"] = row["text"]
                df_remove_list.append(index)  # no additional entry needed in df
                df_existing_sub_reference = df_existing_sub[df_existing_sub['start'] == row['start']][-1:]
                if  row['start'] == df_existing_sub_reference['end'].values[0]:
                    print('stpo here')
                if row['text'] != delta_text:
                    tmp_se = pd.Series([
                        row['session'],
                        row['start'],
                        df_existing_sub_reference['end'].values[0], #substart
                        row['end'],
                        row['actor'],
                        delta_text
                    ], index=df_existing_sub_new.columns)
                    df_existing_sub_new = df_existing_sub_new.append(tmp_se, ignore_index=True)
                    is_found_in_the_pattern_1 = True
                    break

        if is_found_in_the_pattern_1 == True:
            continue

        #   2) first part is different => add existing parts to the current part
        #     incoming text is longer -> can't find it in the past lines....
        s_row = set(row_words)

        # remove the ones that have been invalidated to avoid processing the invalided ones again
        df_existing.drop(index=df_existing_remove_list, inplace=True)
        df_existing_remove_list = []

        for index_existing, existing_row in df_existing[df_to_compare_index].iterrows():
            existing_words = existing_row['text'].translate(maketrans_pairs).replace('  ', ' ').upper().split(" ")

            s_exist = set(existing_words)
            s_difference = s_row - s_exist
            s_common = s_row & s_exist
            s_all = s_row | s_exist
            s_sym = s_row ^ s_exist
            print(s_difference)
            print("s_dif", list(s_difference))
            print("s_com", list(s_common))
            print("s_all", list(s_all))
            print("s_sym", list(s_sym))
            print(len(list(s_difference)))

            def word_n_gram(words, N):
                result = []
                for it, c in enumerate(words):
                    if it + N > len(words):
                        return result
                    result.append(words[it: it + N])
            n_gram_row = word_n_gram(row_words, 3)
            n_gram_exist = word_n_gram(existing_words, 3)
            # if row or exist are not in sufficient length, use what?
            if len(n_gram_row) == 0 or len(n_gram_exist) == 0:
                print("shorter than length = 3")
            # TODO: handle fewer words
            #   critically essential to handle for zoom due to the smaller size of letters sent to server.
            if n_gram_row[0] in n_gram_exist:
                found_new_in_past = [i for i, x in enumerate(n_gram_exist) if x == n_gram_row[0]]
                found_new_in_past = found_new_in_past[0]
                # copy first i items to new
                front_load_part = existing_words[:found_new_in_past]
                frontload_latter_part = existing_words[found_new_in_past:]
                row_words_to_front_load = row['text'].split(" ")
                found_past_in_new = [[i,t,n_gram_row[i],n_gram_exist[t]] for i, x in enumerate(n_gram_row) for t in range(0,len(n_gram_exist)-1,1) if x == n_gram_exist[t]]

                start_position = 0
                front_load_part_string = ""
                for exist_item in front_load_part:
                    start_position += re.search(exist_item, existing_row['text'][start_position:], flags=re.IGNORECASE).end()
                    front_load_part_string = existing_row['text'][:start_position]

                row_original_text = row['text']
                for exist_item in existing_words[found_new_in_past:]:
                    re_compile = re.compile(exist_item + " ", re.IGNORECASE | re.MULTILINE)
                    row_original_text = re_compile.sub("", row_original_text, 1)
                delta_text = row_original_text
                delta_text = delta_text.lstrip()
                if len(delta_text) > 50:
                    # remove different parts
                    #("It's my time. You don't want to find plenty of other outlets Will. Wait. I don't like you and I never will ponytail. I don't need you to like me. Sure. Guy. Draws better insults as you",
                    # "It's my time. You don't want to find plenty of other outlets Will. Wait. I don't like you and I never will ponytail. I don't need you to like me. Sure. Guy. After insults, as you are reporting. Come back tomorrow. Maybe I can teach you something. Do you know? There it is. All the kryptonite on earth.   Thank you.")
                    #'GUY DRAWS BETTER INSULTS AS YOU'
                    #" ".join(existing_words[max([i for existing, row, i in zip(existing_words, row_words, range(0, 10000, 1)) if existing == row]):])
                    if len(frontload_latter_part) == 0:
                        print("DEBUG here")
                    last_match_word_count = max([i for existing, row, i in zip(frontload_latter_part, row_words, range(0, 10000, 1)) if existing == row]) + 1
                    delta_text = " ".join(row_words[last_match_word_count:])
                    # TODO: match with existing to get lower-case in caption_sub
                    print("do sometihng")

                if len(front_load_part_string) == 0:
                    df_existing.at[index_existing, "text"] = row["text"]
                else:
                    df_existing.at[index_existing, "text"] = front_load_part_string + " " + row["text"]
                df_remove_list.append(index)  # no additional entry needed in df
                df_existing_sub_reference = df_existing_sub[df_existing_sub['start'] == row['start']][-1:]
                if len(df_existing_sub_reference) == 0:
                    end_time = row['start']
                else:
                    end_time = df_existing_sub_reference['end'].values[0]  # substart
                if row['text'] != delta_text:
                    tmp_se = pd.Series([
                        row['session'],
                        row['start'],
                        end_time,
                        row['end'],
                        row['actor'],
                        delta_text
                    ], index=df_existing_sub_new.columns)
                    df_existing_sub_new = df_existing_sub_new.append(tmp_se, ignore_index=True)

            else:
                print("not exist")

    df.drop(index=df_remove_list, inplace=True)
    df_existing.drop(index=df_existing_remove_list, inplace=True)
    # drop all
    df_existing_sub.drop(index=[i for i, item in df_existing_sub.iterrows()], axis=1, inplace=True)

    return df, df_existing,df_existing_sub,df_existing_sub_new

def update_captions_to_db(df:pd.DataFrame=None,df_existing:pd.DataFrame=None,
                          df_existing_sub:pd.DataFrame=None,
                          df_existing_sub_new:pd.DataFrame=None):

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)

    try:
        if len(df) > 0:
            for index, delete_item in df.iterrows():
                conn.execute("DELETE FROM caption where " + \
                             "actor = '" + delete_item['actor'] + "' and " + \
                             "start = '" + datetime.datetime.strftime(delete_item['start'],"%Y-%m-%d %H:%M:%S.%f") + "' and " + \
                             "session = '" + delete_item['session'] + "'")
            conn.commit()
            df.to_sql('caption', conn, if_exists='append', index=False)

        if len(df_existing) != 0:
            for index, delete_item in df_existing.iterrows():
                conn.execute("DELETE FROM caption where " + \
                                 "id = '" + str(delete_item['id']) + "'")
            conn.commit()
            df_existing.drop(['id'],axis=1, inplace=True)
            df_existing.to_sql('caption', con=conn, if_exists='append',index=False)

        if len(df_existing_sub_new) > 0:
            df_existing_sub_new.to_sql('caption_sub',conn,if_exists='append',index=False)
    except Exception as e:
        print(e)

    conn.commit()
    conn.close()

    return

@app.route('/render_in_full',methods=['GET'])
def return_all_results():

    received_session = request.args.get('session')
    session_string = received_session
    allowed_function_list = ['get_default_sample_1',
                             'get_vacab_acknowledge_use',
                             'get_vacab_sugestion',
                             'get_vocab_coverage',
                             'get_turn_taking',
                             'get_vocab_frequency',
                             'get_word_per_second']
    data_all = []

    data_show = {"notification": {"text": f"session:{received_session}"},
                 "heading": "Frequency",
                 "setting":
                     {"duration": 500}
                 }
    data = jsonify(data_show)
    data_all.append(data.json)
    for function_item in allowed_function_list:
        if function_item == 'get_vocab_coverage':
            kwargs = {"session_string": session_string, "option_settings": {}}
        else:
            kwargs = {"session_string": session_string}

        data = globals()[function_item](**kwargs)
        data_all.append(data.json)
    text = render_template('show_all.html', data=data_all)
    return text


@app.route('/notification',methods=['POST','GET'])
def return_notification():
    data_received = request.get_data().decode('utf-8')
    data_json = json.loads(data_received)
    username = data_json['username']
    session_string = data_json['transcriptId']
    print("username:",username)
    option_settings = data_json['option_settings']

    data = {"notification": {},
            "setting":{"duration": 2000}
            }

    data = jsonify(data)

    if option_settings != "":
        option_json = json.loads(option_settings)

        data = dynamic_function_call(option_json=option_json,session_string=session_string,
                                     section="/notification",username=username)

        if data is not None:
            return data
    else:
        option_json = {}

    if (datetime.datetime.now().second % 20) <= 1:

        data = get_default_sample_1(session_string=session_string)

    elif (1 < (datetime.datetime.now().second % 20) <= 2):

        data = globals()['get_default_sample_1'](session_string=session_string)

    elif (2 < (datetime.datetime.now().second % 20) <= 6):

        data = get_vacab_acknowledge_use(session_string=session_string)

    elif (6 < (datetime.datetime.now().second % 20) <= 10):

        data = get_vacab_sugestion(session_string=session_string)

    elif (10 < (datetime.datetime.now().second % 20) <= 19):

        if (10 < (datetime.datetime.now().second % 20) <= 13):

            data = get_vocab_coverage(session_string=session_string, option_settings=option_json, username=username)

        elif (13 < (datetime.datetime.now().second % 20) <= 16):

            data = get_turn_taking(session_string=session_string)

        elif (16 < (datetime.datetime.now().second % 20) <= 18):

            data = get_vocab_frequency(session_string=session_string)

        elif (18 < (datetime.datetime.now().second % 20) <= 19):

            data = get_word_per_second(session_string=session_string)

    return data

@app.route('/show',methods=['POST','GET'])
def return_stat_result():
    data = request.get_data().decode('utf-8')
    data_json = json.loads(data)
    # print("show ",data_json)
    if len(data_json['username']) == 0:
        data_show = {"notification": {"text":"no data exists from Meet"},
                 "heading": "no data",
                 "setting":
                     {"duration": 10}
                 }
        return jsonify( data_show)
    session_string = data_json['transcriptId']
    username = data_json['username']
    option_settings = data_json['option_settings']
    print("username:",username)
    data_return = None

    if option_settings != "":
        option_json = json.loads(option_settings)

        data_return = dynamic_function_call(option_json=option_json, session_string=session_string,
                                            section="/show",username=username)

        if data_return is not None:
            return data_return
    else:
        option_json = {}

    if (datetime.datetime.now().second % 15) <= 5:

        data_return = get_turn_taking(session_string=session_string)

    elif 5 < (datetime.datetime.now().second % 15) < 10:

        data_return = get_word_per_second(session_string)

    elif 10 < (datetime.datetime.now().second % 15) < 15:

        data_return = get_vocab_frequency(session_string=session_string)

    else:

        data_return = get_vocab_coverage(session_string=session_string,option_settings=option_json, username=username)

    if data_return is None:
        data_show = {"notification": {"text":"stat result"},
                 "heading": "No data:",
                 "setting":
                     {"duration": 500}
                 }
        data_return = jsonify(data_show)

    return data_return

def dynamic_function_call(option_json={}, session_string="",section="/show",username:str=""):

    # sample for option_json - valid
    # option_sample = {"vocab": ["medical", "designated"], "calling_functions": {
    #     "/notification": {"frequency": 6,
    #                       "function_list": [{"from": 0, "to": 2, "function_name": "get_default_sample_1"},
    #                                         {"from": 3, "to": 5, "function_name": "get_vocab_coverage"}]}}}
    # sample for option_json - error (in key word - frequency and in function_name - get_default_sample_1n )
    # option_sample = {"vocab": ["medical", "designated"], "calling_functions": {
    #     "/show": {"frequecy": 10, "function_list": [{"from": 0, "to": 2, "function_name": "get_default_sample_1n"},
    #                                                  {"from": 3, "to": 5, "function_name": "get_vocab_coverage"},
    #                                                  {"from": 6, "to": 9, "function_name": "get_turn_taking"}]}}}
    allowed_function_list = ['get_default_sample_1',
                             'get_vacab_acknowledge_use',
                             'get_vacab_sugestion',
                             'get_vocab_coverage',
                             'get_turn_taking',
                             'get_vocab_frequency',
                             'get_word_per_second']

    if 'calling_functions' in option_json:

        try:
            calling_functions_all =option_json['calling_functions']

            if section in calling_functions_all:
                calling_functions =calling_functions_all[section]

                frequency = int(calling_functions['frequency'])
                function_list = calling_functions['function_list']

                mod_of_time = datetime.datetime.now().second % frequency
                for function_item in function_list:
                    if function_item['from'] <= mod_of_time <= function_item['to']:
                        function_name = function_item['function_name']
                        if function_name in allowed_function_list:
                            if function_name == 'get_vocab_coverage':
                                kwargs = {"session_string": session_string, "option_settings": option_json, "username": username}
                            else:
                                kwargs = {"session_string": session_string}

                            data = globals()[function_name](**kwargs)
                            return data
                        else:
                            data = {"notification": {"text": f"Function {function_name} for {section} is not available"},
                                    "heading": "Error in Arbitrary option setting:",
                                    "setting":
                                        {"duration": 2000}
                                    }
                            return data

        except KeyError as e:
            data = {"notification": {"text": "Exception KeyError error occured:" + e.args[0] + \
                                     f" is missing in {section}"},
                         "heading": "Error in Arbitrary option setting:",
                         "setting":
                             {"duration": 2000}
                         }
            return data
        except Exception as e:
            data = {"notification": {"text": "Exception error occured"},
                         "heading": "Error in Arbitrary option setting:",
                         "setting":
                             {"duration": 2000}
                         }
            return data

    return None

def get_default_sample_1(session_string=""):

    data = {"notification": {"name": "ヒント:",
                             "text": '<div class="item" style="word-break:break-word;">他の表現も使ってみましょう</div>'},
            "setting":
                {"duration": 1000}
            }

    data = jsonify(data)

    return data

def get_vacab_acknowledge_use(session_string=""):

    share_text = "<div>"
    is_tag_opened = False
    df_freq_session = get_frequently_used_words(session=session_string)
    df_freq_session = remove_stopwords_entry(df=df_freq_session)
    df_freq_session = df_freq_session[(df_freq_session['count(vocab)'] >= 1) & (df_freq_session['level'] >= "B1")]

    df_recent = vocab_calculate_all(session_string=session_string, include_last_record=True)
    if df_recent is not None:
        df_recent = df_recent[df_recent['start'] >= ( df_recent['start'].max() - datetime.timedelta(minutes=1))]
    # recent vocab is not present in the vocab list
    df_freq_session.drop_duplicates(subset=['vocab'], inplace=True)
    if df_freq_session is not None:
        df_freq_session['vocab'] = df_freq_session['vocab'].str.replace("*","")
        for index, row in df_freq_session.iterrows():
            if df_recent is not None:
                try:
                    from re import error as re_error
                    if df_recent['vocab'].str.contains(row['vocab']).sum() == 0:
                        # if is_tag_opened == False:
                        #     is_tag_opened = True
                        #     share_text += "<span class='item'>"
                        # share_text += row['vocab'] + ",　</span>"
                        share_text += "<span>" + row['vocab'] + ",　</span>"
                    else:
                        # if is_tag_opened == True:
                        #     is_tag_opened = False
                        #     share_text += "</span>"
                        share_text += "<span class='repeat_flash'>" + row['vocab'] + ",　</span>"
                except re_error as e:
                    # row['vocab'] 's***'
                    print(e)
                except Exception as e:
                    print(e)
            else:
                # if is_tag_opened == True:
                #     is_tag_opened = False
                #     share_text += "</span>"
                share_text += "<span clsss='repeat_flash'>" + row['vocab'] + ",　</span>"
    # if is_tag_opened == True:
    #     share_text += "</span>"

    share_text += "が使えています"
    share_text += "</div>"
    data = {"notification":{"name": "いいね！",
             "text": share_text},
            "setting":
            {"duration": 2000}
            }

    data = jsonify(data)

    return data

def get_vacab_sugestion(session_string=""):

    df_caption = vocab_calculate_all(session_string=session_string, since_last_update=False)
    # df_sum = get_stats_for_levels_db(session_string=session_string)
    # vocab_result_save(df=df_caption, db_target_name='vocab_aggregate') #save only in the incoming message
    df_freq_session = get_frequently_used_words(session=session_string)
    # merge
    df_caption_last_only = vocab_calculate_all(session_string=session_string,include_last_record=True, since_last_update=True)
    if df_caption_last_only is not None:
        for index, row in df_freq_session[df_freq_session['vocab'].isin(df_caption_last_only['vocab'])].iterrows():
            df_freq_line = df_caption_last_only[df_caption_last_only['vocab']==row['vocab']]
            df_freq_session.at[index,'count(vocab)'] = len(df_freq_line) + row['count(vocab)']

    df_freq_session = remove_stopwords_entry(df=df_freq_session)
    #TODO allow config
    df_freq_session = df_freq_session[(df_freq_session['count(vocab)'] >= 1) & (df_freq_session['level'] >= "B1")]

    if df_caption is None:
        data = {"notification": {"name": "使ってみて",
                                 "text": "no data has been stored. Wait until you have spoken the sufficient amount of words"},
                "setting":
                    {"duration": 2000}
                }

        data = jsonify(data)

        return data

    # look back until the sufficient number (>= 5) of suggestions is found
    #TODO allow config
    list_responses = []
    look_back_set = [2,4,6,100]
    look_back_used = 100
    for look_back_length in look_back_set:
        if len(df_caption) != 0:
            df_caption_to_evaluate = df_caption[df_caption['start'] >= (df_caption['start'].max() - datetime.timedelta(minutes=look_back_length))]
            # df_to_look_for = df[df['vocab'].isin(df_freq_session['vocab'])] df is redundant
            df_to_look_for = df_freq_session[df_freq_session['vocab'].isin(df_caption_to_evaluate['vocab'])]
            df_to_look_for.drop_duplicates(subset=['vocab'],inplace=True)
            if len(df_to_look_for) != 0:
                # TODO allow config
                list_responses = suggest_words(target_level_equal_and_above="B1", df=df_to_look_for)
                if len(list_responses) >= 5 or look_back_length == look_back_set[len(look_back_set)-1]:
                    look_back_used = look_back_length
                    break
            else:
                continue
        # if look_back_length == look_back_set[len(look_back_set)-1]:
    if len(list_responses) != 0:
        list_suggestion_rel = extract_words_from_response(list_responses, "syn_list")
        df_suggestion_rel = pd.DataFrame([[wp[0], wp[1], a, b, l] for wp, a, b, l in list_suggestion_rel],
                                     columns=['vocab', 'pos', 'suggestion', 'definition', 'level'])
    else:
        df_suggestion_rel = None
    share_text = '<br>'
    share_text += f'<div>look back for {str(look_back_used)} minutes</div>eeo'
    share_text += '<div style="font-size:16px;display:inline-block;border: 1px solid #333333;">'
    share_text += f'<span style="width:64px;display:inline-block" class="head">word</span>' \
                  f'<span style="width:512px;display:inline-block" class="head">suggestion</span>' \
                  f'<span style="width:24px;display:inline-block" class="head">level</span>' \
                  f'<span style="width:200px;display:inline-block" class="head">definition</span>' \
                  f'</div>'

    if df_suggestion_rel is not None:
        other_rels = ",".join(list(df_suggestion_rel.drop_duplicates(subset=['vocab'])['vocab'].values))
        df_suggestion_rel['definition_text'] = [b[1] for a in df_suggestion_rel['definition'] for b in a for c in b if c == "text"]
        df_suggestion_rel['definition_vis'] = [b[1] for a in df_suggestion_rel['definition'] for b in a for c in b if c == "vis"]
        # [[a[0], a[1]] for a in df_suggestion_rel_top10.groupby(['vocab', 'definition_text']).groups.items()]
        df_suggestion_rel.sort_values(['vocab', 'definition_text'], inplace=True, ascending=[True, True])
        group_index = df_suggestion_rel.groupby(['vocab', 'definition_text']).groups.items()
        group_suggestion = [df_suggestion_rel['suggestion'][a[1]] for a in
         df_suggestion_rel.groupby(['vocab', 'definition_text']).groups.items()]
        group_level = [df_suggestion_rel['level'][a[1]] for a in
         df_suggestion_rel.groupby(['vocab', 'definition_text']).groups.items()]

        df_suggestion_rel_final = pd.DataFrame(
            {
                "vocab": df_suggestion_rel['vocab'],
                "definition_text": df_suggestion_rel['definition_text'],
                "definition_vis": df_suggestion_rel['definition_vis'],
                "level": df_suggestion_rel['level'],
                "suggestion": df_suggestion_rel['suggestion'],
            })
        df_suggestion_rel_final.drop_duplicates(subset=['vocab','definition_text'],inplace=True)
        l_suggestion = []
        for item_group in zip(group_suggestion,group_level):
            level_text = ""
            vocab_list_text = ""
            df_item = pd.DataFrame({
                "level": item_group[1],
                "text": item_group[0],
            }
            )
            df_item_na = df_item[df_item['level']=='NA']
            df_item_with_level = df_item[-(df_item['level']=='NA')]
            df_item_with_level.sort_values(['level','text'],inplace=True,ascending=[False,False])
            df_item = pd.concat([df_item_with_level,df_item_na])

            for index, item_row in enumerate(df_item.iterrows()):
                item = item_row[1]
                if index == 0:
                    level_text = item['level']
                    vocab_list_text = f"({level_text}) {item['text']}"
                    continue
                if level_text == item['level']:
                    vocab_list_text += f", {item['text']}"
                else:
                    level_text = item['level']
                    vocab_list_text += f"({level_text}) {item['text']}"

            l_suggestion.append(vocab_list_text)
        df_suggestion_rel_final['combined'] = l_suggestion

        for index, row in df_suggestion_rel_final.iterrows():
            row['definition_vis'] = str(row['definition_vis']).replace("{it}","<i>")
            row['definition_vis'] = str(row['definition_vis']).replace("{/it}","</i>")
            share_text += '<div style="font-size:16px;display:inline-block;border: 1px solid #333333;">'
            share_text += f'<span style="width:64px;font-size:16px;display:inline-block;word-wrap: break-word;" class="item">{row["vocab"]}</span>' \
                          f'<span style="width:512px;font-size:24px;display:inline-block;word-wrap: break-word;" class="item">{row["combined"]}</span>' \
                          f'<span style="width:64px;font-size:16px;display:inline-block" class="item">{row["level"]}</span>' \
                          f'<span style="width:200px;font-size:16px;display:inline-block" class="item">{row["definition_text"]}</span>'
            share_text += '</div>'
        share_text += '<br><br><br><div>Other synonyms available for the words (' + other_rels + ')</div>'

    data = {"notification":{"name": "使ってみて",
             "text": share_text },
            "setting":
            {"duration": 1000}
            }

    data = jsonify(data)

    return data

def get_vocab_coverage(session_string="",option_settings={}, username:str="all"):

    try:
        parsed_option_settings = option_settings
    except JSONDecodeError as e:
        data_show = {"notification": {"text":"Incorrect arbitrary option settings"},
                 "heading": "No data",
                 "setting":
                     {"duration": 500}
                 }
        data_return = jsonify(data_show)
        return(data_return)
    except Exception as e:
        parsed_option_settings = None

    # else: if parsed_option_settings is None:
    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    df = pd.read_sql("SELECT * FROM caption where session = '" + session_string + "'", conn)
    df_vocab_list = pd.read_sql("SELECT * FROM session_settings where session = '" + session_string + "'" + \
                                " and key = 'vocab_to_cover'"
                                , conn)
    conn.close()

    df['text'] = df['text'].str.lower()
    vocab_list_used = {}
    if len(df_vocab_list) != 0:
        df_vocab_list = df_vocab_list[(df_vocab_list['actor']=="all") | (df_vocab_list['actor']==username)]
        vocab_list = list(df_vocab_list['value'].str.lower())
    else:
        if parsed_option_settings is None:
            vocab_list = ['SAMPLE LIST','successive','following']
        else:
            if 'vocab' in parsed_option_settings:
                vocab_list = parsed_option_settings['vocab']
            else:
                vocab_list = ['SAMPLE LIST','successive', 'following']

    if len(df) != 0:
        for item in vocab_list:
            vocab_list_used[item] = df['text'].str.contains(item,case=False).sum()
    else:
        for item in vocab_list:
            vocab_list_used[item] = 0
    vocab_list_used_counter = 0
    for item in vocab_list:
        if vocab_list_used[item] != 0:
            vocab_list_used_counter += 1
    vocab_list_used_counter_remaining = len(vocab_list) - vocab_list_used_counter
    data_json = {}
    share_text = ''
    share_text += '<div>' \
                  f'<span class="head" style="font-size:48px;">remaining language to cover:</span>' \
                  f'<span class="head" style="font-size:96px;">{str(vocab_list_used_counter_remaining)}</span>' \
                  f'<span class="head" style="font-size:48px;">covered language:</span>' \
                  f'<span class="head" style="font-size:96px;">{str(vocab_list_used_counter)}</span><br>' \
                  f'<span class="head" style="font-size:48px;">target language:</span>' \
                  f'<span class="head" style="font-size:96px;">{len(vocab_list)}</span>' \
                  '</div>'
    share_text += '<div>'
    for item in vocab_list:
        # share_text += f'<div><span class="item" style="width:40px;">[{str(vocab_list_used[item])}]</span>' \
        #               f'<span class="item_blue">{item}</span></div>'
        if vocab_list_used[item] == 0:
            share_text += f'<span class="item_red"  style="font-size:48px;">{item},</span>'
        elif ( 1 <= vocab_list_used[item] <= 2 ):
            share_text += f'<span class="item_blue" style="font-size:24px;">{item},</span>'
        elif (3 <= vocab_list_used[item] ):
            share_text += f'<span class="item_blue" style="font-size:12px;">{item},</span>'

    share_text += '</div>'
    share_text += '<div><span class="text_item">Activate those vocab.</span></div>'
    data_json["setting"] = {"duration": 500}
    data_json["notification"] = { "text": share_text }
    data_json["heading"] = "vocab coverage"
    data_return = jsonify(data_json)

    return data_return

def get_vocab_frequency(session_string=""):

    # last record needs processing after the session close
    if session_string == "%":
        df_freq_session = get_frequently_used_words(session="%")
    else:
        dbname = DB_NAME
        conn = sqlite3.connect(dbname)

        df_end_max = pd.read_sql("SELECT max(end) FROM caption where " + \
                                      " session = '" + session_string + "'"
                                      , conn)
        conn.commit()
        conn.close()

        if df_end_max is not None:
            last_processed_time = pd.to_datetime(df_end_max['max(end)'])[0].to_pydatetime()
            if ((last_processed_time + datetime.timedelta(minutes=2)) < datetime.datetime.now()):
                print("updated due to max elapsed time")
                df = vocab_calculate_all(session_string=session_string, since_last_update=True, include_last_record=True)
                vocab_result_save(df=df, db_target_name="vocab_aggregate")

        df_freq_session = get_frequently_used_words(session=session_string)

    df_freq_session = remove_stopwords_entry(df=df_freq_session)

    if len(df_freq_session) == 0:
        share_text = f"<div>No frequency data for {session_string}</div>"
        data_show = {"notification": {"text": share_text},
                     "heading": "Frequency",
                     "setting":
                         {"duration": 500}
                     }
        data_return = jsonify(data_show)

        return data_return

    # df_freq_session = df_freq_session[(df_freq_session['count(vocab)'] > 1) & (df_freq_session['level'] >= "B1")]
    # count(vocab), vocab, start, session, level
    df_freq_session.sort_values(['level', 'count(vocab)'], ascending=[False, False], inplace=True)
    share_text = '<br>'
    share_text += '<div style="font-size:16px;display:inline-block;border: 1px solid #333333;height:24px;">'
    share_text += f'<span style="width:120p;display:inline-block" class="head">word</span>' \
                  f'<span style="width:82px;display:inline-block" class="head">level</span>' \
                  f'<span style="width:24px;display:inline-block" class="head">frequency</span>' \
                  f'</div>'
    share_text += '<br><br><br>'
    #TODO allow config
    # for index, row in df_freq_session[0:100].iterrows():
    word_count = df_freq_session['count(vocab)'].sum()
    df_freq_session_all = df_freq_session.groupby(['level','vocab']).sum()
    df_freq_session_all = pd.DataFrame(df_freq_session_all.reset_index())
    df_freq_session_all = df_freq_session_all[df_freq_session_all['count(vocab)'] >= (
    df_freq_session_all[df_freq_session_all['count(vocab)'] >= 2].mean()['count(vocab)'])]
    df_speaker_list = df_freq_session.drop_duplicates(subset=['actor'])
    df_speaker_list_string = "/".join([a for a in df_speaker_list['actor']])
    share_text += f'<div style="font-size:16px;display:inline-block;border: 1px solid #333333;height:24px;">all speakers: {df_speaker_list_string} words({str(word_count)})</div>'
    share_text += '<br><br><br>'
    df_freq_session_all.sort_values(['level','count(vocab)'],ascending=[False,False], inplace=True)
    for index, row in df_freq_session_all.iterrows():
        share_text += '<div style="font-size:16px;display:inline-block;border: 1px solid #333333;height:12px;margin:0;line-height:12px;padding:0px;">'
        share_text += f'<span style="width:120px;font-size:16px;display:inline-block;word-wrap: break-word;height:12px;margin:0;padding:0px;">{row["vocab"]}</span>' \
                      f'<span style="width:82px;font-size:16px;display:inline-block;height:12px;margin:0;padding:0px;">{row["level"]}</span>' \
                      f'<span style="width:24px;font-size:16px;display:inline-block;height:12px;margin:0;padding:0px;">{row["count(vocab)"]}</span>'
        share_text += '</div>'

    for speaker_index, speaker_item in df_speaker_list.iterrows():
        df_freq_each_speaker =df_freq_session[df_freq_session['actor']==speaker_item['actor']]
        # df_freq_each_speaker TODO: remove duplicate
        word_count = df_freq_each_speaker['count(vocab)'].sum()
        df_freq_each_speaker_group = df_freq_each_speaker.groupby(['level','vocab']).sum()
        df_freq_each_speaker_group = pd.DataFrame(df_freq_each_speaker_group.reset_index())
        df_freq_each_speaker = df_freq_each_speaker_group
        df_freq_each_speaker.sort_values(['level', 'count(vocab)'], ascending=[False, False], inplace=True)
        share_text += '<br><br><br>'
        share_text += f'<div style="font-size:16px;display:inline-block;border: 1px solid #333333;height:24px;">Speaker:{speaker_item["actor"]} words({str(word_count)})</div>'
        share_text += '<br><br><br>'
        for index, row in df_freq_each_speaker.iterrows():
            share_text += '<div style="font-size:16px;display:inline-block;border: 1px solid #333333;height:12px;margin:0;line-height:12px;padding:0px;">'
            share_text += f'<span style="width:120px;font-size:16px;display:inline-block;word-wrap: break-word;height:12px;margin:0;padding:0px;">{row["vocab"]}</span>' \
                          f'<span style="width:82px;font-size:16px;display:inline-block;height:12px;margin:0;padding:0px;">{row["level"]}</span>' \
                          f'<span style="width:24px;font-size:16px;display:inline-block;height:12px;margin:0;padding:0px;">{row["count(vocab)"]}</span>'
            share_text += '</div>'



    share_text += "</div>"
    data_show = {"notification": {"text": share_text},
                 "heading": "Frequency",
                 "setting":
                     {"duration": 500}
                 }
    data_return = jsonify(data_show)

    return data_return

def get_turn_taking(session_string=""):

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    df = pd.read_sql("SELECT * FROM caption_sub where session = '" + session_string + "'", conn)
    if len(df) == 0:
        data_show = {"notification": {"text": f"no data exists for session {session_string}"},
                     "heading": "show stats area",
                     "setting":
                         {"duration": 2000}
                     }
        return jsonify(data_show)
    # df.columns = ['id', 'session', 'start', 'end', 'actor', 'text', 'actor_ip']
    df.columns = ['id', 'session', 'start', 'substart', 'end', 'actor', 'text']
    # print("df end",df['end'])
    df['substart'] = pd.to_datetime(df['substart'], format="%Y-%m-%d %H:%M:%S.%f")
    df['end'] = pd.to_datetime(df['end'], format="%Y-%m-%d %H:%M:%S.%f")
    df['dif'] = df['end'] - df['substart']

    sum_df = df.groupby('actor').agg({'dif': 'sum'})
    sum_df = pd.DataFrame(sum_df.reset_index())
    # sum_df['dif'] = sum_df['dif'].apply(datetime.timedelta.total_seconds)
    sum_df.columns = ['name', 'duration']
    sum_df['share'] = sum_df['duration'] / sum_df['duration'].sum() * 100
    sum_df['share'].fillna(0, inplace=True)
    sum_df['share'] = sum_df['share'].astype(int)

    last_clocktime = df['end'].max()
    last_clocktime = last_clocktime - datetime.timedelta(minutes=5)
    df_5 = df[df['end'] > last_clocktime]
    sum_df_5 = df_5.groupby('actor').agg({'dif': 'sum'})
    sum_df_5 = pd.DataFrame(sum_df_5.reset_index())
    # sum_df_5['dif'] = sum_df_5['dif'].apply(datetime.timedelta.total_seconds)
    sum_df_5.columns = ['name', 'duration']
    sum_df_5['share_5'] = sum_df_5['duration'] / sum_df_5['duration'].sum() * 100
    sum_df_5['share_5'].fillna(0, inplace=True)
    sum_df_5['share_5'] = sum_df_5['share_5'].astype(int)
    sum_all = pd.merge(sum_df, sum_df_5, on='name', how="outer")
    sum_all['share_5'].fillna(0, inplace=True)
    sum_all['share'].fillna(0, inplace=True)

    share_text = ''
    share_text += '<div style="font-size:24px;">'
    share_text += f'<span style="width:100px;" class="head">Speaker</span>' \
                  f'<span style="width:100px;" class="head">Total</span>' \
                  f'<span style="width:100px;  class="head">5min.</span>' \
                  f'</div>'
    for index, row in sum_all.iterrows():
        share_text += '<div style="font-size:24px;">'
        share_text += f'<span style="width:100px;" class="item">{row["name"]}</span>' \
                      f'<span style="width:100px;" class="item">{row["share"]}%</span>' \
                      f'<span style="width:100px;" class="item">{row["share_5"]}%</span>'
        share_text += '</div>'
    # single speaker speaking time
    # length = df[-1:]['dif'].values[0].view('<i8')/10**9
    speaker = df[-1:]['actor'].values[0]
    last_row_of_a_different_speaker = df[df['actor'] != speaker].index.max()
    if last_row_of_a_different_speaker is np.nan:
        # all lines are for the single speaker
        length = df['dif'].sum().view('<i8') / 10 ** 9
    else:
        length = df[last_row_of_a_different_speaker + 1:]['dif'].sum().view('<i8') / 10 ** 9
    share_text += '<div style="font-size:24px;">Single speaker speaking time</div>'
    share_text += '<br><br>'
    share_text += '<div style="font-size:24px;">'
    share_text += f'Speaker:{speaker} for {length}'
    share_text += '</div>'
    # print(share_text)
    data_show = {"notification": {"text": share_text},
                 "heading": "Turn taking",
                 "setting":
                     {"duration": 500}
                 }
    data_return = jsonify(data_show)

    return data_return

def get_word_per_second(session_string=""):

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    df = pd.read_sql("SELECT * FROM caption_sub where session = '" + session_string + "'", conn)
    conn.close()

    if len(df) == 0:
        data_return = {"notification": {"text":f"no data exists for session {session_string}"},
                 "heading": "Word per second",
                 "setting":
                     {"duration": 500}
                 }
        data_return_json = jsonify(data_return)
        return data_return_json
    df.columns = ['id', 'session', 'start', 'substart', 'end', 'actor', 'text']
    df['substart'] = pd.to_datetime(df['substart'], format="%Y-%m-%d %H:%M:%S.%f")
    df['end'] = pd.to_datetime(df['end'], format="%Y-%m-%d %H:%M:%S.%f")
    # TODO: allow config -> auto calibrate through the tempo. May need further customization for each individual
    df['dif'] = df['end'] - df['substart']
    df['word_count'] = df['text'].apply(str.split).apply(len)

    list_actors = [ a[0] for a in df.groupby(["actor"]).groups.items()]
    df_all = None
    for each_actor in list_actors:
    # give sufficient length before system recognize part(s) as slower
    # list_df = list(df.values)
        index_loop = -1
        list_df_merged_for_shorter_segment = []
        for index, row in df.iterrows():
            if row['actor'] != each_actor:
                continue
            index_loop += 1
            if index_loop == 0:
                list_df_merged_for_shorter_segment.append(row)
                continue
            if (( row['dif'].seconds + row['dif'].microseconds / 1000000 ) < 0.1) and row['word_count'] <= 2:
                index_to_merge = len(list_df_merged_for_shorter_segment) - 1
                if index_to_merge < 0:
                    index_to_merge = 0
                if list_df_merged_for_shorter_segment[index_to_merge][7].seconds < 3:
                    # add dif and merge text and word count if two captions are adjacent.
                    if list_df_merged_for_shorter_segment[index_to_merge][4] != row['start']:
                        list_df_merged_for_shorter_segment.append(row)
                    else:
                        list_df_merged_for_shorter_segment[index_to_merge][4] = row['end']
                        list_df_merged_for_shorter_segment[index_to_merge][6] = \
                        list_df_merged_for_shorter_segment[index_to_merge][6] + "/" + row['text']
                        list_df_merged_for_shorter_segment[index_to_merge][7] = \
                        list_df_merged_for_shorter_segment[index_to_merge][7] + row['dif']
                        list_df_merged_for_shorter_segment[index_to_merge][8] = \
                        list_df_merged_for_shorter_segment[index_to_merge][8] + row['word_count']
                else:
                    list_df_merged_for_shorter_segment.append(row)
            else:
                list_df_merged_for_shorter_segment.append(row)
        if df_all is None:
            df_all = pd.DataFrame(list_df_merged_for_shorter_segment, columns=df.columns)
        else:
            df_temp = pd.DataFrame(list_df_merged_for_shorter_segment, columns=df.columns)
            df_all = pd.concat([df_all, df_temp])
    df = df_all.copy()

    wps_for_each_actor = []
    df['wps'] = df['word_count'] / (df['dif'].dt.seconds +  df["dif"].dt.microseconds / 1000000 )
    # for mean calculation, it needs sufficient lines of captions

    # for each_actor in list_actors:
    # give sufficient length before system recognize part(s) as slower
    # list_df = list(df.values)
    df_average_all = (df.groupby(["actor"])['word_count'].sum() / df.groupby(["actor"])['dif'].sum().dt.seconds).reset_index()
    df_average_all.columns = ['actor','wps']
    df_average_20 = pd.DataFrame([[ids[0],  (df.iloc[ ids[1],df.columns.get_loc("word_count") ][0:20].sum()) / (df.iloc[ ids[1],df.columns.get_loc("dif") ][0:20].sum().seconds)   ] for ids in df.groupby(["actor"]).groups.items()], columns=['actor','wps'])
    df_average_all[df_average_all['wps'] > 10]['wps'] = 10
    df_average_20[df_average_20['wps'] > 10]['wps'] = 10

    # if len(df) >= 20:
    #     average_wps_all = df['word_count'].sum() / ( df['dif'].dt.microseconds.sum() / 100000 )
    #     average_wps_last_set = df['word_count'][0:20:].sum() / ( df['dif'][0:20:].dt.microseconds.sum() / 100000 )
    # else:
    #     average_wps_all = df['word_count'].sum() / ( df['dif'].dt.microseconds.sum() / 100000 )
    #     average_wps_last_set = df['word_count'][0:20:].sum() / ( df['dif'][0:20:].dt.microseconds.sum() / 100000 )
    #     if average_wps_all > 10:
    #         average_wps_all = 10         #cap to 10
    #     if average_wps_last_set > 10:
    #         average_wps_last_set = 10    #cap to 10

    df['wps'].fillna(0, inplace=True)
    df.loc[df[df['wps'] > 10].index, 'wps'] = 12
    df.sort_values(['substart'], ascending=[False], inplace=True)

    df_wps_line = pd.DataFrame([[a[0][1]['actor'], a[0][1]['wps'], a[1][1]['wps']] for a in
                  zip(df_average_all.iterrows(), df_average_20.iterrows())], columns=['actor', 'wps_all', 'wps_20'])
    share_text = '<div>'
    share_text += f'<span style="width:64px;font-size:12px;" class="head">Speaker</span>' \
                  f'<span style="width:24px;font-size:12px;" class="head">wps(all)</span>' \
                  f'<span style="width:24px;font-size:12px;"  class="head">wps(20 items)</span>' \
                  f'<span style="width:50px;font-size:12px;"  class="head">wps target</span>' + \
                  '</div>'
    for index, row in df_wps_line.iterrows():
        threshold_wps = row['wps_20'] * 0.8
        share_text += f'<div>' + \
                      f'<span style="width:64px;font-size:12px;" class="item">{row["actor"]}</span>' + \
                      f'<span style="width:24px;font-size:12px;" class="item">{format( row["wps_all"],".2f")}</span>' + \
                      f'<span style="width:24px;font-size:12px;" class="item">{format(row["wps_20"], ".2f")}</span>' + \
                      f'<span style="width:50px;font-size:12px;" class="item">{format(threshold_wps, ".2f")}</span>' + \
                      f'</div>'
                     # f'from {df[:1]["substart"].dt.strftime("%H:%m:%S").values[0]} <br>' + \
    share_text += '<div style="font-size:24px;">'
    share_text += f'<span style="width:64px;font-size:12px;" class="head">clock</span>' \
                  f'<span style="width:24px;font-size:12px;" class="head">sec</span>' \
                  f'<span style="width:24px;font-size:12px;"  class="head">words</span>' \
                  f'<span style="width:50px;font-size:12px;"  class="head">wps.</span>'
    #TODO allow config
    is_to_display_speaker_only = False
    if is_to_display_speaker_only == True:
        is_to_display_speaker_only = True
    else:
        share_text += f'<span style="width:100px;font-size:12px;"  class="head">Speaker</span>'
    share_text += f'<span style="width:50%;font-size:12px;"  class="head">text</span>' \
                  f'</div>'
    # for index, row in df[0:20:].iterrows():
    # if len(df[(df['dif'].dt.seconds + df['dif'].dt.microseconds / 1000000) < 0.1]['dif']) != 0:
    #     update_index = (df['wps'] == np.inf )
    #     # update_index = ((df['dif'].dt.seconds + df['dif'].dt.microseconds / 1000000) < 0.1)
    #     # df[(df['dif'].dt.seconds + df['dif'].dt.microseconds / 1000000) < 0.1]['dif'] = pd.Series(
    #     #     [0.1 for a in range(0, len(df[(df['dif'].dt.seconds + df['dif'].dt.microseconds / 1000000) < 0.1]), 1)])
    #     # df_existing.iloc[df_existing[df_to_update_index].index, df_existing.columns.get_loc('end')] = pd.Series(
    #     #     row['end'])
    #     # df.iloc[df[update_index].index, df.columns.get_loc('dif')] = pd.Series([ datetime.timedelta(milliseconds=100) for a in range(0, len(df[(df['dif'].dt.seconds + df['dif'].dt.microseconds / 1000000) < 0.1]), 1)])
    #     df.iloc[df[update_index].index, df.columns.get_loc('wps')] = pd.Series( [ 1 for a in range(0,len(df[update_index]),1)]  )
    for index, row in df.iterrows():
        share_text += '<div style="font-size:12px;">'
        share_text += f'<span style="width:64px;font-size:12px;" class="item">{row["substart"].strftime("%M:%S")}</span>' \
                      f'<span style="width:24px;font-size:12px;" class="item">{format((row["dif"].seconds +row["dif"].microseconds / 1000000 )  ,".1f")}</span>' \
                      f'<span style="width:24px;font-size:12px;" class="item">{row["word_count"]}</span>'
        item_fontsize = "12"
        if row["wps"] < ( threshold_wps ):
            item_type = "item_red"
            item_fontsize = "24"
        elif row["wps"] < 1:
            item_type = "item_red"
            item_fontsize = "12"
        else:
            item_type = "item_blue"
        # if row['wps'] > 10:
        #     row['wps'] = 10
        share_text += f'<span style="width:50px;font-size:{item_fontsize}px;" class="{item_type}">{format(row["wps"], ".2f")}</span>'
        # share_text += f'<span style="width:100px;font-size:12px;" class="{item_type}">{str.lower(row["text"][0:26])}</span>'
        # TODO allow config
        if is_to_display_speaker_only == True:
            is_to_display_speaker_only = True
        else:
            share_text += f'<span style="width:100px;font-size:12px;"  class="item">{row["actor"]}</span>'
        share_text += f'<span style="width:50%;font-size:12px;" class="{item_type}">{str.lower(row["text"])}</span>'
        share_text += '</div>'
    # print(share_text)
    data = {"notification": {"text":share_text},
             "heading": "Word per second",
             "setting":
                 {"duration": 500}
             }
    data = jsonify(data)
    return data

def get_session_settings(username:str="",session_string:str=""):

    df_session_settings = None
    if session_string is not None:
        dbname = DB_NAME
        conn = sqlite3.connect(dbname)

        df_session_settings = pd.read_sql("SELECT * from session_settings where session = '" + session_string + "'", conn)
        conn.close()

        df_session_settings.drop(['id'], axis=1, inplace=True)
        if len(df_session_settings) != 0:
            if username is None or username =="":
                df_session_settings = df_session_settings[df_session_settings['actor'] == 'all']
            else:
                df_session_settings = df_session_settings[df_session_settings['actor'] == username]

            df_session_vocab_to_cover = df_session_settings[df_session_settings['key']== "vocab_to_cover"]
            df_session_vocab_to_suggest = df_session_settings[df_session_settings['key']== "vocab_to_suggest"]
            df_session_vocab_to_avoid = df_session_settings[df_session_settings['key']== "vocab_to_avoid"]
            return df_session_vocab_to_cover,df_session_vocab_to_suggest,df_session_vocab_to_avoid

    return None, None, None

def insert_incoming_log(df:pd.DataFrame):

    dbname = DB_NAME_LOG
    conn = sqlite3.connect(dbname)
    df.to_sql('incoming_message', conn, if_exists='append', index=False)
    conn.commit()
    conn.close()

def check_table():

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    cur.execute('SELECT * FROM caption')

    print(cur.fetchall())
    conn.commit()
    conn.close()

def insert_db():

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    cur.execute("INSERT INTO caption ( start , end , actor , text ) values ( '2021/8/15 13:13:30','2021/8/15 13:15:30','aki','text'  )")

    conn.commit()
    conn.close()


def create_db():

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    # cur.execute('DROP TABLE caption')
    cur.execute(
        'CREATE TABLE IF NOT EXISTS caption(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'session VARCHAR(40),'
        'start DATETIME(6),'
        'end DATETIME(6), '
        'actor VARCHAR(30),'
        'text MESSAGE_TEXT,'
        'actor_ip VARCHAR(60) )')
    cur.execute(
        'CREATE TABLE IF NOT EXISTS caption_sub ('         
        '	id INTEGER,'
        '	session	VARCHAR(40),'
        '	start DATETIME(6),'
        '	substart DATETIME(6),'
        '	end	DATETIME(6),'
        '	actor VARCHAR(30),'
        '	text MESSAGE_TEXT,'
        '	PRIMARY KEY("id" AUTOINCREMENT) );')
    cur.execute(
        'CREATE TABLE IF NOT EXISTS log(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'session VARCHAR(40),'
        'start DATETIME(6),'
        'actor VARCHAR(30),'
        'text MESSAGE_TEXT,'
        'logtype MESSAGE_TEXT )')
    cur.execute(
        'CREATE TABLE  IF NOT EXISTS session_settings('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'session VARHAR(40),'
        'actor VARCHAR(30),'
        'key VARCHAR(20),'
        'value MESSAGE_TEXT )')
    cur.execute(
        'CREATE TABLE  IF NOT EXISTS session_prompt_log('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'session VARHAR(40),'
        'start DATETIME,'
        'actor VARCHAR(30),'
        'key VARCHAR(20),'
        'value VARCHAR(20),'
        'triggering_criteria VARCHAR(20),'
        'prompt_result VARCHAR(20) )')
    conn.commit()
    conn.close()

    dbname = DB_NAME_SITE
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    cur.execute(
        'CREATE TABLE  IF NOT EXISTS site_text('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'url MESSAGE_TEXT,'
	    'title_of_site MESSAGE_TEXT,'
	    'text_in_json  MESSAGE_TEXT,'
	    'time_retrieved	DATETIME ) ')

    conn.commit()
    conn.close()

    dbname = DB_NAME_LOG
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    cur.execute(
        'CREATE TABLE  IF NOT EXISTS incoming_message('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'start DATETIME(6),'
        'end DATETIME(6), '
        'actor VARCHAR(30),'
        'received_time DATETIME(6), '
	    'json TEXT)')

    conn.commit()
    conn.close()


if __name__ == "__main__":

    arguments = docopt(__doc__, version="0.1")

    host = arguments["<host>"]
    port = int(arguments["<port>"])
    log_incoming_message =  arguments["<debug>"]
    create_db()
    # insert_db()
    # check_table()
    if port == 443:
        app.run(debug=False, host=host, port=int(port), ssl_context=('cert.pem','key.pem'))
    else:
        app.run(debug=False, host=host, port=int(port))