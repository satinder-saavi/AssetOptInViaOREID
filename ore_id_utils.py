
import logging
import base64
import requests
import json
from enum import Enum
from decouple import config
from algosdk.encoding import decode_address, msgpack_encode, _sort_dict
from algosdk.future import transaction
from algo_utils import get_client, address_from_private_key
logger = logging.getLogger(__name__)


BASE_URL = config('ORE_ID_BASE_URL')
API_KEY = config('ORE_ID_API_KEY')
SERVICE_KEY = config('ORE_ID_SERVICE_KEY')


class Action(Enum):
    REG = "reg"
    BAL = "bal"
    SEND = "send"
    TOPUP = "topup"
    ALGO_TRANSFER = "algo_transfer"
    SMARTCONTRACT = "smartcontract"


class ChainActionType(Enum):
    APPNOOP = 'AppNoOp'
    VALUE_TRANSFER = 'ValueTransfer'

# ---------------------------------------------------------------
# create_ore_id_user
# ---------------------------------------------------------------


def create_ore_id_user(user_data):
    """
    If service_key , name, user_name , email, picture , password 
    and account_type exists, this function will create a user 
    """

    logger.warning("create_ore_id_user method called")
    url = BASE_URL + "/api/custodial/new-user"

    first_name = user_data.get('first_name')
    last_name = user_data.get('last_name')
    email = user_data.get('email')
    picture = user_data.get('picture', '')
    password = user_data.get('password')  
    phone = user_data.get('phone_number')
    account_type = user_data.get('account_type', 'native')

    full_name = None
    if first_name or last_name:
        name = '%s %s' % (first_name, last_name)
        full_name = name.strip()
    else:
        full_name = email

    data = json.dumps({
        "name": full_name,
        "user_name": email,
        "email": email,
        "picture": picture,
        "user_password": password,
        "phone": phone,
        "account_type": account_type,
        # "email_verified": true,
    })

    headers = {
        "api-key": API_KEY,
        "service-key": SERVICE_KEY,
        "content-type": "application/json",
    }

    res = requests.request("POST",
                           url=url,
                           headers=headers,
                           data=data
                           )
    res_json = res.json()

    if res.status_code == 200:
        logger.info("account is created successfully %s", res.content)
    else:
        logger.warning(
            "facing issue while creating account %s",
            res.text
        )

        if res_json.get('error'):
            _msg = res_json.get('error')
            logger.error("facing error while creating ORE account %s", _msg)

        if res_json.get('message'):
            _msg = res_json.get('message')
            logger.error("facing error while creating ORE account %s", _msg)

        if res_json.get('errorMessage'):
            _msg = res_json.get('errorMessage')
            logger.error("facing error while creating ORE account %s", _msg)
            # raise ValueError(_msg)

    return res_json.get('accountName'), res_json.get('processId')


#  ---------------------------------------------------------------
# get_user
#  ---------------------------------------------------------------
def get_user(account):
    """Get the ORE ID User information record.

    Args:
        account (str): ORE ID Account name (eg: ore1prgcasmw).

    Returns:
        dict: Json Response
    """

    params = {
        "account": account
    }

    url = BASE_URL + "/api/account/user"

    headers = {
        "api-key": API_KEY,
    }

    res = requests.request("GET",
                           url=url,
                           headers=headers,
                           params=params)

    res_json = res.json()

    if res.status_code == 200:
        logger.info("----- code verify successfully completed -----")
    else:
        logger.info(
            f"----- issue while getting user info with status code {res.status_code} -----")

        if res_json.get('error') and res_json.get('message'):
            _msg = res_json.get('message')
            logger.error("facing error while getting ORE account %s", _msg)

        if res_json.get('errorMessage'):
            _msg = res_json.get('errorMessage')
            logger.error("facing error while getting ORE account %s", _msg)

    return res_json


#  ---------------------------------------------------------------
# send_verification_code
#  ---------------------------------------------------------------
def send_verification_code(email=None, phone=None):
    """If username exists, this function will send verification code to the email id"""
    params = {}

    if email and (not phone):
        params.update({
            'provider': 'email',
            'email': email
        })
    elif (not email) and phone:
        params.update({
            'provider': 'phone',
            'phone': phone
        })
    else:
        raise ValueError('Please provide either email or phone')

    url = BASE_URL + "/api/account/login-passwordless-send-code"

    headers = {
        "api-key": API_KEY,
    }

    res = requests.request("GET",
                           url=url,
                           headers=headers,
                           params=params)

    res_json = res.json()

    if res.status_code == 200:
        logger.info("----- code sent on your register email successfully -----")
    else:
        logger.info(
            f"----- facing issue while sending ORE account verification code {res.status_code} -----")

        if res_json.get('message'):
            _msg = res_json.get('message')
            logger.error(
                "facing error while sending ORE account verification code %s", _msg)

        if res_json.get('errorMessage'):
            _msg = res_json.get('errorMessage')
            logger.error(
                "facing error while sending ORE account verification code %s", _msg)

    return res_json


#  ---------------------------------------------------------------
# send_verification_code
#  ---------------------------------------------------------------
def get_action_params(action_dict):

    params_json = json.dumps(action_dict)

    return base64.b64encode(params_json.encode('utf-8')).decode("utf-8")


def compose_transaction(action_dict, chain_action_type):

    url = BASE_URL + '/api/transaction/compose-action'

    data = json.dumps({
        "chain_network": 'algo_test',
        "chain_action_type": chain_action_type,
        "action_params": get_action_params(action_dict)
    })

    headers = {
        "api-key": API_KEY,
        "service-key": SERVICE_KEY,
        "content-type": "application/json",
    }

    res = requests.request("POST",
                           url=url,
                           headers=headers,
                           data=data
                           )

    res_json = res.json()

    logger.info(res_json)

    if res.status_code == 200:
        logger.info("----- compose transaction successfully -----")
        return json.loads(res.content)
    else:
        logger.info(
            f"----- facing issue while compose transaction {res.status_code} -----")

        if res_json.get('message'):
            _msg = res_json.get('message')
            logger.error(
                "facing error while compose transaction %s", _msg)

        if res_json.get('errorMessage'):
            _msg = res_json.get('errorMessage')
            logger.error(
                "facing error while compose transaction %s", _msg)

    return res_json


#  ---------------------------------------------------------------
# sign_transaction
#  ---------------------------------------------------------------
def sign_transaction(account, password, action_dict, chain_action_type, broadcast=True, chain_account='', chain_network='', ):

    url = BASE_URL + "/api/transaction/sign"

    transaction = compose_transaction(action_dict, chain_action_type)

    if not transaction or not transaction.get('transactionAction'):
        raise Exception('Sign transaction fail')
    
    data = json.dumps({
        "account": account,
        "broadcast": broadcast,
        "chain_account": chain_account,
        "chain_network": chain_network,
        "transaction": transaction['transactionAction'],
        "user_password": password,
    })

    headers = {
        "api-key": API_KEY,
        "service-key": SERVICE_KEY,
        "content-type": "application/json",
    }

    res = requests.request("POST", url, headers=headers, data=data)

    res_json = res.json()

    if res.status_code == 200:
        logger.info("transaction successfully %s", res.content)
    else:
        logger.warning(
            "facing issue while ORE sign transaction %s",
            res.text
        )

        if res_json.get('error'):
            _msg = res_json.get('error')
            logger.error("facing error while ORE sign transaction %s", _msg)

        if res_json.get('message'):
            _msg = res_json.get('message')
            logger.error("facing error while ORE sign transaction %s", _msg)

        if res_json.get('errorMessage'):
            _msg = res_json.get('errorMessage')
            logger.error("facing error while ORE sign transaction %s", _msg)



def ore_id_asa_action(sender_address, asa_id,amount=0):
    """
    params = get_client().suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000
    txn = transaction.AssetTransferTxn(sender=sender_address,
                                       sp=params,
                                       receiver=sender_address,
                                       amt=0,
                                       index=asa_id)
    print(txn)
    print(vars(txn))
    print(dir(txn))
    dict_txn = vars(txn)
    params_dict = {
        'fee':params.fee,
        'flatFee':params.flat_fee,
        'genesisID':params.gen,
        'firstRound':params.first,
        'genesisHash':params.gh,
        'lastRound':params.last,
    }
    action_dict = {
        'from':sender_address,
        'to':sender_address,
        'closeRemainderTo':None,
        'revocationTarget':None,
        'amount':0,
        'note':None,
        'assetIndex':asa_id,
        'suggestedParams':params_dict,
    }
    params_json = {
        'from':sender_address,
        'to':sender_address,
        'closeRemainderTo':None,
        'revocationTarget':None,
        'fee':params.fee,
        'amount':0,
        'firstRound':params.first,
        'lastRound':params.last,
        'note':None,
        'genesisHash':params.gh,
        'genesisID':params.gen,
        'assetIndex':asa_id,
    }
    # encoded_data = base64.b64encode(params_json.encode('utf-8')).decode("utf-8")
    # t_dict = msgpack_encode(txn)
    t_dict = {
        "chain_network": 'algo_test',
        "chain_action_type": 'AssetTransfer',
        "action_params": msgpack_encode(txn)
    }
    # action_dict ={
    #     'from':sender_address,
    #     'to':sender_address,
    #     'closeRemainderTo':None,
    #     'revocationTarget':None,
    #     'fee':params.fee,
    #     'amount':0,
    #     'firstRound':params.first,
    #     'lastRound':params.last,
    #     'note':None,
    #     'genesisHash':params.gh,
    #     'genesisID':params.gen,
    #     'assetIndex':asa_id,
    # }
    f_dict =  {
        "chain_network": 'algo_test',
        "chain_action_type": 'AssetTransfer',
        "action_params": action_dict
    }
    
    _prms = json.dumps(action_dict)
    print('\n\n\n\n')
    print(_prms)
    print('\n\n\n\n')
    encoded_data = base64.b64encode(_prms.encode('utf-8')).decode("utf-8")
    """
    action_dict = {
            'from': sender_address,
            'to': sender_address,
            'assetIndex': asa_id,
            'amount': amount,
            'type': "axfer"
        
    }
    _prms = json.dumps(action_dict)
    encoded_data = base64.b64encode(_prms.encode('utf-8')).decode("utf-8")

    return encoded_data






#  ---------------------------------------------------------------
# ore_id_asa_sign_transaction
#  ---------------------------------------------------------------
def ore_id_asa_sign_transaction(account, password,chain_action_type, asa_id,amount=0, broadcast=True, chain_account='', chain_network=''):

    url = BASE_URL + "/api/transaction/sign"
    transaction = ore_id_asa_action(chain_account, asa_id, amount)
    # action_dict = ore_id_asa_action(chain_account, asa_id)
    
    # transaction = compose_transaction(action_dict, chain_action_type)

    # if not transaction or not transaction.get('transactionAction'):
    #     raise Exception('Sign transaction fail')

    # data = json.dumps({
    #     "account": account,
    #     "broadcast": broadcast,
    #     "chain_account": chain_account,
    #     "chain_network": chain_network,
    #     "transaction": transaction['transactionAction'],
    #     "user_password": password,
    # })
    # transaction = get_action_params(action_dict)
    
    data = json.dumps({
        "account": account,
        "broadcast": broadcast,
        "chain_account": chain_account,
        "chain_network": chain_network,
        "transaction": transaction,
        "user_password": password,
    })
    print('\n\n\n\n')
    print(data)
    print('\n\n\n\n')
    headers = {
        "api-key": API_KEY,
        "service-key": SERVICE_KEY,
        "content-type": "application/json",
    }

    res = requests.request("POST", url, headers=headers, data=data)

    res_json = res.json()
    print('\n\n\n\n')
    print(res_json)
    print('\n\n\n\n')
    print()
    if res.status_code == 200:
        logger.info("transaction successfully %s", res.content)
    else:
        logger.warning(
            "facing issue while ORE sign transaction %s",
            res.text
        )

        if res_json.get('error'):
            _msg = res_json.get('error')
            logger.error("facing error while ORE sign transaction %s", _msg)

        if res_json.get('message'):
           _msg = res_json.get('message')
           logger.error("facing error while ORE sign transaction %s", _msg)


def can_auto_sign(account ,chain_network, chain_account , transaction='' , signed_transaction =''):
    url = BASE_URL + "/api/transaction/can-auto-sign"
    
    _dict = {
        'account':account,
        'chain_network':chain_network,
        'chain_account':chain_account
    }
    if transaction:
        _dict.update({'transaction':transaction})
    
    if signed_transaction:
        _dict.update({'signed_transaction':signed_transaction})

    data = json.dumps(_dict)

    headers = {
        "api-key": API_KEY,
        "service-key": SERVICE_KEY,
        "content-type": "application/json",
    }
    
    res = requests.request("POST", url, headers=headers, data=data)

    res_json = res.json()

    if res.status_code == 200:
        logger.warning("transaction successfully %s", res.content)
    else:
        logger.warning(
            "facing issue while ORE sign transaction %s",
            res.text
        )

        if res_json.get('error'):
            _msg = res_json.get('error')
            logger.error("facing error while ORE sign transaction %s", _msg)

        if res_json.get('message'):
           _msg = res_json.get('message')
           logger.error("facing error while ORE sign transaction %s", _msg)

def chain_config():
    url = BASE_URL + "/api/services/config?type=chains"
    
    

    headers = {
        "api-key": API_KEY,
        "service-key": SERVICE_KEY,
        "content-type": "application/json",
    }
    
    res = requests.request("GET", url, headers=headers, data={})

    res_json = res.json()

    if res.status_code == 200:
        logger.warning("transaction successfully %s", res.content)
        print(res_json)
    else:
        logger.warning(
            "facing issue while ORE sign transaction %s",
            res.text
        )

        if res_json.get('error'):
            _msg = res_json.get('error')
            logger.error("facing error while ORE sign transaction %s", _msg)

        if res_json.get('message'):
           _msg = res_json.get('message')
           logger.error("facing error while ORE sign transaction %s", _msg)



