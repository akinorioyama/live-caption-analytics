import sqlite3

import pandas as pd
from nltk import word_tokenize
from nltk import download
from nltk import pos_tag
from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer as WNL
import requests
import json
import datetime
import configparser

config = configparser.ConfigParser()
config.read('../lca_config.ini', encoding='utf8')
key = config['connection.config.dictionary']['merriam_api']

download('stopwords')
download('wordnet')
download( 'punkt')
download( 'averaged_perceptron_tagger' )

translate_mapping = str.maketrans(
    {"J": "a", "V": "v", "N": "n", "R": "r", "C": "n", "D": "n", "E": "n", "F": "n", "I": "n", "L": "n", "M": "n",
     "P": "n", "S": "n", "T": "n", "U": "n", "W": "n", ",": "n", ".": "n"})

DB_NAME = "test.db"
loaded_vocab = pd.read_csv("CEFRJ_vocab.txt", delimiter="\t")
dict_cefr_level = {row['headword']: row['CEFR'] for index, row in loaded_vocab.iterrows()}

wnl = WNL()
stop_words = stopwords.words('english')


def create_db(db_file_name):

    dbname = db_file_name
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    cur.execute(
        'CREATE TABLE IF NOT EXISTS vocab_aggregate ( '
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'session	VARCHAR(40),'
        'start	DATETIME,'
        'vocab	VARCHAR(30),'
        'category	VARCHAR(10),'
        'level	VARCHAR(10),'
        'actor	VARCHAR(30)'
        ')'
    )
    cur.execute(
        'CREATE TABLE IF NOT EXISTS merriam_data ('
        'word	    TEXT,'
        'response	TEXT,'
        'synonym	TEXT,'
        'rel    	TEXT,'
        'sim	    TEXT,'
        'PRIMARY KEY("word")'
        ')'
    )
    conn.commit()
    conn.close()

def removeStopwords(wordlist, stopwords):
    return [w for w in wordlist if w not in stopwords]



def vocab_result_save(df, db_target_name = "vocab_aggregate"):

    if df is None:
        return False

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    df.to_sql(db_target_name, conn, if_exists='append', index=False)
    conn.commit()

    conn.close()

    return True

def vocab_result_load(session = ""):

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)

    df = pd.read_sql("select actor, level, vocab from vocab_aggregate where session = '" + session + "'",
                     conn)

    conn.close()

    return df



def vocab_calculate_all(session_string,db_type):

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    columns = ['id', 'session', 'start', 'end', 'actor', 'text']

    if db_type != "past":
        # current: build only with caption_sub for the latest caption
        # max start for the session to perform further search?
        df_max = pd.read_sql("SELECT max(start) FROM caption " + \
                             " where session = '" + session_string + "'", conn)
        max_start = df_max['max(start)'].values[0]

        df = pd.read_sql("SELECT " + str.join(",",columns) + \
                         " FROM caption_sub " + \
                         " where session = '" + session_string + "'" + \
                         " and start = '" + max_start + "'", conn)
        df.columns = columns
        df['start'] = pd.to_datetime(df['start'], format="%Y-%m-%d %H:%M:%S")
        df['end'] = pd.to_datetime(df['end'], format="%Y-%m-%d %H:%M:%S")
    else:
        # past
        # max start for the session to perform further search?
        df_max = pd.read_sql("SELECT max(start) FROM vocab_aggregate " + \
                             " where session = '" + session_string + "'", conn)
        max_start = df_max['max(start)'].values[0]
        if max_start is None:
            df = pd.read_sql("SELECT " + str.join(",", columns) + \
                             " FROM caption" + \
                             " where session = '" + session_string + "'",
                             conn)
            df = df[0:-1]
            #avoid processing the latest line because the latest line processing entails delta process for level mapping

        else:
            df = pd.read_sql("SELECT " + str.join(",",columns) + \
                             " FROM caption" + \
                             " where session = '" + session_string + "'" + \
                             " and start > '" + max_start + "'",
                             conn)
        df.columns = columns
        df['start'] = pd.to_datetime(df['start'], format="%Y-%m-%d %H:%M:%S")
        df['end'] = pd.to_datetime(df['end'], format="%Y-%m-%d %H:%M:%S")

    if len(df) == 0:
        return None

    df_new = pd.DataFrame(columns = ['session','start','vocab','category','level','actor',])

    df['text_stemmed'] = df['text'].apply(word_tokenize).apply(lambda x: [[word_and_tag[0],word_and_tag[1],wnl.lemmatize(word_and_tag[0],pos=word_and_tag[1][0].translate( translate_mapping ))] for word_and_tag in pos_tag(x)])

    for index, row in df.iterrows():
        for line in row['text_stemmed']:
            if line[2] in dict_cefr_level:
                tmp_se = pd.Series([
                    row['session'],
                    row['start'],
                    line[2],
                    'CEFRJ',
                    dict_cefr_level[line[2]],
                    row['actor']
                ], index=df_new.columns)
                df_new = df_new.append(tmp_se, ignore_index=True)

    return df_new

def get_stats_for_levels_df(df):

    # df_past_for_agg = pd.read_sql("SELECT * FROM vocab_aggregate where session = '" + session_string + "'", conn)
    sum_df = df.groupby(['actor','level']).agg({'level':'count'})
    sum_df['count'] =sum_df['level']
    sum_df.drop('level',axis=1,inplace=True)
    sum_df = pd.DataFrame( sum_df.reset_index())

    return sum_df

def get_stats_for_levels_db(session_string = ""):

    if session_string == "":
        return None

    dbname = DB_NAME
    conn = sqlite3.connect(dbname)

    df_past_for_agg = pd.read_sql("select actor, level, count() from vocab_aggregate where session = '" + session_string + "'" + \
                                  " group by actor ,level;"
                                  , conn)

    conn.close()

    return df_past_for_agg

def extract_words_from_response(list_responses = None,list_type="syn_list"):
    # list_type: ['rel_list', 'syn_list', 'sn', 'sim_list']
    extracted_list = [[[[line['hwi']['hw'], line['fl'], line['def'][0]['sseq'][0][0][1]] for line in json.loads(list_response) if
      keyword in line['def'][0]['sseq'][0][0][1]] for keyword in [list_type]] for list_response in list_responses]
    target_list =[item[0][0][2][list_type][0][0]['wd'] for item in [ext_list for ext_list in extracted_list] if len(item[0]) >= 1]  # item[0] to avoid blank lines
    dt_list =[item[0][0][2]['dt'] for item in [ext_list for ext_list in extracted_list] if len(item[0]) >= 1]                       # item[0] to avoid blank lines
    word_and_pos_list = [[item[0][0][0], item[0][0][1]] for item in [ext_list for ext_list in extracted_list] if len(item[0]) >= 1] # item[0] to avoid blank lines
    level_list = [dict_cefr_level[item[0][0][0]] if item[0][0][0] in dict_cefr_level else 'NA' for item in extracted_list if len(item[0]) >= 1]  # item[0] to avoid blank lines
    return_list = zip(word_and_pos_list,target_list,dt_list,level_list)
    return return_list

def suggest_words(target_level_equal_and_above = "C2",df = None, df_target_language = None):

    if df is None:
        return None
    max_read = 3
    df = df[df['level'] >= target_level_equal_and_above]
    # TODO: add original word and start time
    dbname = DB_NAME
    conn = sqlite3.connect(dbname)

    df_reference = pd.read_sql("SELECT word from merriam_data", conn)
    df_add_to_reference = pd.DataFrame(columns=['word','response'])
    list_synonym = []
    counter = 0

    for index, row in df.iterrows():
        if counter > max_read:
            break

        word = row['vocab']
        if word in df_add_to_reference['word'].values:
            list_synonym.append(df_add_to_reference[df_add_to_reference['word']==word]['response'].values[0])
        elif word in df_reference['word'].values:
            df_single_word_reference = pd.read_sql("SELECT * from merriam_data where word = '" + word + "'", conn)
            list_synonym.append(df_single_word_reference['response'].values[0])
        else:
            url = f'https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{word}?key={key}'
            response = requests.get(url)
            list_synonym.append(response.text)
            tmp_se = pd.Series([
                word,
                response.text ,
            ], index=df_add_to_reference.columns)
            df_add_to_reference = df_add_to_reference.append(tmp_se, ignore_index=True)
            counter += 1
    df_add_to_reference.to_sql("merriam_data" , conn, if_exists='append', index=False)
    conn.commit()
    conn.close()
    conn.close()

    return list_synonym

def get_frequently_used_words(session=None,actor=None,start:datetime=None):

    kwargs = {}
    if session is not None:
        kwargs['session'] = [session,"="]
    if actor is not None:
        kwargs['actor'] = [actor,"="]
    if start is not None:
        kwargs['start'] = [start.strftime("%Y-%m-%d %H:%M:%S"),">="]
    if len(kwargs) == 0:
        where_clause = ""
    else:
        where_clause = 'WHERE ' + ' AND '.join([k + ' %s "%s"' % (kwargs[k][1],kwargs[k][0]) for k in kwargs.keys()])

    sql_string = \
        'select count(vocab), vocab, start, session, level from vocab_aggregate ' + \
        where_clause + \
        ' group by vocab, actor, session order by count(vocab) desc'

    print(sql_string)
    dbname = DB_NAME
    conn = sqlite3.connect(dbname)

    df = pd.read_sql(sql_string, conn)

    conn.close()

    return df


def remove_stopwords_entry(df:pd.DataFrame=None):
    df = df[~df['vocab'].isin(stop_words)]
    return df

if __name__ == "__main__":

    create_db(db_file_name=DB_NAME)
    # TODO: identify the words that are repeatedly used by speaker (cross sessions and in a single session)
    # TODO: suggest words that are synonyms of the uttered words at or above certain profile level
    session = "your session name"
    df = vocab_calculate_all(session_string = session, db_type="past")
    df_sum = get_stats_for_levels_db(session_string=session)
    vocab_result_save(df=df, db_target_name ='vocab_aggregate')
    df = vocab_result_load(session=session)
    df_freq_session = get_frequently_used_words(session=session)
    # df = get_frequently_used_words(session=session,
    #                                start=datetime.datetime.strptime("2021-08-27 21:00:00", "%Y-%m-%d %H:%M:%S"))
    #sort df for the purpose - freq/practice?
    df_freq_session = df_freq_session[~df_freq_session['vocab'].isin(stop_words)]
    df_freq_session = df_freq_session[(df_freq_session['count(vocab)'] > 5) & (df_freq_session['level'] >= "B1")]
    df = df[df['vocab'].isin(df_freq_session['vocab'])]
    list_responses = suggest_words(target_level_equal_and_above="B1",df=df)
    list_suggestion_synonym = extract_words_from_response(list_responses,"syn_list")
    list_suggestion_rel = extract_words_from_response(list_responses,"rel_list")
    list_suggestion_sim = extract_words_from_response(list_responses,"sim_list")
    df_suggestion_synonym = pd.DataFrame([[wp[0],wp[1],a,b,l] for wp,a,b,l in list_suggestion_synonym], columns=['vocab', 'pos', 'suggestion', 'definition', 'level'])
    df_suggestion_rel = pd.DataFrame([[wp[0],wp[1],a,b,l] for wp,a,b,l in list_suggestion_rel], columns=['vocab', 'pos', 'suggestion', 'definition', 'level'])
    df_suggestion_sim = pd.DataFrame([[wp[0],wp[1],a,b,l] for wp,a,b,l in list_suggestion_sim], columns=['vocab', 'pos', 'suggestion', 'definition', 'level'])

    print(df_sum)
    # df_current = vocab_calculate_all(session_string = session, db_type="current")
    # df_sum = get_stats_for_levels_df(df = df_current)
    # list_responses = suggest_words(target_level_equal_and_above="A1",df=df_current)
    # df_suggestion = extract_words_from_response(list_responses,"syn_list")
    # print(df_sum)
