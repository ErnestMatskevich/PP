import datetime
import random

from tinkoff.invest import Client

TOKEN_full = ""

TOKEN = ""

TOKEN_telegram = ""


def generate_key():
    char = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
            'v', 'w', 'x', 'y', 'z']
    current_datetime = datetime.datetime.now()
    data = str(current_datetime.day) + str(current_datetime.month) + str(current_datetime.year)
    time = str(current_datetime.hour) + str(current_datetime.minute) + str(current_datetime.second)
    random_part_num = str([str(random.randint(0, 9)) for i in range(10)]).replace(",", "'"). \
        replace("'", " ").replace(" ", "").replace("[", "]").replace("]", "")
    random_part_chr = str([str(random.choice(char)) for i in range(10)]).replace(",", "'"). \
        replace("'", " ").replace(" ", "").replace("[", "]").replace("]", "")

    return data + random_part_num + time + random_part_chr


class Portfolio:
    """ Portfolio storage class: statistics and positions """

    def __init__(self, total_amount_shares, total_amount_bonds, total_amount_etf, total_amount_currencies,
                 total_amount_futures, expected_yield, positions, account_id, total_amount_options, total_amount_sp,
                 total_amount_portfolio, virtual_positions):
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

        for i in range(len(positions)):
            tf_position = positions[i]
            position_name = get_name_by_figi(tf_position.figi)
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

        answer = ["Общая стоимость портфеля: " + self.total_amount_portfolio.full_price() + "\n",
                  "Стоимость акций в портфеле: " + self.total_amount_shares.full_price() + "\n",
                  "Cтоимость облигаций в портфеле: " + self.total_amount_bonds.full_price() + "\n",
                  "Стоимость фондов в портфеле: " + self.total_amount_etf.full_price() + "\n",
                  "Cтоимость валют в портфеле: " + self.total_amount_currencies.full_price() + "\n",
                  "Cтоимость фьючерсов в портфеле: " + self.total_amount_futures.full_price() + "\n",
                  "Текущая относительная доходность портфеля: " + str(self.excpected_yield.price()) + " %\n"]

        [answer.append(self.positions[i].show()) for i in range(len(self.positions))]

        return answer


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

    def get_currency(self):
        """ The method returns the currency code """
        return self.currency

    def full_price(self):
        """ The method returns a string with a numeric value and an indication of the currency """
        return str(MoneyValue.price(self)) + " " + MoneyValue.get_currency(self)


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

    def show(self):
        """ The method returns a string with position information """

        if self.instrument_type == "share":
            type = "Акция "
        elif self.instrument_type == "etf":
            type = "Фонд "
        elif self.instrument_type == "bond":
            type = "Облигация "
        else:
            type = "Валюта "

        answer = type + self.name + " " + str(self.quantity) + " шт " + "По средней цене: " + str(
            self.average_position_price.full_price() + " На общую сумму: " +
            str(self.quantity * self.average_position_price.price())) + " Доходность: " + str(
            self.expected_yield.price()) + "\n"
        return answer



