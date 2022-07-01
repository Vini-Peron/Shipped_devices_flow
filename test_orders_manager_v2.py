import unittest
import orders_manager_v2  # if dif directories adapt here


class TestOrdersManager_v2(unittest.TestCase):
    
    def test_get_order_date_range(self):
        self.assertIsInstance(orders_manager_v2.get_order_date_range(4), tuple)

    def test_get_current_datetime(self):
        self.assertIsInstance(orders_manager_v2.get_current_datetime(), str)


if __name__ == "__main__":
    unittest.main()
