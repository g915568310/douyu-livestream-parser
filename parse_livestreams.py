import hashlib
import re
import time
import execjs
import requests

class DouYu:
    """ 斗鱼直播流地址解析类 """
    def __init__(self, rid):
        self.did = '10000000000000000000000000001501'
        self.t10 = str(int(time.time()))
        self.t13 = str(int((time.time() * 1000)))
        self.s = requests.Session()
        # 提取真实 rid
        try:
            self.res = self.s.get(f'https://m.douyu.com/{rid}').text
            result = re.search(r'rid":(\d{1,8}),"vipId', self.res)
            if result:
                self.rid = result.group(1)
            else:
                raise Exception('房间号错误')
        except Exception as e:
            raise Exception(f'无法获取房间信息：{e}')

    @staticmethod
    def md5(data):
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def get_pre(self):
        url = f'https://playweb.douyucdn.cn/lapi/live/hlsH5Preview/{self.rid}'
        data = {'rid': self.rid, 'did': self.did}
        auth = self.md5(f'{self.rid}{self.t13}')
        headers = {'rid': self.rid, 'time': self.t13, 'auth': auth}
        res = self.s.post(url, headers=headers, data=data).json()
        if res.get('error') != 0:
            return None
        rtmp_live = res['data'].get('rtmp_live', '')
        return re.search(r'(\d{1,8}[0-9a-zA-Z]+)', rtmp_live).group(1) if rtmp_live else None

    def get_js(self):
        func_ub9 = re.sub(r'eval.*?;}', 'strc;}', re.search(r'(function ub98484234.*?})', self.res).group(1))
        js = execjs.compile(func_ub9)
        res = js.call('ub98484234')
        v = re.search(r'v=(\d+)', res).group(1)
        rb = self.md5(f'{self.rid}{self.did}{self.t10}{v}')
        func_sign = re.sub(r'return rt;});?', 'return rt;}', res).replace('(function (', 'function sign(')
        func_sign = func_sign.replace('CryptoJS.MD5(cb).toString()', f'"{rb}"')
        js = execjs.compile(func_sign)
        params = js.call('sign', self.rid, self.did, self.t10) + f'&ver=219032101&rid={self.rid}&rate=-1'
        res = self.s.post('https://m.douyu.com/api/room/ratestream', params=params).text
        return re.search(r'(\d{1,8}[0-9a-zA-Z]+)', res).group(1)

    def get_real_url(self):
        key = self.get_pre()
        if not key:  # 如果预览接口失败，改用 JS 解析
            key = self.get_js()
        return f'http://hls3-akm.douyucdn.cn/live/{key}.m3u8'

# 批量解析多个直播间
def parse_livestreams(input_file, output_file):
    with open(input_file, 'r') as f:
        input_data = f.read().strip()
    results = []

    entries = [entry.strip() for entry in input_data.split(',')]
    for entry in entries:
        parts = entry.split(':')
        if len(parts) != 2:
            results.append(f"{entry},失败 输入格式错误")
            continue

        category, rid = parts
        try:
            dy = DouYu(rid.strip())
            real_url = dy.get_real_url()
            results.append(f"{category},{real_url}")
        except Exception as e:
            results.append(f"{category},失败 {e}")

    # 写入输出文件
    with open(output_file, 'w') as f:
        f.write('\n'.join(results))

if __name__ == '__main__':
    # 输入和输出文件路径
    input_file = 'input.txt'  # GitHub 中的输入文件
    output_file = 'output.txt'  # GitHub 中的输出文件
    parse_livestreams(input_file, output_file)
