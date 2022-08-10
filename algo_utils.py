import logging
import time
import base64
from algosdk.future import transaction
from algosdk import account, mnemonic
from algosdk.v2client import algod, indexer
from algosdk.encoding import encode_address
from algosdk.account import address_from_private_key
from algosdk.logic import get_application_address
from algosdk.error import IndexerHTTPError, AlgodHTTPError
from decouple import config

logger = logging.getLogger(__name__)


def get_client():
    """
    :return:
        Returns algod_client
    """

    token = config('ALGO_TOKEN')
    address = config('ALGO_SERVER')
    purestake_token = {'X-Api-key': token}

    algod_client = algod.AlgodClient(token, address, headers=purestake_token)
    return algod_client


def get_indexer():

    token = config('ALGO_TOKEN')
    headers = {'X-Api-key': token}
    my_indexer = indexer.IndexerClient(indexer_token=token,
                                       indexer_address="https://testnet-algorand.api.purestake.io/idx2",
                                       headers=headers)

    return my_indexer

# utility function to get address string


def get_address(mn):
    pk_account_a = mnemonic.to_private_key(mn)
    address = account.address_from_private_key(pk_account_a)
    logger.info(f"Address : {address}")
    return address

# helper function to get an algorand account


def get_default_account_credentials():
    """
    Gets the credentials for the account
    :return: (str, str, str) private key, address and mnemonic
    """
    _mnemonic = config('ALGO_FAUCET_PASSPHRASE')
    address = config('ALGO_FAUCET_ACCOUT_ADDRESS')
    private_key = config('ALGO_FAUCET_PRIVATE_KEY')
    return private_key, address, _mnemonic

# helper function to get an algorand account


def generate_account_credentials():
    """
    Gets the credentials for the account
    :return: (str, str, str) private key, address and mnemonic
    """
    private_key, address = account.generate_account()

    return private_key, address, mnemonic.from_private_key(private_key)


# helper function to compile program source
def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])


# helper function that converts a mnemonic passphrase into a private signing key
def get_private_key_from_mnemonic(mn):
    """Get Private key from mnemonic

    Args:
        mn (str): mnemonic

    Returns:
        str: private key
    """
    private_key = mnemonic.to_private_key(mn)
    return private_key


# helper function that waits for a given txid to be confirmed by the network
def wait_for_confirmation(client, txid):
    """Utility function to wait until the transaction is
        confirmed before proceeding. 

    Args:
        client (client): algorand client
        txid (str): Transaction id

    Returns:
        dict: Transaction info
    """
    last_round = client.status().get('last-round')
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
        logger.info("Waiting for confirmation...")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    logger.info("Transaction {} confirmed in round {}.".format(
        txid, txinfo.get('confirmed-round')))
    return txinfo


def wait_for_round(client, round):
    """Wait for a given round until transaction is confirmed.

    Args:
        client (client): algorand client
        round (int): round for lookup
    """
    last_round = client.status().get('last-round')
    logger.info(f"Waiting for round {round}")
    while last_round < round:
        last_round += 1
        client.status_after_block(last_round)
        logger.info(f"Round {last_round}")


# create ASA
def create_asa(algod_client,
               creator_private_key, unit_name,
               asset_name, url, note='',
               total=10, decimals=0,
               default_frozen=False, sender='',
               manager='', reserve='',
               freeze='', clawback=''):
    """Create An ASA

    Args:
        algod_client (client): Algo client
        creator_private_key (str): Private key
        nft_info (dict): NFT Info

    Returns:
        NFT ID, Txn ID(int, str): NFT ID and Txn ID
    """
    params = algod_client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000
    if not sender:
        sender = address_from_private_key(creator_private_key)
    txn = transaction.AssetCreateTxn(sender=sender,
                                     sp=params,
                                     total=total,
                                     decimals=decimals,
                                     default_frozen=default_frozen,
                                     manager=manager,
                                     reserve=reserve,
                                     freeze=freeze,
                                     clawback=clawback,
                                     unit_name=unit_name,
                                     asset_name=asset_name,
                                     url=url,
                                     note=note)
    # sign transactions
    stxn = txn.sign(creator_private_key)

    tx_id = algod_client.send_transaction(stxn)

    # wait for confirmation
    wait_for_confirmation(algod_client, tx_id)

    try:
        ptx = algod_client.pending_transaction_info(tx_id)
        return ptx["asset-index"], tx_id
    except Exception as e:
        # TODO: Proper logging needed.
        logger.error(e)
        logger.warning('Unsuccessful creation of Algorand Standard Asset.')


# ASA Opt In
def asa_opt_in(algod_client, sender_private_key, asa_id):
    """ASA Opt in

    Args:
        algod_client (client): Algo client
        sender_private_key (str): Sender private key
        nft_id (int): NFT ID
    """
    params = algod_client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000
    sender_address = address_from_private_key(sender_private_key)
    txn = transaction.AssetTransferTxn(sender=sender_address,
                                       sp=params,
                                       receiver=sender_address,
                                       amt=0,
                                       index=asa_id)

    # sign transactions
    stxn = txn.sign(sender_private_key)

    tx_id = algod_client.send_transaction(stxn)

    # wait for confirmation
    wait_for_confirmation(algod_client, tx_id)
    return tx_id


# Create NFT
def create_non_fungible_asa(algod_client,
                            creator_private_key, unit_name,
                            asset_name, url, note='',
                            total=1, decimals=0,
                            default_frozen=False, sender='',
                            manager='', reserve='',
                            freeze='', clawback=''):
    """Create A NFT

    Args:
        algod_client (client): Algo client
        creator_private_key (str): Private key
        nft_info (dict): NFT Info

    Returns:
        NFT ID, Txn ID(int, str): NFT ID and Txn ID
    """
    params = algod_client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000
    if not sender:
        sender = address_from_private_key(creator_private_key)
    txn = transaction.AssetCreateTxn(sender=sender,
                                     sp=params,
                                     total=total,
                                     decimals=decimals,
                                     default_frozen=default_frozen,
                                     manager=manager,
                                     reserve=reserve,
                                     freeze=freeze,
                                     clawback=clawback,
                                     unit_name=unit_name,
                                     asset_name=asset_name,
                                     url=url,
                                     note=note)
    # sign transactions
    stxn = txn.sign(creator_private_key)

    tx_id = algod_client.send_transaction(stxn)

    # wait for confirmation
    wait_for_confirmation(algod_client, tx_id)

    try:
        ptx = algod_client.pending_transaction_info(tx_id)
        return ptx["asset-index"], tx_id
    except Exception as e:
        # TODO: Proper logging needed.
        logger.error(e)
        logger.warning('Unsuccessful creation of Algorand NFT.')


# NFT Opt In
def nft_opt_in(algod_client, sender_private_key, nft_id):
    """NFT Opt in

    Args:
        algod_client (client): Algo client
        sender_private_key (str): Sender private key
        nft_id (int): NFT ID
    """
    params = algod_client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000
    sender_address = address_from_private_key(sender_private_key)
    txn = transaction.AssetTransferTxn(sender=sender_address,
                                       sp=params,
                                       receiver=sender_address,
                                       amt=0,
                                       index=nft_id)

    # sign transactions
    stxn = txn.sign(sender_private_key)

    tx_id = algod_client.send_transaction(stxn)

    # wait for confirmation
    wait_for_confirmation(algod_client, tx_id)


# create new application
def create_app(client, private_key, approval_program, clear_program, global_schema, local_schema, app_args, foreign_assets):
    """Application Create

    Args:
        client (client): algorand client
        private_key (str): private key
        approval_program (str): approval program
        clear_program (str): clear program
        global_schema (dict): global schema
        local_schema (dict): local schema
        app_args (list): application args

    Returns:
        int : application id
    """
    # define sender as creator
    sender = account.address_from_private_key(private_key)

    # declare on_complete as NoOp
    on_complete = transaction.OnComplete.NoOpOC.real

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    # create unsigned transaction
    txn = transaction.ApplicationCreateTxn(sender=sender,
                                           sp=params,
                                           on_complete=on_complete,
                                           approval_program=approval_program,
                                           clear_program=clear_program,
                                           global_schema=global_schema,
                                           local_schema=local_schema,
                                           app_args=app_args,
                                           foreign_assets=foreign_assets,
                                           )

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response['application-index']
    logger.info(f"Created new app-id: {app_id}")

    return app_id, tx_id


# opt-in to application
def opt_in_app(client, private_key, index):
    """Application opt in call

    Args:
        client (client): algorand client
        private_key (str): private key
        index (int): application id
    """
    # declare sender
    sender = account.address_from_private_key(private_key)
    logger.info(f"OptIn from account: {sender}")

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    # create unsigned transaction
    txn = transaction.ApplicationOptInTxn(sender, params, index)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    logger.info(
        f"OptIn to app-id: { transaction_response['txn']['txn']['apid']}",)


# call application
def call_app(client, private_key, index, app_args):
    """Application call with app args

    Args:
        client (client): algorand client
        private_key (str): private key
        index (int): application id
        app_args (list): application args

    Returns:
        str: transaction id
    """
    # declare sender
    sender = account.address_from_private_key(private_key)
    logger.info("Call from account: %s", sender)

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    # create unsigned transaction
    txn = transaction.ApplicationNoOpTxn(sender, params, index, app_args)

    # # sign transaction
    # signed_txn = txn.sign(private_key)
    # tx_id = signed_txn.transaction.get_txid()

    # # send transaction
    # client.send_transactions([signed_txn])

    # # await confirmation
    # wait_for_confirmation(client, tx_id)
    return txn


def format_state(state):
    """get formatted state

    Args:
        state (dict): local or global state

    Returns:
        dict: formated state
    """
    formatted = {}
    for item in state:
        key = item['key']
        value = item['value']
        formatted_key = base64.b64decode(key).decode('utf-8')
        if value['type'] == 1:
            # byte string
            if formatted_key == 'voted':
                formatted_value = base64.b64decode(
                    value['bytes']).decode('utf-8')
            else:
                formatted_value = value['bytes']
            formatted[formatted_key] = formatted_value
        else:
            # integer
            formatted[formatted_key] = value['uint']
    return formatted


# read user local state
def read_local_state(client, addr, app_id):
    """Read app local state

    Args:
        client (client): alogrand client
        addr (str): address of the account
        app_id (int): application id

    Returns:
        dict: local state
    """
    results = client.account_info(addr)
    for local_state in results['apps-local-state']:
        if local_state['id'] == app_id:
            if 'key-value' not in local_state:
                return {}
            return format_state(local_state['key-value'])
    return {}


# read app global state
def read_global_state(client, addr, app_id):
    """Read app global state

    Args:
        client (client): alogrand client
        addr (str): address of the account
        app_id (int): application id

    Returns:
        dict: global state
    """
    results = client.account_info(addr)
    apps_created = results['created-apps']
    for app in apps_created:
        if app['id'] == app_id:
            return format_state(app['params']['global-state'])
    return {}


def decode_state_parameter(param_value):
    """Decode state parameter

    Args:
        param_value (str): param value

    Returns:
        str: param value
    """
    return base64.b64decode(param_value).decode('utf-8')


def load_app_state(app_id: int):
    """Load Global App State from Indexer

    Args:
        app_id (int): APP ID

    Returns:
        dict: APP Global state
    """
    time.sleep(5)
    indexer = get_indexer()
    response = indexer.search_applications(application_id=app_id)
    state = dict()
    for state_k in response['applications'][0]['params']['global-state']:
        key = decode_state_parameter(state_k['key'])
        if state_k['value']['type'] == 1:
            state[key] = encode_address(
                base64.b64decode(state_k['value']['bytes']))
        else:
            state[key] = state_k['value']['uint']
    return state


# delete application
def delete_app(client, private_key, index):
    """Delate an application

    Args:
        client (client): algorand client
        private_key (str): private key
        index (int): application id
    """
    # declare sender
    sender = account.address_from_private_key(private_key)

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    # create unsigned transaction
    txn = transaction.ApplicationDeleteTxn(sender, params, index)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    logger.info(
        f"Deleted app-id: {transaction_response['txn']['txn']['apid']}", )


# close out from application
def close_out_app(client, private_key, index):
    """Close out an application

    Args:
        client (client): algorand client
        private_key (str): private key
        index (int): application id
    """
    # declare sender
    sender = account.address_from_private_key(private_key)

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    # create unsigned transaction
    txn = transaction.ApplicationCloseOutTxn(sender, params, index)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    logger.info(f"Closed out from app-id: {transaction_response['txn']['txn']['apid']}",
                )


# clear application
def clear_app(client, private_key, index):
    """Clear an application

    Args:
        client (client): algorand client
        private_key (str): private key
        index (int): application id
    """
    # declare sender
    sender = account.address_from_private_key(private_key)

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    # create unsigned transaction
    txn = transaction.ApplicationClearStateTxn(sender, params, index)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    logger.info(
        f"Cleared app-id: {transaction_response['txn']['txn']['apid']}",)


# convert 64 bit integer i to byte string
def intToBytes(i):
    """Convert int into byte

    Args:
        i (int): int

    Returns:
        byte: byte
    """
    return i.to_bytes(8, "big")

# get NFT Image


def nft_image(nft_id, wait=False):

    if wait:
        time.sleep(5)
    indexer = get_indexer()
    response = indexer.search_assets(asset_id=nft_id)
    return response["assets"][0]["params"]["url"]


def payment_transaction(algod_client, sender_private_key, receiver_address, amount):

    params = algod_client.suggested_params()

    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    sender_address = address_from_private_key(sender_private_key)

    payment_txn = transaction.PaymentTxn(sender=sender_address,
                                         sp=params,
                                         receiver=receiver_address,
                                         amt=amount)

    # sign txn
    stxn = payment_txn.sign(sender_private_key)
    try:
        tx_id = algod_client.send_transaction(stxn)
        # wait for confirmation
        wait_for_confirmation(algod_client, tx_id)
        logger.info(
            "Transaction Lookup: https://testnet.algoexplorerapi.io/tx/{}".format(tx_id))
        return {"msg": f"Payment Transfer of amount {amount} Success in txn : {tx_id}"}, True

    except Exception as err:
        logger.exception(err)

    return {"msg": f"Payment Transfer of amount {amount} fail for account: {receiver_address}"}, False


def fund_account_and_transfer_asa(algod_client, creator_private_key,asa_receiver_address,  asa_amount, asa_id,fund_account=True,fund_amount=200_000):
    """ASA Transfer

    Args:
        algod_client (client): Algo client
        creator_private_key (str): Creator private key
        receiver_private_key (str): Receiver private key
        asa_amount (int): ASA Transfer amount
        asa_id (int): ASA ID
    Returns:
        Txn ID (str): Txn ID
    """

    params = algod_client.suggested_params()

    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    creator_address = address_from_private_key(creator_private_key)
    # asa_receiver_address = address_from_private_key(receiver_private_key)

    account_info = algod_client.account_info(asa_receiver_address)

    if not account_info.get('amount') or account_info.get('amount',0) < 200_000:
        if fund_account:
            payment_transaction(algod_client, creator_private_key, asa_receiver_address, fund_amount)
        else:
            return {"msg": f"No initial amount found on Account: {asa_receiver_address}. Add initial fund to the account via https://bank.testnet.algorand.network/"}, False
    # checking for opt in, but unable to opt in as Account is at ORE ID
    # 1. Opt in ASA Txn
    # holding = None
    # idx = 0
    # for _ in account_info['assets']:
    #     scrutinized_asset = account_info['assets'][idx]
    #     idx = idx + 1
    #     if (scrutinized_asset['asset-id'] == asa_id):
    #         holding = True
    #         break
    # if not holding:
    #     logger.info(f'Opt in account {asa_receiver_address}')
        # Use the AssetTransferTxn class to transfer assets and opt-in
        # txn = transaction.AssetTransferTxn(
        #     sender=asa_receiver_address,
        #     sp=params,
        #     receiver=asa_receiver_address,
        #     amt=0,
        #     index=asa_id)
        # stxn = txn.sign(receiver_private_key)
        # # Send the transaction to the network and retrieve the txid.
        # try:
        #     txid = algod_client.send_transaction(stxn)
        #     logger.info("Signed transaction with txID: {}".format(txid))
        #     # Wait for the transaction to be confirmed
        #     confirmed_txn = wait_for_confirmation(algod_client, txid, 4)
        #     logger.info(f"TXID: {txid}", )
        #     logger.info("Result confirmed in round: {}".format(confirmed_txn['confirmed-round']))
        # except Exception as err:
        #     logger.error(err)
        # try:
        #     asa_opt_in(algod_client, receiver_private_key, asa_id)
        #     raise

        # except Exception as ee:
        #     logger.exception(ee)
        #     return {"msg": f"Error while ASA Opt in for account: {asa_receiver_address}"}, False

    # 2. ASA Transfer Txn
    asa_transfer_txn = transaction.AssetTransferTxn(sender=creator_address,
                                                    sp=params,
                                                    receiver=asa_receiver_address,
                                                    amt=asa_amount,
                                                    index=asa_id)
    # sign txn
    stxn = asa_transfer_txn.sign(creator_private_key)
    try:
        tx_id = algod_client.send_transaction(stxn)
        # wait for confirmation
        wait_for_confirmation(algod_client, tx_id)
        logger.info(
            "Transaction Lookup: https://testnet.algoexplorer.io/tx/{}".format(tx_id))
        return {"msg": f"ASA Transfer Success in txn : {tx_id}"}, True

    except Exception as err:
        logger.exception(err)
        {"msg": f"ASA Transfer Error: {err}"}, False

    return {"msg": f"ASA Transfer Fail for account: {asa_receiver_address}"}, False


def transfer_asa(algod_client, creator_private_key, receiver_private_key, asa_amount, asa_id):
    """ASA Transfer

    Args:
        algod_client (client): Algo client
        creator_private_key (str): Creator private key
        receiver_private_key (str): Receiver private key
        asa_amount (int): ASA Transfer amount
        asa_id (int): ASA ID
    Returns:
        Txn ID (str): Txn ID
    """

    params = algod_client.suggested_params()

    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    creator_address = address_from_private_key(creator_private_key)
    asa_receiver_address = address_from_private_key(receiver_private_key)

    account_info = algod_client.account_info(asa_receiver_address)

    if not account_info.get('amount'):
        return {"msg": f"No initial amount found on Account: {asa_receiver_address}. Add initial fund to the account via https://bank.testnet.algorand.network/"}, False

    # 1. Opt in ASA Txn
    holding = None
    idx = 0
    for _ in account_info['assets']:
        scrutinized_asset = account_info['assets'][idx]
        idx = idx + 1
        if (scrutinized_asset['asset-id'] == asa_id):
            holding = True
            break
    if not holding:
        logger.info(f'Opt in account {asa_receiver_address}')
        # Use the AssetTransferTxn class to transfer assets and opt-in
        # txn = transaction.AssetTransferTxn(
        #     sender=asa_receiver_address,
        #     sp=params,
        #     receiver=asa_receiver_address,
        #     amt=0,
        #     index=asa_id)
        # stxn = txn.sign(receiver_private_key)
        # # Send the transaction to the network and retrieve the txid.
        # try:
        #     txid = algod_client.send_transaction(stxn)
        #     logger.info("Signed transaction with txID: {}".format(txid))
        #     # Wait for the transaction to be confirmed
        #     confirmed_txn = wait_for_confirmation(algod_client, txid, 4)
        #     logger.info(f"TXID: {txid}", )
        #     logger.info("Result confirmed in round: {}".format(confirmed_txn['confirmed-round']))
        # except Exception as err:
        #     logger.error(err)
        try:
            asa_opt_in(algod_client, receiver_private_key, asa_id)

        except Exception as ee:
            logger.exception(ee)
            return {"msg": f"Error while ASA Opt in for account: {asa_receiver_address}"}, False

    # 2. ASA Transfer Txn
    asa_transfer_txn = transaction.AssetTransferTxn(sender=creator_address,
                                                    sp=params,
                                                    receiver=asa_receiver_address,
                                                    amt=asa_amount,
                                                    index=asa_id)
    # sign txn
    stxn = asa_transfer_txn.sign(creator_private_key)
    try:
        tx_id = algod_client.send_transaction(stxn)
        # wait for confirmation
        wait_for_confirmation(algod_client, tx_id)
        logger.info(
            "Transaction Lookup: https://testnet.algoexplorerapi.io/tx/{}".format(tx_id))
        return {"msg": f"ASA Transfer Success in txn : {tx_id}"}, True

    except Exception as err:
        logger.exception(err)

    return {"msg": f"ASA Transfer Fail for account: {asa_receiver_address}"}, False




#  ---------------------------------------------------------------
# asset_info
#  ---------------------------------------------------------------
def asset_info(asset_id):
    """Fetch asset info of the address

    Args:
        address (str): address of account

    Raises:
        IndexerHTTPError: Too Many Requests

    Returns:
        tuple(dict,bool): ({message,list of asset dict}, True/False)
    """

    indexer_client = get_indexer()
    response = {}
    try:
        response = indexer_client.asset_info(asset_id=asset_id)
        logger.info(response)
        return response.get('asset',{})

    except Exception as ex:
        logger.exception(ex)
        return response




#  ---------------------------------------------------------------
# fetch_asset_info
#  ---------------------------------------------------------------
def fetch_asset_info(address,include_zero_assets=False):
    """Fetch asset info of the address

    Args:
        address (str): address of account

    Raises:
        IndexerHTTPError: Too Many Requests

    Returns:
        tuple(dict,bool): ({message,list of asset dict}, True/False)
    """
    logger.info("Fetching asset info of the address:- %s", address)

    indexer_client = get_indexer()
    response = {}
    account_amount = 0
    try:
        response = indexer_client.account_info(address=address, include_all=True)
        logger.info(response)
        account_amount = response.get('account', {}).get('amount', 0)
        if not account_amount:
            return {"msg": f"No initial amount found on Account: {address}. Add initial fund to the account via https://bank.testnet.algorand.network/", "account_amount": account_amount}, False

    except IndexerHTTPError as indxerr:
        _msg = f'{indxerr}'
        if 'no accounts found for address' in _msg:
            _msg += ' Add initial fund to the account via https://bank.testnet.algorand.network/'
            return {"msg": _msg, "account_amount": account_amount}, False
        logger.error(_msg)
        return {"msg": _msg}, False
    time.sleep(0.2)
    non_zero_asset = []
    try:
        asset_dict = response["account"]["assets"]
        non_zero_asset = asset_dict
        if not include_zero_assets:
            non_zero_asset = [v for v in asset_dict if v['amount'] != 0]
    except KeyError:
        return {"msg": "Account doesn't have any asset", "account_amount": account_amount}, False

    try:
        asset_list = [{'asset_id': a['asset-id'],
                       'asset_amount':a['amount']
                       } for a in non_zero_asset
                      ]
        logger.warn("List of Asset dict:- %s", asset_list)
        result = {
            "account_amount": account_amount,
            "msg": f"{len(non_zero_asset)} asset found.",
            "result": asset_list
        }
        return result, True

    except KeyError:
        return {"msg": "Required asset info error.", "account_amount": account_amount}, False


#  ---------------------------------------------------------------
# fetch_asset_info_with_details
#  ---------------------------------------------------------------
def fetch_asset_info_with_details(address,include_zero_assets=False):
    """Fetch asset info of the address with details

    Args:
        address (str): address of account

    Raises:
        IndexerHTTPError: Too Many Requests

    Returns:
        tuple(dict,bool): ({message,list of asset dict}, True/False)
    """
    logger.info("Fetching asset info of the address:- %s", address)

    indexer_client = get_indexer()
    response = {}
    account_amount = 0
    try:
        response = indexer_client.account_info(address=address, include_all=True)
        # response1 = indexer_client.lookup_account_assets(address=address, include_all=True)
        response2 = indexer_client.search_transactions_by_address(address=address, txn_type="axfer")
        if response2:
            ass_txn_lst =  response2.get('transactions',[])
            for t in ass_txn_lst:
                t.get('asset-transfer-transaction',{})
        logger.info(response)
        account_amount = response.get('account', {}).get('amount', 0)
        if not account_amount:
            return {"msg": f"No initial amount found on Account: {address}. Add initial fund to the account via https://bank.testnet.algorand.network/", "account_amount": account_amount}, False

    except IndexerHTTPError as indxerr:
        _msg = f'{indxerr}'
        if 'no accounts found for address' in _msg:
            _msg += ' Add initial fund to the account via https://bank.testnet.algorand.network/'
            return {"msg": _msg, "account_amount": account_amount}, False
        logger.error(_msg)
        return {"msg": _msg}, False
    time.sleep(0.2)
    non_zero_asset = []
    try:
        asset_dict = response["account"]["assets"]
        non_zero_asset = asset_dict
        if not include_zero_assets:
            non_zero_asset = [v for v in asset_dict if v['amount'] != 0]
    except KeyError:
        return {"msg": "Account doesn't have any asset", "account_amount": account_amount}, False

    for ast in non_zero_asset:
        try:
            asset_info = indexer_client.asset_info(asset_id=ast['asset-id'])
            ast.update(asset_info)
            time.sleep(0.2)
        except IndexerHTTPError as indxerr:
            # print(indxerr)
            logger.error(indxerr)
            try:
                time.sleep(0.5)
                asset_info = indexer_client.asset_info(
                    asset_id=ast['asset-id'])
                ast.update(asset_info)
                time.sleep(0.5)

            except Exception as err:
                print(err)
                logger.exception(err)
    try:
        asset_list = [{'asset_id': a['asset-id'],
                       'asset_name':a['asset']['params']['name'],
                       'asset_amount':a['amount']
                       } for a in non_zero_asset
                      ]
        logger.warn("List of Asset dict:- %s", asset_list)
        result = {
            "account_amount": account_amount,
            "msg": f"{len(non_zero_asset)} asset found.",
            "result": asset_list
        }
        return result, True

    except KeyError:
        return {"msg": "Required asset info error.", "account_amount": account_amount}, False



#  ---------------------------------------------------------------
# fetch_asset_txn_info
#  ---------------------------------------------------------------
def fetch_asset_txn_info(address,include_zero_assets=False):
    """Fetch asset info of the address

    Args:
        address (str): address of account

    Raises:
        IndexerHTTPError: Too Many Requests

    Returns:
        tuple(dict,bool): ({message,list of asset dict}, True/False)
    """
    logger.info("Fetching asset info of the address:- %s", address)

    indexer_client = get_indexer()
    response = {}
    asset_list = []
    try:
        response = indexer_client.search_transactions_by_address(address=address, txn_type="axfer")

        for t in response.get('transactions',[]):
            asset_list.append(t.get('asset-transfer-transaction'))
        logger.info(response)
        # account_amount = response.get('account', {}).get('amount', 0)
        # if not account_amount:
        #     return {"msg": f"No initial amount found on Account: {address}. Add initial fund to the account via https://bank.testnet.algorand.network/", "account_amount": account_amount}, False

    except IndexerHTTPError as indxerr:
        _msg = f'{indxerr}'
        if 'no accounts found for address' in _msg:
            _msg += ' Add initial fund to the account via https://bank.testnet.algorand.network/'
            return {"msg": _msg}, False
        logger.error(_msg)
        return {"msg": _msg}, False
    time.sleep(0.2)

    try:
        asset_list = [{'asset_id': a['asset-id'],
                       'asset_amount':a['amount']
                       } for a in asset_list
                      ]
        logger.warn("List of Asset dict:- %s", asset_list)
        result = {
            "msg": f"{len(asset_list)} asset found.",
            "result": asset_list
        }
        return result, True

    except KeyError:
        return {"msg": "Required asset info error."}, False


#  ---------------------------------------------------------------
# fetch_asset_txn_info
#  ---------------------------------------------------------------
def fetch_asset_txn_info_with_detail(address,include_zero_assets=False):
    """Fetch asset info of the address

    Args:
        address (str): address of account

    Raises:
        IndexerHTTPError: Too Many Requests

    Returns:
        tuple(dict,bool): ({message,list of asset dict}, True/False)
    """
    logger.info("Fetching asset info of the address:- %s", address)

    indexer_client = get_indexer()
    response = {}
    asset_list = []
    try:
        response = indexer_client.search_transactions_by_address(address=address, txn_type="axfer")

        for t in response.get('transactions',[]):
            asset_list.append(t.get('asset-transfer-transaction'))
        logger.info(response)
        # account_amount = response.get('account', {}).get('amount', 0)
        # if not account_amount:
        #     return {"msg": f"No initial amount found on Account: {address}. Add initial fund to the account via https://bank.testnet.algorand.network/", "account_amount": account_amount}, False

    except IndexerHTTPError as indxerr:
        _msg = f'{indxerr}'
        if 'no accounts found for address' in _msg:
            _msg += ' Add initial fund to the account via https://bank.testnet.algorand.network/'
            return {"msg": _msg}, False
        logger.error(_msg)
        return {"msg": _msg}, False
    time.sleep(0.2)

    for ast in asset_list:
        try:
            asset_info = indexer_client.asset_info(asset_id=ast['asset-id'])
            ast.update(asset_info)
            time.sleep(0.2)
        except IndexerHTTPError as indxerr:
            # print(indxerr)
            logger.error(indxerr)
            try:
                time.sleep(0.5)
                asset_info = indexer_client.asset_info(
                    asset_id=ast['asset-id'])
                ast.update(asset_info)
                time.sleep(0.5)

            except Exception as err:
                print(err)
                logger.exception(err)
    try:
        asset_list = [{'asset_id': a['asset-id'],
                       'asset_name':a['asset']['params']['name'],
                       'asset_amount':a['amount']
                       } for a in asset_list
                      ]
        logger.warn("List of Asset dict:- %s", asset_list)
        result = {
            "msg": f"{len(asset_list)} asset found.",
            "result": asset_list
        }
        return result, True

    except KeyError:
        return {"msg": "Required asset info error."}, False

