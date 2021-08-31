"""
Caption analytics

Usage:
  main.py <host> <port>
  main.py -h | --help
  main.py --version

  <host>:
  <port>:

Examples:
  main.py 0.0.0.0 443

Options:
  -h --help     Show this screen.
  --version     Show version.
"""

import datetime
import sqlite3
from docopt import docopt

from flask import Flask, request, jsonify,json
from flask_cors import CORS
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
DB_NAME = "test.db"

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
CORS(app)

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
    date_string_iso = data_json['date']
    # date_string = (datetime.datetime.fromisoformat(date_string_iso.split(".")[0]) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    date_string = (datetime.datetime.fromisoformat(str(date_string_iso).replace("Z","")) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S.%f")
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
    df = pd.DataFrame(data_json['transcript'])
    df.columns = ['dateStart','dateEnd',
                  'actor','text']
    df['start'] = pd.to_datetime(df['dateStart'].str.replace("Z","")) + datetime.timedelta(hours=9)
    df['end'] = pd.to_datetime(df['dateEnd'].str.replace("Z","")) + datetime.timedelta(hours=9)
    df['dif'] = df['end'] - df['start']
    df['session'] = session_string
    df['actor_ip'] = user_ip_address
    # print("df in /",df)
    # print(df.columns)
    df.drop(['dateStart','dateEnd','dif'],axis=1, inplace=True)
    # df.drop(['time','timeEnd','year','month','day','hour','min','sec',
    #               'yearend', 'monthend', 'dayend', 'hourend', 'minend', 'secend','dif'
    #               ],axis=1,inplace=True)
    # print(df.columns)
    df.columns=['actor','text','start','end','session','actor_ip']
    # print("df in / after",df)
    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    df_existing = pd.read_sql("SELECT * FROM caption where session = '" + session_string + "'", conn)
    df_existing['start'] = pd.to_datetime(df_existing['start'],format="%Y-%m-%d %H:%M:%S.%f")
    df_existing['end'] = pd.to_datetime(df_existing['end'],format="%Y-%m-%d %H:%M:%S.%f")

    df_to_add = df[-(df['start'].isin(df_existing['start']) & df['end'].isin(df_existing['end']) & df['actor'].isin(df_existing['actor']) & df['session'].isin(df_existing['session']))]
    # df_to_delete = df[(df['start'].isin(df_existing['start']) & df['actor'].isin(df_existing['actor']) & df['session'].isin(df_existing['session']))]
    for index, row in df_to_add.iterrows():
        # print("delete:",row['session'],row['actor'],row['start'])
        conn.execute("DELETE FROM caption where " + \
                     "actor = '" + row['actor'] + "' and " + \
                     "start = '" + datetime.datetime.strftime(row['start'],"%Y-%m-%d %H:%M:%S.%f") + "' and " + \
                     "session = '" + row['session'] + "'")
    df_to_add.to_sql('caption',conn,if_exists='append',index=False)
    # running caption part
    if len(df_to_add) == 0:
        conn.commit()
        conn.close()
        data = [{"name": "data received",
                 "duration": 0}]
        return jsonify(data)

    df_existing_sub_from_df_to_add = df_to_add.copy()
    df_existing_sub = pd.read_sql("SELECT * FROM caption_sub where session = '" + session_string + "'", conn)
    df_existing_sub['start'] = pd.to_datetime(df_existing_sub['start'],format="%Y-%m-%d %H:%M:%S.%f")
    df_existing_sub['end'] = pd.to_datetime(df_existing_sub['end'],format="%Y-%m-%d %H:%M:%S.%f")
    # if new, insert the line
    if len(df_existing_sub) == 0:
        df_existing_sub_from_df_to_add['substart'] = df_existing_sub_from_df_to_add['start']
        df_existing_sub_from_df_to_add.to_sql('caption_sub', conn, if_exists='append', index=False)

    else:
        df_existing_sub_new = df_existing_sub[-1:].copy()
        df_existing_sub_new['substart'] = df_existing_sub_new['end'].values[0]
        df_existing_sub_new['start'] = df_to_add['start'].values[0]
        df_existing_sub_new['end'] = df_to_add['end'].values[0]
        text_to_edit = df_to_add['text'].values[0]
        text_to_edit = text_to_edit.replace(".","")
        text_to_edit = text_to_edit.replace(",","")
        text_to_edit = text_to_edit.replace("?","")
        # text_to_edit = text_to_edit.replace(" ","") # preserve space to count words
        text_to_edit = str.upper(text_to_edit)
        text_to_remove = df_existing[-1:]['text'].values[0]
        text_to_remove = text_to_remove.replace(".","")
        text_to_remove = text_to_remove.replace(",","")
        text_to_remove = text_to_remove.replace("?","")
        # text_to_remove = text_to_remove.replace(" ","") # preserve space to count words

        text_to_remove = str.upper(text_to_remove)
        text_to_edit_new = text_to_edit.replace(text_to_remove,"",1)
        import re
        p = re.compile('[a-zA-Z]+')

        if p.search(text_to_edit_new) is not None:
            if len(text_to_edit_new) > 20:
                print(text_to_edit)
                print(text_to_remove)
                print(text_to_edit_new)
            df_existing_sub_new['text'] = text_to_edit_new
            df_existing_sub_new.drop(['id'],axis=1, inplace=True)
            df_existing_sub_new['actor'] = username
            df_existing_sub_new.to_sql('caption_sub',conn,if_exists='append',index=False)
    conn.commit()
    conn.close()

    data = [{"name": "data received",
             "duration": 0}]
    return jsonify(data)

@app.route('/notification',methods=['POST','GET'])
def return_notification():
    data_received = request.get_data().decode('utf-8')
    data_json = json.loads(data_received)
    username = data_json['username']
    session_string = data_json['transcriptId']
    print("username:",username)

    data = {"notification": {},
            "setting":{"duration": 2000}
            }
    if (datetime.datetime.now().second % 15) <= 3:
        data = {"notification":{"name": "ヒント:",
                 "text": "他の表現も使ってみましょう"},
                "setting":
                {"duration": 2000}
                }
    elif (3 < (datetime.datetime.now().second % 15) <= 6):
        share_text = ""
        df_freq_session = get_frequently_used_words(session=session_string)
        df_freq_session = remove_stopwords_entry(df=df_freq_session)
        df_freq_session = df_freq_session[(df_freq_session['count(vocab)'] >= 1) & (df_freq_session['level'] >= "B1")]
        if df_freq_session is not None:
            for index, row in df_freq_session.iterrows():
                share_text += row['vocab'] + ","
        share_text += "が使えています"
        data = {"notification":{"name": "いいね！",
                 "text": share_text},
                "setting":
                {"duration": 2000}
                }
    elif (6 < (datetime.datetime.now().second % 15) <= 15):

        df = vocab_calculate_all(session_string=session_string, db_type="past")
        # df_sum = get_stats_for_levels_db(session_string=session_string)
        vocab_result_save(df=df, db_target_name='vocab_aggregate')
        df = vocab_result_load(session=session_string)
        df_freq_session = get_frequently_used_words(session=session_string)
        df_freq_session = remove_stopwords_entry(df=df_freq_session)
        df_freq_session = df_freq_session[(df_freq_session['count(vocab)'] >= 1) & (df_freq_session['level'] >= "B1")]
        df = df[df['vocab'].isin(df_freq_session['vocab'])]
        list_responses = suggest_words(target_level_equal_and_above="B1", df=df)
        if len(list_responses) != 0:
            list_suggestion_rel = extract_words_from_response(list_responses, "syn_list")
            df_suggestion_rel = pd.DataFrame([[wp[0], wp[1], a, b, l] for wp, a, b, l in list_suggestion_rel],
                                         columns=['vocab', 'pos', 'suggestion', 'definition', 'level'])
        else:
            df_suggestion_rel = None
        share_text = '<br>'
        share_text += '<div style="font-size:16px;display:inline-block;border: 1px solid #333333;">'
        share_text += f'<span style="width:64px;display:inline-block" class="head">word</span>' \
                      f'<span style="width:128px;display:inline-block" class="head">suggestion</span>' \
                      f'<span style="width:64px;display:inline-block" class="head">level</span>' \
                      f'<span style="width:70%;display:inline-block" class="head">definition</span>' \
                      f'</div>'

        if df_suggestion_rel is not None:
            df_suggestion_rel_top10 = df_suggestion_rel[0:5]
            df_suggestion_rel_top10.sort_values(['level','vocab'],inplace=True, ascending=[False,True])
            for index, row in df_suggestion_rel_top10.iterrows():
                row['definition'][1] = str(row['definition'][1]).replace("{it}","<i>")
                row['definition'][1] = str(row['definition'][1]).replace("{/it}","</i>")
                share_text += '<div style="font-size:16px;display:inline-block;border: 1px solid #333333;">'
                share_text += f'<span style="width:64px;font-size:16px;display:inline-block;word-wrap: break-word;" class="item">{row["vocab"]}</span>' \
                              f'<span style="width:128px;font-size:24px;display:inline-block;word-wrap: break-word;" class="item">{row["suggestion"]}</span>' \
                              f'<span style="width:64px;font-size:16px;display:inline-block" class="item">{row["level"]}</span>' \
                              f'<span style="width:70%;font-size:16px;display:inline-block" class="item">{row["definition"]}</span>'
                share_text += '</div>'


        data = {"notification":{"name": "使ってみて",
                 "text": share_text },
                "setting":
                {"duration": 8000}
                }

    return jsonify(data)

@app.route('/show',methods=['POST','GET'])
def return_stat_result():
    data = request.get_data().decode('utf-8')
    data_json = json.loads(data)
    # print("show ",data_json)
    if len(data_json['username']) == 0:
        data = [{"name": "no data exists from Meet",
                 "duration": 0}]
        return jsonify( data)
    session_string = data_json['transcriptId']
    username = data_json['username']
    print("username:",username)

    if (datetime.datetime.now().second % 15) <= 3:
        dbname = DB_NAME
        conn = sqlite3.connect(dbname)
        df = pd.read_sql("SELECT * FROM caption where session = '" + session_string + "'", conn)
        if len(df) == 0:
            data = [{"name": f"no data exists for session {session_string}",
                     "duration": 0}]
            return jsonify( data)
        df.columns = ['id','session','start','end','actor','text','actor_ip']
        # print("df end",df['end'])
        df['start'] = pd.to_datetime(df['start'],format="%Y-%m-%d %H:%M:%S.%f")
        df['end'] = pd.to_datetime(df['end'],format="%Y-%m-%d %H:%M:%S.%f")
        df['dif'] = df['end'] - df['start']

        sum_df = df.groupby('actor').agg({'dif':'sum'})
        sum_df =pd.DataFrame( sum_df.reset_index())
        sum_df['dif'] = sum_df['dif'].apply(datetime.timedelta.total_seconds)
        sum_df.columns= ['name','duration']
        sum_df['share'] = sum_df['duration'] / sum_df['duration'].sum() * 100
        sum_df['share'].fillna(0,inplace=True)
        sum_df['share'] = sum_df['share'].astype(int)

        last_clocktime = df['end'].max()
        last_clocktime = last_clocktime - datetime.timedelta(minutes=5)
        df_5 = df[df['end'] > last_clocktime]
        sum_df_5 = df_5.groupby('actor').agg({'dif':'sum'})
        sum_df_5 =pd.DataFrame( sum_df_5.reset_index())
        sum_df_5['dif'] = sum_df_5['dif'].apply(datetime.timedelta.total_seconds)
        sum_df_5.columns= ['name','duration']
        sum_df_5['share_5'] = sum_df_5['duration'] / sum_df_5['duration'].sum() * 100
        sum_df_5['share_5'].fillna(0,inplace=True)
        sum_df_5['share_5'] = sum_df_5['share_5'].astype(int)
        sum_all = pd.merge(sum_df, sum_df_5, on='name',how="outer")
        sum_all['share_5'].fillna(0,inplace=True)
        sum_all['share'].fillna(0,inplace=True)
        data = sum_all.to_json(orient="records")

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
        # print(share_text)
        data = [{"name": share_text,
                 "duration": "Turn taking"}]
        data = jsonify(data)

    elif 3 < (datetime.datetime.now().second % 15) < 8:
        # data = [{"name": "stat result",
        #          "duration": 10}]
        # data = jsonify(data)
        dbname = DB_NAME
        conn = sqlite3.connect(dbname)
        df = pd.read_sql("SELECT * FROM caption_sub where session = '" + session_string + "'", conn)
        if len(df) == 0:
            data = [{"name": f"no data exists for session {session_string}",
                     "duration": 0}]
            return jsonify( data)
        df.columns = ['id','session','start','substart','end','actor','text']
        df['substart'] = pd.to_datetime(df['substart'],format="%Y-%m-%d %H:%M:%S.%f")
        df['end'] = pd.to_datetime(df['end'],format="%Y-%m-%d %H:%M:%S.%f")
        df['dif'] = df['end'] - df['substart']
        df['word_count'] = df['text'].apply(str.split).apply(len)
        df['wps'] = df['word_count'] / df['dif'].dt.seconds
        df['wps'].fillna(0,inplace=True)
        df.sort_values(['substart'],ascending=[False],inplace=True)

        data = df.to_json(orient="records")

        share_text = ''
        share_text += '<div style="font-size:24px;">'
        share_text += f'<span style="width:64px;font-size:12px;" class="head">clock</span>' \
                      f'<span style="width:24px;font-size:12px;" class="head">sec</span>' \
                      f'<span style="width:24px;font-size:12px;"  class="head">words</span>' \
                      f'<span style="width:50px;font-size:12px;"  class="head">wps.</span>' \
                      f'<span style="width:100px;font-size:12px;"  class="head">text</span>' \
                      f'</div>'
        for index, row in df[0:20:].iterrows():
            share_text += '<div style="font-size:24px;">'
            share_text += f'<span style="width:64px;font-size:12px;" class="item">{row["substart"].strftime("%M:%S")}</span>' \
                          f'<span style="width:24px;font-size:12px;" class="item">{row["dif"].seconds}</span>' \
                          f'<span style="width:24px;font-size:12px;" class="item">{row["word_count"]}</span>'
            item_type = ""
            item_fontsize = "12"
            if row["wps"] < 0.4:
                item_type = "item_red"
                item_fontsize = "24"
            else:
                item_type = "item"
            share_text += f'<span style="width:50px;font-size:{item_fontsize}px;" class="{item_type}">{format(row["wps"],".2f")}</span>'
            share_text += f'<span style="width:100px;font-size:12px;" class="{item_type}">{str.lower(row["text"][0:26])}</span>'
            share_text += '</div>'
        # print(share_text)
        data = [{"name": share_text,
                 "duration": "Word per second"}]
        data = jsonify(data)
    elif 8 < (datetime.datetime.now().second % 15) < 12:
        df = vocab_calculate_all(session_string=session_string, db_type="past")
        df_sum = get_stats_for_levels_db(session_string=session_string)
        vocab_result_save(df=df, db_target_name='vocab_aggregate')
        df = vocab_result_load(session=session_string)
        df_freq_session = get_frequently_used_words(session=session_string)
        df_freq_session = remove_stopwords_entry(df=df_freq_session)
        # df_freq_session = df_freq_session[(df_freq_session['count(vocab)'] > 1) & (df_freq_session['level'] >= "B1")]
        # count(vocab), vocab, start, session, level
        df_freq_session.sort_values(['level','count(vocab)'],ascending=[False,True],inplace=True)
        share_text = '<br>'
        share_text += '<div style="font-size:16px;display:inline-block;border: 1px solid #333333;height:24px;">'
        share_text += f'<span style="width:120p;display:inline-block" class="head">word</span>' \
                      f'<span style="width:82px;display:inline-block" class="head">level</span>' \
                      f'<span style="width:24px;display:inline-block" class="head">frequency</span>' \
                      f'</div>'

        for index, row in df_freq_session[0:30].iterrows():
            share_text += '<div style="font-size:16px;display:inline-block;border: 1px solid #333333;height:12px;margin:0;line-height:12px;padding:0px;">'
            share_text += f'<span style="width:120px;font-size:16px;display:inline-block;word-wrap: break-word;height:12px;margin:0;padding:0px;">{row["vocab"]}</span>' \
                          f'<span style="width:82px;font-size:16px;display:inline-block;height:12px;margin:0;padding:0px;">{row["level"]}</span>' \
                          f'<span style="width:24px;font-size:16px;display:inline-block;height:12px;margin:0;padding:0px;">{row["count(vocab)"]}</span>'
            share_text += '</div>'

        share_text += "</div>"
        data = [{"name": share_text,
                 "duration": "Frequency"}]
        data = jsonify(data)


    else:
        data_json = [{}]
        data_json[0]['title'] = ''
        data_json[0]['title'] += '<div><span class="text_head">vocab.</span></div>'
        data_json[0]['title'] += '<div><span class="text_item">[X]Successive</span></div>'
        data_json[0]['title'] += '<div><span class="text_item">[ ]Following</span></div>'
        data_json[0]['title2'] = ''
        data_json[0]['title2'] += '<div><span class="text_item">Activate those vocab.</span></div>'
        # print("data_json:",data_json)
        data = jsonify(data_json)
        # print("data:",data)


    if data == "[]":
        data = [{"name": "stat result",
                 "duration": "No data:"}]
        data = jsonify(data)
    # print(data)
    return data

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
    conn.commit()
    conn.close()

if __name__ == "__main__":

    arguments = docopt(__doc__, version="0.1")

    host = arguments["<host>"]
    port = int(arguments["<port>"])
    create_db()
    # insert_db()
    # check_table()
    if port == 443:
        app.run(debug=False, host=host, port=int(port), ssl_context=('cert.pem','key.pem'))
    else:
        app.run(debug=False, host=host, port=int(port))