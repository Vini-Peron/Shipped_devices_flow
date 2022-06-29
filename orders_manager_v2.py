import re
import requests
from datetime import datetime, timedelta
from time import sleep
import copy
import logging

import pandas as pd
import gspread

from params.secrets import DCL_LOGIN, DCL_PASSWORD


logging.basicConfig(
    filename='data/sn_logger_v2.log', 
    filemode='a', 
    format='%(asctime)s %(message)s', 
    level=logging.INFO
    )

COMPLETED_ORDERS_PATH = 'completed_hsb_orders_test.csv'


def get_order_date_range(range): 
    to_date = datetime.today()
    from_date = to_date - timedelta(days=range)
    return str(from_date)[:10], str(to_date)[:10]


def get_current_datetime():
    time_now = datetime.now()
    return str(time_now)[11:16]


def get_all_orders(username, password, from_date, to_date, order_status=0):
    """
    DCL API call to fetch order details
    received_from 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS'.
    received_to 'YYYY-MM-DD'
    status == 0 returns orders in any status except cancelled. (default)
    status == 1 returns Open orders which never have SNs assigned
    status == 2 returns cancelled orders
    status == 3 returns shipped orders (this seems to always return the same orders regardless)
    """
    s = requests.Session()
    s.auth = (username, password)
    s.headers.update({'x-test': 'true'})
    raw_data = []
    order_params = {'status':order_status, 'received_from':from_date, 'received_to':to_date}
    # both 'x-test' and 'x-test2' are sent

    r = s.get(
        'https://api.dclcorp.com/api/v1/orders', 
        headers={'x-test2': 'true'}, 
        params=order_params,
        )
    data = r.json()
    raw_data.append(data)
    return raw_data


def filter_order_num(order_num):
    """
    iterate through series to filter regex pattern matching order numbers
    for HSB and device purchases.
    #TODO check if regex covers all possible order numbers required
    #TODO check below pattern with -R at the end.
    """
    return re.findall(r'D[\d]{5,7}-[\d]{10}-[a-zA-Z0-9]{3}', order_num)


def collect_order_data(all_orders_raw, orders_list):
    orders_dict = {}
    for order_dict in all_orders_raw:  # api call response
        for order in order_dict['orders']:
            order_number = order['order_number']
            try:
                if order_number in orders_list:
                    stage_description = order['stage_description']
                    order_date = order['received_date']
                    email_address = list(order['shipping_address'].values())[4]
                    serial_numbers = order['shipments'][0]['shipped_lines'][0]['serial_numbers']
                    orders_dict[order_number] = {
                    'order_date': order_date, 
                    'stage_description': stage_description,
                    'email_address': email_address,
                    'serial_numbers': serial_numbers,
                    }
            except TypeError:
                print(f"No S/N assigned for order # {order_number}")
               
    for key, value in orders_dict.items():
        # even out dict values' length before we turn it into a df and dump the data
        if len(value['serial_numbers']) == 1:
            value['serial_numbers'].append('None')
            value['serial_numbers'].append('None')
        if len(value['serial_numbers']) == 2:
            value['serial_numbers'].append('None')
    return orders_dict


def prep_orders_list(all_orders_raw): 
    all_order_numbers_within_range = []
    for order_dict in all_orders_raw:
        for order in order_dict['orders']:
            order_number = order['order_number']
            all_order_numbers_within_range.append(order_number)
    #logging.info(f'all orders fetched - {all_order_numbers_within_range}')  #debugger
    raw_df = pd.DataFrame(all_order_numbers_within_range)
    raw_df.columns = ['Order #']
    return raw_df


def clean_orders_list(raw_orders_list):
    new_orders = [i[0] for i in raw_orders_list if len(i) > 0]
    completed_orders_list = pd.read_csv(COMPLETED_ORDERS_PATH)['0'].to_list()
    clean_new_orders = [ordn for ordn in new_orders if ordn not in completed_orders_list]
    return clean_new_orders


def data_dump(orders_sn_dict, activation_date_range):
    orders_sn_dict_copy = copy.deepcopy(orders_sn_dict)
    # pre-process new orders dict before dumping onto gsheet
    new_orders_df = pd.DataFrame(orders_sn_dict_copy).T
    new_orders_df = new_orders_df.reset_index()
    activation_period = datetime.today() + timedelta(days=activation_date_range)  # change 14 days to 10 days (email follow up after 3 days if no response.)
    new_orders_df['Activate By'] = str(activation_period)[:10]
    new_orders_df.reset_index(inplace=True, drop=True)
    if len(new_orders_df.index) > 0:
        new_orders_df['dev_string'] = [','.join(map(str, l)) for l in new_orders_df['serial_numbers']]
        new_orders_df[['dev_1', 'dev_2', 'dev_3']] = new_orders_df['dev_string'].str.split(',', expand=True)
        new_orders_df = new_orders_df.copy()
        new_orders_df.drop(
            ['serial_numbers', 'dev_string', 'order_date', 'stage_description'], 
                axis=1, 
                inplace=True
                )
        new_orders_df.columns = ['order_#', 'email_addr', 'Activate By', 'dev_1', 'dev_2', 'dev_3']
        new_orders_df = new_orders_df[['order_#', 'dev_1', 'dev_2', 'dev_3', 'Activate By', 'email_addr']]
        print(new_orders_df)
        # read in existing orders before merging new completed orders
        gc = gspread.service_account()
        sh = gc.open('test_hsb_data_dump').sheet1  # TEST SHEET ON
        existing_orders = pd.DataFrame(sh.get_all_records())
        orders_df = pd.concat([existing_orders, new_orders_df])
        sh.update([orders_df.columns.values.tolist()] + orders_df.values.tolist())
    else:
        print("No records to dump")
    print("Data Dump complete.")


def manage_orders_list(orders_sn_dict):
    new_completed_orders = orders_sn_dict.keys()
    logging.info(f"Completed {list(new_completed_orders)}")
    new_complete_orders_df = pd.DataFrame(new_completed_orders)
    completed_orders_df = pd.read_csv(COMPLETED_ORDERS_PATH)['0']
    clean_orders = pd.concat([completed_orders_df, new_complete_orders_df], axis=0)
    clean_orders = clean_orders.reset_index(drop=True).drop_duplicates()
    pd.DataFrame(clean_orders).to_csv(COMPLETED_ORDERS_PATH, mode='w')
    print("Completed Orders Updated.")
    #TODO review process, add tests, eventually migrate from csv to sql

def main():
    from_date, to_date = get_order_date_range(28)  # range of days to filter from present day
    print(f"Dates range From: {from_date}, To: {to_date}")

    order_stages = [0, 1, 3]
    for ord_stage in order_stages:
        print(f'calling order status: {ord_stage}')
        all_orders_raw = get_all_orders(
            DCL_LOGIN, DCL_PASSWORD,
            from_date, to_date, 
            order_status=ord_stage
            )
        raw_df = prep_orders_list(all_orders_raw)
        raw_orders_list = raw_df['Order #'].apply(filter_order_num)
        clean_new_orders = clean_orders_list(raw_orders_list)
        if len(clean_new_orders) > 0:
            new_orders_dict = collect_order_data(all_orders_raw, clean_new_orders)
            if len(new_orders_dict.keys()) > 0:
                data_dump(new_orders_dict, activation_date_range=14)  # completed orders to gsheet
                manage_orders_list(new_orders_dict)  # completed orders to file
            else:
                print('No orders to update.')
        else:
            print('No orders to complete.')


if __name__ == "__main__":
    current_time = get_current_datetime()
    print(f'Initiated loop {current_time}')
    try:
        while True:
            current_time = get_current_datetime()
            print(f"Clock-check at {current_time}")
            if current_time == '08:00' or current_time == '09:34':  #TODO check only hour-digits so it can sleep for an hour
                main()
                sleep(60)  # run the programm only once 
            else:
                sleep(60)  # check every minute if its time to run
    except KeyboardInterrupt:
        print('loop terminated')
