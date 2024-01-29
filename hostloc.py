import time
import re
import textwrap
import requests
import json
import time
from datetime import datetime
from pyaes import AESModeOfOperationCBC
from requests import Session as req_Session

# 使用Python实现防CC验证页面中JS写的的toNumbers函数
def toNumbers(secret: str) -> list:
    text = []
    for value in textwrap.wrap(secret, 2):
        text.append(int(value, 16))
    return text

# 不带Cookies访问论坛首页，检查是否开启了防CC机制，将开启状态、AES计算所需的参数全部放在一个字典中返回
def check_anti_cc() -> dict:
    result_dict = {}
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    }
    home_page = "https://hostloc.com/forum.php"
    res = requests.get(home_page, headers=headers)
    aes_keys = re.findall('toNumbers\("(.*?)"\)', res.text)
    cookie_name = re.findall('cookie="(.*?)="', res.text)

    if len(aes_keys) != 0:  # 开启了防CC机制
        print("检测到防 CC 机制开启！")
        if len(aes_keys) != 3 or len(cookie_name) != 1:  # 正则表达式匹配到了参数，但是参数个数不对（不正常的情况）
            result_dict["ok"] = 0
        else:  # 匹配正常时将参数存到result_dict中
            result_dict["ok"] = 1
            result_dict["cookie_name"] = cookie_name[0]
            result_dict["a"] = aes_keys[0]
            result_dict["b"] = aes_keys[1]
            result_dict["c"] = aes_keys[2]
    else:
        print("未检测到防 CC 机制开启！")
        pass

    return result_dict


# 在开启了防CC机制时使用获取到的数据进行AES解密计算生成一条Cookie（未开启防CC机制时返回空Cookies）
def gen_anti_cc_cookies() -> dict:
    cookies = {}
    anti_cc_status = check_anti_cc()

    if anti_cc_status:  # 不为空，代表开启了防CC机制
        if anti_cc_status["ok"] == 0:
            print("防 CC 验证过程所需参数不符合要求，页面可能存在错误！")
        else:  # 使用获取到的三个值进行AES Cipher-Block Chaining解密计算以生成特定的Cookie值用于通过防CC验证
            print("自动模拟计尝试通过防 CC 验证")
            a = bytes(toNumbers(anti_cc_status["a"]))
            b = bytes(toNumbers(anti_cc_status["b"]))
            c = bytes(toNumbers(anti_cc_status["c"]))
            cbc_mode = AESModeOfOperationCBC(a, b)
            result = cbc_mode.decrypt(c)

            name = anti_cc_status["cookie_name"]
            cookies[name] = result.hex()
    else:
        pass

    return cookies


# 登录帐户
def login(username: str, password: str) -> req_Session:
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
        "origin": "https://hostloc.com",
        "referer": "https://hostloc.com/forum.php",
    }
    login_url = "https://hostloc.com/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1"
    login_data = {
        "fastloginfield": "username",
        "username": username,
        "password": password,
        "quickforward": "yes",
        "handlekey": "ls",
    }

    s = req_Session()
    s.headers.update(headers)
    s.cookies.update(gen_anti_cc_cookies())
    res = s.post(url=login_url, data=login_data)
    res.raise_for_status()
    if parse_response(res):
       s.status = True
    else:
       s.status = False
    return s

#判断是否登录成功
def parse_response(res):
    # 使用正则表达式检查是否包含'登录失败'
    fail_match = re.search(r'登录失败，您还可以尝试 (\d+) 次', res.text)
    if fail_match:
        attempts_left = fail_match.group(1)
        print(f"登录失败，您还可以尝试 {attempts_left} 次")
        return False
    else:
        print(f"登录成功,正在T楼中....")
        return True
# 抓取楼层
def get_maxposition(s: req_Session,tid:str) -> int:
    test_url = f"https://hostloc.com/api/mobile/index.php?version=4&module=viewthread&tid={tid}"
    res = s.get(test_url)
    res.raise_for_status()
    res.encoding = "utf-8"
    data = json.loads(res.text)
    maxposition = data["Variables"]["thread"]["maxposition"]
    formhash= data["Variables"]["formhash"]
    return maxposition,formhash
#回帖
def reply(s: req_Session,formhash, tid, message,maxposition):
        reply_url = f'https://hostloc.com/forum.php?mod=post&action=reply&tid={tid}&extra=&replysubmit=yes&infloat=yes&handlekey=fastpost&inajax=1'
        data = {
                'file': '',
                'message': message,
                'posttime': int(time.time()),
                'formhash': formhash,
                'usesig': 1,
                'subject': '',
            }
        res = s.post(reply_url, data=data).text
        if 'succeed' in res:
            url = re.search(r'succeedhandle_fastpost\(\'(.+?)\',', res).group(1)
            print(f'T楼成功，中奖楼层:{maxposition},链接:{"https://hostloc.com/" + url},请收到检查是否中奖!')
        else:
            print('T楼失败\t' + res)


if __name__ == "__main__":
    #===============请每次修改以下内容================
    tid  =  "1268921" #帖子ID
    floor = [50,100]  #中奖楼层
    kouhao = "免费领钱随便啥都行" #回帖內容
    #===============请每次修改以上内容================
    username = "账号"
    password = "密码"
    s = login(username,password) #登录
    while s.status:
        # 获取当前楼层和formhash
        maxposition, formhash = get_maxposition(s, tid)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{current_time} 当前楼层: {maxposition},等待中奖楼层出现")
        maxposition = int(maxposition)+1
        # 判断当前楼层+1是否=中奖楼层
        if maxposition in floor:
            print(f"{current_time} 当前楼层=中奖楼层:{maxposition},开始执行回复操作")
            # 执行回帖操作
            reply(s,formhash,tid,kouhao,maxposition)
        # 如果当前喽册大于最大楼层，跳出循环
        if maxposition > max(floor):
            print("循环结束，中奖楼层已经结束")
            break
        # 每隔0.1秒执行一次循环
        time.sleep(0.1)


    