import time
from time import strftime
import grequests
import os 
import sys
from engines.exchanges.loader import EngineLoader
import json

class CryptoEngineTriArbitrage(object):
    def __init__(self, exchange, mock=False):
        self.exchange = exchange
        self.mock = mock
        self.minProfitUSDT = 0.00013
        self.hasOpenOrder = True # always assume there are open orders first
        self.openOrderCheckCount = 0
      
        self.engine = EngineLoader.getEngine(self.exchange['exchange'], self.exchange['keyFile'])


    # This loop starts the engine for the triangular Arbitrage..Since it will not appear an exception 
    '''In order to have a successful arbitrage they exist some steps which have to follow:
    1st : To check if exist open orders (This mean that an arbitrage still waits to fullfill)
    2nd : Check how much balance we have from each coin 
    3rd : Check the orderbook 
    4rth : Place orders since they exist arbitrage opporunity
    '''
    
    def start_engine(self):
        print ('starting Triangular Arbitrage Engine...')
        while True:
            try:
                if  self.hasOpenOrder: #We always assume in the start of the program that we have open orders
                    self.check_openOrder()
                elif self.check_balance():           
                    bookStatus = self.check_orderBook()
                    if bookStatus['status']:
                        self.place_order(bookStatus['orderInfo'])
            except Exception as e :
               print (e)
            time.sleep(self.engine.sleepTime)
    
    def check_openOrder(self):
        if self.openOrderCheckCount >= 5:
            self.cancel_allOrders()
        else:
            print ('checking open orders...')
            rs = [self.engine.get_open_order()]
            responses = self.send_request(rs)

            if not responses[0]:
                print (responses)
                return False
            
            if responses[0].parsed:
                self.engine.openOrders = responses[0].parsed
                print (self.engine.openOrders)
                self.openOrderCheckCount += 1
            else:
                self.hasOpenOrder = False
                print ('no open orders')
                print ('starting to check order book...')
    
    def cancel_allOrders(self):
        print ('cancelling all open orders...')
        rs = []
        print (self.exchange['exchange'])
        for order in self.engine.openOrders:
            print (order)
            rs.append(self.engine.cancel_order(order['orderId']))

        responses = self.send_request(rs)
        
        self.engine.openOrders = []
        self.hasOpenOrder = False
   
   #Here we check the balance for each coin that we want to make Arbitrage
    def check_balance(self):
        rs = [self.engine.get_balance([
            self.exchange['tickerA'],
            self.exchange['tickerB'],
            self.exchange['tickerC']
            ])]

        responses = self.send_request(rs)
 
        self.engine.balance = responses[0].parsed
 
        return True
    
   #Check different opportunities which can give us arbitrage opportunities 
    def check_the_whole_order_book(self):
        # I used to the zero to define which path we want the program to follow 
        #Here we are interesting to see prices only from stable coins and fiat currencies
        #0 - BID 
        #1 - ASK
        all_combinations = [
             ['USD-EUR' , 'BTC-USD', 'BTC-EUR' , 0]
            ,['USDT-EUR' , 'BTC-USDT', 'BTC-EUR' , 0]
            ,['USD-EUR' , 'ETH-USD', 'ETH-EUR' , 0]
            ,['USDT-EUR' , 'ETH-USDT', 'ETH-EUR' , 0]
            ,['USD-EUR' , 'ADA-USD', 'ADA-EUR' , 0]
            ,['USDT-EUR' , 'ADA-USDT', 'ADA-EUR' , 0]
            ,['USD-EUR' , 'BAND-USD', 'BAND-EUR' , 0]
            ,['USDT-EUR' , 'BAND-USDT', 'BAND-EUR' , 0]
            ,['USD-EUR' , 'XLM-USD', 'XLM-EUR' , 0]
            ,['USDT-EUR' , 'XLM-USDT', 'XLM-EUR' , 0]
            ,['USD-EUR' , 'XRP-USD', 'XRP-EUR' , 0]
            ,['USDT-EUR' , 'XRP-USDT', 'XRP-EUR' , 0]
            ,['USD-EUR' , 'BSV-USD', 'BSV-EUR' , 0]
            ,['USDT-EUR' , 'BSV-USDT', 'BSV-EUR' , 0]
            ,['USD-EUR' , 'DOT-USD', 'DOT-EUR' , 0]
            ,['USDT-EUR' , 'DOT-USDT', 'DOT-EUR' , 0]
            ,['USD-EUR' , 'GRT-USD', 'GRT-EUR' , 0]
            ,['USDT-EUR' , 'GRT-USDT', 'GRT-EUR' , 0]
            ,['USD-EUR' , 'AAVE-USD', 'AAVE-EUR' , 0]
            ,['USDT-EUR' , 'AAVE-USDT', 'AAVE-EUR' , 0]
         
            ,['BTC-USDT' , 'ETH-BTC', 'ETH-USDT' , 0]
            ,['ETH-USDT' , 'BAND-ETH', 'BAND-USDT' , 0]
          
       
             
            
            ]
         
        while True:
            rs  = self.engine.get_all_tickers_of_bittrex()
            response = self.send_request([rs])
            json = response[0].json()
        
            for pairs in all_combinations:
                lastPrices = []
                bidRates = []
                askRates =  []
                
                tickerA = pairs[0].replace('-', ' ').split()[1] + '-USDT'
                tickerB = pairs[1].replace('-', ' ').split()[1] + '-USDT'
                tickerC = pairs[2].replace('-', ' ').split()[0] + '-USDT'
                
                tickers = [tickerA , tickerB , tickerC ]
                
                for ticker in tickers:
                    for value in json: 
                        if ticker == value['symbol']: 
                            lastPrices.append(value['lastTradeRate'])              

                    
                
                
                for pair in pairs:
                    for value in json:
                        if pair ==  value['symbol'] :
                            bidRates.append(value['bidRate'])
                            askRates.append(value['askRate']) 
                
           
                lastPrices =  list(map(float, lastPrices))
                bidRates = list(map(float, bidRates))
                askRates =list(map(float, askRates))

                
                bidRoute_result = 0 
                askRoute_result = 0
                
                if pairs[3] == 0:
                    bidRoute_result = (1 /  askRates[0]) / askRates[1] *   bidRates[2]
                else:
                    askRoute_result = (1 *  bidRates[0]) / askRates[2] *   bidRates[1] 
                
 
                if askRoute_result > 1 :
                    percentage_profit =( (askRoute_result - 1 ) / 1 ) * 100
                    print(pairs)
                    print('AskRoute Percentage Profit: %.2f' %  percentage_profit  + '%')
                    
                if bidRoute_result > 1 :
                    percentage_profit =( (bidRoute_result - 1 ) / 1 ) * 100
                    print(pairs)
                    print('BidRoute Percentage Profit:  %.2f' %  percentage_profit  + '%')
                    
                         
                        
                
            time.sleep(2)
     
    #This Function is going_to check the orderbook for the pairs that we have defined to see if we arbitrage.    
    def check_orderBook(self):
        rs = [self.engine.get_ticker_lastPrice(self.exchange['tickerA']),
              self.engine.get_ticker_lastPrice(self.exchange['tickerB']),
              self.engine.get_ticker_lastPrice(self.exchange['tickerC']),
        ]
        lastPrices = []
        for res in self.send_request(rs):
            for value in res.parsed.values(): 
                lastPrices.append(value)
                
        rs = [self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairA']),
              self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairB']),
              self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairC']),
              ]
 
        responses = self.send_request(rs)
       
        '''It supposed that we have an arbitrage opporunity since the bidRoute_result is greater than 1 
        or askRoute_result is greater than 1 
        '''
       
        
        # bid route BTC->ETH->LTC->BTC for instance
        '''
        MORE EXPLANATION
        1st We buy ETH for BTC 
        2nd We buy LTC for ETH 
        3rd We sell LTC for BTC
        
        '''
        bidRoute_result = (1 / responses[0].parsed['ask']['price']) / responses[1].parsed['ask']['price'] * responses[2].parsed['bid']['price']  
   
        if bidRoute_result > 1:
            print('Bidroute :'+ str(bidRoute_result) )
            percentage_profit =( (bidRoute_result - 1 ) / 1 ) * 100
            print('Percentage Profit:' + str(percentage_profit))
                    
        # ask route ETH->BTC->LTC->ETH for instance 
        '''
        MORE EXPLANATION
        1st We buy ETH for BTC 
        2nd We buy LTC for BTC 
        3rd We sell LTC for ETH
        
        '''
                
        askRoute_result = (1 * responses[0].parsed['bid']['price']) / responses[2].parsed['ask']['price']   * responses[1].parsed['bid']['price']
        if askRoute_result > 1 :
            print('Askroute :'+ str(askRoute_result) )
            percentage_profit =( (askRoute_result - 1 ) / 1 ) * 100
            print('Percentage Profit:' + str(percentage_profit))
        
        # Max amount for bid route & ask routes can be different and so less profit
        if bidRoute_result > 1 or \
        (bidRoute_result > 1 and askRoute_result > 1 and (bidRoute_result - 1) * lastPrices[0] > (askRoute_result - 1) * lastPrices[1]):
            status = 1 # bid route
        elif askRoute_result > 1:
            status = 2 # ask route
        else:
            status = 0 # do nothing
 
        if status   > 0  :
            #Since that now has appeared an arbitrage we have to check if with the fees we will have still a profit.
            maxAmounts = self.getMaxAmount(lastPrices, responses, status)
            fee = 0
            for index, amount in enumerate(maxAmounts):
                fee += amount * float(lastPrices[index])
            fee *= self.engine.feeRatio
            
            bidRoute_profit = (bidRoute_result - 1) * float(lastPrices[0]) * maxAmounts[0]
            askRoute_profit = (askRoute_result - 1) * float(lastPrices[1]) * maxAmounts[1]
            print ('bidRoute_profit - {0} askRoute_profit - {1} fee - {2}'.format( bidRoute_profit, askRoute_profit, fee))
            print('Profit-'+ str( bidRoute_profit - fee ))
            print('Profit-'+ str( askRoute_profit - fee ))
            if status == 1 and bidRoute_profit - fee > self.minProfitUSDT:
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "bid",
                        "price": responses[0].parsed['ask']['price'],
                        "amount":  maxAmounts[1]   
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "bid",
                        "price": responses[1].parsed['ask']['price'],
                        "amount": maxAmounts[2]   
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "ask",
                        "price": responses[2].parsed['bid']['price'],
                        "amount": maxAmounts[2]  
                    }                                        
                ]
                return {'status': 1, "orderInfo": orderInfo}
            elif status == 2 and askRoute_profit - fee > self.minProfitUSDT:
                print (strftime('%Y%m%d%H%M%S') + ' Ask Route: Result - {0} Profit - {1} Fee - {2}'.format(askRoute_result, askRoute_profit, fee))
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "ask",
                        "price": responses[0].parsed['bid']['price'],
                        "amount": maxAmounts[1]  
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "ask",
                        "price": responses[1].parsed['bid']['price'],
                        "amount": maxAmounts[2]   
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "bid",
                        "price": responses[2].parsed['ask']['price'],
                        "amount":maxAmounts[2]   
                    }                                        
                ]               
                return {'status': 2, 'orderInfo': orderInfo}
        return {'status': 0}
    
    # Using USDT may not be accurate
    # Here we calculate the max amounts that we can offer for the arbitrage
    def getMaxAmount(self, lastPrices, orderBookRes, status):
        maxUSDT = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # 1: 'bid', -1: 'ask'
            if index == 0: bid_ask = -1
            elif index == 1: bid_ask = -1
            else: bid_ask = 1
            # switch for ask route
            if status == 2: bid_ask *= -1
            bid_ask = 'bid' if bid_ask == 1 else 'ask'

            maxBalance = min(orderBookRes[index].parsed[bid_ask]['amount'], self.engine.balance[self.exchange[tickerIndex]])


            USDT = maxBalance * float(lastPrices[index]) * (1 - self.engine.feeRatio)
            if not maxUSDT or USDT < maxUSDT: 
                maxUSDT = USDT       

        maxAmounts = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # May need to handle scientific notation
            maxAmounts.append(maxUSDT / float(lastPrices[index]))

        return maxAmounts

    #This is the function for placing an order
    def place_order(self, orderInfo):
        print (orderInfo)
        rs = []
        for order in orderInfo:
            rs.append(self.engine.place_order(
                order['tickerPair'],
                order['action'],
                order['amount'],
                order['price'])
            )

        if  self.mock:
            responses = self.send_request(rs)

        self.hasOpenOrder = True
        self.openOrderCheckCount = 0

    #This is the function which is responsible to send the requests and it returns us the response from the API
    def send_request(self, rs):
        responses = grequests.map( rs )
        for res in responses:
            if not res:
                print (responses)
                raise Exception
        return responses


    ''' This function over here is responsible just to check all the pairs that I have defined inside to here
    to find in what percentages they exist arbitrage opportunities.
    
    For now you cannot choose both of them running.
    
    Choose the ckeck_the_whole_order_book or start_engine     
    '''
    def run(self):

      self.check_the_whole_order_book()
            #    self.start_engine()
        
 