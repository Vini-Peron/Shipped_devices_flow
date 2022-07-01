# Shipped_devices_flow
flow monitoring of shipped devices and activation ratio

- **orders_manager.py**

is a trial prototype which requires a manual export of DCL's Open or All Orders and running the script.

- **orders_manager_v2.py**


does not require a file as the initial api call pulls orders on statuses 0, 1 and 3.
This script is also built to run on a loop and check orders twice a day.


**FIRST RUN SET UP NOTE:** 
Before running the code, a JSON authentication file needs to be in place to work with the gsheets library.
DCL_LOGIN and PASSWORDs need to be set as environment variables, as well as the google_sheets name in question.

