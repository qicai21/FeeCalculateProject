from fee_crawler import FeeCrawler


DISCOUNT_DATA_LIST = {
    'sy220808a': {'基础运费': 0.4, '铁路建设基金': 0.4, '电气化附加费': 1,
                  '集装箱使用费': 0, '发站取送车费': 1, '到站取送车费': 1,
                  '发站装卸费': 0.7, '到站装卸费': 0.7},
}

COAL_LIST = ['风化煤', '粉煤', '蜂窝煤', '褐块煤', '褐煤',
             '混煤', '红煤粉', '块煤', '炼焦烟煤', '煤粉',
             '煤矸石', '末煤', '其他煤', '水煤浆', '筛选粉煤',
             '筛选混煤', '筛选块煤', '原煤']

LOCAL_STATION_DATA = {
    '鲅鱼圈北': {
        'tmism': '53687', 'dbm': 'SGT', 'hzzm': '沙岗', 'pym': 'SG',
        'ljdm': 'T00', 'ljqc': '沈阳局', 'dzm': '02', 'ljm': '00002'
    },
    '金帛湾': {
        "tmism": "51998", "dbm": "BED", "hzzm": "渤海", "pym": "BH",
        "ljdm": "T00", "ljqc": "沈阳局", "dzm": "02", "ljm": "00002"
    },
    '珲春南': {
        'tmism': '62465', 'dbm': 'TML', 'hzzm': '图们', 'pym': 'TM',
        'ljdm': 'T00', 'ljqc': '沈阳局', 'dzm': '02', 'ljm': '00002'
    },
}

PRICE_TABLE = {
    'bulk_2': [9.5, 0.086, 0.033, 0.007],
    'bulk_3': [12.8, 0.091, 0.033, 0.007],
    'bulk_4': [16.3, 0.098, 0.033, 0.007],
    'bulk_5': [18.6, 0.103, 0.033, 0.007],
    'bulk_6': [26, 0.138, 0.033, 0.007],
    'T20': [440, 3.185, 0.528, 0.112],
    'T40': [532, 3.357, 1.122, 0.238]
}

QUANTITY_TABLE = {
    'T20': 2,
    'T40': 1,
    'C60': 60,
    'C61': 61,
    'C70': 70,
    'TBJU35': 64
}

PORTS = ['鲅鱼圈北', '金帛湾', '高桥镇', '马仗房']


class FeeCalculator:  # pylint: disable-msg=too-many-instance-attributes
    def __init__(self):
        self.crawler = FeeCrawler()
        self.available_lj = ['沈阳局', '哈尔滨局']  # 目前只支持沈哈两局
        self.freight_list = None
        self.query_stations = None
        self.start_station = None
        self.end_station = None
        self.guotie_mile = 0
        self.jj_mile = 0
        self.dqh_mile = 0
        self.cargo = ''
        self.cargo_data = None
        self.carriage = None
        self.guotie_price_1 = 0
        self.guotie_price_2 = 0
        self.jj_price = 0
        self.dqh_price = 0
        self.start_subline = None
        self.end_subline = None
        self.discount_rate = 1
        self.discount_no = None

    def get_freight(self, start, end, cargo, carriage,  # pylint: disable-msg=too-many-arguments
                    discount_rate=1, discount_no=None,
                    start_subline=None, end_subline=None,
                    start_station_load=False, end_station_discharge=False):
        self.carriage = carriage  # 因为锦州港的货车占用费与运输方式有关,敞车有,集装箱没有,所以,此处要预加载carriage.
        if self.query_stations is None:
            self.set_from_to_stations(start, end)
        elif self.query_stations[0] != start and self.query_stations[1] == end:
            self.set_from_to_stations(start, None)
        elif self.query_stations[0] == start and self.query_stations[1] != end:
            self.set_from_to_stations(None, end)
        elif self.query_stations[0] != start and self.query_stations[1] != end:
            self.set_from_to_stations(start, end)
        else:
            pass
        return self.get_freight_of_current_stations(
            cargo, carriage, discount_rate, discount_no,
            start_subline, end_subline,
            start_station_load, end_station_discharge
        )

    def get_freight_of_current_stations(
        self, cargo, carriage,
        discount_rate=1, discount_no=None,
        start_subline=None, end_subline=None,
        start_station_load=False, end_station_discharge=False
    ):  # pylint: disable-msg=too-many-arguments
        """
        发到站如果是港口,则无论该站装卸费是否为True都不计算.
        计算装卸费就添加装卸费的计算方法.
        如果是集装箱就添加集装箱使用费的计算方法.
        如果有专用线就添加专用线的计算方法.
        """

        self.cargo_data = self.crawler.query_cargo_by_name(cargo)
        self.cargo = self.cargo_data['pmhz']
        self.carriage = carriage
        self.set_discount_rate(discount_rate, discount_no)
        if carriage in ['T20', 'T40']:
            key = carriage
        else:
            key = 'bulk_' + self.cargo_data['zcjh']
        self.guotie_price_1, self.guotie_price_2, self.jj_price, self.dqh_price = PRICE_TABLE[key]
        if self.carriage in ['T20', 'T40', 'TBJU35']:
            self.freight_list.append(self.container_usage_fee)
        if start_subline:
            self.start_subline = start_subline
            self.freight_list.append(self.start_subline_fee)
        if end_subline:
            self.end_subline = end_subline
            self.freight_list.append(self.end_subline_fee)
        if start_station_load and self.start_station not in PORTS:
            self.freight_list.append(self.start_load_fee)
        if end_station_discharge and self.end_station not in PORTS:
            self.freight_list.append(self.end_discharge_fee)
        result = [cal_func() for cal_func in self.freight_list]
        stamp_duty = get_stamp_duty(result)
        result.append(stamp_duty)
        ttl_freight = 0
        for i in result:
            ttl_freight += i[1]
        ttl_freight = round(ttl_freight, 1)
        freight_table = {
            '运费总价': ttl_freight,
        }
        for i in result:
            freight_table[i[0]] = i[1]
        return freight_table

    def calculate_discount_with_one_decimal(self, fee_name, fee_value):
        rate = self.get_discount_by_item(fee_name)
        fee = round(fee_value * rate, 1)
        return [fee_name, fee]

    def start_subline_fee(self):
        fee = self.query_subline_fee('start', self.start_subline)
        return self.calculate_discount_with_one_decimal('发站取送车费', fee)

    def end_subline_fee(self):
        fee = self.query_subline_fee('end', self.end_subline)
        return self.calculate_discount_with_one_decimal('到站取送车费', fee)

    def query_subline_fee(self, start_or_end, subline):
        result = self.crawler.query_subline_miles(start_or_end, subline)
        if result:
            name, miles = result
            if start_or_end == 'start':
                self.start_subline = name
            if start_or_end == 'end':
                self.end_subline = name
            miles = miles * 2 / 1000
            if miles % 1 != 0:
                miles = int(miles) + 1
            return round(8.1 * miles, 1)
        return 0

    def start_load_fee(self):
        fee = self.query_load_fee('start')
        return self.calculate_discount_with_one_decimal('发站装卸费', fee)

    def end_discharge_fee(self):
        fee = self.query_load_fee('end')
        return self.calculate_discount_with_one_decimal('到站装卸费', fee)
    
    def query_load_fee(self, start_or_end):
        if self.carriage == 'T40':
            fee = 292.5
        elif self.carriage in ['T20', 'TBJU35']:
            fee = 390
        elif self.carriage in ['C60', 'C61', 'C70']:
            weight = int(self.carriage[1:])
            if start_or_end == 'start':
                self.crawler.start_station_load = True
                self.crawler.end_station_discharge = False
            if start_or_end == 'end':
                self.crawler.start_station_load = False
                self.crawler.end_station_discharge = True
            self.crawler.set_cargo_by_data(self.cargo_data)
            data = self.crawler.query_crt_fee()
            fee = float(data[0]['loadCost']) / 60 * weight
        else:
            raise KeyError('运输方式设置有误,查询装卸费失败')
        return round(fee, 1)

    def container_usage_fee(self):
        cost = 70
        remains = self.guotie_mile - 250
        for station in self.query_stations:
            if station in LOCAL_STATION_DATA:
                remains += get_local_contaion_usage_miles(station)
        while remains > 0:
            cost += 12
            remains -= 100
        return self.calculate_discount_with_one_decimal('集装箱使用费', cost)

    def set_from_to_stations(self, start_station=None, end_station=None):
        if start_station is None and end_station is None:
            raise KeyError('start_station and end_station不能同时为None')
        self.query_stations = (start_station, end_station)
        if start_station:
            start_stn_data = LOCAL_STATION_DATA.get(start_station)
            self.start_station = start_stn_data['hzzm'] if start_stn_data else start_station
            self.crawler.set_start_station(self.start_station, self.available_lj, start_stn_data)

        if end_station:
            end_stn_data = LOCAL_STATION_DATA.get(end_station)
            self.end_station = end_stn_data['hzzm'] if end_stn_data else end_station
            self.crawler.set_end_station(self.end_station, self.available_lj, end_stn_data)
        self.update_mile_args_by_crawler_and_reset_frieght_list()
        self.set_freight_list()
    
    def set_freight_list(self):
        if '鲅鱼圈北' in self.query_stations:
            self.append_byq_freight()
        if self.query_stations[0] == '高桥镇':
            self.append_gaoqiaozhen_start_freight()
        if '金帛湾' in self.query_stations:
            self.append_jinbowan_freight()
        if '珲春南' in self.query_stations:
            self.append_hunchunnan_freight()

    def append_jinbowan_freight(self):
        self.freight_list.append(self.jinbowan_fee)

    def jinbowan_fee(self):
        if self.carriage == 'T20':
            fee = 198 * QUANTITY_TABLE[self.carriage]
        elif self.cargo in COAL_LIST:
            fee = 612.2 / 70 * QUANTITY_TABLE[self.carriage]
        else:
            fee = 556.5 / 70 * QUANTITY_TABLE[self.carriage]
        return self.calculate_discount_with_one_decimal('金渤运费', fee)

    def append_hunchunnan_freight(self):
        raise NotImplementedError('珲春南的待完善.')

    def append_byq_freight(self):
        # 铁路建设基金增加里程14公里
        self.jj_mile += 14
        # 其他鲅鱼圈费用
        self.freight_list.append(self.byq_fee)

    def append_gaoqiaozhen_start_freight(self):
        if self.carriage in ['C60', 'C61', 'C70']:
            self.freight_list.append(self.gaoqiaozhen_occupy_fee)

    def gaoqiaozhen_occupy_fee(self):
        # 高桥镇发出货物,增加货车占用费,煤炭和尿素化肥16小时,其他8小时,集装箱免收.
        hrs = 16 if self.cargo in COAL_LIST else 16 if '化肥' in self.cargo else 8
        return self.calculate_discount_with_one_decimal('货车占用费', hrs * 5.7)
       
    def byq_fee(self):
        price = self.guotie_price_2
        if self.carriage in ['C60', 'C61', 'C70', 'TBJU35']:
            price += self.dqh_price
        fee = price * 14 * QUANTITY_TABLE[self.carriage] * self.get_base_rate()
        return self.calculate_discount_with_one_decimal('沙鲅运费', fee)

    def update_mile_args_by_crawler_and_reset_frieght_list(self):
        kz_fee = self.get_bulk_fee('矿渣')
        tks_fee = self.get_bulk_fee('铁矿石')
        nsh_fee = self.get_bulk_fee('尿素(化肥)')
        self.guotie_mile = get_guotie_mile(tks_fee, kz_fee)
        self.jj_mile = get_jj_mile(tks_fee, nsh_fee)
        self.dqh_mile = get_dqh_mile(self.guotie_mile, nsh_fee)
        self.freight_list = [self.cal_guotie_fee, self.cal_jj_fee, self.cal_dqh_fee]

    def get_bulk_fee(self, cargo):
        fee_list = self.crawler.query_calculate_base_fee(cargo)
        fee = [i['estimateCost'] for i in fee_list if i['name'] == '整车']
        return float(fee[0])

    def cal_guotie_fee(self):
        price = self.guotie_price_1 + self.guotie_price_2 * self.guotie_mile
        fee = price * QUANTITY_TABLE[self.carriage] * self.get_base_rate()
        return self.calculate_discount_with_one_decimal('基础运费', fee)
        
    def get_base_rate(self):
        """基础费率,区别于下浮."""
        if self.carriage == 'T20':
            return 1 - 0.9 / 100
        if self.carriage == 'TBJU35':
            return 1 - 0.89 / 100
        if self.carriage not in ['C60', 'C61', 'C70']:
            raise KeyError('不支持的运输类型,待完善.')
        if self.cargo in COAL_LIST:
            return 1 + 8.04 / 100
        return 1 - 1.78 / 100

    def cal_jj_fee(self):
        if (self.carriage in ['C60', 'C61', 'C70', 'TBJU35']) and ('化肥' in self.cargo):
            return ['铁路建设基金', 0]
        fee = self.jj_price * self.jj_mile * QUANTITY_TABLE[self.carriage] * self.get_base_rate()
        return self.calculate_discount_with_one_decimal('铁路建设基金', fee)

    def cal_dqh_fee(self):
        if self.carriage == 'T20':
            fee = 0.2 * QUANTITY_TABLE[self.carriage]
        elif self.carriage == 'T40':
            fee = 0.4 * QUANTITY_TABLE[self.carriage]
        else:
            fee = self.dqh_price * self.dqh_mile * QUANTITY_TABLE[self.carriage]
        return self.calculate_discount_with_one_decimal('电气化附加费', fee)

    def set_discount_rate(self, discount_rate=None, discount_no=None):
        if discount_no:
            self.discount_no = discount_no.lower()
            self.discount_rate = DISCOUNT_DATA_LIST.get(self.discount_no)['基础运费']
        elif discount_rate is None:
            raise ValueError('discount_rate and discount_no can be None at same time.')
        else:
            if isinstance(discount_rate, float) and discount_rate < 1:
                self.discount_rate = discount_rate
            elif isinstance(discount_rate, str):
                self.discount_rate = (1 - int(discount_rate) / 100)
            elif type(discount_rate) in [int, float] and discount_rate > 1:
                self.discount_rate = (1 - discount_rate / 100)
            else:
                raise ValueError('discount_rate类型有误,应为: float, int, str. int&str参考下浮比例,float是计算用值.')
                
    def get_discount_by_item(self, item_name):
        """
        基础运费 = F * (1-rate / 100)
        铁路建设基金 = JJ * (1-rate / 100)
        其他区段运费 = f * (1-rate / 100)
        dqh = dqh * 1
        集装箱使用费 = U * (1 - rate != 0)
        货车占用费 = Oc * 1
        取送车费 = QS * 1
        装卸费 = 0.5 煤炭类,其他0.7
        """
        if self.discount_no:
            discount_data = DISCOUNT_DATA_LIST.get(self.discount_no)
            if discount_data:
                return discount_data.get(item_name, 1)
            raise AttributeError('设置了下浮号,但没有匹配的下浮数据.')
        # 没有下浮号的使用常规下浮比例进行计算
        if self.discount_rate == 1:
            return 1
        if '运费' in item_name or item_name == '铁路建设基金':
            return self.discount_rate
        if item_name == '集装箱使用费':
            return 0
        if '装卸费' in item_name:
            return 0.5 if self.cargo in COAL_LIST else 0.7
        return 1


def get_guotie_mile(tks_fee, kz_fee):
    mile = ((tks_fee - kz_fee) / (1 - 1.78 / 100) / 60 - (16.3 - 9.5)) / (0.098 - 0.086)
    return int(round(mile, 0))


def get_jj_mile(tks_fee, nsh_fee):
    mile = (tks_fee - nsh_fee) / (1 - 1.78 / 100) / 0.033 / 60
    return int(round(mile, 0))


def get_dqh_mile(guotie_mile, nsh_fee):
    p_1 = 16.3
    p_2 = 0.098
    p_dqh = 0.007
    guotie_fee = (p_1 + p_2 * guotie_mile) * (1 - 1.78 / 100)
    mile = (nsh_fee / 60 - guotie_fee) / p_dqh
    return int(round(mile, 0))


def get_stamp_duty(freight_list):
    cost = 0
    for i in freight_list:
        if '运费' in i[0] or (i[0] == '电气化附加费'):
            cost += i[1]
    duty = round((cost * 100 / 109) * 5 / 10000, 1)
    return ['印花税', duty]


def get_local_contaion_usage_miles(station):
    miles_table = {
        '鲅鱼圈北': 14,
        '金帛湾': 48,
        '珲春南': 73,
    }
    return miles_table[station]


if __name__ == '__main__':
    clt = FeeCalculator()
