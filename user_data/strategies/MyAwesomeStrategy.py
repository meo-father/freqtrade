# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
from datetime import datetime

import pandas as pd
# --------------------------------
# Add your lib to import here
import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.persistence.trade_model import Trade
from freqtrade.strategy import (IntParameter, IStrategy)
from freqtrade.strategy import stoploss_from_absolute


class MyAwesomeStrategy(IStrategy):
    """
    This is a strategy template to get you started.
    More information in https://www.freqtrade.io/en/latest/strategy-customization/

    You can:
        :return: a Dataframe with all mandatory indicators for the strategies
    - Rename the class name (Do not forget to update class_name)
    - Add any methods you want to build your strategy
    - Add any lib you need to build your strategy

    You must keep:
    - the lib in the section "Do not remove these libs"
    - the methods: populate_indicators, populate_entry_trend, populate_exit_trend
    You should keep:
    - timeframe, minimal_roi, stoploss, trailing_*
    """
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 3

    # Optimal timeframe for the strategy.
    timeframe = '5m'

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {

    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -0.99
    use_custom_stoploss = True

    # Trailing stoploss
    trailing_stop = False
    # trailing_only_offset_is_reached = False
    # trailing_stop_positive = 0.01
    # trailing_stop_positive_offset = 0.0  # Disabled / not configured

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = True
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Strategy parameters
    buy_rsi = IntParameter(10, 40, default=20, space="buy")
    sell_rsi = IntParameter(60, 90, default=80, space="sell")

    # Optional order type mapping.
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    """
            "BTC/USDT",
            "BCH/USDT",
            "ETH/USDT",
            "LINK/USDT",
            "LTC/USDT",
            "SOL/USDT",
            "BNB/USDT",
            "XRP/USDT",
            "ADA/USDT",
            "DOT/USDT",
            "ETC/USDT",
            "LUNA/USDT"
    """
    # Optional order time in force.
    order_time_in_force = {
        'entry': 'GTC',
        'exit': 'GTC'
    }

    @property
    def plot_config(self):
        return {
            # Main plot indicators (Moving averages, ...)
            'main_plot': {
                'ema144': {'color': 'red'},
                'ema169': {'color': 'pink'},
                'ema576': {'color': 'green'},
                'ema676': {'color': 'yellow'},
                'ema12': {'color': 'blue'}
            },
            'subplots': {
                # Subplots - each dict defines one additional plot
                "RSI": {
                    'rsi': {'color': 'red'},
                }
            }
        }

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Dataframe with data from the exchange
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """

        # Momentum Indicators
        # ------------------------------------

        # ADX
        dataframe['adx'] = ta.ADX(dataframe)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe)

        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # MFI
        dataframe['mfi'] = ta.MFI(dataframe)

        # # ROC
        # dataframe['roc'] = ta.ROC(dataframe)

        # Overlap Studies
        # ------------------------------------

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe["bb_percent"] = (
                (dataframe["close"] - dataframe["bb_lowerband"]) /
                (dataframe["bb_upperband"] - dataframe["bb_lowerband"])
        )
        dataframe["bb_width"] = (
                (dataframe["bb_upperband"] - dataframe["bb_lowerband"]) / dataframe["bb_middleband"]
        )

        dataframe['ema144'] = ta.EMA(dataframe, timeperiod=144)
        dataframe['ema169'] = ta.EMA(dataframe, timeperiod=169)
        dataframe['ema576'] = ta.EMA(dataframe, timeperiod=576)
        dataframe['ema676'] = ta.EMA(dataframe, timeperiod=676)
        dataframe['ema12'] = ta.EMA(dataframe, timeperiod=12)
        dataframe.loc[qtpylib.crossed_above(dataframe["ema12"], dataframe["ema144"]), 'ema12x144'] = 1

        # TEMA - Triple Exponential Moving Average
        dataframe['tema'] = ta.TEMA(dataframe, timeperiod=9)

        # Cycle Indicator
        # ------------------------------------
        # Hilbert Transform Indicator - SineWave
        hilbert = ta.HT_SINE(dataframe)
        dataframe['htsine'] = hilbert['sine']
        dataframe['htleadsine'] = hilbert['leadsine']

        """
        # first check if dataprovider is available
        if self.dp:
            if self.dp.runmode.value in ('live', 'dry_run'):
                ob = self.dp.orderbook(metadata['pair'], 1)
                dataframe['best_bid'] = ob['bids'][0][0]
                dataframe['best_ask'] = ob['asks'][0][0]
        """

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with entry columns populated
        """
        dont_buy_conditions = [(dataframe["ema676"] > dataframe["close"])]
        dataframe.loc[(
                (dataframe["ema144"] > dataframe["ema576"]) &
                (dataframe["ema144"] > dataframe["ema676"]) &
                (dataframe["ema169"] > dataframe["ema576"]) &
                (dataframe["ema169"] > dataframe["ema676"]) &
                (dataframe["ema144"] < dataframe["bb_upperband"]) &
                (dataframe["ema144"] > dataframe["bb_lowerband"]) &
                (dataframe["close"] > dataframe["bb_middleband"]) &
                (dataframe['rsi'] > 70) &
                (dataframe["volume"] > 0)
        ), ['enter_long', 'enter_tag']] = (1, "rsi 70 且 突破")

        dataframe.loc[(
                (dataframe["ema144"] > dataframe["ema576"]) &
                (dataframe["ema144"] > dataframe["ema676"]) &
                (dataframe["ema169"] > dataframe["ema576"]) &
                (dataframe["ema169"] > dataframe["ema676"]) &
                (qtpylib.crossed_above(dataframe["ema12"], dataframe["ema144"])) &
                (dataframe["close"] > dataframe["bb_middleband"]) &
                (dataframe['rsi'] > 55) &
                (dataframe["volume"] > 0)
        ), ['enter_long', 'enter_tag']] = (1, "12x144 金叉")

        if dont_buy_conditions:
            for condition in dont_buy_conditions:
                dataframe.loc[condition, 'enter_long'] = 0
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(), ['exit_long', 'exit_tag']] = (0, 'long_out')
        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        if last_candle['ema576'] > last_candle['ema144']:
            return stoploss_from_absolute(last_candle["close"], current_rate, is_short=trade.is_short)

        # 从 下单后第 10 个开始判断是否当前的 144 和 169 的均线 开始变小
        if len(dataframe[dataframe["date"] > trade.open_date_utc]) > 200:
            temp = dataframe[dataframe["date"] == trade.open_date_utc]
            trade_k = temp.squeeze()
            if len(temp) == 1:
                if trade_k["ema144"] > last_candle["ema144"]:
                    return stoploss_from_absolute(last_candle["close"], current_rate, is_short=trade.is_short)

        # Use  parabolic  sar as absolute stoploss price
        stoploss_price = last_candle['ema676'] + (last_candle['ema676'] * -0.05)

        # Convert absolute price to percentage relative to current_rate
        if stoploss_price < current_rate:
            return stoploss_from_absolute(stoploss_price, current_rate, is_short=trade.is_short)

        # return maximum stoploss value, keeping current stoploss price unchanged
        return None

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        pd.set_option("display.max_columns", None)
        last_candle = dataframe.iloc[-1].squeeze()

        # Above 20% profit, sell when rsi < 80
        if current_profit > 0.2:
            if last_candle['rsi'] < 80:
                return 'rsi_below_80'

        # 12 对 144 死叉 有盈利就可以先退出 等金叉后接回来
        if current_profit > 0 and last_candle["ema12x144"] == 1:
            return '12 对 144 死叉'

        # Between 2% and 10%, sell if EMA-long above EMA-short

        if 0.02 < current_profit:
            if (last_candle["bb_lowerband"] < last_candle['ema169']
                    and last_candle["bb_middleband"] > last_candle['close']):
                return "布林轨道下沿跌破 169"

        if current_profit > 0.1:
            return '10%收益'
