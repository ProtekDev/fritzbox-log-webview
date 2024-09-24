from dotenv import load_dotenv
import pytz
import os

# if development mode / debugger active
if os.path.exists('../dev/'):
    load_dotenv('../dev/.env')

class Var:
    '''
    Contains global and environment variables
    '''

    timezone = pytz.timezone('Europe/Berlin')
    db_name = "data/fritzbox_logs.db"
    router_user = os.getenv('USER', '')
    router_password = os.getenv('PASSWORD', '')
    baseurl = os.getenv('URL', '')

    ignore_log_id = os.getenv('IGNORE_LOG_ID', '')
    ignore_refs = [int(ref) for ref in ignore_log_id.split(',') if ref.isdigit()]