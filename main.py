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
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
CORS(app)

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
    date_string = (datetime.datetime.fromisoformat(date_string_iso.split(".")[0]) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    session_id  = data_json['transcriptId']

    dbname = 'TEST.db'
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
    print("username:",username)

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
    df['start'] = pd.to_datetime(df['dateStart'].str[:19]) + datetime.timedelta(hours=9)
    df['end'] = pd.to_datetime(df['dateEnd'].str[:19]) + datetime.timedelta(hours=9)
    df['dif'] = df['end'] - df['start']
    df['session'] = session_string
    # print("df in /",df)
    # print(df.columns)
    df.drop(['dateStart','dateEnd','dif'],axis=1, inplace=True)
    # df.drop(['time','timeEnd','year','month','day','hour','min','sec',
    #               'yearend', 'monthend', 'dayend', 'hourend', 'minend', 'secend','dif'
    #               ],axis=1,inplace=True)
    # print(df.columns)
    df.columns=['actor','text','start','end','session']
    # print("df in / after",df)
    dbname = 'TEST.db'
    conn = sqlite3.connect(dbname)
    df_existing = pd.read_sql("SELECT * FROM caption where session = '" + session_string + "'", conn)
    df_existing['start'] = pd.to_datetime(df_existing['start'],format="%Y-%m-%d %H:%M:%S")
    df_existing['end'] = pd.to_datetime(df_existing['end'],format="%Y-%m-%d %H:%M:%S")

    df_to_add = df[-(df['start'].isin(df_existing['start']) & df['end'].isin(df_existing['end']) & df['actor'].isin(df_existing['actor']) & df['session'].isin(df_existing['session']))]
    # df_to_delete = df[(df['start'].isin(df_existing['start']) & df['actor'].isin(df_existing['actor']) & df['session'].isin(df_existing['session']))]
    for index, row in df_to_add.iterrows():
        # print("delete:",row['session'],row['actor'],row['start'])
        conn.execute("DELETE FROM caption where " + \
                     "actor = '" + row['actor'] + "' and " + \
                     "start = '" + datetime.datetime.strftime(row['start'],"%Y-%m-%d %H:%M:%S") + "' and " + \
                     "session = '" + row['session'] + "'")
    df_to_add.to_sql('caption',conn,if_exists='append',index=False)
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
    print("username:",username)

    data = {"notification": {},
            "setting":{"duration": 2000}
            }
    if (datetime.datetime.now().second % 15) < 5:
        data = {"notification":{"name": "ヒント:",
                 "text": "他の表現も使ってみましょう"},
                "setting":
                {"duration": 2000}
                }
    elif (6 < (datetime.datetime.now().second % 15) < 10):
        data = {"notification":{"name": "いいね！",
                 "text": "<br>successive が使えましたね"},
                "setting":
                {"duration": 5000}
                }

    # print(data)
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
    dbname = 'TEST.db'
    conn = sqlite3.connect(dbname)
    df = pd.read_sql("SELECT * FROM caption where session = '" + session_string + "'", conn)
    if len(df) == 0:
        data = [{"name": f"no data exists for session {session_string}",
                 "duration": 0}]
        return jsonify( data)
    df.columns = ['id','session','start','end','actor','text']
    # print("df end",df['end'])
    df['start'] = pd.to_datetime(df['start'],format="%Y-%m-%d %H:%M:%S")
    df['end'] = pd.to_datetime(df['end'],format="%Y-%m-%d %H:%M:%S")
    df['dif'] = df['end'] - df['start']

    sum_df = df.groupby('actor').agg({'dif':'sum'})
    sum_df =pd.DataFrame( sum_df.reset_index())
    sum_df['dif'] = sum_df['dif'].apply(datetime.timedelta.total_seconds)
    sum_df.columns= ['name','duration']
    sum_df['share'] = sum_df['duration'] / sum_df['duration'].sum() * 100
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

    if (datetime.datetime.now().second % 10) < 3:
        # data_json = json.loads(data)
        # print("data_json length",len(data_json))
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
    elif 6 < (datetime.datetime.now().second % 10) < 7:
        data = [{"name": "stat result",
                 "duration": 10}]
        data = jsonify(data)
    else:
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

    if data == "[]":
        data = [{"name": "stat result",
                 "duration": "No data:"}]
        data = jsonify(data)
    # print(data)
    return data

def check_table():

    dbname = 'TEST.db'
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    cur.execute('SELECT * FROM caption')

    print(cur.fetchall())
    conn.commit()
    conn.close()

def insert_db():

    dbname = 'TEST.db'
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    cur.execute("INSERT INTO caption ( start , end , actor , text ) values ( '2021/8/15 13:13:30','2021/8/15 13:15:30','aki','text'  )")

    conn.commit()
    conn.close()


def create_db():

    dbname = 'TEST.db'
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    # cur.execute('DROP TABLE caption')
    cur.execute(
        'CREATE TABLE IF NOT EXISTS caption(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'session VARCHAR(40),'
        'start DATETIME,'
        'end DATETIME, '
        'actor VARCHAR(30),'
        'text MESSAGE_TEXT )')

    conn.commit()

    cur.execute(
        'CREATE TABLE IF NOT EXISTS log(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'session VARCHAR(40),'
        'start DATETIME,'
        'actor VARCHAR(30),'
        'text MESSAGE_TEXT,'
        'logtype MESSAGE_TEXT )')

    conn.close()

if __name__ == "__main__":

    arguments = docopt(__doc__, version="0.1")

    host = arguments["<host>"]
    port = int(arguments["<port>"])

    create_db()
    # insert_db()
    # check_table()
    if port == "443":
        app.run(debug=False, host=host, port=int(port), ssl_context=('cert.pem','key.pem'))
    else:
        app.run(debug=False, host=host, port=int(port))