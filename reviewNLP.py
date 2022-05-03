# references:
# https://github.com/willismax/py-scraping-analysis-book/commit/6af384b535bc2cc42df9f4741f6dbfff787f0362#diff-a953591fc8ee1f094b843193c4fbc88f860f4fe2318aa474725d1b921b18cd4e
# https://github.com/willismax/ICT-Python-101/blob/master/04.Python%E8%B3%87%E6%96%99%E5%88%86%E6%9E%90%E6%87%89%E7%94%A8-%E8%AA%9E%E6%84%8F%E5%88%86%E6%9E%90%E7%AF%87NLP.ipynb

import requests
import time
import random
import json
import re
import csv
from bs4 import BeautifulSoup
import pandas as pd
import jieba
from snownlp import SnowNLP


PTT_URL = 'https://www.ptt.cc'


def get_web_page(url):
    resp = requests.get(
        url=url,
        cookies={'over18': '1'}  # 告知Server已回答過滿18歲的問題
    )
    if resp.status_code != 200:
        print('Invalid url:', resp.url)
        return None
    else:
        return resp.text


def sanitize(txt):
    # 保留英數字, 中文 (\u4e00-\u9fa5) 及中文標點, 部分特殊符號

    expr = re.compile('[^\u4e00-\u9fa5。；，：“”（）、？「」『』【】\s\w:/\-.()]')  # ^ 表示"非括號內指定的字元"
    txt = re.sub(expr, '', txt)
    txt = re.sub('(\s)+', ' ', txt)  # 用單一空白取代多個換行或 tab 符號
    txt = txt.replace('--', '')
    txt = txt.lower()  # 英文字轉為小寫
    return txt


def get_post(url):
    resp = requests.get(
        url= PTT_URL + url,
        cookies={'over18': '1'}  # 告知 Server 已回答過滿 18 歲的問題
    )
    soup = BeautifulSoup(resp.text, 'html')
    main_content = soup.find('div', id='main-content')

    # 把非本文的部份 (標題區及推文區) 移除
    # 移除標題區塊
    for meta in main_content.find_all('div', 'article-metaline'):
        meta.extract()
    for meta in main_content.find_all('div', 'article-metaline-right'):
        meta.extract()
    # 移除推文區塊
    for push in main_content.find_all('div', 'push'):
        push.extract()

    parsed = []
    for txt in main_content.stripped_strings:
        # 移除 '※ 發信站:', '--' 開頭, 及本文區最後一行文章網址部份
        if txt[0] == '※' or txt[:2] == '--' or url in txt:
            continue
        txt = sanitize(txt)
        if txt:
            print(txt)
            parsed.append(txt)
    return ''.join(parsed)


def get_article_body(df):
    # titles = []
    bodys = []

    # df_merged = pd.DataFrame()
    for i in range(len(df['href'])):
        body = get_post(df['href'][i])
        print('處理', df['title'][i], df['href'][i])
        bodys.append(body)
        time.sleep(random.choice(range(1,7)))  # 放慢爬蟲速度

    df['body'] = bodys
    return df

# 輸入要爬取的food版醉心頁面網址編報; n = 想往前爬的頁數
def get_articles_all_text(ptt_food_today_page_num, n): 
    articles = []  # 儲存取得的文章資料
    for p in range(ptt_food_today_page_num, ptt_food_today_page_num - n, -1):
        url =  f'/bbs/Food/index{p}.html'
        dom = get_web_page(PTT_URL + url) # 取得 food 版第一頁
        soup = BeautifulSoup(dom, features="html.parser")

        divs = soup.find_all('div', 'r-ent')
        for d in divs:
            # 取得推文數
            push_count = 0
            push_str = d.find('div', 'nrec').text
            if push_str:
                try:
                    push_count = int(push_str)  # 轉換字串為數字
                except ValueError:
                    # 若轉換失敗，可能是'爆'或 'X1', 'X2', ...
                    # 若不是, 不做任何事，push_count 保持為 0
                    if push_str == '爆':
                        push_count = 99
                    elif push_str.startswith('X'):
                        push_count = -10

            # 取得文章連結及標題
            if d.find('a'):  # 有超連結，表示文章存在，未被刪除
                date = d.find('div', 'date').text.strip()
                href = d.find('a')['href']
                title = d.find('a').text
                body = get_post(href) #　取得PO文內文
                print('處理', title, href, '的po文')
                time.sleep(random.choice(range(1,6)))  # 放慢爬蟲速度
                articles.append({
                    'date': date,
                    'title': title,
                    'href': href,
                    'push_count': push_count,
                    'body' : body              
                })
            
    df = pd.DataFrame(articles)

    return df

def df_to_csv(file_path, ptt_food_today_page_num, n):
    df = get_articles_all_text(ptt_food_today_page_num, n)
    df.to_csv(file_path, encoding="utf-8", index=False)
    return file_path

def Emotion_Analysis(csv_file_path_to_load, csv_file_path_to_save):
    ## 將CSV內的分店留言內容與食記內容存成一整個字串
    good_count_list= []
    avg_score_list = []
    bad_count_list= []

    for row in range(df.shape[0]):
        try:
            # 取出df2內的評論內容
            all_article_string = df['body'][row]

            ## 進行情感分析
            total_score = 0
            good_count = 0
            bad_count = 0

            s = SnowNLP(all_article_string) 
            for sentence in s.sentences : 
                if "nan" in sentence:
                    pass
                else:
                    sentiments_score = SnowNLP(sentence).sentiments 
                    if sentiments_score > 0.5:
                        good_count += 1
                    elif sentiments_score <= 0.5:
                        bad_count += 1
                    total_score += sentiments_score

            avg_score = total_score/len(s.sentences)
            avg_score_list.append(avg_score)
            good_count_list.append(good_count)
            bad_count_list.append(bad_count)

        except:
            print(f'row{row} went wrong')
            avg_score_list.append('NaN')
            good_count_list.append('NaN')
            bad_count_list.append('NaN')
            pass

            
    # 將評分結果新增至原df並建新的CSV
    df["正評數"] = good_count_list
    df["負評數"] = bad_count_list
    df["情感平均分數"] = avg_score_list
    df.drop(columns=['body'])
    df.to_csv('./ptt/ptt_sentiments.csv',index=False,encoding='utf-8',header=['日期','標題','連結','推文數','內文',"正評數","負評數","情感平均分數"])

    return df, csv_file_path_to_save



### 編寫詞頻分析函式
def Jieba_Analysis(csv_file):
    ## 將CSV內的分店留言內容與食記內容存成一整個字串
    try:    
        df = pd.read_csv(csv_file)
        ## 進行詞頻分析
        word_count = {}
        for row in range(df.Shape[0]):
            s_list = jieba.cut(df['body'][row])
            for i in s_list:
                if i in word_count:
                    word_count[i] += 1
                else:
                    word_count[i] = 1

            sorted_word_count = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
            print(sorted_word_count)

    except:
        print ("No article available!")


if __name__ == '__main__':
    csv_file_path = './ptt/ptt_food.csv' # csv檔想儲存的路徑
    global df
    df_to_csv(csv_file_path, 7006, 333) # 想爬幾頁ptt food版 
    csv_file_path_to_save = './ptt/ptt_sentiments.csv'
    Emotion_Analysis(csv_file_path, csv_file_path_to_save)
