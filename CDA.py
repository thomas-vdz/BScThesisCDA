# -*- coding: utf-8 -*-
"""
Created on Tue May  3 10:22:34 2022

@author: Gebruiker
"""
import csv
import random
from tqdm import tqdm
from copy import deepcopy

class Order:
    
    def __init__(self, oid, tid, otype, ptype, price, quantity, time):
        #Order ID: Integer, Unique id for each order
        self.oid = oid
        #Trader ID: Integer, ID of the trader who posted the order
        self.tid = tid
        #Order Type: String, bid or ask
        self.otype = otype
        #Product Type: String, either product X or product Y 
        self.ptype = ptype
        #Price: Integer, price of the good
        self.price = price
        #Quantity: Integer, quantity of the good
        self.quantity = quantity
        #Time: Integer at which tick of the system the order has been submitted
        self.time = time
        
    def __str__(self):
        return f"Order{self.oid}: trader{self.tid} posted a {self.otype} {self.price} per unit for {self.quantity} of good {self.ptype} at t={self.time}"



class Orderbook:

    def __init__(self):
        #Limit order book: Dictionary, 
        self.lob = {
            "X":{},
            "Y":{},
            }
        self.alob = {
            "X":{"bid":{},"ask":{}},
            "Y":{"bid":{},"ask":{}},
            }

    
    def anon_lob(self):
        #Test if there is a best-ask/bid present and report it in the anon_lob else return a empty list
        #For loop to avoid writing the same line 4 times
        for pair in [("X","bid"),("X","ask"),("Y","bid"),("Y","ask")]:
            
            #Check for each pair if there is an order in the orderbook and anonymize it
            if self.lob[pair[0]].get(pair[1]) is not None:
                order = self.lob[pair[0]].get(pair[1])                
                self.alob[pair[0]][pair[1]] = (order.price, order.quantity)
            else:
                #return empty order
                self.alob[pair[0]][pair[1]] = (None , None)
                
                
    def add_order_lob(self, order):        
        #Check if orderbook is empty
        if self.lob[order.ptype].get(order.otype) is None:
            self.lob[order.ptype][order.otype] = order
        else:
            if order.otype == "bid":
                #If the ordertype is bid replace the current bid if the price of the offer is higher
                if order.price > self.lob[order.ptype]["bid"].price:
                    self.lob[order.ptype][order.otype] = order
                else:
                    #ignore the order
                    pass
            elif order.otype == "ask":
                #If the ordertype is ask replace the current bid if the price of the offer is lower
                if order.price < self.lob[order.ptype]["ask"].price:
                    self.lob[order.ptype][order.otype] = order
                else:
                    #ignore the order
                    pass
        #Update the anonymous lob
        self.anon_lob()
    
    def del_order_lob(self, ptype, otype):
        
        del self.lob[ptype][otype]
        #Update the anonymous lob
        self.anon_lob()        
    
    
    
    
    

class Exchange(Orderbook):
            
    
    def __init__(self, traders):
        self.minprice = -1  # minimum price in the system, in cents/pennies
        self.maxprice = 201  # maximum price in the system, in cents/pennies
        self.traders = traders
        self.ob = Orderbook() #Orderbook
        
    
    def process_order(self, time, order):        
        trade = None
        
        if order.otype == "ask":
            #Check if they have enough to post the offer
            if order.quantity <= traders[order.tid].balance[order.ptype]:
                
                #Set the floor ask to maximum price if there is no current best floor 
                #To prevent the comparison to see if ask crosses bid to fail
                if self.ob.lob[order.ptype].get("bid") is None:
                    floorprice = self.minprice
                else:
                    floorprice = self.ob.lob[order.ptype].get("bid").price
                    
                
                #Check if the bid crosses the ask
                if order.price <= floorprice:
                    

                    #Get ID of counterparty                                       
                    buyer_id = self.ob.lob[order.ptype]["bid"].tid 
                    seller_id = order.tid
                    
                    #Check if counterparty still holds the money to complete the trade else delete their old offer
                    if ( self.ob.lob[order.ptype]["bid"].price * self.ob.lob[order.ptype]["bid"].quantity) <= traders[buyer_id].balance["money"]:
                        
                        #Partial sell: update quantity
                        if order.quantity < self.ob.lob[order.ptype]["bid"].quantity:
                            self.ob.lob[order.ptype]["bid"].quantity -= order.quantity                        
                            quant_sold = order.quantity
                            price_sold = self.ob.lob[order.ptype]["bid"].price
                            
                        
                        #Full sell: remove order
                        else:                        
                            
                            quant_sold = self.ob.lob[order.ptype]["bid"].quantity
                            price_sold = self.ob.lob[order.ptype]["bid"].price
                            self.ob.del_order_lob(order.ptype, "bid")
                        
                        #Create trade for book keeping (we might add type here if we want to save other transactions like cancellations)                
                        trade = {"time" : time,
                                 "buyer_id" : buyer_id,
                                 "seller_id" : seller_id,
                                 "price" : price_sold,
                                 "quantity" : quant_sold,
                                 "ptype" : order.ptype
                                 }
                        
                        return trade
                    else:
                        #Delete offer counterparty 
                        self.ob.del_order_lob(order.ptype, "bid")
                        #Add as regular offer
                        self.ob.add_order_lob(order)
                                                           
                else:
                    self.ob.add_order_lob(order)
        
            else:
                #Add functionality here to record traders posting infeasible bids
                #print("Not enough goods")
                pass
                
        elif order.otype == "bid":
            #Check if they have enough money to post the bid
            if (order.price * order.quantity) <= traders[order.tid].balance["money"]:
                                 
                #Set the floor ask to maximum price if there is no current best floor 
                #To prevent the comparison to see if bid crosses ask to fail
                if self.ob.lob[order.ptype].get("ask") is None:
                    floorprice = self.maxprice 
                else:
                    floorprice = self.ob.lob[order.ptype].get("ask").price
                    
                #Check if the bid crosses the ask if the floor offer does not exist give maxprice
                if order.price >= floorprice:
                    #Get id of counterparty
                    seller_id = self.ob.lob[order.ptype]["ask"].tid 
                    buyer_id  = order.tid
                    
                    #Check if counterparty still holds the goods to complete the trade else delete their old offer
                    if (order.quantity) <= traders[seller_id].balance[order.ptype]:
                        #Partial buy: update quantity
                        if order.quantity < self.ob.lob[order.ptype]["ask"].quantity:
                            self.ob.lob[order.ptype]["ask"].quantity -= order.quantity                        
                            quant_sold = order.quantity
                            price_sold = self.ob.lob[order.ptype]["ask"].price
                            
                        
                        #Full buy: remove order
                        else:                        
                            
                            quant_sold = self.ob.lob[order.ptype]["ask"].quantity
                            price_sold = self.ob.lob[order.ptype]["ask"].price
                            self.ob.del_order_lob(order.ptype, "ask")
                        
                        #Create trade for book keeping (we might add type here if we want to save other transactions like cancellations)                
                        trade = {"time" : time,
                                 "buyer_id" : buyer_id,
                                 "seller_id" : seller_id,
                                 "price" : price_sold,
                                 "quantity" : quant_sold,
                                 "ptype" : order.ptype
                                 }
                        return trade                                     
                    else:
                        #Delete offer counterparty 
                        self.ob.del_order_lob(order.ptype, "ask")
                        #Add as regular offer
                        self.ob.add_order_lob(order)
                else:
                    self.ob.add_order_lob(order)
            else:
                #Add functionality here to record traders posting infeasible bids
                #print("Not enough money")
                pass
        else:
            raise ValueError("Offer was neither a bid nor an ask")
        
    
    def publish_alob(self):
        """Updates the anonymous LOB"""
        self.ob.anon_lob()
        return self.ob.alob
    


#--------------------------- Traders -------------------------------------------------

#Main trader class
class Trader:
    
    def __init__(self, tid, ttype, talgo, balance):
        self.minprice = 1  # minimum price in the system, in cents/pennies
        self.maxprice = 200  # maximum price in the system, in cents/pennies
        self.tid = tid #Integer: Unique identifier for each trader
        self.ttype = ttype #Integer: 1,2,3 specifies which utility function the trader has
        self.talgo = talgo #String: What kind of trader it is: ZIP,ZIC eGD etc
        self.balance = balance #Dictionary containing the balance of the trader
        self.blotter = [] #List of executed trades
        self.utility = 0 #Utility level of the trader
        
        
    def __str__(self):
        return f"Trader{self.tid}: Money:{self.balance['money']}, X:{self.balance['X']}, Y, {self.balance['Y']}"    
        
    def calc_utility(self):
        """Function returning the current utility level given the balance and trader type"""
        
        if self.ttype == 1:
            self.utility = min( self.balance["money"]/400, self.balance["Y"]/20)            
        elif self.ttype == 2:
            self.utility = min( self.balance["money"]/400, self.balance["X"]/10)
        elif self.ttype == 3:
            self.utility = min( self.balance["X"]/10, self.balance["Y"]/20)
        else:
            raise ValueError("Invalid trader type. Traders must be of type 1, 2 or 3 INTEGER")
        
    def get_feasible_choices(self, orderbook):
        """Returns a list of all feasible option a trader has given the restiction that it should always improve the orderbook  """
        choices = [("do nothing"," ")] 
        
        if self.balance["X"] > 0:
            choices.append( ("ask", "X") )
        if self.balance["Y"] > 0: 
            choices.append( ("ask", "Y") )
        
        #Check if we can improve best bid
        if self.balance["money"] > int(orderbook["X"]["bid"][0] or 0):
            choices.append( ("bid", "X") )
            
        if self.balance["money"] >  int(orderbook["Y"]["bid"][0] or 0):
            choices.append( ("bid", "Y") )
                   
        return choices
        
    
    def bookkeep(self, trade):
        """Updates the balance of the trader and adds the trade to the blotter """
        #Add the transaction to blotter
        self.blotter.append(trade)
        
        #If trader and seller are the same do nothing
        if trade["buyer_id"] == trade["seller_id"]:
            pass
        #Check if its the buyer or seller of the trade and update balances
        elif trade["buyer_id"] == self.tid:
            
            #Add goods of correct type
            self.balance[ trade["ptype"] ] += trade["quantity"]
            #Subtract money
            self.balance["money"] -= (trade["quantity"] * trade["price"])
            
        elif trade["seller_id"] == self.tid:
            
            #Subtract goods of correct type
            self.balance[ trade["ptype"] ] -= trade["quantity"]
            #Add money
            self.balance["money"] += (trade["quantity"] * trade["price"])
            
        else:
            raise ValueError("Trader was not involved in this trade")
        
        #Recalculate utility
        self.calc_utility()
        
        #Return new balance and utility level after transaction
        return [self.balance , self.utility]
    
    #This method will be overwritten by the different traders
    def get_order(self, time, lob):
        """ Given the orderbook give an order """
        pass
    
    #This method will be overwritten by the different traders
    def response(self, time, orderbook):
        """ Given the orderbook post an order """
        pass
     



class Trader_ZI(Trader):
    """Trader with no intelligence restricted to posting offers it can complete"""
    def get_order(self, time, lob):
        
        money = self.balance["money"]
        
        #Gives list which goods the trader has more than one of
        available_goods = [item for item in ["X","Y"] if self.balance[item] > 0 ]
        
        quantity = 1 
        
        #Check if trader has money and at least one good then choose randomly to bid or ask
        if money > 0 and len(available_goods) > 0 :
            
            #Choose to bid or ask
            action = random.choice(["bid", "ask"])
            
            #If bid choose a random good to bid on and choose a random price 
            if action == "bid":
                good = random.choice(["X", "Y"])
                #Choose random price max is maxprice or money left whatever is less
                try:
                    price = random.randint( self.minprice, min(self.maxprice, money) )
                except:
                    #If error is raised because minprice==money then just set price to the amount of money
                    price = money
                 
                
            elif action == "ask":
                good = random.choice(available_goods)
                price = random.randint( self.minprice, self.maxprice )
        
        #Only money: post a random bid on a random good        
        elif money > 0:
            action = "bid"
            good = random.choice(["X", "Y"])
            #Choose random price max is maxprice or money left whatever is less
            try:
                price = random.randint( self.minprice, min(self.maxprice, money) )
            except:
                #If error is raised because minprice==money then just set price to the amount of money
                price = money
        
        #Only goods: Choose random good from available goods and a random price
        elif len(available_goods) > 0:
            action = "ask"
            good = random.choice(available_goods)
            #Choose random price
            price = random.randint( self.minprice, self.maxprice )
        else:
            print(f" {money}, {self.balance['X']}, {self.balance['Y']}")
            raise ValueError("No money and no goods")
        
        order = Order(1, self.tid, action, good, price, quantity, time)
        
        return order


class Trader_ZIP(Trader):
    """Modified version of the ZIP trader invented by Dave Cliff"""
    
    
    def __init__(self, tid, ttype, talgo, balance):
        Trader.__init__(self, tid, ttype, talgo, balance)
        
        self.last_price_bid = {"X":None, "Y": None}
        self.last_price_ask = {"X":None, "Y": None}
        self.gamma = 0.2 + 0.6 * random.random()  
        self.cgamma_old = {"X":0, "Y": 0}
        self.kappa = 0.1
        self.shout_price = {"X": 100*random.random(), "Y":100*random.random()}
        self.choice = None
        self.buyer = True
        self.active = True
    
    def get_order(self, time, lob):
        
        action = self.choice[0]
        
        if action == "do nothing":
            return None
        else:
            good = self.choice[1]
            price = round(self.shout_price[good])
            quantity = 1
            
            order = Order(1, self.tid, action, good, price, quantity, time)
            return order
    
    def choose_action(self, lob):
        choices = self.get_feasible_choices(lob)
        
        #Select random action
        action = random.choice(choices)        
        self.choice = action
        #Determine if buyer or seller this time pre 
        if action[0] == "ask":
            self.buyer = False
            
        elif action[0] == "bid":
            self.buyer = True
            
    def respond(self, time, lob):
        
                                                               
        def price_up(p_last, product):
            delta = 0.05 * random.random()
            lam = 0.05 * random.random()
            R = 1 + lam
            target = R*p_last + delta
            diff =  self.kappa*(target - self.shout_price[product])
            cgamma = self.gamma*self.cgamma_old[product] + (1 - self.gamma)*diff            
            self.cgamma_old[product] = cgamma
            self.shout_price[product] += cgamma
        
        def price_down(p_last, product):
            delta = -0.05 * random.random()
            lam = 0.05 * random.random()
            R = 1 - lam
            target = R*p_last + delta
            diff =  self.kappa*(target - self.shout_price[product])
            cgamma = self.gamma*self.cgamma_old[product] + (1 - self.gamma)*diff            
            self.cgamma_old[product] = cgamma
            self.shout_price[product] += cgamma
        
        
        for product in ["X","Y"]:
            best_bid = lob[product]["bid"][0]
            best_ask = lob[product]["ask"][0]
            
            #Check if we have a previous price
            if self.last_price_bid[product] != None:
                
                #If bid is now empty bid has been accepted
                if best_bid == None:
                    if self.buyer == True:
                        if self.shout_price[product] >= self.last_price_bid[product]:
                            price_down(self.last_price_bid[product], product)
                    elif self.buyer == False:
                        if (self.shout_price[product]  >= self.last_price_bid[product]) and self.active == True:
                            price_down(self.last_price_bid[product]  , product)
                        elif (self.shout_price[product] < self.last_price_bid[product]):
                            price_up( self.last_price_bid[product] , product)
                
                #If best bid is not none then we check if it was rejected or not                
                elif best_bid != None:
                    
                    if best_bid > self.last_price_bid[product]:
                        #Bid rejected
                        if self.buyer == True:
                            if (self.shout_price[product]  <= self.last_price_bid[product]) and self.active == True:
                                price_up( self.last_price_bid[product] , product)
                        elif self.buyer == False:
                            pass
              
            if self.last_price_ask[product] != None:
                
                if best_ask == None:
                    if self.buyer == True:
                        if (self.shout_price[product] <= self.last_price_ask[product]) and self.active == True:
                            price_up(self.last_price_ask[product] , product)
                        elif (self.shout_price[product] > self.last_price_ask[product]):
                            price_down(self.last_price_ask[product] , product)                    
                    elif self.buyer == False:
                        if self.shout_price[product] <= self.last_price_ask[product]:
                            price_up(self.last_price_ask[product] , product)
                        
                elif best_ask != None:
                    if best_ask < self.last_price_ask[product]:
                        #Ask rejected                        
                        if self.buyer == True:
                            pass
                        elif self.buyer == False:
                            if (self.shout_price[product]  >= self.last_price_ask[product]) and self.active == True:
                                price_down(self.last_price_ask[product] , product)  
                                
            self.last_price_bid[product] = lob[product]["bid"][0]
            self.last_price_ask[product] = lob[product]["ask"][0]
    
    
    
    

#-------------------------- Other functions --------------------------------
def create_csv(file_loc, dictionaries):
    """Creates csv file from a list of dictionaries"""
    #Get the keys of the dictionary as column names
    keys = dictionaries[0].keys()
    
    #ADD CHECK TO SEE IF FILE ALREADY EXISTS ELSE CREATE A NEW ONE
    
    #Create csv file with write access 
    file = open(file_loc, "w", newline='')
    
    dict_writer = csv.DictWriter(file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(dictionaries)
    
    #Close the file
    file.close()

def trader_type(tid, ttype, talgo):
        """Function returns the correct trader object given the talgo value and trader type"""
        
        #Give starting balance given the trading type for the STABLE scarf economy
        if ttype == 1:
            balance = {"money":0,"X":10,"Y":0}
        elif ttype == 2:
            balance = {"money":0,"X":0,"Y":20}
        elif ttype == 3:
            balance = {"money":400,"X":0,"Y":0}
        else:
            raise ValueError(f"Trader type {ttype} is invalid, please choose 1,2 or 3.")
        
        #Select the correct trader algorithm
        if talgo == 'ZI':
            return Trader_ZI(tid, ttype, talgo, balance)
        elif talgo == 'ZIP':
            return Trader_ZIP(tid, ttype, talgo, balance)
        else:
            raise ValueError(f"Trader of type {talgo} does not exist")
        
#-------------------------- END Other functions -----------------------------



# #Market session

endtime = 3000


#History of all succesfull trades
history = []
orders = []

time = 1 
order_id = 1

#Dictionary of traders indexed by unique trader id
traders = {}

#Create 15 ZI traders
trader_id = 1
for i in range(5):
    for j in [1,2,3]:
        traders[trader_id] = trader_type(trader_id, j, "ZIP") 
        trader_id += 1 

exchange = Exchange(traders)



for i in tqdm(range(endtime)):
    
    lob = exchange.publish_alob()
    #To add the factor of speed we can alter this bucket to have a trader in there more than once
    #Depending on what speed score it has gotten
    for i in range(1, len(traders)+1):
        traders[i].choose_action(lob)
    
    #List of all trader ID's for selecting which one can act
    trader_list = [i for i in range(1, len(traders)+1)]

    while len(trader_list) != 0:
        #Reset variables
        trade = None
        order = None
        
        #Choose random trader to act        
        tid = random.choice( trader_list )
        #Remove that trader from the temporary list
        trader_list.remove(tid)
        
        #Select that trader
        trader = traders[tid]
        
        #Ask the trader to give an order
        lob = exchange.publish_alob()
        
        
        order = trader.get_order(time, lob)
        
     
        #Check if trader gave an order
        if order:
            #Give order unique id and increment
            order.oid = order_id
            order_id += 1
            
            #Add order to the list 
            orders.append(deepcopy(order))
            
            
            #Process the order
            trade = exchange.process_order(time, order)
            
            alob = exchange.publish_alob()
            for i in range(1, len(traders)+1):
                traders[i].respond(time, alob)

            #Check if trade has occurred
            if trade is not None:
                #Update the balance and utility of the parties involved after the trade 
                #and save the current values of their balance and utility level after the trade
                seller_balance, seller_util = traders[ trade["seller_id"] ].bookkeep(trade)
                buyer_balance, buyer_util = traders[ trade["buyer_id"] ].bookkeep(trade)    
                
                
                #Add updated information to the trade
                trade["seller_util"] = seller_util
                trade["seller_balance"] = seller_balance
                trade["buyer_util"] = buyer_util
                trade["buyer_balance"] = buyer_balance
    
                #Append it to the history using deepcopy 
                history.append(deepcopy(trade))   
                if (seller_balance["money"] < 0 or buyer_balance["money"] < 0):
                    raise ValueError("money negative")
        else:
            pass
    time += 1


create_csv("test.csv", history)