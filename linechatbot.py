from __future__ import unicode_literals

import os
import sys
import redis
import hashlib
import time
import random
import string
from urllib.parse import quote
from argparse import ArgumentParser
import requests
from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage, VideoMessage, FileMessage, StickerMessage, StickerSendMessage, TemplateSendMessage, ImageCarouselTemplate, ImageCarouselColumn, URITemplateAction
)
from linebot.utils import PY3

HOST = "redis-11943.c1.asia-northeast1-1.gce.cloud.redislabs.com"
PWD = "7w7O1oNH5GJY5ocDGr0ercUNFkE6PcPy"
PORT = "11943"

redis1 = redis.Redis(host=HOST, password=PWD, port=PORT)

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

# obtain the port that heroku assigned to this app.
heroku_port = os.getenv('PORT', None)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if isinstance(event.message, TextMessage):
            handle_TextMessage(event)
        if isinstance(event.message, ImageMessage):
            handle_ImageMessage(event)
        if isinstance(event.message, VideoMessage):
            handle_VideoMessage(event)
        if isinstance(event.message, FileMessage):
            handle_FileMessage(event)
        if isinstance(event.message, StickerMessage):
            handle_StickerMessage(event)

        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

    return 'OK'

def train_mode(event, train_step=0):
    if train_step == 0:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('Which keyword do you want to teach me to reply?')
        )
        redis1.set('train_step', 1)
    elif train_step == 1:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('How do you want me to reply it?')
        )
        redis1.set(event.source.user_id + 'teach', event.message.text)
        redis1.set('train_step', 2)
    elif train_step == 2:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('Ok! I remember it!')
        )
        redis1.set(event.source.user_id + str(redis1.get(event.source.user_id + 'teach'), encoding='utf-8'), event.message.text)
        redis1.delete('train_step')
    # line_bot_api.push_message(
    #     event.source.user_id,
    #     TextSendMessage('Push ' + msg))
    # line_bot_api.reply_message(
    #     event.reply_token,
    #     TextSendMessage(msg))

# Handler function for Text Message
def handle_TextMessage(event):
    if redis1.get('train_step'):
        train_mode(event, int.from_bytes(redis1.get('train_step'), byteorder='big')-48)
    elif event.message.text == "teach":
        train_mode(event)
    elif redis1.get(event.message.text):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(str(redis1.get(event.message.text), encoding='utf-8'))
        )
    elif redis1.get(event.source.user_id + event.message.text):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(str(redis1.get(event.source.user_id + event.message.text), encoding='utf-8'))
        )
    elif event.message.text.find("coronavirus") != -1 or event.message.text.find("新冠肺炎") != -1 \
            or event.message.text.find("Coronavirus") != -1:

        message = TemplateSendMessage(
            alt_text='ImageCarousel template',
            template=ImageCarouselTemplate(
                columns=[
                    ImageCarouselColumn(
                        image_url='https://static.rti.org.tw/assets/thumbnails/2020/02/09/2583ee607285f873217e56f34079cd9d.jpg',
                        action=URITemplateAction(
                            label='新冠肺炎全球疫情分布图',
                            uri='https://letswritetw.github.io/letswrite-google-map-api-6/'
                        )
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, message)
    else:
        answer = get_content(event.message.text)
        # msg = 'You said: "' + event.message.text + '" '
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(answer)
        )

# Handler function for Sticker Message
def handle_StickerMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        StickerSendMessage(
            package_id=event.message.package_id,
            sticker_id=event.message.sticker_id)
    )

# Handler function for Image Message
def handle_ImageMessage(event):
    line_bot_api.reply_message(
	event.reply_token,
	TextSendMessage(text="Nice image!")
    )

# Handler function for Video Message
def handle_VideoMessage(event):
    line_bot_api.reply_message(
	event.reply_token,
	TextSendMessage(text="Nice video!")
    )

# Handler function for File Message
def handle_FileMessage(event):
    line_bot_api.reply_message(
	event.reply_token,
	TextSendMessage(text="Nice file!")
    )
# getmd5 hash
def curlmd5(src):
    m = hashlib.md5(src.encode('UTF-8'))
    return m.hexdigest().upper()
#tencent chat api
def get_params(plus_item):
    global params
    t = time.time()
    time_stamp=str(int(t))
    nonce_str = ''.join(random.sample(string.ascii_letters + string.digits, 10))
    app_id='2130472468'
    app_key='DvMmB8imryjfBYQc'
    params = {'app_id':app_id,
              'question':plus_item,
              'time_stamp':time_stamp,
              'nonce_str':nonce_str,
              'session':'10000'
             }
    sign_before = ''
    for key in sorted(params):
        sign_before += '{}={}&'.format(key,quote(params[key], safe=''))
    sign_before += 'app_key={}'.format(app_key)
    sign = curlmd5(sign_before)
    params['sign'] = sign
    return params
 
import requests
#send http request to the server
def get_content(plus_item):
    global payload,r
    # 聊天的API地址  
    url = "https://api.ai.qq.com/fcgi-bin/nlp/nlp_textchat"
    # 获取请求参数  
    plus_item = plus_item.encode('utf-8')
    payload = get_params(plus_item)
    # r = requests.get(url,params=payload)  
    r = requests.post(url,data=payload)
    return r.json()["data"]["answer"]

if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(host='0.0.0.0', debug=options.debug, port=heroku_port)
