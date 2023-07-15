"""
This is a main file with interface for our project. It contains 1 function for help demonstrate portfolio of user
and 14 handlers (functions with decorators) for communicate with user
"""
import asyncio
import logging

import config
from config import Portfolio, MoneyValue, Qutotation, Search, InstrumentSearch, InstrumentTerminal
from tinkoff.invest import Client
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ParseMode
from aiogram.utils import executor

API_TOKEN = config.TOKEN_telegram

logging.basicConfig(level=logging.INFO, format="\033[33m {}".format('%(name)s %(levelname)s: %(message)s'))
# Create the Telegram Bot
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# All functions in this file are asyncronuos and except bottom one have @dp.message_nandler() for catch the user's text
async def portfolio_show(portfolio: list[str], chat_id: str):
    """
    Asynchronous function that send portfolio as text message to chat with user and Telegram bot

    :param portfolio: Takes list of strings from Portfolio.show()
    :param chat_id: Takes String as identificator of chat with bot and user
    :return: Nothing. Sent message(s)
    """
    answer = ""

    for i in range(len(portfolio)):
        answer = answer + str(portfolio[i]) + "\n"

        if i < len(portfolio) - 1:
            # Checking if the message exceeds the length limit with next position
            # if yes, then send current message and clear answer variable
            if len(answer + str(portfolio[i + 1])) >= 4096:
                await bot.send_message(chat_id, answer)
                answer = ""
        else:
            await bot.send_message(chat_id, answer)


# Start communication
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    This function activates by commands /start and /help, then sent a keybpard with menu

    :param message: Takes message that entered user (/start, /help)
    :return: Nothing. Sends main menu in chat
    """
    # Create buttons for keyboard
    kb = [
        [
            types.KeyboardButton(text="Portfolio"),
            types.KeyboardButton(text="Trade terminal"),
            types.KeyboardButton(text="Search")
        ],
    ]
    # Set properties for keyboard
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Choose action"
    )
    await message.answer("Hello, " + message.from_user.first_name)
    await message.answer("With help this bot you can trade directly in Telegram!", reply_markup=keyboard)


# Search branch
@dp.message_handler(Text("Search"))
async def search(message: types.Message):
    """
    This function activates when user pressed Search buttons, then ask name of instrument and save it in FSM

    :param message: Takes message that entered user (Search)
    """
    await Search.name.set()  # class Search() from config.py for store user data
    await message.answer("Enter name of instrument:")


@dp.message_handler(state=Search.name)
async def process_name(message: types.Message, state: FSMContext):
    """
    This function activates after user's input name for Search

    :param message: Takes message that entered user (name of financial instrument for searching)
    :param state: Saves name as state in FSM
    :return: Nothing. Sents keyboard in chat
    """
    inline_have, inline_not = config.find_instrument_by_name(message.text)

    await message.reply("Here what was found:")

    await message.answer("🟢 Instruments that you have 🟢", reply_markup=inline_have)
    await message.answer("🔴 Instruments that you don't have 🔴", reply_markup=inline_not)

    await state.finish()


@dp.callback_query_handler()
async def instrument_page(callback: types.CallbackQuery, state: FSMContext):
    """
    This function create a page for picked stock from the bot's message with all instruments which was found
    by user entered name

    :param callback: This object represents an incoming callback query from a callback button in an inline keyboard.
    :param state: Saves data of instrument as states in FSM
    """

    # Create keyboard with 2 buttons Buy and Sell
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Buy", "Sell")

    with Client(config.TOKEN_full) as client:
        # Get all data of picked stock from Tinkoff
        request = client.instruments.get_instrument_by(id_type=1, id=callback.data).instrument

        last_price = client.market_data.get_last_prices(figi=[callback.data]).last_prices[0].price
        last_price_cls = config.Qutotation(last_price.units, last_price.nano)  # Convert last_price to Quotation format

        await callback.message.answer(
            request.name + "\n" + request.instrument_type + "\n" + str(last_price_cls.price()),
            reply_markup=markup)

    # Initialization FSM for save all needs data of instrument

    await InstrumentSearch.figi.set()

    async with state.proxy() as data:
        data['figi'] = callback.data
        await InstrumentSearch.amount_in_lot.set()
        data['amount_in_lot'] = request.lot
        await InstrumentSearch.name.set()
        data['name'] = request.name

    await InstrumentSearch.next()  # Switch FSM to direction(buy/sell) button

    await callback.answer()


@dp.message_handler(lambda message: message.text in ["Buy", "Sell"], state=InstrumentSearch.direction)
async def direction(message: types.Message, state: FSMContext):
    """
    This function activates by pressing buttons Buy/Sell, save user's type(direction) of trade order

    :param message: Takes message that entered user (Buy/Sell)
    :param state: Saves direction as state in FSM
    :return: Nothing. Sends message in chat
    """
    async with state.proxy() as data:
        data['direction'] = message.text

    await InstrumentSearch.next()  # Switch FSM to amount of lots in this trade order

    # Message asks of amount lots for Buy/Sell
    # 1 lot usually is not equal 1 stock. Message inform about how many instruments in 1 lot.
    await message.answer("Enter amount of lots for " +
                         ("buying " if data['direction'] == "Buy" else "selling") +
                         "1 lot = " + str(data['amount_in_lot']) + " amount")


@dp.message_handler(lambda message: message.text.isdigit, state=InstrumentSearch.lots)
async def set_lots_search(message: types.Message, state: FSMContext):
    """
    This function activates after user enters amount of lots. Function saves amounts and return message with all
    user's input for matching trade order

    :param message: Takes message that entered user (amount of lots: int)
    :param state: Saves lots as state in FSM
    :return: Nothing. Sends information about order in chat
    """
    async with state.proxy() as data:
        data['lots'] = int(message.text)

    await InstrumentSearch.next()  # Switch FSM to status state (OK/Cancel)

    # Create keyboard with 2 buttons OK and cancel for adjustment trade order
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("OK", "Cancel")

    # Send message with user's trade order and 2 options: send order or cancel order (if e.g there is mistake)
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
async def send_order_nandler(message: types.Message, state: FSMContext):
    """
    This function activates when user pressed OK button and send trade order. Function posts trade order to broker's
    server and inform about it in the chat

    :param message: Takes message that entered user (OK)
    :param state: Takes states from FSM
    """

    async with state.proxy() as data:
        # With help post_order() function sends trade order with FIGI, amounts and type to broker's server
        await asyncio.create_task(config.post_order(data['figi'], data['lots'], data['direction']))

    # If sent successfully (without errors), then client will see this message
    await message.answer("Your oder has been completed")


# Portfolio branch
@dp.message_handler(Text("Portfolio"))
async def portfolio_button_handler(message: types.Message):
    """
    This function activates when user pressed Portfolio button from main menu and initializes Portfolio branch

    :param message: Takes message that entered user (Portfolio)
    :return: Nothing. Sends all information about Portfolio in chat
    """
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


# Trade terminal branch
@dp.message_handler(Text("Trade terminal"))
async def cmd_start(message: types.Message):
    """
    This function activates when user pressed Trade terminal button from main menu and initializes Trade terminal branch
    :param message: Takes message that entered user (Trade terminal)
    """
    # Set state
    await InstrumentTerminal.figi.set()

    await message.reply("Write figi number")


@dp.message_handler(state=InstrumentTerminal.figi)
async def process_figi(message: types.Message, state: FSMContext):
    """
    This function activates when user entered FIGI and saves it in FSM

    :param message: Takes message that entered user (FIGI number)
    :param state: Save FIGI as state in FSM
    """
    async with state.proxy() as data:
        data['figi'] = message.text

    await InstrumentTerminal.next()
    await message.reply("How many lots do you need?")


# Check lots
@dp.message_handler(lambda message: not message.text.isdigit(), state=InstrumentTerminal.lots)
async def process_lots_invalid(message: types.Message):
    """
    This function activates when user entered not digit for lots input and informes about it in chat.

    :param message: Takes wrong (not integer) input from user
    :return: Message about data type error
    """
    return await message.reply("Amount of lots should be integer.\nHow many lots do you need? (onlu digits)")


@dp.message_handler(lambda message: message.text.isdigit(), state=InstrumentTerminal.lots)
async def process_lots(message: types.Message, state: FSMContext):
    """
    This function activates when user enter amount of lots and continue branch next

    :param message: Takes right (integer) input from user
    :param state: Save amount of lots as state in FSM
    """
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
    This function checks using keyboard
    """
    return await message.reply("Invalid type, use keyboard.")


@dp.message_handler(state=InstrumentTerminal.direction)
async def process_order(message: types.Message, state: FSMContext):
    """
    This function activates when user entered direction (type of trade order) and sends trade order.

    :param message: Takes direction: Buy or Sell
    :param state: Saves direction as state in FSM
    :return: Nothing. Sends messages about order in chat.
    """
    async with state.proxy() as data:
        data['direction'] = message.text

        markup = types.ReplyKeyboardRemove()

        await asyncio.create_task(config.post_order(data['figi'], data['lots'], data['direction']))

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
