from fee_crawler import FeeCrawler


COAL_LIST = ['风化煤', '粉煤', '蜂窝煤', '褐块煤', '褐煤',
             '混煤', '红煤粉', '块煤', '炼焦烟煤', '煤粉',
             '煤矸石', '末煤', '其他煤', '水煤浆', '筛选粉煤',
             '筛选混煤', '筛选块煤']

LOCAL_STATIONS = {
    '鲅鱼圈北': '沙岗',
    '金帛湾': '渤海',
    '珲春南': '图们',
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

    def get_freight(self, start, end, cargo, carriage, discount=0):  # pylint: disable-msg=too-many-arguments
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
        # 之后补全discount的相关部分
        discount = 1 - discount
        return self.get_freight_of_current_stations(cargo, carriage)

    def get_freight_of_current_stations(self, cargo, carriage):
        self.cargo_data = self.crawler.query_cargo_by_name(cargo)
        self.cargo = self.cargo_data['pmhz']
        self.carriage = carriage
        if carriage in ['T20', 'T40']:
            key = carriage
        else:
            key = 'bulk_' + self.cargo_data['zcjh']
        self.guotie_price_1, self.guotie_price_2, self.jj_price, self.dqh_price = PRICE_TABLE[key]
        result = [cal_func() for cal_func in self.freight_list]
        stamp_duty = get_stamp_duty(result)
        result.append(stamp_duty)
        ttl_freight = 0
        for i in result:
            ttl_freight += i[1]
        print(result)
        print(f'ttl freight: {ttl_freight}')
        return ttl_freight

    def set_from_to_stations(self, start_station=None, end_station=None):
        if start_station is None and end_station is None:
            raise KeyError('start_station and end_station不能同时为None')
        self.query_stations = (start_station, end_station)
        if start_station:
            self.start_station = LOCAL_STATIONS.get(start_station, start_station)
            self.crawler.set_start_station(self.start_station, self.available_lj)

        if end_station:
            self.end_station = LOCAL_STATIONS.get(end_station, end_station)
            self.crawler.set_end_station(self.end_station, self.available_lj)
        self.update_mile_args_by_crawler_and_reset_frieght_list()
        self.set_freight_list()
    
    def set_freight_list(self):
        if '鲅鱼圈北' in self.query_stations:
            self.append_byq_freight()
        if self.query_stations[0] == '高桥镇':
            self.append_gaoqianzhen_start_freight()
        if '金帛湾' in self.query_stations:
            self.append_jinbowan_freight()
        if '珲春南' in self.query_stations:
            self.append_hunchunnan_freight()

    def append_jinbowan_freight(self):
        if self.carriage == 'T20':
            self.freight_list.append(self.jinbowan_t20_freight)
        elif self.cargo in COAL_LIST:
            self.freight_list.append(self.jinbowan_coal_freight)
        else:
            self.freight_list.append(self.jinbowan_general_freight)

    def jinbowan_t20_freight(self):
        fee = 198 * QUANTITY_TABLE[self.carriage]
        return ['金渤运费', fee]

    def jinbowan_coal_freight(self):
        fee = 612.2 / 70 * QUANTITY_TABLE[self.carriage]
        return ['金渤运费', fee]

    def jinbowan_general_freight(self):
        fee = 556.5 / 70 * QUANTITY_TABLE[self.carriage]
        return ['金渤运费', fee]

    def append_hunchunnan_freight(self):
        raise NotImplementedError('珲春南的待完善.')

    def append_byq_freight(self):
        # 建设基金增加里程14公里
        self.jj_mile += 14
        # 其他鲅鱼圈费用
        self.freight_list.append(self.byq_fee)

    def append_gaoqianzhen_start_freight(self):
        # 高桥镇发出货物,增加货车占用费,煤炭16小时,其他8小时.
        hrs = 16 if self.cargo in COAL_LIST else 8
        self.freight_list.append(lambda: ['货车占用费', hrs * 5.7])
       
    def byq_fee(self):
        price = self.guotie_price_2 + self.dqh_price
        fee = price * 14 * QUANTITY_TABLE[self.carriage] * self.get_discount()
        fee = round(fee, 1)
        return ['沙鲅运费', fee]

    def raise_error_if_station_outof_dongbei(self, stations):
        for stn in stations:
            station_data = self.crawler.query_station_by_name(stn)
            if station_data['ljdm'] not in self.available_ljdm:
                raise NotImplementedError(f'{stn}是关内站,暂不支持.')
        return True

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
        fee = price * QUANTITY_TABLE[self.carriage] * self.get_discount()
        return ['国铁正线运费', round(fee, 1)]
        
    def get_discount(self):
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
            return ['建设基金', 0]
        fee = self.jj_price * self.jj_mile * QUANTITY_TABLE[self.carriage] * self.get_discount()
        return ['建设基金', round(fee, 1)]

    def cal_dqh_fee(self):
        if self.carriage == 'T20':
            return ['电气化费', 0.2 * QUANTITY_TABLE[self.carriage]]
        if self.carriage == 'T40':
            return ['电气化费', 0.4 * QUANTITY_TABLE[self.carriage]]
        fee = self.dqh_price * self.dqh_mile * QUANTITY_TABLE[self.carriage]
        return ['电气化费', round(fee, 1)]


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
    sum_ = 0
    for i in freight_list:
        if i[0] == '建设基金':
            continue
        if '装卸费' in i[0]:
            sum_ += round(i[1] / 106 * 100, 2)
        else:
            sum_ += round(i[1] / 109 * 100, 2)
    duty = round(sum_ * 5 / 10000, 1)
    return ['印花税', duty]


if __name__ == '__main__':
    clt = FeeCalculator()
