import asyncio
import logging

from tinkoff.invest import Client, GetOperationsByCursorRequest

from config import Portfolio, MoneyValue, Qutotation

import config
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO, format="\033[33m {}".format('%(name)s %(levelname)s: %(message)s'))

API_TOKEN = ''


async def post_order(figi, lots, direction):
    if direction == "Продать":
        direction = 2
    else:
        direction = 1

    print(figi, type(lots), direction)

    with Client(config.TOKEN_full) as client:

        client.orders.post_order(figi=figi, quantity=lots,
                                 direction=direction,
                                 account_id=client.users.get_accounts().accounts[0].id,
                                 order_type=2, order_id=config.generate_key())



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


bot = Bot(token=API_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# States
class InstrumentTerminal(StatesGroup):
    figi = State()
    lots = State()
    direction = State()


class InstrumentSearch(StatesGroup):
    figi = State()

    amount_in_lot = State()
    name = State()

    direction = State()
    lots = State()
    status = State()


class Search(StatesGroup):
    name = State()


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    kb = [
        [
            types.KeyboardButton(text="Portfolio"),
            types.KeyboardButton(text="Trade terminal"),
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


@dp.callback_query_handler()
async def instrument_page(callback: types.CallbackQuery, state: FSMContext):

    with Client(config.TOKEN_full) as client:
        request = client.instruments.get_instrument_by(id_type=1, id=callback.data).instrument

    await InstrumentSearch.figi.set()

    async with state.proxy() as data:
        data['figi'] = callback.data
        await InstrumentSearch.amount_in_lot.set()
        data['amount_in_lot'] = request.lot
        await InstrumentSearch.name.set()
        data['name'] = request.name

    await InstrumentSearch.next()  # direction button

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Buy", "Sell")

    with Client(config.TOKEN_full) as client:
        instrument = client.instruments.get_instrument_by(id_type=1, id=callback.data).instrument
        last_price = client.market_data.get_last_prices(figi=[callback.data]).last_prices[0].price
        last_price_cls = config.Qutotation(last_price.units, last_price.nano)
        await callback.message.answer(
            instrument.name + "\n" + instrument.instrument_type + "\n" + str(last_price_cls.price()),
            reply_markup=markup)

    await callback.answer()


@dp.message_handler(lambda message: message.text in ["Buy", "Sell"], state=InstrumentSearch.direction)
async def direction(message: types.Message, state: FSMContext):

    async with state.proxy() as data:
        data['direction'] = message.text

    await InstrumentSearch.next()  # lots

    await message.answer("Enter amount of lots for " +
                         ("buying " if data['direction'] == "Купить" else "selling") +
                         "1 lot = " + str(data['amount_in_lot']) + " amount")


@dp.message_handler(lambda message: message.text.isdigit, state=InstrumentSearch.lots)
async def set_lots_search(message: types.Message, state: FSMContext):

    async with state.proxy() as data:
        data['lots'] = int(message.text)

    await InstrumentSearch.next()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("OK", "Cancel")

    await bot.send_message(
        message.chat.id,
        md.text(
            md.text(md.bold(data['name'])),
            md.text('Amount of lots: ', md.code(data['lots'])),
            md.text('Type of operation:', data['direction']),
            sep='\n',
        ),
        reply_markup=markup,
        parse_mode=ParseMode.MARKDOWN,
    )


@dp.message_handler(Text("OK"), state=InstrumentSearch.status)
async def portfolio_button_handler(message: types.Message, state: FSMContext):

    async with state.proxy() as data:

        await asyncio.create_task(post_order(data['figi'], data['lots'], data['direction']))

    await message.answer("Your oder has been completed")


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


@dp.message_handler(Text("Trade terminal"))
async def cmd_start(message: types.Message):
    # Set state
    await InstrumentTerminal.figi.set()

    await message.reply("Write figi number")


@dp.message_handler(state=InstrumentTerminal.figi)
async def process_figi(message: types.Message, state: FSMContext):
    """
    Process figi name
    """
    async with state.proxy() as data:
        data['figi'] = message.text

    await InstrumentTerminal.next()
    await message.reply("How many lots do you need?")


# Check lots. Lots gotta be digit
@dp.message_handler(lambda message: not message.text.isdigit(), state=InstrumentTerminal.lots)
async def process_lots_invalid(message: types.Message):
    """
    If lots is invalid
    """
    return await message.reply("Amount of lots should be integer.\nHow many lots do you need? (onlu digits)")


@dp.message_handler(lambda message: message.text.isdigit(), state=InstrumentTerminal.lots)
async def process_lots(message: types.Message, state: FSMContext):
    # Update state and data
    await InstrumentTerminal.next()
    await state.update_data(lots=int(message.text))

    # Configure ReplyKeyboardMarkup
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Buy", "Sell")

    await message.reply("What do you want?", reply_markup=markup)


@dp.message_handler(lambda message: message.text not in ["Buy", "Sell"], state=InstrumentTerminal.direction)
async def process_order_invalid(message: types.Message):
    """

    """
    return await message.reply("Invalid type, use keyboard.")


@dp.message_handler(state=InstrumentTerminal.direction)
async def process_order(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['direction'] = message.text

        markup = types.ReplyKeyboardRemove()

        await asyncio.create_task(post_order(data['figi'], data['lots'], data['direction']))

        await bot.send_message(
            message.chat.id,
            md.text(
                md.text(md.bold(data['name'])),
                md.text('Amount of lot: ', md.code(data['lots'])),
                md.text('Type of operation:', data['direction']),
                sep='\n',
            ),
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN,
        )

    # Finish conversation
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
