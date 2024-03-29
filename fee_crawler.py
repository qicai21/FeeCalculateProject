import requests
import json
import random
import time


KZ_Data = {
    'dm': '0898003', 'pym': 'KZ', 'pmhz': '矿渣', 'ldjh': '21',
    'wpdm': 'null', 'jzz': 'null', 'ifszjf': 'null', 'plhz': 'null',
    'jzxjh': '0', 'zcjh': '2', 'shpmsspmdm': '0898003', 'ifshpm': '0',
    'shpmhz': '矿渣', 'shpmpym': 'KZ'
}

TKS_Data = {
    "dm": "0410013", "pym": "TKS", "pmhz": "铁矿石", "ldjh": "21",
    'wpdm': 'null', 'jzz': 'null', 'ifszjf': 'null', 'plhz': 'null',
    "jzxjh": "0", "zcjh": "4", "shpmsspmdm": "0410013", "ifshpm": "0",
    "shpmhz": "铁矿石", "shpmpym": "TKS"
}

NSH_Data = {
    'dm': '1310013', 'pym': 'NSH', 'pmhz': '尿素(化肥)', 'ldjh': '21',
    'wpdm': 'null', 'jzz': 'null', 'ifszjf': 'null', 'plhz': 'null',
    'jzxjh': '0', 'zcjh': '4', 'shpmsspmdm': '1310013', 'ifshpm': '0',
    'shpmhz': '尿素(化肥)', 'shpmpym': 'NSH'
}


def wait_for(condition_func):
    def wrap(*args, **kwargs):
        delay = 0.5
        max_delay = 5
        inner_exp_msg = None
        while delay < max_delay:
            try:
                result = condition_func(*args, **kwargs)
                if result:
                    return result
                time.sleep(delay)
                delay += 0.5
            except KeyError as exp:
                inner_exp_msg = str(exp)
                time.sleep(delay)
                delay += 0.5
        inner_exp_msg = '执行多次均未能刷新' if not inner_exp_msg else inner_exp_msg
        raise Exception(
            '执行{}超时,错误信息如下:'.format(condition_func.__name__), inner_exp_msg
        )
    return wrap


class FeeCrawler():
    def __init__(self, delay=0):
        self.delay = delay
        self.query_code = None
        self.cookie = None
        self.token = None

        # for post data:
        self.start_lj_data = None
        self.start_lj_code = None
        self.start_station_name = None
        self.start_station_code = None
        self.start_station_data = None

        self.end_lj_data = None
        self.end_lj_code = None
        self.end_station_name = None
        self.end_station_code = None
        self.end_station_data = None

        self.cargo_name = None
        self.cargo_data = None
        self.cargo_code = None

        self.start_station_load = False
        self.end_station_discharge = False

        self.used_query_codes = []
        self.used_tokens = []
        self.refresh_query_code_and_cookie()
 
    @wait_for
    def refresh_query_code_and_cookie(self):
        url = 'https://ec.95306.cn/api/gxzx/verfication/query'
        resp = requests.post(url, data={})
        if resp.status_code != 200:
            raise KeyError('刷新cookie返回了{}'.format(resp.status_code))
        if resp.json()['msg'] != 'OK':
            raise KeyError('刷新cookie失败:{}'.format(resp.json()['msg']))
        query_code = resp.json()['data']['randomCode']
        token = resp.json()['data']['code']
        if query_code in self.used_query_codes or token in self.used_tokens:
            return False
        session = resp.headers['Set-Cookie'].split(';')[0]
        self.cookie = f'95306-1.6.10-loginType=outer;{session}'
        self.query_code = query_code
        self.token = token
        self.used_tokens.append(token)
        self.used_query_codes.append(query_code)
        return True

    def send_cargo_name_request(self, name):
        data = {'q': name, 'limit': "50", 'isShieldYsfs': 'true'}
        length = len(json.dumps(data, ensure_ascii=False)) + 1
        url = 'https://ec.95306.cn/api/zd/pm/queryList'
        headers = create_headers_by(length, self.cookie)
        resp = requests.post(url, headers=headers, json=data)
        return resp.json()

    def send_station_request(self, name):
        data = {'q': name, 'ljdm': '', 'limit': '50'}
        length = len(json.dumps(data, ensure_ascii=False)) + 1
        url = 'https://ec.95306.cn/api/zd/lj/queryTmismForYfcx'
        headers = create_headers_by(length, self.cookie)
        resp = requests.post(url, headers=headers, json=data)
        return resp.json()

    def query_station_by_name(self, name):
        stations = self.send_station_request(name)
        if len(stations['data']) == 0:
            new_name = input('未查到任何站名,请输入新站名:')
            return self.query_station_by_name(new_name)
        elif len(stations['data']) == 1:
            name = stations['data'][0]['hzzm']
            print('查到车站:' + name)
            return stations['data'][0]
        else:
            names = [i['hzzm'] for i in stations['data']]
            names_txt = ', '.join([f'{i}: {n};' for i, n in zip(range(len(names)), names)])
            select = input('查到多条结果:' + names_txt + '输入序号选定车站,输入站名文字重新搜索')
            try:
                index = int(select)
                return stations['data'][index]
            except ValueError:
                new_name = select
                return self.query_station_by_name(new_name)

    def send_lj_request(self, lj_name):
        data = {'q': lj_name, 'limit': '50'}
        length = 60  # 不再算了,60足够了
        url = 'https://ec.95306.cn/api/zd/lj/queryLjs'
        headers = create_headers_by(length, self.cookie)
        resp = requests.post(url, headers=headers, json=data)
        resp_json = resp.json()
        if resp.status_code != 200 or resp_json['msg'] != 'OK':
            return None
        return resp_json['data'][0]

    def set_start_station(self, name, limited_lj=None, destine_station_data=None):
        if destine_station_data:
            station_data = destine_station_data
        else:
            station_data = self.query_station_by_name(name)
        self.start_station_code = station_data['dbm']
        self.start_station_name = station_data['hzzm']
        self.start_station_data = station_data
        self.start_lj_code = station_data['ljm']
        start_lj_name = station_data['ljqc']
        if limited_lj and start_lj_name not in limited_lj:
            raise AttributeError(f'{name} 不是{limited_lj}中的站.')
        lj_data = self.send_lj_request(start_lj_name)
        if lj_data:
            self.start_lj_data = lj_data
        else:
            raise AttributeError('路局数据获取失败')

    def set_end_station(self, name, limited_lj=None, destine_station_data=None):
        if destine_station_data:
            station_data = destine_station_data
        else:
            station_data = self.query_station_by_name(name)
        self.end_station_code = station_data['dbm']
        self.end_station_name = station_data['hzzm']
        self.end_station_data = station_data
        self.end_lj_code = station_data['ljm']
        end_lj_name = station_data['ljqc']
        if limited_lj and end_lj_name not in limited_lj:
            raise AttributeError(f'{name} 不是{limited_lj}中的站.')
        data = self.send_lj_request(end_lj_name)
        if data:
            self.end_lj_data = data
        else:
            raise AttributeError('路局数据获取失败')

    def query_cargo_by_name(self, name):
        cargo = self.send_cargo_name_request(name)
        if len(cargo['data']) == 0:
            new_name = input('未查到任何货物名称,请输入货名:')
            return self.query_cargo_by_name(new_name)
        elif len(cargo['data']) == 1:
            name = cargo['data'][0]['pmhz']
            print('查到货名:' + name)
            return cargo['data'][0]
        else:
            names = [i['pmhz'] for i in cargo['data']]
            names_txt = ', '.join([f'{i}: {n};' for i, n in zip(range(len(names)), names)])
            select = input('查到多条结果:' + names_txt + '输入序号选定货名,输入货名文字重新搜索')
            try:
                index = int(select)
                return cargo['data'][index]
            except ValueError:
                new_name = select
                return self.query_cargo_by_name(new_name)

    def set_cargo_by_name(self, name):
        resp_data = self.query_cargo_by_name(name)
        self.cargo_name = resp_data['pmhz']
        self.cargo_data = resp_data
        self.cargo_code = resp_data['dm']

    def set_cargo_by_data(self, cargo_data):
        self.cargo_data = cargo_data
        self.cargo_name = cargo_data['pmhz']
        self.cargo_code = cargo_data['dm']

    @wait_for
    def query_subline_miles(self, start_or_end, subline_name=None):
        url = 'https://ec.95306.cn/api/zx/czmpxx/queryByTimism'
        if start_or_end == 'start':
            data = {'fztmism': self.start_station_data['tmism']}
        if start_or_end == 'end':
            data = {'fztmism': self.end_station_data['tmism']}
        data = replace_tmism_if_station_is_port_station(data)
        resp = requests.post(url, json=data)
        if resp.status_code != 200 or resp.json()['msg'] != 'OK':
            msg = f'查询{data["hzpm"]}失败! code: {resp.status_code}. retrun msg:{resp.json()["msg"]}'
            raise KeyError(msg)
        sublines = resp.json()['data'].get('zyxInfoList')
        if sublines is None or len(sublines) == 0:
            print(f'{self.start_station_name}站下没有任何专用线.')
            return None
        sublines_data = {}
        for line in sublines:
            sublines_data[line['zyxName']] = line['zyxQsclc']
        names = list(sublines_data)
        names_txt = ', '.join([f'{i}: {n};' for i, n in zip(range(len(names)), names)])
        msg = ('查询到如下专用线:' + names_txt + '输入序号选定专用线')
        if subline_name:
            if subline_name in names:
                name = subline_name
            else:
                msg = subline_name + '不存在,' + msg
                index = int(input(msg))
                name = names[index]
        else:
            index = int(input(msg))
            name = names[index]
        mile = float(sublines_data[name])
        return name, mile

    def query_calculate_base_fee(self, cargo):
        if cargo == '矿渣':
            self.set_cargo_by_data(KZ_Data)
        elif cargo == '铁矿石':
            self.set_cargo_by_data(TKS_Data)
        elif cargo == '尿素(化肥)':
            self.set_cargo_by_data(NSH_Data)
        else:
            raise KeyError('cargo 不正确,请输入:矿渣,铁矿石, 尿素(化肥)')
        return self.query_crt_fee()

    def get_post_data(self):
        data = {
            'flj': self.start_lj_data,
            'dlj': self.end_lj_data,
            'hw': '1',
            'fzhzzm': self.start_station_name,
            'fzObj': self.start_station_data,
            'dzhzzm': self.end_station_name,
            'dzObj': self.end_station_data,
            'hwmcObj': self.cargo_data,
            'hwmc': self.cargo_name,
            'plObj': '',
            'pl': '',
            'xplObj': '',
            'xpl': '',
            'code': self.query_code,
            'token': self.token,
            'dz': self.end_station_code,
            'dzljm': self.end_lj_code,
            'dztlzx': '1' if self.end_station_discharge else '0',  # 到站装卸
            'fz': self.start_station_code,
            'fzljm': self.start_lj_code,
            'fztlzx': '1' if self.start_station_load else '0',  # 发站装卸
            'hzpm': self.cargo_name,
            'pm': self.cargo_code,
            'shsm': '0',  # 送货上门
            'smqh': '0',  # 上门取货
            'smxc': '0',  # 上门卸车
            'smzc': '0',  # 上门装车
            'fsqhlc': '0',  # 上门取货里程
            'ddqhlc': '0'  # 送货上门里程
        }
        return data

    def get_missing_properties(self):
        necessary_datas = {
            'query_code': self.query_code,
            'cookie': self.cookie,
            'token': self.token,
            'start_lj_data': self.start_lj_data,
            'start_lj_code': self.start_lj_code,
            'start_station_name': self.start_station_name,
            'start_station_code': self.start_station_code,
            'start_station_data': self.start_station_data,
            'end_lj_data': self.end_lj_data,
            'end_lj_code': self.end_lj_code,
            'end_station_name': self.end_station_name,
            'end_station_code': self.end_station_code,
            'end_station_data': self.end_station_data
        }
        return [k for k, v in necessary_datas.items() if v is None]

    def query_crt_fee_by_cargo(self, cargo, start_stn_load=False, end_stn_discharge=False):
        self.start_station_load = start_stn_load
        self.end_station_discharge = end_stn_discharge
        self.set_cargo_by_name(cargo)
        return self.query_crt_fee()

    @wait_for
    def query_crt_fee(self):
        self.refresh_query_code_and_cookie()
        time.sleep(0.8)  # 等待1秒钟,否则刷新太快导致95306服务器没有加载完新的token,导致400错误.
        missing_properties = self.get_missing_properties()
        if any(missing_properties):
            raise KeyError(f'following properties are not ready:{missing_properties}')
        data = self.get_post_data()
        length = len(json.dumps(data, ensure_ascii=False)) + 10
        headers = create_headers_by(length, self.cookie)
        url = 'https://ec.95306.cn/api/zx/businessFor/carriageCalculateNew'
        resp = requests.post(url, headers=headers, json=data)
        if resp.status_code != 200 or resp.json()['msg'] != 'OK':
            print(f'查询{data["hzpm"]}失败! code: {resp.status_code}. retrun msg:{resp.json()["msg"]}')
            return None
        return resp.json()['data']['freightVoNewList']


def make_random_cookie():
    chars = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
             'abcdefghijklmnopqrstuvwxyz'
             '0123456789')
    seesion = [random.choice(chars) for i in range(48)]
    return ''.join(seesion)


def create_headers_by(data_length, cookie_str):
    return {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'channel': 'P',
        'Connection': 'Keep-Alive',
        'Content-Length': str(data_length),
        'Content-Type': 'application/json',
        'Host': 'ec.95306.cn',
        'Origin': 'http://ec.95306.cn',
        'Referer': 'http://ec.95306.cn/del-query',
        'type': 'outer',
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '

                       'AppleWebKit/537.36 (KHTML, like Gecko) '

                       'Chrome/96.0.4664.110 '

                       'Safari/537.36'),
        'Cookie': cookie_str
    }


def replace_tmism_if_station_is_port_station(data):
    if data['fztmism'] == '53687':  # 沙岗--鲅鱼圈北
        return {'fztmism': '54329'}
    if data['fztmism'] == '51998':  # 渤海--金帛湾
        return {'fztmism': '54329'}
    return data


if __name__ == '__main__':
    print('ok!')
