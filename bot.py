import asyncio
import logging

from tinkoff.invest import Client

from config import Portfolio, MoneyValue, Qutotation

import config

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from aiogram.dispatcher.filters import Text, Regexp

from aiogram.utils import executor

logging.basicConfig(level=logging.INFO, format="\033[33m {}".format('%(name)s %(levelname)s: %(message)s'))

API_TOKEN = ''

bot = Bot(token=API_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

async def portfolio_show(portfolio, id):

    answer = ""

    for i in range(len(portfolio)):
        answer = answer + str(portfolio[i]) + "\n"

        if i < len(portfolio)-1:
            if len(answer + str(portfolio[i+1])) >= 4096:
                await bot.send_message(id, answer)
                answer = ""
        else:
            await bot.send_message(id, answer)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    kb = [
        [
            types.KeyboardButton(text="Portfolio")
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Choose action"
    )
    await message.answer("Hello, " + message.from_user.first_name)
    await message.answer("With help this bot you can trade directly in Telegram!", reply_markup=keyboard)

@dp.message_handler(Text("Portfolio"))
async def portfolio_button_handler(message: types.Message):
    await message.reply("Loading of portfolio")
    with Client(config.TOKEN_full) as client:
        acc_id = client.users.get_accounts().accounts[0].id
        r = client.operations.get_portfolio(account_id=acc_id)

        portfolio = Portfolio(
            MoneyValue(r.total_amount_shares.units, r.total_amount_shares.nano, r.total_amount_shares.currency),
            MoneyValue(r.total_amount_bonds.units, r.total_amount_bonds.nano, r.total_amount_bonds.currency),
            MoneyValue(r.total_amount_etf.units, r.total_amount_etf.nano, r.total_amount_etf.currency),
            MoneyValue(r.total_amount_currencies.units, r.total_amount_currencies.nano,
                       r.total_amount_currencies.currency),
            MoneyValue(r.total_amount_futures.units, r.total_amount_futures.nano, r.total_amount_futures.currency),
            Qutotation(r.expected_yield.units, r.expected_yield.units),
            r.positions,
            r.account_id,
            MoneyValue(r.total_amount_options.units, r.total_amount_options.nano, r.total_amount_options.currency),
            MoneyValue(r.total_amount_sp.units, r.total_amount_sp.nano, r.total_amount_sp.currency),
            MoneyValue(r.total_amount_portfolio.units, r.total_amount_portfolio.nano,
                       r.total_amount_portfolio.currency),
            r.virtual_positions)

    await asyncio.create_task(portfolio_show(portfolio.show(), message.chat.id))

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
