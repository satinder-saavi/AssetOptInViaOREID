import logging

from decouple import config
from algo_utils import get_client, asset_info,  fund_account_and_transfer_asa
from ore_id_utils import sign_transaction

logger = logging.getLogger(__name__)


# Initialize Algo Client
algod_client = get_client()


# ASA Creator account (Master Account)
creator_private_key = config('ALGO_FAUCET_PRIVATE_KEY')
creator_address = config('ALGO_FAUCET_ACCOUT_ADDRESS')

# ASA Reciever account (ORE ID algo_test account)
asa_receiver_address = config('ORE_ID_CHAIN_ACCOUNT')

# ASA Transfer amount
asa_amount = 10

# ASA ID
asa_id = config('ASSET_ID', default=96230975, cast=int)




if __name__ == '__main__':
    logger.warning("==========================================================")
    logger.warning('---------- ASA Transfer using python sdk  ----------')
    # assetInfo = asset_info( asset_id=asa_id)

    # unable to transfer asset as reciever account is not opt in
    # as reciever account is an ORE ID account, we need a way to opt in the ORE ID Account for a given ASA
    try:
        fund_account_and_transfer_asa(algod_client=algod_client,
                                                        creator_private_key=creator_private_key,
                                                        asa_receiver_address=asa_receiver_address,
                                                        asa_amount=asa_amount,
                                                        asa_id=asa_id
                                                            )

    except Exception as ex:
        logger.error(f'ASA Transfer using python sdk Error: {ex}')


    logger.warning("==========================================================")

    logger.warning("---------- ASA OPT In using ORE ID ----------")
    # the main issue is that the action_dict format or chain_action_type value for asa transfer is not valid
    action_dict = {
                "fromAccountName": creator_address,
                "toAccountName": asa_receiver_address,
                "amount": 10, "symbol": 'algo',
                'assetIndex':asa_id,
            }

    chain_action_type = 'AssetTransfer'
    account = config('ORE_ID_ACCOUNT')
    password = config('ORE_ID_ACCOUNT_PASSWORD')
    chain_account = asa_receiver_address
    chain_network = 'algo_test'
    broadcast = True

    action_dict = {
                "fromAccountName": creator_address,
                "toAccountName": asa_receiver_address,
                "amount": 0, "symbol": 'algo',
                'assetIndex':asa_id,
            }
    try:
        sign_transaction(account, password, action_dict, chain_action_type, broadcast, chain_account, chain_network)

    except Exception as ex:
        logger.error(f'ASA OPT In using ORE ID Error: {ex}')
    logger.warning("==========================================================")

    logger.warning("---------- ASA Transfer using ORE ID ----------")
    action_dict = {
                "fromAccountName": creator_address,
                "toAccountName": asa_receiver_address,
                "amount": 10, "symbol": 'algo',
                'assetIndex':asa_id,
            }
    try:
        sign_transaction(account, password, action_dict, chain_action_type, broadcast, chain_account, chain_network)
    except Exception as ex:
        logger.error(f'ASA Transfer using ORE ID Error: {ex}')
    logger.warning("==========================================================")