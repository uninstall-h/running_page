import base64
import datetime
import os
import requests
from loguru import logger

ENV_RQ_USERNAME = "RQ_USERNAME"
ENV_RQ_PASSWD = "RQ_PASSWD"
ENV_JFBYM_TOKEN = "JFBYM_TOKEN"
ENV_SYNC_RQ = "SYNC_RQ"


class RQ(object):
    _instance = None

    _login_url = "https://www.rq.run/Home/Login/password_login"
    _verify_url = "https://rq.run/Home/Tool/verify"
    _upload_url = "https://www.rq.run/dc/api?module=User&controller=ManualUpload&function=event_upload&options[is_upload]=1"
    _check_base_url = "https://www.rq.run/dc/api?_=User/Training/condition"

    _headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.rq.run',
        'Referer': 'https://www.rq.run/Home/Login/login.html?refer_url=%2Fuser%2Fupload%3Flang%3Dzh-CN%26pure%3D1',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-gpc': '1',
    }

    def __new__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = object.__new__(cls, *args, **kw)
        return cls._instance

    def __init__(self):
        self._available = False
        if not self._check_params():
            return

        self._session = requests.session()

        if self._login():
            self._available = True

    def _check_params(self):
        if not os.environ.get(ENV_RQ_USERNAME):
            logger.error(f"can not get {ENV_RQ_USERNAME}")
            return False
        self._user_name = os.environ.get(ENV_RQ_USERNAME)
        if not os.environ.get(ENV_RQ_PASSWD):
            logger.error(f"can not get {ENV_RQ_PASSWD}")
            return False
        self._passwd = os.environ.get(ENV_RQ_PASSWD)
        if not os.environ.get(ENV_JFBYM_TOKEN):
            logger.error(f"can not get {ENV_JFBYM_TOKEN}")
            return False
        self._verify_token = os.environ.get(ENV_JFBYM_TOKEN)

        return True

    def _login(self):
        code = self._get_verify_code()
        logger.info("开始登录。。。")

        payload = f"username={self._user_name}&password={self._passwd}&login_code={code}&remember=1"
        response = self._session.request("POST", self._login_url, headers=self._headers, data=payload)
        try:
            data = response.json()
            if data["status"] == 0:
                logger.info(f"login success")
                return True
            else:
                logger.error(f"login error, data: {data}")
                return False
        except Exception as e:
            logger.error(f"登录失败: {e}, {response.text}")
            return False

    def get_user_info(self):
        if not self._available:
            logger.error("instance is not available")
            return

        dt = datetime.datetime.now()

        url = f"{self._check_base_url}&date={dt.year}-{dt.month:02d}-{dt.day:02d}+{dt.hour:02d}%3A{dt.minute:02d}%3A01&student_user_id=0&group_id=0"

        response = self._session.request("GET", url, headers=self._headers, data={})
        try:
            data = response.json()
            logger.info(data)
        except Exception as e:
            logger.exception(f"get user_info error, {e}")

    def _get_verify_code(self):
        response = self._session.request("GET", self._verify_url, headers=self._headers, data={})
        image = base64.b64encode(response.content).decode()
        logger.info(f"get verify image headers: {response.headers}")

        code = self._recognized_code(image)

        return code

    def _recognized_code(self, image: str):
        url = "http://api.jfbym.com/api/YmServer/customApi"
        data = {
            "token": self._verify_token,
            "type": "10110",
            "image": image,
        }

        response = requests.request("POST", url, headers={"Content-Type": "application/json"}, json=data).json()

        try:
            data = response['data']['data']
            logger.info(f"验证码: {data}")
            return response['data']['data']
        except Exception as e:
            logger.error(f"验证码获取失败: {e}, {response}")
            return None

    def upload_gpx(self, path: str):
        if not self._available:
            logger.error("instance is not available")
            return

        with open(path, "rb") as f:
            files = [
                ('file', ('9223370287639252907.gpx', f, 'application/octet-stream'))
            ]

        response = self._session.request("POST", self._upload_url, headers=self._headers, data={}, files=files)
        try:
            data = response.json()
            logger.info(data)
            if data["status"] != 0:
                logger.error(f"upload gpx<{path}>, error")
            else:
                logger.info(f"upload gpx<{path}> success")
        except Exception as e:
            logger.error(f"上传GPX<{path}>失败: {e}, {response.text}")


rq_instance = RQ()
