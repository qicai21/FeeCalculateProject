import unittest
from fee_crawler import FeeCrawler
from fee_calculator import FeeCalculator


class CalculatorTest(unittest.TestCase):
    @unittest.skip('确定成功')
    def test_can_get_correct_miles_args(self):
        cal = FeeCalculator()
        cal.set_from_to_stations('高桥镇', '四平')
        self.assertEqual(cal.guotie_mile, 460)
        self.assertEqual(cal.jj_mile, 460)
        self.assertEqual(cal.dqh_mile, 460)

    @unittest.skip('确定成功')
    def test_calculator_create_diff_freight_list_by_station(self):
        cal = FeeCalculator()
        cal.set_from_to_stations('四平', '沙岗')
        freight_list_1 = cal.freight_list
        jjlc_1 = cal.jj_mile
        cal.set_from_to_stations('四平', '鲅鱼圈北')
        freight_list_2 = cal.freight_list
        jjlc_2 = cal.jj_mile
        self.assertNotEqual(freight_list_1, freight_list_2)
        self.assertEqual(jjlc_2 - jjlc_1, 14)

    @unittest.skip('确定成功')
    def test_guonei_station_raise_attributeerror(self):
        cal = FeeCalculator()
        with self.assertRaises(AttributeError):
            cal.set_from_to_stations('四平', '古冶')

    @unittest.skip
    def test_calculator_get_correct_freight(self):
        start = '元宝山'
        end = '金帛湾'
        cargo = '矿渣'
        carriage = 'C70'
        cal = FeeCalculator()
        freight = cal.get_freight(start, end, cargo, carriage)
        estimate_freight = 3322 + 1.8 + 1005.1 + 556.5
        diff = abs(freight['运费总价'] - estimate_freight)
        self.assertTrue(diff < 0.2)

    @unittest.skip
    def test_support_loading_usage_subline_fee(self):
        # loading fee: 装卸费, usage fee:集装箱使用费, subline fee 专用线取送车费.
        start = '高桥镇'
        end = '松原'
        subline = '嘉吉生化有限公司专用线'
        cargo = '尿素(化肥)'
        carriage = 'T20'
        cal = FeeCalculator()
        freight = cal.get_freight(start, end, cargo, carriage,
                                  end_subline=subline,
                                  end_station_discharge=True)
        est_freight_items = [
            '运费总价', '基础运费', '铁路建设基金', '电气化附加费',
            '集装箱使用费', '到站取送车费', '到站装卸费', '印花税'
        ]
        self.assertListEqual(list(freight), est_freight_items)
        '''
        est_freight = 5455.6
        est_stamp = 2.5
        est_jj = 759.8
        est_usage = 130
        est_subline_fee = 81
        est_discharge_fee = 390
        '''
        est_ttl = 5455.6 + 2.5 + 759.8 + 130 + 81 + 390
        self.assertTrue(abs(freight['运费总价'] - est_ttl) < 0.2)

    def test_get_freight_item_return_correct_discount(self):
        item_rates = {'基础运费': 0.4, '铁路建设基金': 0.4, '电气化附加费': 1,
                      '集装箱使用费': 0, '到站取送车费': 1, '到站装卸费': 0.7}
        cal = FeeCalculator()
        cal.cargo = '铁矿粉'
        cal.discount_rate = 0.4
        rate_list = [cal.get_discount_by_item(name) for name in item_rates]
        self.assertListEqual(rate_list, list(item_rates.values()))
        cal.cargo = '原煤'
        discharge_discount = cal.get_discount_by_item('到站装卸费')
        self.assertEqual(discharge_discount, 0.5)

    def test_freight_calculated_with_discount_rate(self):
        rate = '60'
        start = '高桥镇'
        end = '四平'
        cargo = '铁矿粉'
        carriage = 'TBJU35'
        cal = FeeCalculator()
        freight = cal.get_freight(start, end, cargo,
                                  carriage, discount_rate=rate,
                                  end_station_discharge=True)
        estimate_freight = 2422.5
        print(freight)
        self.assertTrue(abs(freight['运费总价'] - estimate_freight) <= 0.2)


class CrawlerTest(unittest.TestCase):
    @unittest.skip('确定成功')
    def test_crawler_can_refresh_cookie_code_and_token(self):
        crl = FeeCrawler()
        cookie = crl.cookie
        code = crl.query_code
        token = crl.token
        crl.refresh_query_code_and_cookie()
        self.assertNotEqual(cookie, crl.cookie)
        self.assertNotEqual(code, crl.query_code)
        self.assertNotEqual(token, crl.token)

    @unittest.skip('确定成功')
    def test_query_cargo_names(self):
        crl = FeeCrawler()
        content = crl.send_cargo_name_request('化肥')
        self.assertEqual(content['msg'], 'OK')

    @unittest.skip('确定成功')
    def test_query_station_and_set_station_info(self):
        crl = FeeCrawler()
        crl.set_start_station('高桥')
        self.assertEqual(crl.start_lj_code, '00002')
        self.assertEqual(crl.start_lj_data['qc'], '沈阳局')
        self.assertEqual(crl.start_lj_data['dm'], 'T00')
        self.assertEqual(crl.start_station_name, '高桥镇')
        self.assertEqual(crl.start_station_data['tmism'], '51632')

    @unittest.skip('确定成功')
    def test_popup_station_selection_if_queried_multi_record(self):
        crl = FeeCrawler()
        station = crl.query_station_by_name('高')
        self.assertEqual(station['hzzm'], '高桥镇')

    @unittest.skip('确定成功')
    def test_query_cgo_and_set_cgo_data(self):
        crl = FeeCrawler()
        crl.set_cargo_by_name('化肥')
        self.assertEqual(crl.cargo_name, '尿素(化肥)')
        self.assertEqual(crl.cargo_data['pym'], 'NSH')
        self.assertEqual(crl.cargo_code, '1310013')

    @unittest.skip('确定成功')
    def test_query_price_post_data_format_and_code_token_is_correct(self):
        crl = FeeCrawler()
        crl.set_cargo_by_name('尿素(化肥)')
        crl.set_start_station('高桥镇')
        crl.set_end_station('四平')
        formated_data_keys = [
            'flj', 'dlj', 'hw', 'fzhzzm', 'fzObj', 'dzhzzm', 'dzObj',
            'hwmcObj', 'hwmc', 'plObj', 'pl', 'xplObj', 'xpl', 'code',
            'token', 'dz', 'dzljm', 'dztlzx', 'fz', 'fzljm', 'fztlzx',
            'hzpm', 'pm', 'shsm', 'smqh', 'smxc', 'smzc', 'fsqhlc', 'ddqhlc'
        ]
        data = crl.get_post_data()
        print(crl.cookie)
        print(data['code'])
        print(data['token'])
        self.assertEqual(set(data.keys()), set(formated_data_keys))
        self.assertIsNotNone(data['code'])
        self.assertIsNotNone(data['token'])

    @unittest.skip
    def test_query_crt_fee_successful(self):
        crl = FeeCrawler()
        crl.set_start_station('高桥镇')
        crl.set_end_station('四平')
        result = crl.query_crt_fee_by_cargo('尿素(化肥)')
        bulk_freight_ttl = result[0]['totalCost']
        self.assertEqual(float(bulk_freight_ttl), 3812.10)

    @unittest.skip
    def test_query_subline_return_name_and_mile(self):
        crl = FeeCrawler()
        crl.set_start_station('高桥镇')
        crl.set_end_station('元宝山')
        subline, mile = crl.query_subline_miles('end')
        self.assertEqual(subline, '内蒙古平庄煤业（集团）有限责任公司专用铁路')
        self.assertEqual(mile, 0)

    @unittest.skip
    def test_set_load_fee_then_get_correct_post_data(self):
        crl = FeeCrawler()
        crl.start_station_load = True
        post_data = crl.get_post_data()
        self.assertEqual(post_data['fztlzx'], '1')

    @unittest.skip
    def test_query_load_fee(self):
        crl = FeeCrawler()
        crl.set_start_station('高桥镇')
        crl.set_end_station('元宝山')
        cargo_data = {
            "dm": "0410013", "pym": "TKS", "pmhz": "铁矿石", "ldjh": "21",
            'wpdm': 'null', 'jzz': 'null', 'ifszjf': 'null', 'plhz': 'null',
            "jzxjh": "0", "zcjh": "4", "shpmsspmdm": "0410013", "ifshpm": "0",
            "shpmhz": "铁矿石", "shpmpym": "TKS"
        }
        crl.set_cargo_by_data(cargo_data)
        crl.start_station_load = True
        cost_list = crl.query_crt_fee()
        print(cost_list)
        self.assertEqual(float(cost_list[0]['loadCost']) / 60, 15.1)


if __name__ == '__main__':
    unittest.main()
