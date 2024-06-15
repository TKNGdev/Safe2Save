from flask import (Flask, request, abort)
import google.generativeai as genai
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (MessageEvent, TextMessage, TextSendMessage)
import os


app = Flask(__name__)

gemini = genai.configure(api_key=os.getenv('GEMINI_KEY'))

def get_response(question):
  model = genai.GenerativeModel('gemini-pro')
  response = model.generate_content(question)
  return response.text

line_bot_api = LineBotApi(os.getenv('LINE_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_SECRET'))

import openai

# openai.api_key = '你的 OpenAI API key'

hist = []  # 歷史對話紀錄
backtrace = 2  # 記錄幾組對話


def get_reply(messages):
  try:
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                            messages=messages)
    reply = response["choices"][0]["message"]["content"]
  except openai.OpenAIError as err:
    reply = f"發生 {err.error.type} 錯誤\n{err.error.message}"
  return reply


def chat(sys_msg, user_msg):
  while len(hist) >= 2 * backtrace:  # 超過記錄限制
    hist.pop(0)  # 移除最舊的紀錄
  hist.append({"role": "user", "content": user_msg})
  reply = get_reply(hist + [{"role": "system", "content": sys_msg}])
  while len(hist) >= 2 * backtrace:  # 超過記錄限制
    hist.pop(0)  # 移除最舊紀錄
  hist.append({"role": "assistant", "content": reply})
  return reply


@app.route("/callback", methods=['POST'])
def callback():
  signature = request.headers['X-Line-Signature']
  body = request.get_data(as_text=True)
  app.logger.info(f"Request body: {body}")
  
  try:
    handler.handle(body, signature)
  except InvalidSignatureError:
    print("Please check your channel access token/channel secret.")
    abort(400)
  return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
  reply_msg = chat('食物、藥品及化妝品安全小助理, 名字叫宋順蓮', event.message.text)
  
  if event.reply_token == "00000000000000000000000000000000":
    return
  line_bot_api.reply_message (
    event.reply_token,
    TextMessage(text=get_response(event.message.text))
  )

  line_bot_api.reply_message(event.reply_token,
                             TextSendMessage(text=reply_msg))


if __name__ == "__main__":
  app.run(host='0.0.0.0', port=5000)
