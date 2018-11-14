from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage
)
import os
import pya3rt
import requests
import base64
import json
import uuid
import os

app = Flask(__name__)

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

talk_api = os.getenv('talk_api', None)
talk = pya3rt.TalkClient(talk_api)

VISION_API = os.getenv('VISION_API', None)
GOOGLE_CLOUD_VISION_API_URL = 'https://vision.googleapis.com/v1/images:annotate?key='

# APIを呼び、認識結果をjson型で返す
def request_cloud_vison_api(image_base64):
    api_url = GOOGLE_CLOUD_VISION_API_URL + VISION_API
    req_body = json.dumps({
        'requests': [{
            'image': {
                'content': image_base64.decode('utf-8') # jsonに変換するためにstring型に変換する
            },
            'features': [{
                'type': 'TEXT_DETECTION', # ここを変更することで分析内容を変更できる
                'maxResults': 10,
            }]
        }]
    })
    res = requests.post(api_url, data=req_body)
    return res.json()

# 画像読み込み
def img_to_base64(filepath):
    with open(filepath, 'rb') as img:
        img_byte = img.read()
    return base64.b64encode(img_byte)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    mtext = event.message.text
    message_list = mtext.split()
    if mtext[:5] == "json:":
        try:
            reply_mes = json.dumps(json.loads(mtext[5:]), indent=2)
        except:
            reply_mes = "jsonの形式が間違っています"
    else:
        reply_mes = talk.talk(mtext)["results"][0]["reply"]
    reply_message(event, TextSendMessage(text=reply_mes))

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_id = event.message.id
    print(message_id)
    message_content = line_bot_api.get_message_content(message_id)
    fp = "tmp/"+str(uuid.uuid4())+".jpg"
    with open(fp, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)
    img_base64 = img_to_base64(fp)
    os.remove(fp)
    result = request_cloud_vison_api(img_base64)
    text_r = result["responses"][0]["fullTextAnnotation"]["text"]
    reply_message(event, TextSendMessage(text=text_r))


def reply_message(event, messages):
    line_bot_api.reply_message(
        event.reply_token,
        messages=messages
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

#URL受信
#URLを元に音楽ファイルDLし送信