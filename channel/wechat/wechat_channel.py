# -*- coding=utf-8 -*-
import json
import os

import web

from bridge.context import Context
from bridge.reply import Reply, ReplyType
from common.log import logger
from common.singleton import singleton
from channel.chat_channel import ChatChannel
from config import conf
from .wechat_client import WechatClient
import base64

from .wechat_message import WechatMessage

try:
    from voice.audio_convert import any_to_sil
except Exception as e:
    pass

@singleton
class WechatChannel(ChatChannel):
    NOT_SUPPORT_REPLYTYPE = []

    def __init__(self):
        super().__init__()
        self.wechatsdk_port = conf().get("wechatsdk_request_port", 8888)
        self.client = WechatClient(f"http://127.0.0.1:{self.wechatsdk_port}/api/")

    def startup(self):
        # start message listener
        urls = ("/callback", "channel.wechat.wechat_channel.Handler")
        app = web.application(urls, globals(), autoreload=False)
        port = conf().get("wechatsdk_callback_port", 9898)
        self.client.addCallBackUrl(f"http://127.0.0.1:{port}/callback")
        web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", port))


    def send(self, reply: Reply, context: Context):
        receiver = context["receiver"]
        if reply.type in [ReplyType.TEXT, ReplyType.ERROR, ReplyType.INFO]:
            self.client.send_text_message(receiver, reply.content)
            logger.info("[WX] Do send text to {}: {}".format(receiver, reply.content))
        elif reply.type == ReplyType.VOICE:
            file_path = reply.content
            sil_file = os.path.splitext(file_path)[0] + ".sil"
            voiceLength = int(any_to_sil(file_path, sil_file))
            if voiceLength >= 60000:
                voiceLength = 60000
                logger.info("[WX] voice too long, length={}, set to 60s".format(voiceLength))
            # 发送语音
            self.client.send_voice_message(receiver, sil_file)
            try:
                os.remove(file_path)
                if sil_file != file_path:
                    os.remove(sil_file)
            except Exception as e:
                pass
            logger.info("[WX] sendVoice={}, receiver={}".format(reply.content, receiver))
        elif reply.type == ReplyType.IMAGE_URL:  # 从网络下载图片
            img_url = reply.content
            self.client.send_image_message(receiver, img_url)
            logger.info("[WX] sendImage url={}, receiver={}".format(img_url, receiver))
        elif reply.type == ReplyType.IMAGE:  # 从文件读取图片
            image_storage = reply.content
            image_storage.seek(0)
            self.client.send_image_base64_message(receiver, base64.b64encode(image_storage.read()))
            logger.info("[wechatcom] sendImage, receiver={}".format(receiver))


class Handler:
    def GET(self):
        return "hello"

    def POST(self):
        params = web.data()
        # 设置HTTP头部
        web.header('Content-Type', 'application/json')
        data = json.loads(params)  # 解析 JSON 数据
        logger.info("[WX] receive params: {}".format(data))
        pushType = data["pushType"]  #
        if pushType != 1:  # 这里演示，只处理同步类型消息，其他类型可以自行处理
            return json.dumps({"success": "true"})
        # 消息类型详见： https://github.com/WeChatAPIs/wechatAPI/blob/main/doc/处理消息/消息类型.md
        channel = WechatChannel()
        try:
            wechat_msg = WechatMessage(data["data"], client=channel.client)
        except NotImplementedError as e:
            logger.debug("[WX] " + str(e))
            return json.dumps({"success": "true"})
        context = channel._compose_context(
            wechat_msg.ctype,
            wechat_msg.content,
            isgroup=wechat_msg.is_group,
            msg=wechat_msg,
        )
        if context:
            channel.produce(context)
        return json.dumps({"success": "true"})


