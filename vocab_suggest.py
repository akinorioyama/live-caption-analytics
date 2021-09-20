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
     "P": "n", "S": "n", "T": "n", "U": "n", "W": "n", ",": "n", ".": "n","(": "n",")": "n"})

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
        'start	DATETIME(6),'
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

    df = pd.read_sql("select actor, level, vocab, start from vocab_aggregate where session = '" + session + "'",
                     conn)

    conn.close()

    return df



def vocab_calculate_all(session_string="",include_last_record=False,since_last_update = None):
                        # only_last_record_for_current=False, # removed part of since_last_update


    dbname = DB_NAME
    conn = sqlite3.connect(dbname)
    columns = ['id', 'session', 'start', 'end', 'actor', 'text']
    max_start = None
    max_processed_vocab_start = None

    if since_last_update == True:
        df_vocab_max = pd.read_sql("SELECT max(start) FROM vocab_aggregate " + \
                             " where session = '" + session_string + "'", conn)
        max_processed_vocab_start = df_vocab_max['max(start)'].values[0]

    kwargs = []

    df_max = pd.read_sql("SELECT max(start) FROM caption " + \
                         " where session = '" + session_string + "'", conn)
    max_start = df_max['max(start)'].values[0]

    if session_string is not None:
        # if session_string == "%":
        #     kwargs.append(['session',session_string, "like"])
        # else:
        kwargs.append(['session', session_string, "="])
    # TODO: potential parallel updates...
    #  need a mehanism to exclude the latest ones where caption is still being updated
    if include_last_record == False:
        if max_start is not None:
            item = ["start",max_start, "<"]
            kwargs.append(item)

    if since_last_update == True:
        if max_processed_vocab_start is not None:
            item = ["start",max_processed_vocab_start, ">"]
            kwargs.append(item)
    elif since_last_update == False:
        if max_processed_vocab_start is not None:
            item = ["start", max_processed_vocab_start, "<="]
            kwargs.append(item)
    if len(kwargs) == 0:
        where_clause = ""
    else:
        where_clause = 'WHERE ' + ' AND '.join(
            [k[0] + ' %s "%s"' % (k[2], k[1]) for k in kwargs])

    print("read caption with where:", where_clause)
    df = pd.read_sql("SELECT " + str.join(",", columns) + \
                     " FROM caption " + \
                     where_clause,
                     conn)

    df.columns = columns
    df['start'] = pd.to_datetime(df['start'], format="%Y-%m-%d %H:%M:%S.%f")
    df['end'] = pd.to_datetime(df['end'], format="%Y-%m-%d %H:%M:%S.%f")
    df['text'] = df['text'].str.lower()

    if len(df) == 0:
        return None

    df_new = pd.DataFrame(columns = ['session','start','vocab','category','level','actor',])
    # error
    # (0, ['aki', 'aki', '(', 'you', ')', 'aki', 'aki'])
    try:
        # df['text_stemmed'] = df['text'].apply(word_tokenize).apply(lambda x: [[word_and_tag[0],word_and_tag[1],wnl.lemmatize(word_and_tag[0],pos=word_and_tag[1][0].translate( translate_mapping ))] for word_and_tag in pos_tag(x)])
        l_all_entries = []
        tokenized_df = df['text'].apply(word_tokenize)
        word_and_tag = tokenized_df.apply(lambda x: [[word_and_tag[0],word_and_tag[1]] for word_and_tag in pos_tag(x)])
        for w_t_set in word_and_tag:
            l_entries = []
            for w_t_item in w_t_set:
                if w_t_item[1][0] == "'":
                    continue
                if w_t_item[1][0] == ".":
                    continue
                try:
                    an_entry = wnl.lemmatize(w_t_item[0],pos=w_t_item[1][0].translate( translate_mapping ))
                    l_entries.append([w_t_item[0],w_t_item[1],an_entry])
                except KeyError as e:
                    print("KeyError at vocab_create_all", e)
            l_all_entries.append(l_entries)
        df['text_stemmed'] = l_all_entries
    except Exception as e:
        print("Exception at creating text_stemmed",e,df['text'])

    for index, row in df.iterrows():
        for line in row['text_stemmed']:
            if line[2] in stop_words:
                continue
            if ',' in line[2]:
                continue
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
            else:
                tmp_se = pd.Series([
                    row['session'],
                    row['start'],
                    line[2],
                    'CEFRJ',
                    'NA',
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
    word_and_pos_list = []
    target_list  = []
    dt_list = []
    level_list = []
    for list_response in list_responses:
        response = json.loads(list_response)
        for entry_in_response in response:
            if ('meta' in entry_in_response) == False:
                continue
            id = entry_in_response['meta']['id']
            if ('hwi' in entry_in_response) == False:
                continue
            hwi_hw = entry_in_response['hwi']['hw']
            if ('fl' in entry_in_response) == False:
                continue
            fl = entry_in_response['fl']
            # syns/ants/offensive
            for entry_in_sseq in entry_in_response['def'][0]['sseq']:
                if (list_type in entry_in_sseq[0][1]) == False:
                    continue
                if ('dt' in entry_in_sseq[0][1]) == True:
                    dt_item = entry_in_sseq[0][1]['dt']
                for list_type_entry in entry_in_sseq[0][1][list_type]:
                    for wd_in_entry in list_type_entry:
                        if 'wd' in wd_in_entry:
                            wd_item = wd_in_entry['wd']
                            if wd_item in dict_cefr_level:
                                level = dict_cefr_level[wd_item]
                            else:
                                level = "NA"
                            word_and_pos_list.append([id,fl])
                            target_list.append(wd_item)
                            dt_list.append(dt_item)
                            level_list.append(level)
                        else:
                            print(wd_in_entry)
    return_list = zip(word_and_pos_list,target_list,dt_list,level_list)
    #
    # pre_extract_list = [[[line] for line in json.loads(list_response) if ('meta' in line) for keyword in [list_type]] for list_response in
    #  list_responses if
    #  len([[line] for line in json.loads(list_response) if ('meta' in line) for keyword in [list_type]]) != 0]
    # pre_extract_list = [[[line] for line in json.loads(list_response) if ('meta' in line) for keyword in [list_type]] for list_response in
    #  list_responses if
    #  len([[line] for line in json.loads(list_response) if ('meta' in line) for keyword in [list_type]]) != 0].copy()
    # import itertools
    # flatten_extract_list = list(itertools.chain.from_iterable([[line for line in list_response] for list_response in pre_extract_list]))
    # # [x for line in flatten_extract_list for x in line for y in x]
    # # [entry for line in pre_extract_list for entry in line]
    # extracted_list = [[[[line['hwi']['hw'], line['fl'], line['def'][0]['sseq'][0][0][1]] for line in list_response if
    #   keyword in line['def'][0]['sseq'][0][0][1]] for keyword in [list_type]] for list_response in pre_extract_list]
    # # [[list_response[0]['hwi']['hw'], list_response[0]['def'], list_response[0]['def'][0]['sseq']] for list_response in
    # #  flatten_extract_list if ('hwi' in list_response[0].keys())]
    # # extracted_list = [[[[line['hwi']['hw'], line['fl'], line['def'][0]['sseq'][0][0][1]] for line in json.loads(list_response) if
    # #   keyword in line['def'][0]['sseq'][0][0][1]] for keyword in [list_type]] for list_response in list_responses]
    # target_list =[item[0][0][2][list_type][0][0]['wd'] for item in [ext_list for ext_list in extracted_list] if len(item[0]) >= 1]  # item[0] to avoid blank lines
    # dt_list =[item[0][0][2]['dt'] for item in [ext_list for ext_list in extracted_list] if len(item[0]) >= 1]                       # item[0] to avoid blank lines
    # word_and_pos_list = [[item[0][0][0], item[0][0][1]] for item in [ext_list for ext_list in extracted_list] if len(item[0]) >= 1] # item[0] to avoid blank lines
    # level_list = [dict_cefr_level[item[0][0][0]] if item[0][0][0] in dict_cefr_level else 'NA' for item in extracted_list if len(item[0]) >= 1]  # item[0] to avoid blank lines
    # return_list = zip(word_and_pos_list,target_list,dt_list,level_list)
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
            word = word.replace("'","")
            df_single_word_reference = pd.read_sql("SELECT * from merriam_data where word = '" + word + "'", conn)
            if len(df_single_word_reference) != 0:
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
        if session == "%":
            kwargs['session'] = [session, "LIKE"]
        else:
            kwargs['session'] = [session,"="]
    if actor is not None:
        kwargs['actor'] = [actor,"="]
    if start is not None:
        kwargs['start'] = [start.strftime("%Y-%m-%d %H:%M:%S.%f"),">="]
    if len(kwargs) == 0:
        where_clause = ""
    else:
        where_clause = 'WHERE ' + ' AND '.join([k + ' %s "%s"' % (kwargs[k][1],kwargs[k][0]) for k in kwargs.keys()])

    sql_string = \
        'select count(vocab), vocab,actor, session, level from vocab_aggregate ' + \
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
    # dbname = DB_NAME
    # conn = sqlite3.connect(dbname)
    #
    # df_end_max = pd.read_sql("SELECT max(end) FROM caption where " + \
    #                               " session = '" + session + "'"
    #                               , conn)
    # conn.commit()
    # conn.close()
    #
    # if df_end_max is not None:
    #     last_processed_time = pd.to_datetime(df_end_max['max(end)'])[0].to_pydatetime()
    #     if ((last_processed_time + datetime.timedelta(minutes=2)) < datetime.datetime.now()):
    #         print("updated due to max elapsed time")
    #         df = vocab_calculate_all(session_string=session, since_last_update=True, include_last_record=True)
    #         vocab_result_save(df=df, db_target_name="vocab_aggregate")

    session_start = datetime.datetime(2020,9,10,0,0,0)
    session_start_string = session_start.strftime("%Y-%m-%d %H:%M:%S.%f")
    dbname = DB_NAME
    conn = sqlite3.connect(dbname)

    df_session_list = pd.read_sql("SELECT distinct session FROM caption where " + \
                                  " start >= '" + session_start_string + "'"
                                  , conn)
    conn.commit()
    conn.close()

    for index, session_item in df_session_list.iterrows():
        session = session_item['session']
        print(f"Processing session:{session}")
        df = vocab_calculate_all(session_string = session, include_last_record=True)
        df_sum = get_stats_for_levels_db(session_string=session)
        vocab_result_save(df=df, db_target_name ='vocab_aggregate')
    import sys
    sys.exit(1)
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
