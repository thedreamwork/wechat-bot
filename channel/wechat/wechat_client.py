import requests
import json
from common.log import logger
from .WechatUtils import *
import base64
import datetime
import os
import uuid


class WechatClient():
    def __init__(self, request_url):
        self.request_url = request_url

    # 添加Http处理器
    def addCallBackUrl(self, callBackUrl):
        """
        设置回调地址，当有人发送消息时，微信会就把信息发送到这个接口中
        :param callBackUrl: 回调地址，当有人发送消息时，微信会就把信息发送到这个接口中
        :return:
        """
        # 获取所有的回调地址
        resdatalist = self._post_wx_request({
            "type": 1003
        })["data"]
        # 删除之前的回调地址
        for item in resdatalist:
            self._post_wx_request({
                "type": 1002,
                "cookie": item["cookie"]
            })
        # 设置新的回调地址
        self._post_wx_request({
            "type": 1001,
            "protocol": 2,
            "url": callBackUrl
        })

    def _post_wx_request(self, requestData: object) -> object:
        response = requests.post(self.request_url, json=requestData)
        if response.status_code != 200:
            raise Exception(f"wechat request error, response: {response}")
        try:
            return json.loads(response.text)["data"]
        except Exception as e:
            logger.error(f"wechat request error, response: {response} exception: {e}")
            # 抛异常
            raise e

    def get_group_member_detail(self, group_id):
        """
        获取群成员详细信息

        :param group_id: 群聊id
        :return:
        """
        req = {
            "type": 31,
            "chatroomUserName": group_id
        }
        return self._post_wx_request(req)

    def get_group_user_info_map(self, userIdOrGroupId):
        """
        批量获取用户信息

        :param userIdOrGroupId: 群id
        :return: 用户信息
        """
        res = {}
        reqData = self.get_group_member_detail(userIdOrGroupId)
        userlist = reqData["data"]["members"]
        for user in userlist:
            res[user["userName"]] = user["nickName"]

        return res

    def send_text_message_base(self, userIdOrGroupId, content, atUserList=[]):
        # 如果atUserList不为空，则查找atUserList中的用户，如果找到，则在content中添加@xxx
        # if not (userIdOrGroupId.startswith("wxid_") or userIdOrGroupId.endswith("@chatroom")):
        #     raise Exception(f"userIdOrGroupId必须是群id，且长度不能超过100,{userIdOrGroupId}")
        if content is None or content == '':
            return None
        if userIdOrGroupId.endswith("@chatroom"):
            user_data_map = self.get_group_user_info_map(userIdOrGroupId)
            content = content
            if atUserList:
                content += "\n"
                for atUser in atUserList:
                    if atUser in user_data_map:
                        userName = user_data_map[atUser]
                        content += ("@" + userName + "\u2005")

        return self._post_wx_request(
            {
                "type": 10009,
                "userName": userIdOrGroupId,
                "msgContent": content,
                "atUserList": atUserList
            })["msgSvrID"]

    def send_text_message(self, userIdOrGroupId, content):
        """
        发送文本消息
        :param wechat_id: 使用哪个微信发送
        :param userIdOrGroupId: 用户ID或者群ID
        :param content:  消息内容
        :return:
        """
        return self.send_text_message_base(userIdOrGroupId, content, [])

    def send_image_message(self, userIdOrGroupId, filePath):
        """
        发送图片消息
        :param wechat_id:  使用哪个微信发送
        :param userIdOrGroupId: 用户ID或者群ID
        :param filePath: 文件路径 本地文件或者http开头的url
        :return:
        """
        filePath, md5 = getFilePathAndMd5(filePath)
        return self._post_wx_request(
            {
                "type": 10010,
                "userName": userIdOrGroupId,
                "filePath": filePath
            })["msgSvrID"]

    def send_image_base64_message(self, userIdOrGroupId, base64Str):
        # 将base64转换为图片
        imgdata = base64.b64decode(base64Str)
        today = datetime.now().strftime('%Y-%m-%d')
        directory = f"gen_image/{today}/"
        # 如果是windows电脑
        if os.name == 'nt':
            # 创建目标目录路径
            directory = f'gen_image\\{today}\\'
        # 创建目录
        os.makedirs(directory, exist_ok=True)

        imageName = str(uuid.uuid1()) + ".png"
        full_path = os.path.abspath(os.path.join(directory, imageName))
        file = open(full_path, 'wb')
        file.write(imgdata)
        file.close()
        return self.send_image_message(userIdOrGroupId, full_path)

    def send_emoji_message(self, userIdOrGroupId, filePath):
        """
        发送表情
        :param userIdOrGroupId: 用户ID或者群ID
        :param filePath: 文件路径 本地文件或者http开头的url
        :return:
        """
        if not filePath.endswith(".gif"):
            raise Exception("表情文件必须是gif格式")

        filePath, md5 = getFilePathAndMd5(filePath)
        return self._post_wx_request(
            {
                "type": 10011,
                "userName": userIdOrGroupId,
                "filePath": filePath
            })

    def send_file_message(self, userIdOrGroupId, filePath):
        """
        发送文件
        :param wechat_id:  使用哪个微信发送
        :param userIdOrGroupId: 用户ID或者群ID
        :param filePath: 文件路径 本地文件或者http开头的url
        :return: msgSvrID
        """
        filePath, md5 = getFilePathAndMd5(filePath)
        return self._post_wx_request(
            {
                "type": 10012,
                "userName": userIdOrGroupId,
                "filePath": filePath
            })["msgSvrID"]

    # 发送名片
    def send_card_message(self, userIdOrGroupId, cardUserId):
        """
        发送名片
        :param wechat_id: 使用哪个微信发送
        :param userIdOrGroupId:  用户ID或者群ID
        :param cardUserId: 名片用户id
        :return:
        """
        return self._post_wx_request(
            {
                "type": 10037,
                "userName": userIdOrGroupId,
                "beSharedUserName": cardUserId,
            })["msgSvrID"]

    def send_xml_message(self, userIdOrGroupId, xml):
        """
        发送xml消息
        :param userIdOrGroupId: 用户ID或者群ID
        :param xml: xml内容
        :return:
        """
        return self._post_wx_request(
            {
                "type": 10053,
                "userName": userIdOrGroupId,
                "msgContent": xml,
            })

    def send_location_message(self, userIdOrGroupId, longitude, latitude, label, poiName, poiId, isFromPoiList):
        """
        发送位置消息
        :param userIdOrGroupId: 用户ID或者群ID
        :param longitude: 经度
        :param latitude: 纬度
        :param label: 位置信息
        :param poiName: poi名称
        :param poiId: poiId
        :param isFromPoiList: 是否来自poi列表
        :return:
        """
        return self._post_wx_request(
            {
                "type": 10022,
                "userName": userIdOrGroupId,
                "longitude": longitude,
                "latitude": latitude,
                "label": label,
                "poiName": poiName,
                "poiId": poiId,
                "isFromPoiList": False
            })

    # 发送语音
    def send_voice_message(self, userIdOrGroupId, filePath):
        """
        发送语音
        :param userIdOrGroupId: 用户ID或者群ID
        :param filePath: 文件路径 本地文件或者http开头的url
        :return:
        """
        filePath, md5 = getFilePathAndMd5(filePath)
        return self._post_wx_request(
            {
                "type": 10014,
                "userName": userIdOrGroupId,
                "filePath": filePath
            })

    # 拍一拍
    def send_shake_message(self, userId, groupId=None):
        """
        拍一拍
        :param wechat_id:  微信id
        :param userId:  用户id
        :param groupId:  如果是群聊，则需要传入群聊id
        :return:
        """
        param = {
            "type": 57,
            "userName": userId
        }
        if groupId:
            param["chatroomUserName"] = groupId
        return self._post_wx_request(param)

    def download_media_message(self, fileid, aeskey, savePath):
        # 下载音频文件
        return self._post_wx_request({
            "type": 66,
            "fileid": fileid,
            "aeskey": aeskey,
            "fileType": 15,
            "savePath": savePath
        })

    def recognize_voice_message(self, filePath):
        # 识别音频文件
        return self._post_wx_request({
            "type": 10045,
            "filePath": filePath
        })

    # 转发语音消息
    def forward_voice_message(self, userIdOrGroupId, fileSize, duration, fileid, aeskey):
        """
        转发语音消息

        :param userIdOrGroupId: 用户id或者群id
        :param fileSize: 语音文件大小
        :param duration: 语音文件时长，单位毫秒 最大60000（即60s）
        :param fileid: 语音文件id
        :param aeskey: 语音文件aeskey
        :return:
        """
        # 如果duration 大于60000，则需要强制为60000
        duration = duration if int(duration) >= 60000 else 60000
        return self._post_wx_request(
            {
                "type": 6,
                "userName": userIdOrGroupId,
                "fileSize": fileSize,
                "duration": duration,
                "fileid": fileid,
                "aeskey": aeskey
            })

    # 发送表情（无源）
    def send_emoji_message_no_file(self, userIdOrGroupId, emojiMd5):
        """
        发送表情（无源）

        :param userIdOrGroupId: 用户id或者群id
        :param emojiMd5: 表情包文件md5
        :param emojiLen: 表情包文件大小
        :return:
        """
        return self._post_wx_request(
            {
                "type": 11,
                "userName": userIdOrGroupId,
                "emojiMd5": emojiMd5
            })

    # 撤回消息
    def revoke_message(self, userIdOrGroupId, msgId):
        """
        撤回消息

        :param userIdOrGroupId: 用户id或者群id
        :param msgId: 通过发送消息接口返回的msgSvrID
        :return:
        """
        return self._post_wx_request(
            {
                "type": 58,
                "userName": userIdOrGroupId,
                "msgSvrID": int(msgId),
            })["status"] == 0

    # 发送引用消息
    def send_quote_message(self, userIdOrGroupId, msgSvrID, content, sourceContent, sourceUserName=None):
        """
        发送引用消息
        :param userIdOrGroupId: 用户id或者群id
        :param sourceUserName: 源消息发送者wxid，当userName为群聊id时必须提供该字段
        :param msgSvrID: 引用的消息id
        :param content: 消息内容
        :param sourceContent: 引用的消息内容
        :return:
        """
        return self._post_wx_request(
            {
                "type": 10056,
                "userName": userIdOrGroupId,
                "sourceUserName": sourceUserName,
                "content": content,
                "msgSvrID": msgSvrID,
                "sourceContent": sourceContent,
            })
