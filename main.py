import math
import websocket, json, pprint, talib, numpy
import config
from binance.client import Client
from binance.enums import *
import time
import numpy as np



# pip uninstall numpy

# comparing chosen coin with tether
#SOCKET = "wss://testnet.binance.vision/ws/btcusdt@kline_15m"
# RSI candle period
RSI_PERIOD = 14
# Overbought indicator
RSI_OVERBOUGHT = 70
# Oversold indicator
RSI_OVERSOLD = 30
# Trade symbol
TRADE_SYMBOL = 'BTCUSDT'
# Amount to buy
TRADE_QUANTITY = 1
# Closes will be collected in a list
closes = []
# Don't own currency
in_position = False
# Client data
client = Client(config.BINANCE_API_KEY, config.BINANCE_SECRET_KEY, )
client.testnet = False


# Make an order
def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    try:
        # Sending order to binance
        print("Sending order....")
        # order data
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        # print order made
        print("Order completed!!!!")
        print(order)
    # Failed payment
    except Exception as e:
        print("an exception has occured - {}".format(e))
        return False

    return True


# Connection opened
def on_open(ws):
    print('Opened connection')


# Connection closed
def on_close(ws):
    print('Closed connection')


# Message recieved
def on_message(ws, message):
    global closes, in_position

    print('Incoming Message')
    json_message = json.loads(message)
    # Print in readable format
    pprint.pprint(json_message)

    candle = json_message['k']
    # Candle closed
    is_candle_closed = candle['x']
    close = candle['c']

    order_succeeded = order(SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL)

    if is_candle_closed:
        # Print out candle closing data
        print("Candle closed at {}".format(close))
        closes.append(float(close))
        print("Closes: ")
        print(closes)
        # if number of closes is greater than the RSI period
        if len(closes) > RSI_PERIOD:
            # Get array of 14 closes
            np_closes = numpy.array(closes)
            rsi = talib.RSI(np_closes, RSI_PERIOD)
            print("RSI'S calculted so far: ")
            print(rsi)
            # Get the previous RSI DATA
            last_rsi = rsi[-1]
            print("The current RSI: {}".format(last_rsi))
            # if the previous RSI is greater than the overbought limit
            if last_rsi > RSI_OVERBOUGHT:
                if in_position:
                    print("{TRADE_SYMBOL} is OVERBOUGHT, SELLING!!!!!!!")
                    # TRIGGER SELL ORDER
                    order_succeeded = order(SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL)
                    # IF SUCCESFULL
                    if order_succeeded:
                        in_position = False
                else:
                    print("NO {TRADE_SYMBOL} owned. DOING NOTHING!!!! ")
            # if the previous RSI is LESS than the oversold limit
            if last_rsi < RSI_OVERSOLD:
                if in_position:
                    print("{TRADE_SYMBOL} is OVERSOLD, but you already own this curreny. DOING NOTHING!!!!!.")
                else:
                    print("{TRADE_SYMBOL} is OVERSOLD, BUYING {TRADE_SYMBOL} !!!!!!!!!")
                    # buy logic
                    order_succeeded = order(SIDE_BUY, TRADE_QUANTITY, TRADE_SYMBOL)
                    # if buy successful
                    if order_succeeded:
                        in_position = True


def CheckKoyin(symbol, balances):
    sysUSDT = symbol + 'USDT'
    orders = client.get_all_orders(symbol=sysUSDT)
    sortedorders = sorted(orders, key=lambda x: x['time'], reverse=True)
    print("TÜM EMİRLER")
    print(sortedorders)

    curren_avail_coin = 0.0
    for balance in balances:
        if balance['asset'] == symbol:
            curren_avail_coin = balance['free']

    if float(curren_avail_coin) > 0.0:
        print("GERÇEKLEŞMİŞ ALIM EMİRLERİ:")
        for order in sortedorders:
            if (order['side'] == 'BUY' and order['status'] == 'FILLED'):
                print(order)
                sellOrderExists = False

                for order2 in sortedorders:
                    if (order2['side'] == 'SELL' and order2['status'] == 'NEW'):
                        sellOrderExists = True
                        break

                takeProfitPrice = (float(order['cummulativeQuoteQty']) / float(order['executedQty'])) * 1.05
                stopLossPrice = (float(order['cummulativeQuoteQty']) / float(order['executedQty'])) * 0.985
                if not sellOrderExists:
                    try:
                        q = math.floor(float(curren_avail_coin))
                        order1 = client.create_oco_order(
                            side='SELL',
                            symbol=symbolUSDT,
                            quantity=q,
                            price=round(takeProfitPrice, 2),
                            stopPrice=round(stopLossPrice, 2),
                            stopLimitPrice=round(stopLossPrice, 2),
                            stopLimitTimeInForce='GTC'
                        )
                        print('OCO EMİR GİRİLDİ...')
                        print(order1)
                    except Exception as ex:
                        print(ex)

                    break

# Get account info
freeCash = 0.0
account_info = client.get_account()
balances = account_info['balances']
for balance in balances:
    if (balance['asset'] == 'USDT' and float(balance['free']) >= 10.00):
        freeCash = balance['free']

# Bollinger bandı için parametreler
window_length = 1 * 24
num_std_dev = 2

RSI_PERIOD = 14
CANDLE_STICK_COUNT = 100

symbols = ['CHESS', 'MANA', 'SAND', 'LTC', 'MINA']


while True:
    print("Koyinler kontrol ediliyor...")
    try:
        for symbol in symbols:
            symbolUSDT = symbol + 'USDT'
            # Geçmiş verileri al
            klines = client.get_klines(symbol=symbolUSDT, interval=Client.KLINE_INTERVAL_15MINUTE,
                                       limit=CANDLE_STICK_COUNT)
            close_values = np.array([float(kline[4]) for kline in klines])

            rsi = talib.RSI(close_values, RSI_PERIOD)

            # Bollinger bandını hesapla
            upper_band, middle_band, lower_band = talib.BBANDS(close_values, timeperiod=20, nbdevup=num_std_dev,
                                                               nbdevdn=num_std_dev, matype=0)

            # Son fiyatı bollinger alt bandıyla karşılaştır
            last_price = float(client.get_symbol_ticker(symbol=symbolUSDT)['price'])
            if last_price <= lower_band[-1] and rsi[-1] <= 35:
                print(symbol + ' fiyatı bollinger alt bandına dokundu: ' + str(last_price))
                try:
                    TRADE_QUANTITY = round(float(freeCash) / last_price, 0)
                    order_succeeded = order(SIDE_BUY, TRADE_QUANTITY, symbolUSDT)
                except Exception as e:
                    print('=== BAŞARISIZ İŞLEM === ' + 'Koyin: ' + symbolUSDT)
                    print(e)

            CheckKoyin(symbol=symbol, balances=balances)

    except Exception as e:
        print('Hata oluştu: ' + str(e))

    time.sleep(5)

# Web socket
# s = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
# KEEP RUNNING
# ws.run_forever()