import re
import logging
import requests
import copy
from datetime import datetime, timedelta

import pandas as pd
import gspread

from params.secrets import DCL_LOGIN, DCL_PASSWORD


pd.set_option('display.max_columns', None)
logging.basicConfig(filename='sn_logger.log', filemode='a', format='%(asctime)s %(message)s', level=logging.INFO)


def scan_order_num(order_num):
    """
    iterate through series to filter regex pattern matching order numbers
    for HSB and device purchases. 
    """
    return re.findall(r'D[\d]{5,7}-[\d]{10}-[a-zA-Z0-9]{3}', order_num)


def fetch_order_details(username, password, order_list):
    """
    DCL API call to fetch order details  
    """
    s = requests.Session()
    s.auth = (username, password)
    s.headers.update({'x-test': 'true'})
    raw_data = []
    for item in order_list:
      order_num = {
          "order_numbers": item
      }
      # both 'x-test' and 'x-test2' are sent
      r = s.get('https://api.dclcorp.com/api/v1/orders', headers={'x-test2': 'true'}, params=order_num)
      data = r.json()
      raw_data.append(data)
    return raw_data


def collect_serial_numbers(raw_order_data):
    device_checking_list = {}
    order_emails = {}
    # FETCH SN if available
    for order_num in raw_order_data:
        try:
            device_order = order_num['orders'][0]['order_number']
            email_address = list(order_num['orders'][0]['shipping_address'].values())[4]
            order_emails[device_order] = email_address
            device_checking_list[device_order] = {'S/Ns': []}
            #print('SHIPPING DETAILS:', order_num['orders'][0]['shipping_address'].values())
            for devices in order_num['orders']:
                for device_serial in devices['shipments'][0]['shipped_lines']:
                    # print(device_serial['item_number'])
                    # print(device_serial['description'])
                    #TODO TESTING FOR BELOW BLOCK URGENT
                    # append only completed orders i.e contain SN
                    serial_numbers = device_serial['serial_numbers'][0]
                    device_checking_list[device_order]['S/Ns'].append(serial_numbers)
                    logging.info(serial_numbers)                      
        except TypeError:
            print("S/N not assigned.")
    order_serial_dict = {}
    # remove keys with empty lists
    for key, value in device_checking_list.items():
        if len(value['S/Ns']) == 0:
            continue
        else:
            order_serial_dict[key] = value
    # merge
    for key_k, value_k in order_emails.items():
        if key_k in order_serial_dict.keys():
            order_serial_dict[key_k]['email_addr'] = value_k
            #TODO need to add tests
    return order_serial_dict


def manage_orders_list(orders_sn_dict):
    new_completed_orders = orders_sn_dict.keys()
    new_complete_orders_df = pd.DataFrame(new_completed_orders)
    print('Completed Orders:')
    print(new_complete_orders_df)
    logging.info(new_complete_orders_df)
    completed_orders_df = pd.read_csv('data/completed_hsb_orders.csv')['0']
    clean_orders = pd.concat([completed_orders_df, new_complete_orders_df], axis=0)
    clean_orders = clean_orders.reset_index(drop=True).drop_duplicates()
    pd.DataFrame(clean_orders).to_csv('data/completed_hsb_orders.csv', mode='w')
    #TODO review process, add tests, eventually migrate from csv to sql

def data_dump(orders_sn_dict):
    orders_sn_dict_copy = copy.deepcopy(orders_sn_dict)
    # pre-process new orders dict before dumping onto gsheet
    for key, value in orders_sn_dict_copy.items():
        # even out dict values' length before we turn it into a df and dump the data
        if len(value['S/Ns']) == 1:
            value['S/Ns'].append('None')
            value['S/Ns'].append('None')
        if len(value['S/Ns']) == 2:
            value['S/Ns'].append('None')
    new_orders_df = pd.DataFrame(orders_sn_dict_copy).T
    new_orders_df = new_orders_df.reset_index()
    activation_period = datetime.today() + timedelta(days=14)  # change 14 days to 10 days (email follow up after 3 days if no response.)
    new_orders_df['Activate By'] = str(activation_period)[:10]
    new_orders_df.reset_index(inplace=True, drop=True)
    new_orders_df['dev_string'] = [','.join(map(str, l)) for l in new_orders_df['S/Ns']]
    new_orders_df[['dev_1', 'dev_2', 'dev_3']] = new_orders_df['dev_string'].str.split(',', expand=True)
    new_orders_df = new_orders_df.copy()
    new_orders_df.drop(['S/Ns', 'dev_string'], axis=1, inplace=True)
    new_orders_df.columns = ['order_#', 'email_addr', 'Activate By', 'dev_1', 'dev_2', 'dev_3']
    new_orders_df = new_orders_df[['order_#', 'dev_1', 'dev_2', 'dev_3', 'Activate By', 'email_addr']]
    # read in existing orders before merge
    gc = gspread.service_account()
    sh = gc.open('hsb_orders_devices').sheet1
    existing_orders = pd.DataFrame(sh.get_all_records())
    orders_df = pd.concat([existing_orders, new_orders_df])
    sh.update([orders_df.columns.values.tolist()] + orders_df.values.tolist())


if __name__ == "__main__":
    # GET NEW ORDERS FROM FILE, GET ORDERS LIST AND DataFrame OF ORDERS TO PROCESS ONLY
    file_path = 'data/AllOrdersDCL05072022.csv'  #TODO input / argparse / fetch file directly via DCL API
    raw_df = pd.read_csv(file_path)[['Order #', "Receipt Date", "Stage Description"]]  # file to df
    raw_orders_list = raw_df['Order #'].apply(scan_order_num)  # regex out hsb and dev orders only
    new_orders = [i[0] for i in raw_orders_list if len(i) > 0]  # clean order list into list of strings of order#s
    completed_orders_list = pd.read_csv('data/completed_hsb_orders.csv')['0'].to_list()
    clean_new_orders = [ordn for ordn in new_orders if ordn not in completed_orders_list]
    # removed completed orders from new_orders list before running any checks
    new_orders_df = raw_df[raw_df['Order #'].isin(clean_new_orders)]  # update df of orders to check without completed orders
    print("ORDERS TO CHECK")
    print(new_orders_df)  # debbug/log new orders with status cli == orders to be checked
    #TODO check order date is not older than 4 days (ALERT LATE ORDER?)
    # FETCH ORDER DETAILS VIA DCL API
    raw_order_data = fetch_order_details(DCL_LOGIN, DCL_PASSWORD, clean_new_orders)
    orders_sn_dict = collect_serial_numbers(raw_order_data)
    #print(orders_sn_dict)
    if len(orders_sn_dict.keys()) > 0:
        # UPDATE COMPLETED ORDERS LIST & SEND SNs for checks (if any)
        data_dump(orders_sn_dict) # dumps completed orders with serial numbers onto gsheet
        manage_orders_list(orders_sn_dict)  # completed orders to file
    else:
        print('No orders completed this run.')
    print("All Done")
    #TODO need to handle bundled orders?
    #TODO Implement CE HSB dashboard
    