from fee_crawler import FeeCrawler


class FeeCalculator:
    def __init__(self):
        self.start_station = None
        self.end_station = None
        self.guotie_mile = 0
        self.jj_mile = 0
        self.dqh_mile = 0
        self.crawler = FeeCrawler()

    def set_from_to_stations(self, start_station=None, end_station=None):
        if start_station is None and end_station is None:
            raise KeyError('start_station and end_station不能同时为None')
        if start_station:
            self.start_station = start_station
            self.crawler.set_start_station(start_station)
        if end_station:
            self.end_station = end_station
            self.crawler.set_end_station(end_station)
        self.update_mile_args_by_crawler()

    def update_mile_args_by_crawler(self):
        kz_fee = self.get_bulk_fee('矿渣')
        tks_fee = self.get_bulk_fee('铁矿石')
        nsh_fee = self.get_bulk_fee('尿素(化肥)')
        self.guotie_mile = get_guotie_mile(tks_fee, kz_fee)
        self.jj_mile = get_jj_mile(tks_fee, nsh_fee)
        self.dqh_mile = get_dqh_mile(self.guotie_mile, nsh_fee)

    def get_bulk_fee(self, cargo):
        fee_list = self.crawler.query_calculate_base_fee(cargo)
        fee = [i['estimateCost'] for i in fee_list if i['name'] == '整车']
        return float(fee[0])


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
