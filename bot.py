import asyncio
import logging

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from tinkoff.invest import Client, GetOperationsByCursorRequest

from config import Portfolio, MoneyValue, Qutotation

import config

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from aiogram.dispatcher.filters import Text, Regexp

from aiogram.utils import executor

logging.basicConfig(level=logging.INFO, format="\033[33m {}".format('%(name)s %(levelname)s: %(message)s'))

API_TOKEN = '5523251499:AAGtkpPhKGBvzt2efV4WKj-JAP19tAIit_Y'

bot = Bot(token=API_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Search(StatesGroup):
    name = State()


def instrument_have(figi, account_id):
    with Client(config.TOKEN_full) as client:

        def get_request(cursor=""):
            return GetOperationsByCursorRequest(
                account_id=account_id,
                instrument_id=figi,
                cursor=cursor,
                limit=1,
            )

        operations = client.operations.get_operations_by_cursor(get_request())
        return operations.has_next


def find(name_instrument):

    with Client(config.TOKEN_full) as client:
        r = client.instruments.find_instrument(query=name_instrument)

        accounts = client.users.get_accounts()
        account_id = accounts.accounts[0].id

        inline_have = InlineKeyboardMarkup(row_width=1)
        inline_not = InlineKeyboardMarkup(row_width=1)

        for i in r.instruments:

            if instrument_have(i.figi, account_id=account_id):
                inline_have.add(InlineKeyboardButton(i.name, callback_data=i.figi))
            else:
                inline_not.add(InlineKeyboardButton(i.name, callback_data=i.figi))

    return inline_have, inline_not


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
            types.KeyboardButton(text="Portfolio"),
            types.KeyboardButton(text="Search")
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


@dp.message_handler(Text("Search"))
async def search(message: types.Message):
    await Search.name.set()
    await message.answer("Enter name of instrument:")

@dp.message_handler(state=Search.name)
async def process_name(message: types.Message, state: FSMContext):

    inline_have, inline_not = find(message.text)

    await message.reply("Here what was found:")

    await message.answer("🟢 Instruments that you have 🟢", reply_markup=inline_have)
    await message.answer("🔴 Instruments that you don't have 🔴", reply_markup=inline_not)

    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
