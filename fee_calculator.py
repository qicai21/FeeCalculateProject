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

class FeeCalculator:
    def __init__(self):
        self.available_ljdm = ['B00', 'T00']  # 目前只支持沈哈两局
        self.freight_list = None
        self.start_station = None
        self.query_stations = None
        self.end_station = None
        self.guotie_mile = 0
        self.jj_mile = 0
        self.dqh_mile = 0
        self.crawler = FeeCrawler()
        self.cargo = ''
        self.carriage = None

    def set_from_to_stations(self, start_station=None, end_station=None):
        if start_station is None and end_station is None:
            raise KeyError('start_station and end_station不能同时为None')
        self.query_stations = (start_station, end_station)
        self.raise_error_if_station_outof_dongbei([start_station, end_station])
        if start_station:
            self.start_station = LOCAL_STATIONS.get(start_station, start_station)
            self.crawler.set_start_station(self.start_station)

        if end_station:
            self.end_station = LOCAL_STATIONS.get(end_station, end_station)
            self.crawler.set_end_station(self.end_station)
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
        if self.carriage != 'bulk':
            raise KeyError('不支持的运输类型,待完善.')
        if self.carriage == 'T20':
            fee = 198 * self.quantity
        elif self.cargo in COAL_LIST:
            fee = 612.2 / 70 * self.quantity
        else:
            fee = 556.5 / 70 * self.quantity
        self.freight_list.append(lambda: {'金渤运费': fee})

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
        self.freight_list.append(lambda: {'货车占用费': hrs * 5.7})
       
    def byq_fee(self):
        price = self.guotie_price[1] + self.dqh_price
        fee = price * 14 * self.quantity * self.get_discount()
        fee = round(fee, 1)
        return {'沙鲅运费': fee}

    def raise_error_if_station_outof_dongbei(self, stations):
        for st in stations:
            station_data = self.crawler.query_station_by_name(st)
            if station_data['ljdm'] not in self.available_ljdm:
                raise NotImplementedError(f'{st}是关内站,暂不支持.')
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
        price = self.guotie_price[0] + self.guotie_price[1] * self.guotie_mile
        fee = price * self.quantity * self.get_discount()
        return {'国铁正线运费': round(fee, 1)}
        
    def get_discount(self):
        if self.carriage == 'T20':
            return 1 - 0.9 / 100
        if self.carriage == 'T35':
            return 1 - 0.89 / 100
        if self.carriage != 'bulk':
            raise KeyError('不支持的运输类型,待完善.')
        if self.cargo in COAL_LIST:
            return 1 + 8.04 / 100
        return 1 - 1.78 / 100

    def cal_jj_fee(self):
        if '化肥' in self.cargo:
            return 0
        fee = self.jj_price * self.jj_mile * self.quantity * self.get_discount()
        return {'建设基金': round(fee, 1)}

    def cal_dqh_fee(self):
        fee = self.dqh_price * self.dqh_mile * self.quantity
        return {'电气化费': round(fee, 1)}


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


if __name__ == '__main__':
    clt = FeeCalculator()
