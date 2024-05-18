import xmltodict

from channel.chat_message import ChatMessage
from channel.wechat.wechat_client import WechatClient
from bridge.context import ContextType
from common.tmp_dir import TmpDir
from common.log import logger


class WechatMessage(ChatMessage):
    def __init__(self, msg, client: WechatClient):
        super().__init__(msg)
        self.msg_id = msg["msgSvrID"]
        self.create_time = msg["createtime"]
        sendChannel = msg["from"]
        self.is_group = "@chatroom" in sendChannel
        if msg['type'] == 1:
            self.ctype = ContextType.TEXT
            self.content = msg["content"]
        elif msg['type'] == 34:
            self.ctype = ContextType.VOICE
            xmlContent = msg['content']
            content = xmltodict.parse(xmlContent)
            aeskey = content['msg']['voicemsg']['@aeskey']
            fileid = content['msg']['voicemsg']['@voiceurl']
            self.content = TmpDir().path() + fileid + ".slik" # content直接存临时目录路径

            def download_voice():
                # 如果响应状态码是200，则将响应内容写入本地文件
                response = client.download_media_message(fileid, aeskey, self.content)
                logger.info(f"[WX] download voice file, {response}")

            self._prepare_fn = download_voice
        elif msg['type'] == 3:
            self.ctype = ContextType.IMAGE
            xmlContent = msg['content']
            content = xmltodict.parse(xmlContent)
            aeskey = content['msg']['img']['@aeskey']
            fileid = content['msg']['img']['@cdnmidimgurl']
            self.content = TmpDir().path() + fileid + ".png"  # content直接存临时目录路径

            def download_image():
                # 如果响应状态码是200，则将响应内容写入本地文件
                response = client.download_media_message(fileid, aeskey, self.content)
                logger.info(f"[WX] download voice file, {response}")

            self._prepare_fn = download_image
        else:
            raise NotImplementedError("Unsupported message type: Type:{} ".format(msg['type']))

        self.from_user_id = msg["from"]
        self.to_user_id = msg["to"]
        self.other_user_id = msg["from"]
