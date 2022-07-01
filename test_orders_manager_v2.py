import unittest

import pandas as pd

import orders_manager_v2  # if dif directories adapt here




class TestOrdersManager_v2(unittest.TestCase):
    def test_get_order_date_range(self):
        self.assertIsInstance(orders_manager_v2.get_order_date_range(4), tuple)


    def test_get_current_datetime(self):
        self.assertIsInstance(orders_manager_v2.get_current_datetime(), str)


    def test_collect_order_data(self):
        pass


    def test_prep_orders_list(self):
        pass


    def test_clean_orders_list(self):
        # orders_list = pd.DataFrame(['D57787-1654041538-65B', 'D1229423-1654108182-2A8'])
        # test_orders_list = orders_manager_v2.clean_orders_list(orders_list)
        # self.assertIsInstance(test_orders_list, list)
        """
        new_orders = [i[0] for i in raw_orders_list_df if len(i) > 0]
        TypeError: object of type 'int' has no len()
        the input format may be incorrect
        """
        pass

    def test_prep_data_dump(self):
        pass

    
    def test_data_dump(self):  # currently returns None
        #self.assertIsNone(orders_manager_v2.data_dump())  # needs an input
        pass

    def test_manage_orders_list(self):  # currently returns None
        #self.assertIsNone(orders_manager_v2.manage_orders_list())  # needs an input
        pass

if __name__ == "__main__":
    unittest.main()
