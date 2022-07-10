# Shipped_devices_flow
flow monitoring of shipped devices and activation ratio.

- **orders_manager_v2.py**

This is a more stable version which does not require a file. The API call returns all orders (not cancelled) and relevant details from the past 4 days.

**FIRST TIME SET UP NOTE:** 
Before running the code, a JSON authentication file needs to be in place to work with the gsheets library, the sheet itself needs to be shared with your GCP service account and have the sheet name saved under a variable called HSB_GOOGLE_SHEET. DCL_LOGIN and PASSWORDs need to be set as variables.

**Brief summary**

If left unchanged the script will run twice a day, retrieve all relevant order numbers, check if any of these orders have already been completed and remove them from the list if the program has already collected serial numbers from this order.

All order numbers left in the list are then checked for new serial number allocations. Upon collection we add the order to the completed orders csv file. 