import requests
import asyncio

import config
import db
import keyboards


async def start(bot):
    try:
        # Try to load last_lt from file
        with open('last_lt.txt', 'r') as f:
            last_lt = int(f.read())
    except FileNotFoundError:
        # If file not found, set last_lt to 0
        last_lt = 0

    while True:
        # 2 Seconds delay between checks
        await asyncio.sleep(2)

        # API call to TON Center that returns last 100 transactions of our wallet
        resp = requests.get(f'{config.API_BASE_URL}/api/v2/getTransactions?'
                            f'address={config.DEPOSIT_ADDRESS}&limit=100&'
                            f'archival=true&api_key={config.API_KEY}').json()

        # If call was not successful, try again
        if not resp['ok']:
            continue

        # Iterating over transactions
        for tx in resp['result']:
            # LT is Logical Time and Hash is hash of our transaction
            lt, hash = int(tx['transaction_id']['lt']), tx['transaction_id']['hash']

            # If this transaction's logical time is lower than our last_lt,
            # we already processed it, so skip it

            if lt <= last_lt:
                continue

            # at this moment, `tx` is some new transaction that we haven't processed yet

            value = int(tx['in_msg']['value'])
            bonus = 0
            if value > 0:
                user_id = tx['in_msg']['message']

                if not user_id.isdigit():
                    continue

                user_id = int(user_id)
                lang_code = await db.get_user_lang_code(user_id=user_id)

                if not await db.check_user_new(user_id):
                    continue

                if not await db.check_bonus(user_id):
                    original_value = value
                    bonus = original_value / 100 * 5  # 5% deposit bonus
                    value *= 1.05

                    await db.insert_deposit_bonus(user_id, bonus)

                    await bot.send_message(
                        chat_id=user_id,
                        text=str(await db.get_text(lang_code=lang_code, text_id=1085)) + \
                             str(await db.get_text(lang_code=lang_code, text_id=1086)
                                 % (f'{original_value / 1e9:.2f}', 'TON')))

                    await bot.send_message(
                        chat_id=user_id,
                        text=str(await db.get_text(lang_code=lang_code, text_id=1090)) + \
                             str(await db.get_text(lang_code=lang_code, text_id=1086)
                                 % (f'{bonus / 1e9:.2f}', 'TON')),
                        disable_web_page_preview=True,
                        reply_markup=await keyboards.get_back_btn_kd(lang_code, 'balance'))

                elif await db.check_bonus(user_id):
                    await bot.send_message(
                        chat_id=user_id,
                        text=str(await db.get_text(lang_code=lang_code, text_id=1085)) + \
                             str(await db.get_text(lang_code=lang_code, text_id=1086)
                                 % (f'{value / 1e9:.2f}', 'TON')),
                        reply_markup=await keyboards.get_back_btn_kd(lang_code, 'balance'))

                await db.add_balance_ton(user_id, value)

            # we have processed this tx
            # lt variable here contains LT of the last processed transaction
            last_lt = lt
            with open('last_lt.txt', 'w') as f:
                f.write(str(last_lt))
