"""
config.py is a file that contains Tokens for work with API's and also contain helping classes and needing functions
"""

import datetime
import random

from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from tinkoff.invest import Client, GetOperationsByCursorRequest

# Tokens


# Full acces Token for connect to Tinkoff API
TOKEN_full = "t.zkPVI8qiRnM0btgMIhsaqBTy1TjnmcFXdgnjU8wyhQyZbG9hwXN9F7tABbBgn4O2WnZwE9sqQAewpSEru-no8w"

# Safe acces Token for connect to Tinkoff API. Provide all non-trade operations.
TOKEN = "t.zkPVI8qiRnM0btgMIhsaqBTy1TjnmcFXdgnjU8wyhQyZbG9hwXN9F7tABbBgn4O2WnZwE9sqQAewpSEru-no8w"

# Token for connect to Telegram Bot
TOKEN_telegram = "5523251499:AAGtkpPhKGBvzt2efV4WKj-JAP19tAIit_Y"


# Classes


# States
class InstrumentTerminal(StatesGroup):
    """Class needs for work with Trade terminal button and branch."""
    figi = State()
    lots = State()
    direction = State()


class InstrumentSearch(StatesGroup):
    """
    Class needs for store all information, user action and status(ok/error) when client interact with bot in menu
    of instrument, which opening after picking instrument from the finding list.
    """
    figi = State()

    amount_in_lot = State()
    name = State()

    direction = State()
    lots = State()
    status = State()


class Search(StatesGroup):
    """Class needs for find instrument, save name and use it in opening trade branch."""
    name = State()


class Qutotation:
    """ Class for storing numeric values without specifying a currency """

    def __init__(self, units, nano):
        """ The constructor accepts units - the integer part, nano - the fractional part """
        self.units = units
        self.nano = nano

    def price(self):
        """ The method returns the collected price as a float """
        if self.units >= 0 and self.nano >= 0:
            return round(float(str(self.units) + "." + str(int(str(self.nano)[::-1]))[::-1]), 7)
        elif self.units < 0 and self.nano < 0:
            return round(float(str(self.units) + "." + str(int(str(self.nano).replace("-", "")[::-1]))[::-1]), 7)
        elif self.units >= 0 and self.nano < 0:
            return round(float("-" + str(self.units) + "." + str(int(str(self.nano).replace("-", "")[::-1]))[::-1]), 7)
        else:
            return round(float(str(self.units) + "." + str(int(str(self.nano)[::-1]))[::-1]), 7)


class MoneyValue(Qutotation):
    """ Class for storing numeric values with currency """

    def __init__(self, units, nano, currency):
        """The constructor accepts units - the integer part, nano - the fractional part, currency - the currency code"""
        super().__init__(units, nano)
        self.currency = currency

    def get_currency(self) -> str:
        """The method returns the currency code """
        return self.currency

    def full_price(self) -> str:
        """ The method returns a string with a numeric value and an indication of the currency """
        return str(MoneyValue.price(self)) + " " + MoneyValue.get_currency(self)


class Portfolio:
    """Portfolio storage class: statistics and positions """

    def __init__(self, total_amount_shares: MoneyValue, total_amount_bonds: MoneyValue, total_amount_etf: MoneyValue,
                 total_amount_currencies: MoneyValue, total_amount_futures: MoneyValue, expected_yield: Qutotation,
                 positions: list, account_id: str, total_amount_options: MoneyValue,
                 total_amount_sp: MoneyValue, total_amount_portfolio: MoneyValue, virtual_positions: MoneyValue):
        """ The constructor takes the corresponding arguments from the returned object PortfolioResponse() """
        self.total_amount_shares = total_amount_shares
        self.total_amount_bonds = total_amount_bonds
        self.total_amount_etf = total_amount_etf
        self.total_amount_currencies = total_amount_currencies
        self.total_amount_futures = total_amount_futures
        self.excpected_yield = expected_yield
        self.positions = positions
        self.account_id = account_id
        self.total_amount_options = total_amount_options
        self.total_amount_sp = total_amount_sp
        self.total_amount_portfolio = total_amount_portfolio
        self.virtual_positions = virtual_positions

        def get_name_by_figi(figi):
            """ Returns the asset name by its FIGI number """
            with Client(TOKEN) as client:
                return client.instruments.get_instrument_by(id_type=1, id=figi).instrument.name

        # Loop for make each Position in Portfolio according to OOP structure

        for i in range(len(positions)):
            tf_position = positions[i]
            position_name = get_name_by_figi(tf_position.figi)

            # Create instance my_position from filled Position class
            my_position = Position(tf_position.figi, position_name, tf_position.instrument_type,
                                   tf_position.quantity.units,
                                   MoneyValue(tf_position.average_position_price.units,
                                              tf_position.average_position_price.nano,
                                              tf_position.average_position_price.currency),
                                   Qutotation(tf_position.expected_yield.units, tf_position.expected_yield.nano),
                                   MoneyValue(tf_position.current_nkd.units, tf_position.current_nkd.nano,
                                              tf_position.current_nkd.currency),
                                   Qutotation(tf_position.average_position_price_pt.units,
                                              tf_position.average_position_price_pt.nano),
                                   MoneyValue(tf_position.current_price.units, tf_position.current_price.nano,
                                              tf_position.current_price.currency),
                                   MoneyValue(tf_position.average_position_price_fifo.units,
                                              tf_position.average_position_price_fifo.nano,
                                              tf_position.average_position_price_fifo.currency),
                                   tf_position.quantity_lots.units, tf_position.blocked, tf_position.position_uid,
                                   tf_position.instrument_uid,
                                   MoneyValue(tf_position.var_margin.units, tf_position.var_margin.nano,
                                              tf_position.var_margin.currency),
                                   Qutotation(tf_position.expected_yield_fifo.units,
                                              tf_position.expected_yield_fifo.nano)
                                   )
            positions[i] = my_position

    def show(self):
        """ The method returns statistics on the portfolio and position in a convenient form """

        answer = ["Total portfolio value: " + self.total_amount_portfolio.full_price() + "\n",
                  "The value of shares in the portfolio: " + self.total_amount_shares.full_price() + "\n",
                  "The value of bonds in the portfolio: " + self.total_amount_bonds.full_price() + "\n",
                  "The value of the funds in the portfolio: " + self.total_amount_etf.full_price() + "\n",
                  "The cost of currencies in the portfolio: " + self.total_amount_currencies.full_price() + "\n",
                  "The cost of futures in the portfolio: " + self.total_amount_futures.full_price() + "\n",
                  "Current relative portfolio return: " + str(self.excpected_yield.price()) + " %\n"]

        [answer.append(self.positions[i].show()) for i in range(len(self.positions))]

        return answer


class Position:
    """ Class for storing portfolio position """

    def __init__(self, figi: str, name: str, instrument_type: str, quantity: int, average_position_price: MoneyValue,
                 expected_yield: Qutotation, current_nkd: MoneyValue, average_position_price_pt: Qutotation,
                 current_price: MoneyValue, average_position_price_fifo: MoneyValue, quantity_lots: int, blocked: bool,
                 position_uid: str, instrument_uid: str, var_margin: MoneyValue, expected_yield_fifo: Qutotation):
        """ The constructor takes the appropriate arguments from the returned PortfolioResponse.positions object and
        a name """
        self.figi = figi
        self.name = name
        self.instrument_type = instrument_type
        self.quantity = quantity
        self.average_position_price = average_position_price
        self.expected_yield = expected_yield
        self.current_nkd = current_nkd
        self.average_position_price_pt = average_position_price_pt
        self.current_price = current_price
        self.average_position_price_fifo = average_position_price_fifo
        self.quantity_lots = quantity_lots
        self.blocked = blocked
        self.position_uid = position_uid
        self.instrument_uid = instrument_uid
        self.var_margin = var_margin
        self.expected_yield_fifo = expected_yield_fifo

    def show(self) -> str:
        """ The method returns a string with position information """

        # This block needs for localization to Russian
        # Change value of type_for_answer with respect to language and self.instrument_type
        # Example: if self.instrument_type = "share", then type_for_answer = "Акция"

        if self.instrument_type == "share":
            type_for_answer = "Share "
        elif self.instrument_type == "etf":
            type_for_answer = "Fund or ETF "
        elif self.instrument_type == "bond":
            type_for_answer = "Bond "
        else:
            type_for_answer = "Currency "

        answer = type_for_answer + self.name + " " + str(self.quantity) + " pc " + "Average price: " + str(
            self.average_position_price.full_price() + " For total cost: " +
            str(self.quantity * self.average_position_price.price())) + " Yield: " + str(
            self.expected_yield.price()) + "\n"

        return answer


# Functions


def generate_key() -> str:
    """
    Function that generate unique string key for marked request

    :return: String in next format: ddmmyynnnnnnnnnnhhmmssxxxxxxxxxx, where dd - day, mm - month, yy - year, n - random
    digit, hh - hours, mm - minutes, ss - seconds, x - random char
    """

    char = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
            'v', 'w', 'x', 'y', 'z']
    current_datetime = datetime.datetime.now()
    data = str(current_datetime.day) + str(current_datetime.month) + str(current_datetime.year)
    time = str(current_datetime.hour) + str(current_datetime.minute) + str(current_datetime.second)
    random_part_num = str([str(random.randint(0, 9)) for _ in range(10)]).replace(",", "'"). \
        replace("'", " ").replace(" ", "").replace("[", "]").replace("]", "")
    random_part_chr = str([str(random.choice(char)) for _ in range(10)]).replace(",", "'"). \
        replace("'", " ").replace(" ", "").replace("[", "]").replace("]", "")

    return data + random_part_num + time + random_part_chr


async def post_order(figi: str, lots: int, direction: str):
    """
    Asynchronous function that sends trade order to the server

    :param figi: String of unique FIGI needs for identification financial instrument
    :param lots: Integer that represents amount of lots for thic trade order
    :param direction: String that can be iqual either "Sell" either "Buy", needs for marks type of order respectevely
    :return: Nothing. Send request to broker
    """

    if direction == "Sell":
        direction = 2
    else:
        direction = 1

    with Client(TOKEN_full) as client:
        client.orders.post_order(figi=figi, quantity=lots,
                                 direction=direction,
                                 account_id=client.users.get_accounts().accounts[0].id,
                                 order_type=2, order_id=generate_key())


def find_instrument_by_name(name_instrument: str) -> tuple:
    """
    Function that find names of financial instruments which contain entering name and splits result in tuple by
    2 categories: instruments in/out portfolio

    :param name_instrument: String that contains user's enter name
    :return: Tuple that contains InlineKeyboardMarkup
    """
    with Client(TOKEN_full) as client:
        request = client.instruments.find_instrument(query=name_instrument)

        accounts = client.users.get_accounts()
        account_id = accounts.accounts[0].id

        inline_have = InlineKeyboardMarkup(row_width=1)
        inline_not = InlineKeyboardMarkup(row_width=1)

        for i in request.instruments:
            if instrument_have(i.figi, account_id=account_id):
                inline_have.add(InlineKeyboardButton(i.name, callback_data=i.figi))
            else:
                inline_not.add(InlineKeyboardButton(i.name, callback_data=i.figi))

    return inline_have, inline_not


def instrument_have(figi: str, account_id: str) -> bool:
    """
    Boolean function that checks is account_id has instrument with entered figi number

    :param figi: String of unique FIGI needs for identification financial instrument
    :param account_id: String of user's account identificator
    """

    with Client(TOKEN_full) as client:
        def get_request(cursor=""):
            return GetOperationsByCursorRequest(
                account_id=account_id,
                instrument_id=figi,
                cursor=cursor,
                limit=1,
            )

        operations = client.operations.get_operations_by_cursor(get_request())
        return operations.has_next
