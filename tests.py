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
    def test_guonei_station_raise_notimplementederror(self):
        cal = FeeCalculator()
        with self.assertRaises(NotImplementedError):
            cal.set_from_to_stations('四平', '古冶')

    def test_calculator_get_correct_freight(self):
        start = '元宝山'
        end = '金帛湾'
        cargo = '矿渣'
        carriage = 'C70'
        cal = FeeCalculator()
        freight = cal.get_freight(start, end, cargo, carriage)
        estimate_freight = 3322 + 1.8 + 1005.1 + 556.5
        diff = abs(freight - estimate_freight)
        self.assertTrue(diff < 0.2)


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
        crl.set_cargo('化肥')
        self.assertEqual(crl.cargo_name, '尿素(化肥)')
        self.assertEqual(crl.cargo_data['pym'], 'NSH')
        self.assertEqual(crl.cargo_code, '1310013')

    @unittest.skip('确定成功')
    def test_query_price_post_data_format_and_code_token_is_correct(self):
        crl = FeeCrawler()
        crl.set_cargo('尿素(化肥)')
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


if __name__ == '__main__':
    unittest.main()
