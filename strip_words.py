"""
get vocab

Usage:
  strip_words.py <host> <port>
  strip_words.py -h | --help
  strip_words.py --version

  <host>:
  <port>:

Examples:
  strip_words.py 0.0.0.0 443

Options:
  -h --help     Show this screen.
  --version     Show version.
"""
import datetime
import sqlite3
import os
import time

import numpy as np
from docopt import docopt

from flask import Flask, request, jsonify,json
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
import itertools
import pandas as pd
from nltk import word_tokenize
from nltk import download
from nltk import pos_tag
from nltk.corpus import stopwords
from nltk.corpus import wordnet
from os.path import exists
import sys
from nltk.stem.wordnet import WordNetLemmatizer as WNL
import urllib.parse
from flask import render_template

DB_NAME = "main.db"
DB_NAME_SITE = "site.db"

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
CORS(app)

loaded_vocab = pd.read_csv("CEFRJ_vocab.txt", delimiter="\t")
dict_cefr_level = {row['headword']: row['CEFR'] for index, row in loaded_vocab.iterrows()}
loaded_vocab_ngsl = pd.read_csv("NGSL+1.txt", delimiter="\t")
dict_ngsl_level = {row['Lemma']: index for index, row in loaded_vocab_ngsl.iterrows()}

wnl = WNL()
stop_words = stopwords.words('english')

import spacy
from spacy_wordnet.wordnet_annotator import WordnetAnnotator
from spacy.tokens import Token

# Load an spacy model (supported models are "es" and "en")
nlp = spacy.load('en_core_web_lg')

def get_site_text(url):

    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36'

    dcap = {
        "phantomjs.page.settings.userAgent": user_agent,
        'marionette': True
    }
    # driver = webdriver.PhantomJS(executable_path="D:/software/phantomjs-2.1.1-windows/bin/phantomjs.exe",desired_capabilities=dcap)
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(chrome_options=options)
    driver.get(url)
    # WebDriverWait(driver,10)
    time.sleep(10)
    html = driver.page_source.encode('utf-8')  # more sophisticated methods may be available
    driver.close()
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")


    texts = [p_element.text for p_element in soup.find_all('p')]
    title = soup.title.string
    return texts,title

def create_new_df_for_word_list(df:pd.DataFrame=None):

    translate_mapping = str.maketrans(
        {"J": "a", "V": "v", "N": "n", "R": "r", "C": "n", "D": "n", "E": "n", "F": "n", "I": "n", "L": "n",
         "M": "n",
         "P": "n", "S": "n", "T": "n", "U": "n", "W": "n", ",": "n", ".": "n",
         ":":"n","'":"n", ")":"n", "(":"n","`":"n","#":"n","$":"n"})

    df_new = pd.DataFrame(columns = ['vocab','category','level','NGSL'])

    try:
        l_all_entries = []
        tokenized_df = df['text'].str.lower()
        tokenized_df = tokenized_df.apply(word_tokenize)
        word_and_tag = tokenized_df.apply(lambda x: [[word_and_tag[0],word_and_tag[1]] for word_and_tag in pos_tag(x)])
        for w_t_set in word_and_tag:
            l_entries = []
            for w_t_item in w_t_set:
                if w_t_item[1][0] == "'":
                    continue
                if w_t_item[1][0] == ".":
                    continue
                an_entry = wnl.lemmatize(w_t_item[0],pos=w_t_item[1][0].translate( translate_mapping ))
                l_entries.append([w_t_item[0],w_t_item[1],an_entry])
            l_all_entries.append(l_entries)
        df['text_stemmed'] = l_all_entries
    except KeyError as e:
        print(e)
        pass
    except Exception as e:
        print(e)
        pass

    for index, row in df.iterrows():
        for line in row['text_stemmed']:
            if line[2] in dict_cefr_level:
                tmp_se = pd.Series([
                    line[2],
                    'CEFRJ',
                    dict_cefr_level[line[2]],
                    ''
                ], index=df_new.columns)
                df_new = df_new.append(tmp_se, ignore_index=True)
            else:
                tmp_se = pd.Series([
                    line[2],
                    'CEFRJ',
                    'NA',
                    ''
                ], index=df_new.columns)
                df_new = df_new.append(tmp_se, ignore_index=True)
            if line[2] in dict_ngsl_level:
                tmp_se = pd.Series([
                    line[2],
                    'NGSL',
                    '',
                    dict_ngsl_level[line[2]],
                ], index=df_new.columns)
                df_new = df_new.append(tmp_se, ignore_index=True)
            else:
                tmp_se = pd.Series([
                    line[2],
                    'NGSL',
                    '',
                    'NA',
                ], index=df_new.columns)
                df_new = df_new.append(tmp_se, ignore_index=True)

    return df_new


def get_domain_list():

    if exists('lookup_result.txt') == True:
        df_domain_list = pd.read_csv('lookup_result.txt')
    else:
        Token.set_extension('context', default=False, force=True)
        nlp.add_pipe(WordnetAnnotator('en'), after='tagger')
        token = nlp('prices')[0]
        token._.wordnet.wordnet_domains()
        domains = {}
        lines_vocab = []
        fh = open('wordnet domains/spacy-wordnet_source/wordnet_domains.txt', 'r')
        for line in fh:
            line = line.replace("\n", "")
            offset, domains = line.split('\t')
            line_domains = domains.split(" ")
            vocab_pair = [[offset[0:8] + offset[9:10], a] for a in line_domains]
            lines_vocab.extend(vocab_pair)
        df_domain_list = pd.DataFrame(lines_vocab)
        df_domain_list.columns = ['id', 'domain']
        df_domain_list = df_domain_list[df_domain_list['id'].str.len() == 9]
        df_temp = df_domain_list['id'][0:10].apply(lambda a: wordnet.of2ss(a).lemma_names()[0])
        df_domain_list['vocab'] = df_domain_list['id'].apply(lambda a: wordnet.of2ss(a).lemma_names()[0])

        # write a few times
        df_domain_list.to_csv('lookup_result.txt')

    return df_domain_list

def get_resource_list():
    dbname = DB_NAME_SITE
    conn = sqlite3.connect(dbname)
    df = pd.read_sql("SELECT id, url,title_of_site FROM site_text", conn)
    conn.close()
    if len(df) == 0:
        return None
    else:
        return df

def read_from_storage(url,id=None):

    dbname = DB_NAME_SITE
    conn = sqlite3.connect(dbname)
    if id is not None:
        df = pd.read_sql("SELECT url, text_in_json,title_of_site FROM site_text where id = '" + str(id) + "'", conn)
    else:
        url_text = urllib.parse.quote(url)
        df = pd.read_sql("SELECT url, text_in_json,title_of_site FROM site_text where url = '" + url_text + "'", conn)
    conn.close()
    if len(df) == 0:
        return None
    else:
        return df

def save_to_storage(url,raw_texts,title_text):

    dbname = DB_NAME_SITE
    conn = sqlite3.connect(dbname)
    json_text = json.dumps(raw_texts)
    df_insert = pd.DataFrame(columns=['url','text_in_json','title_of_site','time_retrieved'])
    url_text = urllib.parse.quote(url)
    tmp_se = pd.Series([
            url_text,
            json_text,
            title_text,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ], index=df_insert.columns)
    df_insert = df_insert.append(tmp_se, ignore_index=True)

    df_insert.to_sql('site_text',conn,if_exists='append', index=False)
    conn.close()

    df_insert.drop(['time_retrieved'],axis=1, inplace=True)

    return df_insert

# @app.route('/show_list',methods=['POST','GET'])
def show_text_from_url():
    data = request.get_data().decode('utf-8')
    url = request.form.get("url")
    df_site_text = read_from_storage(url)
    if df_site_text is None:
        texts,title = get_site_text(url)
        df_site_text = save_to_storage(url,texts,title)

    title_text = df_site_text['title_of_site'][0]
    df_site_text_json =  df_site_text['text_in_json'][0]
    text = json.loads(df_site_text_json)
    df = pd.DataFrame(text)
    df.columns=['text']
    df_new = create_new_df_for_word_list(df)

    df_new['NGSL'] = pd.Series( [ dict_ngsl_level[a] if (a in dict_ngsl_level) else "" for a in df_new['vocab'] ])

    df_new.drop_duplicates(subset=['vocab'],inplace=True)

    df_list_c1 = df_new.sort_values(['level'], ascending=False)[df_new['level'] >= "C1"]
    df_list_b1 = df_new.sort_values(['level'], ascending=False)[df_new['level'] >= "B1"]
    df_list_all = df_new.sort_values(['level'], ascending=False)[0:100]

    if len(df_list_c1) == 0:
        vocab_string = json.dumps({"vocab": list(df_list_b1['vocab'].values)})
        if len(df_list_b1) == 0:
            vocab_string = json.dumps({"vocab": list(df_list_all['vocab'].values)})
    else:
        vocab_string = json.dumps({"vocab": list(df_list_c1['vocab'].values )})
    vocab_count = 0
    if len(df_list_c1) != 0:
        vocab_count = len(df_list_c1)
    kwargs = {"df_list_c1" : df_list_c1, "df_list_b1" : df_list_b1, "df_list_all": df_list_all,
              "vocab_string": vocab_string, "url":url,
              "title": title_text, "vocab_count":vocab_count}

    text = render_template('get_vocab_list_result.html',**kwargs )
    # text = render_template('get_vocab_list_result.html',df_list_c1 = df_list_c1)

    return text

# @app.route('/get_vocab', methods=['POST', 'GET'])
# def get_vocabs():
#
#     text = render_template('get_vocab_list.html')
#
#     return text

# @app.route('/personalize_session_settings', methods=['POST', 'GET'])
def personalize_for_session_settings(session_string:str="",email_part:str=""):

    data = request.get_data().decode('utf-8')
    text_to_avoid = request.form.get("text_to_avoid",None)
    text_to_suggest_alternatives = request.form.get("text_to_suggest_alternatives",None)
    vocab_to_cover = request.form.get("vocab_to_cover",None)
    # session_string_str = request.form.get("session_id",None)
    username = request.form.get("username",None)

    kwargs = {}
    for a in request.form.keys():
        kwargs[a] =request.form.get(a)

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
            if text_to_avoid == "":
                if len(df_session_vocab_to_avoid) != 0:
                    kwargs['text_to_avoid'] = ",".join(df_session_vocab_to_avoid['value'])
            else:
                kwargs['text_to_avoid'] = text_to_avoid
            if text_to_suggest_alternatives == "":
                if len(df_session_vocab_to_suggest) != 0:
                    kwargs['text_to_suggest_alternatives'] = ",".join(df_session_vocab_to_suggest['value'])
            else:
                kwargs['text_to_suggest_alternatives'] = text_to_suggest_alternatives
            if vocab_to_cover == "":
                if len(df_session_vocab_to_cover) != 0:
                    kwargs['vocab_to_cover'] = ",".join(df_session_vocab_to_cover['value'])
            else:
                kwargs['vocab_to_cover'] = vocab_to_cover
    kwargs["email"]= email_part
    button_command_value = request.form.get("command",None)
    if button_command_value == "save"  and session_string is not None:
        print("save words to db!!")
        conn = sqlite3.connect(DB_NAME)
        user_to_update_db = username
        if user_to_update_db == "":
            user_to_update_db = "all"

        for key in ['vocab_to_cover','vocab_to_suggest','vocab_to_avoid']:
            sql_string = 'DELETE FROM session_settings where session = "' + session_string + '"' + \
                         ' and key = "' + key + '"' + \
                         ' and actor = "' + user_to_update_db + '"'
            conn.execute(sql_string)
        conn.commit()
        # add entries
        if vocab_to_cover != "":
            df_session_vocab_to_cover = pd.DataFrame(vocab_to_cover.split(","))
            df_session_vocab_to_cover.columns = ['value']
            df_session_vocab_to_cover['session'] = session_string
            df_session_vocab_to_cover['actor'] = user_to_update_db
            df_session_vocab_to_cover['key'] = "vocab_to_cover"
            df_session_vocab_to_cover.to_sql('session_settings', conn, if_exists='append', index=False)
        if text_to_avoid != "":
            df_session_vocab_to_avoid = pd.DataFrame(text_to_avoid.split(","))
            df_session_vocab_to_avoid.columns = ['value']
            df_session_vocab_to_avoid['session'] = session_string
            df_session_vocab_to_avoid['actor'] = user_to_update_db
            df_session_vocab_to_avoid['key'] = "vocab_to_avoid"
            df_session_vocab_to_avoid.to_sql('session_settings', conn, if_exists='append', index=False)
        if text_to_suggest_alternatives != "":
            df_session_vocab_to_suggest = pd.DataFrame(text_to_suggest_alternatives.split(","))
            df_session_vocab_to_suggest.columns = ['value']
            df_session_vocab_to_suggest['session'] = session_string
            df_session_vocab_to_suggest['actor'] = user_to_update_db
            df_session_vocab_to_suggest['key'] = "vocab_to_suggest"
            df_session_vocab_to_suggest.to_sql('session_settings', conn, if_exists='append', index=False)
        conn.commit()
        conn.close()
    text = render_template('personalize_session_settings.html', **kwargs)
    return text

# @app.route('/personalize_session', methods=['POST', 'GET'])
def personalize_for_session_vocab(session_string:str="",email_part:str=""):

    data = request.get_data().decode('utf-8')
    text_to_be_parsed = request.form.get('text_to_parse',"")
    outside_form_value = "calculated result"
    kwargs = {"outside_form": outside_form_value }

    df_resource_list = get_resource_list()
    df_resource_list['id_checked'] = ""
    button_command_value = request.form.get("command",None)
    # session_string_str = request.form.get("session_id",None)

    # google_userid, google_part_of_email = get_user_id_from_session()
    # session_id = get_sessionid(session_string=session_string_str,owner=google_userid)
    # session_string = session_id

    target_cefr_level = request.form.get("CEFR_equal_or_above",None)
    NGSL_equal_or_above = request.form.get("NGSL_equal_or_above",None)
    NGSL_equal_or_below = request.form.get("NGSL_equal_or_below",None)
    domain_list = request.form.get("domains",None)
    for a in request.form.keys():
        kwargs[a] =request.form.get(a)
    if request.form.get('alert_overused_words',None) == "1":
        kwargs['alert_overused_words'] = "checked"
    if request.form.get('suggest_alternatives_for_overused_words',None) == "1":
        kwargs['suggest_alternatives_for_overused_words'] = "checked"
    for a in request.form.getlist("resource_list"):
        df_resource_list.iloc[
            df_resource_list[df_resource_list['id'] == int(a)].index, df_resource_list.columns.get_loc('id_checked')] = "checked"

    df_new = None
    df_new_domain = None
    for index, row in df_resource_list.iterrows():
        if row['id_checked'] != "checked":
            continue
        df_site_text = read_from_storage(None, row['id'])
        df_site_text_json =  df_site_text['text_in_json'][0]
        text = json.loads(df_site_text_json)
        df = pd.DataFrame(text)
        df.columns=['text']
        if df_new is None:
            df_new = create_new_df_for_word_list(df)
        else:
            df_to_add = create_new_df_for_word_list(df)
            df_new = pd.concat([df_new,df_to_add])

    if text_to_be_parsed != "":
        df = pd.DataFrame([text_to_be_parsed])
        df.columns=['text']
        if df_new is None:
            df_new = create_new_df_for_word_list(df)
        else:
            df_to_add = create_new_df_for_word_list(df)
            df_new = pd.concat([df_new,df_to_add])

    if df_new is None:
        kwargs['df_resource_list'] = df_resource_list
        kwargs["df_list_c1"] = pd.DataFrame()
        vocab_string = ""
        kwargs["outside_form"] = vocab_string
        kwargs['text_to_be_parsed'] = text_to_be_parsed
        kwargs["email"] = email_part
        text = render_template('personalize_vocab.html', **kwargs)
        return text

    df_resource_vocab = df_new.copy()
    df_resource_vocab.drop_duplicates(subset=['vocab'],inplace=True)
    # df_resource_vocab.sort_values(['level'], ascending=False,inplace=True)
    if target_cefr_level is not None:
        df_list = df_resource_vocab[df_resource_vocab['level'] >= target_cefr_level]
    else:
        df_list = df_resource_vocab.copy()
    #     df_list = df_resource_vocab[df_resource_vocab['level'] >= "C1"]
    import sys
    df_list.reset_index(inplace=True)
    df_list['NGSL'] = pd.Series( [ dict_ngsl_level[a] if (a in dict_ngsl_level) else sys.maxsize for a in df_list['vocab'] ])
    # df_list['NGSL'] = pd.Series([dict_ngsl_level[a['vocab']] if (a['vocab'] in dict_ngsl_level) else sys.maxsize for index, a in df_list.iterrows()] )
    if NGSL_equal_or_above is not None and NGSL_equal_or_below is not None:
        if NGSL_equal_or_above == "":
            NGSL_equal_or_above = 0
        if NGSL_equal_or_below == "":
            NGSL_equal_or_below = 20000
        df_list = df_list[(df_list['NGSL'].astype(int) >= int(NGSL_equal_or_above)) & (df_list['NGSL'].astype(int) <= int(NGSL_equal_or_below)) ]


    if domain_list is not None:
        if domain_list != "":
            df_domain_list = get_domain_list()
            df_domain_list.drop_duplicates(subset=['vocab','domain'],inplace=True)
            df_domain_list_domain = df_domain_list[(df_domain_list['domain'].isin(str(domain_list).split(",")))]
            df_list = df_list[df_list['vocab'].isin(df_domain_list_domain['vocab'])]
            df_list['domain'] = [",".join(list(df_domain_list_domain[df_domain_list_domain['vocab'] == a]['domain'])) for a in df_list['vocab']]
        else:
            df_domain_list = get_domain_list()
            df_domain_list.drop_duplicates(subset=['vocab','domain'],inplace=True)
            df_list['domain'] = [",".join(list(df_domain_list[df_domain_list['vocab'] == a]['domain'])) for a in df_list['vocab']]

    df_list.sort_values(['level'], ascending=False,inplace=True)
    kwargs['df_resource_list'] = df_resource_list
    kwargs["df_list_c1"] = df_list
    vocab_string = json.dumps({"vocab": list(df_list['vocab'].values)})
    kwargs["outside_form"] = vocab_string
    kwargs["email"]= email_part
    text = render_template('personalize_vocab.html',**kwargs)

    if button_command_value == "save" and session_string is not None:
        print("save words to db!!")
        dbname = DB_NAME
        conn = sqlite3.connect(dbname)
        df_session_setting_vocab = df_list.copy()
        df_session_setting_vocab.drop(['index','category','level','NGSL','domain'], axis=1, inplace=True)
        df_session_setting_vocab.columns = ['value']
        df_session_setting_vocab['session'] = session_string
        df_session_setting_vocab['actor'] = "all"
        df_session_setting_vocab['key'] = "vocab_to_cover"
        df_session_setting_vocab.to_sql('session_settings', conn, if_exists='append', index=False)
        conn.close()

    return text

if __name__ == "__main__":

    arguments = docopt(__doc__, version="0.1")

    host = arguments["<host>"]
    port = int(arguments["<port>"])
    app.run(debug=False, host=host, port=int(port), ssl_context=('cert/cert.pem', 'cert/key.pem'))
