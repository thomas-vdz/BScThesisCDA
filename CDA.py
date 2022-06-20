
import csv
import random
from tqdm import tqdm, trange
from copy import deepcopy
import os
from datetime import datetime
from operator import itemgetter
import numpy as np

from time import time as t
  
  
def timer_func(func):
    # This function shows the execution time of 
    # the function object passed
    def wrap_func(*args, **kwargs):
        t1 = t()
        result = func(*args, **kwargs)
        t2 = t()
        print(f"Function {func.__name__!r} executed in {(t2-t1):.7f}s")
        return result
    return wrap_func


class Order:
    """
    Order object

    ...

    Attributes
    ----------
    oid : int
        Unique identifier for each order.
    tid : int 
        Trader ID for trader who posted the order.
    otype : str {"ask", "bid"}
        Order type indicating if its a bid or an ask. 
    ptype : str {"X", "Y"}
        Product type of the order.
    price : int 
        Price per unit of the order.
    quantity : int
        Quantity of the good.
    time : int
        Number indicating in which timestep the order was posted.
    accepted : bool, optional, default=False
        Boolean indicating if order got accepted by the exchange
    lob : dict
        Limit order book at the time of posting to see why orders are rejected

    """
    def __init__(self, oid, tid, otype, ptype, price, quantity, time):
        """
        Constructs all the necessary attributes for the order object.

        Parameters
        ----------
        oid : int
            Unique identifier for each order.
        tid : int 
            Trader ID for trader who posted the order.
        otype : str {"ask", "bid"}
            Order type indicating if its a bid or an ask. 
        ptype : str {"X", "Y"}
            Product type of the order.
        price : int 
            Price per unit of the order.
        quantity : int
            Quantity of the good.
        time : int
            Number indicating in which timestep the order was posted.
        """
        
        self.oid = oid
        self.tid = tid
        self.otype = otype
        self.ptype = ptype
        self.price = price
        self.quantity = quantity
        self.time = time
        self.accepted = False
        self.strategic = False

        
    def __str__(self):
        return f"Order{self.oid}: trader{self.tid} posted a {self.otype} {self.price} per unit for {self.quantity} of good {self.ptype} at t={self.time}, {self.accepted}"


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
            return True
        else:
            if order.otype == "bid":
                #If the ordertype is bid replace the current bid if the price of the offer is higher
                if order.price > self.lob[order.ptype]["bid"].price:
                    self.lob[order.ptype][order.otype] = order
                    return True
                else:
                    #ignore the order
                    return False
            elif order.otype == "ask":
                #If the ordertype is ask replace the current bid if the price of the offer is lower
                if order.price < self.lob[order.ptype]["ask"].price:
                    self.lob[order.ptype][order.otype] = order
                    return True
                else:
                    #If order did not improve orderbook then it does not count as a change so exchange should know this to avoid calling response
                    return False
    
    def del_order_lob(self, ptype, otype):
        
        del self.lob[ptype][otype]
        #Update the anonymous lob
        self.anon_lob()        
    
    
class Exchange(Orderbook):
            
    
    def __init__(self, traders):
        self.minprice = 0  # minimum price in the system, in cents/pennies
        self.maxprice = 201  # maximum price in the system, in cents/pennies
        self.traders = traders
        self.ob = Orderbook() #Orderbook
        
    
    def process_order(self, time, order):        
        trade = None
        successful_order = True
        
        #Reject order if not in min/maxprice
        if order.price <= self.minprice or order.price >= self.maxprice:
            return False, None
        
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
                        
                        if self.ob.lob[order.ptype]["bid"].strategic is True:
                            arbitrage = True
                        else:
                            arbitrage = False
                            
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
                                 "ptype" : order.ptype,
                                 "arbitrage" : arbitrage,
                                 "taker" : buyer_id
                                 }
                        
                    else:
                        #Delete offer counterparty 
                        self.ob.del_order_lob(order.ptype, "bid")
                        #Add as regular offer
                        successful_order = self.ob.add_order_lob(order)
                                                           
                else:
                    successful_order = self.ob.add_order_lob(order)
        
            else:
                #Add functionality here to record traders posting infeasible bids
                successful_order = False
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
                        
                        if self.ob.lob[order.ptype]["ask"].strategic is True:
                            arbitrage = True
                        else:
                            arbitrage = False
                        
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
                                 "ptype" : order.ptype,
                                 "arbitrage" : arbitrage,
                                 "taker" : seller_id
                                 }                                     
                    else:
                        #Delete offer counterparty 
                        self.ob.del_order_lob(order.ptype, "ask")
                        #Add as regular offer
                        successful_order = self.ob.add_order_lob(order)
                else:
                    successful_order = self.ob.add_order_lob(order)
            else:
                #Add functionality here to record traders posting infeasible bids
                #print("Not enough money")
                successful_order = False
                pass
        else:
            raise ValueError("Offer was neither a bid nor an ask")
        
        return successful_order, trade
    
    
    def reset_allocations(self):
        #Resets allocation for all traders
        for i in range(1, len(traders)+1):
            traders[i].reset_allocation()
    
    def publish_alob(self):
        """Updates the anonymous LOB"""
        self.ob.anon_lob()
        return self.ob.alob
    


#--------------------------- Traders -------------------------------------------------

#Main trader class
class Trader:
    

    def __init__(self, tid, ttype, talgo):
        self.minprice = 1  # minimum price in the system, in cents/pennies
        self.maxprice = 200  # maximum price in the system, in cents/pennies
        self.tid = tid #Integer: Unique identifier for each trader
        self.ttype = ttype #Integer: 1,2,3 specifies which utility function the trader has
        self.talgo = talgo #String: What kind of trader it is: ZIP,ZIC eGD etc
        self.balance = {}  #Dictionary containing the balance of the trader
        self.blotter = [] #List of executed trades
        self.pending_orders = []
        self.utility = 0 #Utility level of the trader
        self.active = False
        self.reset_allocation()
        
    def __str__(self):
        return f"Trader{self.tid}: Money:{self.balance['money']}, X:{self.balance['X']}, Y, {self.balance['Y']}"    
    
    def reset_allocation(self):
        #Give starting balance given the trading type for the STABLE scarf economy
        if self.ttype == 1:
            balance = {"money":0,"X":10,"Y":0}
        elif self.ttype == 2:
            balance =  {"money":0,"X":0,"Y":20}
        elif self.ttype == 3:
            balance =  {"money":400,"X":0,"Y":0}
        else:
            raise ValueError(f"Trader type {self.ttype} is invalid, please choose 1,2 or 3.")
        self.balance = balance
        self.active = True
        self.utility = 0 
        
            
    def calc_utility(self, balance):
        """Function returning the current utility level given the balance and trader type.
           If a new balance is given it calculates the utility of the new_balance else it calulates the agents current utility
        """
            
        if self.ttype == 1:
            utility = min( balance["money"]/400, balance["Y"]/20)            
        elif self.ttype == 2:
            utility = min( balance["money"]/400, balance["X"]/10)
        elif self.ttype == 3:
            utility = min( balance["X"]/10, balance["Y"]/20)
        else:
            raise ValueError("Invalid trader type. Traders must be of type 1, 2 or 3 INTEGER")
            
        return utility

    def excess(self):
        """Returns the excess allocation it has given the balance"""
        excess = {"money":0,"X":0,"Y":0}
        
        if self.ttype == 1:
            excess["X"] += self.balance["X"]
            util_m = self.balance["money"]/400
            util_y = self.balance["Y"]/20
            
            if util_m > util_y:
                e = (self.balance["money"] - util_y*400)
                excess["money"] += e
            elif util_m < util_y:
                e = (self.balance["Y"] - util_m*20)
                excess["Y"] += e
                
        elif self.ttype == 2:
            excess["Y"] += self.balance["Y"]
            util_m = self.balance["money"]/400
            util_x = self.balance["X"]/10
            
            if util_m > util_x:
                e = (self.balance["money"] - util_x*400)
                excess["money"] += e
            elif util_m < util_x:
                e = (self.balance["X"] - util_m*10)
                excess["X"] += e
                
        elif self.ttype == 3:
            excess["money"] += self.balance["money"]
            util_x = self.balance["X"]/10
            util_y = self.balance["Y"]/20
            
            if util_x > util_y:
                e = (self.balance["X"] - util_y*10)
                excess["X"] += e
            elif util_x < util_y:
                e = (self.balance["Y"] - util_x*20)
                excess["Y"] += e   
        return excess
    
    def get_feasible_choices(self, orderbook, do_nothing=True):
        """Returns a list of all feasible options a trader has given the restiction that it should always improve the orderbook  """
        
        if do_nothing:
            choices = [("do nothing"," ")] 
        else:
            choices = []
        
        
        if self.balance["X"] > 0:
            choices.append( ("ask", "X") )
        if self.balance["Y"] > 0: 
            choices.append( ("ask", "Y") )
            
        #Check if we can improve best bid
        if self.balance["money"] > (orderbook["X"]["bid"][0] or 0):
            choices.append( ("bid", "X") )
            
        if self.balance["money"] >  (orderbook["Y"]["bid"][0] or 0):
            choices.append( ("bid", "Y") )                
        
        # if self.tid == 1:
        #     if ("bid","X") in choices:
        #         choices.remove(("bid","X") )
        # elif self.tid == 2:
        #     if ("bid","Y") in choices:
        #         choices.remove(("bid","Y") )
        # elif self.tid == 3:
        #     if ("ask","X") in choices:
        #         choices.remove(("ask","X") )
        #     if ("ask","Y") in choices:
        #         choices.remove(("ask","Y") )    
                
        
        return choices
    
    def add_pending_order(self, order):
        """Adds pending order to the list"""
        self.pending_orders.append(order)
    
    def check_pending_orders(self, lob, trade):
        """Checks if orders are still pending in orderbook"""
        
        if len(self.pending_orders) > 0:
            still_pending_orders = []
            for order in self.pending_orders:
                if lob[order.ptype][order.otype] == (order.price, order.quantity):
                    still_pending_orders.append(order)
            
            self.pending_orders = still_pending_orders
                

    
    def utility_gain_order(self, order):
        """Function takes in an order and calculates the utility difference before and after assuming the order would result in an transaction"""
        new_balance = deepcopy(self.balance)
        #Check what the new balance will be if the order leads to a transaction
        if order.otype == "ask":
            new_balance["money"] += order.price * order.quantity
            new_balance[order.ptype] -= order.quantity
        elif order.otype == "bid":
            new_balance["money"] -= order.price * order.quantity
            new_balance[order.ptype] += order.quantity


        return self.calc_utility(new_balance) - self.calc_utility(self.balance)
    
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
        self.utility = self.calc_utility(self.balance)
        
        #Return new balance and utility level after transaction
        return [self.balance , self.utility]
    
    #This method will be overwritten by the different traders
    def get_order(self, time, lob):
        """ Given the orderbook give an order """
        pass
    
    #This method will be overwritten by the different traders
    def respond(self, time, lob, order):
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
        #Check if the order does not decrease utility else post nothing
        if self.utility_gain_order(order) >= 0 :                    
            return order
        else:
            #Order does not give extra utility
            return None
        

class Trader_ZIP(Trader):
    """
    Modified version of the ZIP trader invented by Dave Cliff.
    This algorithms still chooses a random choice out of feasible options but chooses its shout prices in a smart way.
    
    """
    
    
    def __init__(self, tid, ttype, talgo):
        Trader.__init__(self, tid, ttype, talgo)
        
        self.last_price_bid = {"X":None, "Y": None}
        self.last_price_ask = {"X":None, "Y": None}
        self.gamma = 0.2 + 0.6 * random.random()  
        self.cgamma_old = {"X":0, "Y": 0}
        self.kappa = 0.1 + 0.4 * random.random()
        self.shout_price = {"X": 20 + 60*random.random(), "Y": 10 + 30*random.random()}
        self.choice = None
        self.buyer = True
        self.active = True
    
    def get_order(self, time, lob):
        
        action = self.choice[0]
        
        
        #If no action dont return an order
        if action == "do nothing":
            return None
        else:
            #Get good of the action and their calculated shout price
            good = self.choice[1]
            price = round(self.shout_price[good])
            quantity = 1
            
            #Check if they can improve the order book with this shout price else order will get rejected
            # (lob[good]["bid"][0] or 0) gives a 0 when there is no best bid and  (lob[good]["ask"][0] or 10000) gives a 10000 if there is no best ask
            if (action == "bid" and (price > (lob[good]["bid"][0] or 0)) ) or (action == "ask" and (price < (lob[good]["ask"][0] or 10000))):
                order = Order(1, self.tid, action, good, price, quantity, time)
                
                #Check if the order does not decrease utility else post nothing
                if self.utility_gain_order(order) >= 0 and price > 0:                 
                    return order
                else:
                    #Order does not give extra utility
                    return None
            else:
                #It cant post an offer at this shoutprice
                return None
    
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
            
    def respond(self, time, lob, order):
        
                                                               
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
        
        #Adjust shout price for both products
        for product in ["X","Y"]:
            best_bid = lob[product]["bid"][0]
            best_ask = lob[product]["ask"][0]
            
            #Check if we have a previous price
            if self.last_price_bid[product] != None:               
                last_price = self.last_price_bid[product]
                shout_price = self.shout_price[product]
                
                #If bid is now empty bid has been accepted
                if best_bid is None:
                    #Bid has been crossed
                    if self.buyer is True:
                        if shout_price >= last_price:
                            price_down(last_price, product)
                    elif self.buyer is False:
                        if (shout_price  >= last_price) and self.active is True:
                            price_down(last_price  , product)
                        elif (shout_price < last_price):
                            price_up( last_price , product)
                
                #If best bid is not none then we check if it was rejected or not                
                elif best_bid is not None:
                    
                    if best_bid > last_price:
                        #Bid rejected
                        if self.buyer is True:
                            if (shout_price  <= last_price) and self.active is True:
                                price_up( last_price , product)
                        elif self.buyer is False:
                            pass
              
            if self.last_price_ask[product] is not None:                
                last_price = self.last_price_ask[product]
                shout_price = self.shout_price[product]
                
                if best_ask is None:
                    #Ask has been crossed
                    if self.buyer is True:
                        if (shout_price <= last_price) and self.active is True:
                            price_up(last_price , product)
                        elif (shout_price > last_price):
                            price_down(last_price , product)                    
                    elif self.buyer is False:
                        if shout_price <= last_price:
                            price_up(last_price , product)
                        
                elif best_ask is not None:
                    if best_ask < last_price:
                        #Ask rejected                        
                        if self.buyer is True:
                            pass
                        elif self.buyer is False:
                            if (shout_price  >= last_price) and self.active is True:
                                price_down(last_price , product)  
            
            #Set the last price to the new price
            self.last_price_bid[product] = lob[product]["bid"][0]
            self.last_price_ask[product] = lob[product]["ask"][0]
    
        
class Trader_eGD(Trader):
    """
    eGD Trader
    
    """
    history = {
        "X":[],
        "Y":[],
        } 
    
    last_lob = {
            "X":{"bid":(None,None),"ask":(None,None)},
            "Y":{"bid":(None,None),"ask":(None,None)},
            }
    
    new_turn = False
    e_price = {"X": 20 + 60*random.random(), "Y":10 + 30*random.random()}

    def __init__(self, tid, ttype, talgo):
        Trader.__init__(self, tid, ttype, talgo)
        self.markup = 0 #0.01 + 0.01 * random.random()
        self.memory = 30
        self.possible_orders = []


    def trim_history(self, good):
        n_trades = len([t for t in Trader_eGD.history[good] if t[2]==True])
                      
        if n_trades > self.memory:
            #Get the index of the first trade
            index = [t[2] for t in Trader_eGD.history[good]].index(True)
            #Forget the history that happend before and including the last trade
            Trader_eGD.history[good] = Trader_eGD.history[good][index+1:]
        

    def p_bid_accept(self, good, price):
        """ Estimates the probability a bid will be accepted given previous observations"""
        
        if price == 0:
            return 0
        elif price == 200:
            return 1
        
        q_bid_acc = sum( [ q[1] for q in Trader_eGD.history[good] if (q[0] <= price  and q[2] == True and q[3] == "bid" ) ] )
        q_ask = sum( [ q[1] for q in Trader_eGD.history[good] if (q[0] <= price and q[3] == "ask" )] )
        
        #Rejected bids
        q_bid_rej = sum( [ q[1] for q in Trader_eGD.history[good] if (q[0] >= price and q[2] == False and q[3] == "bid") ] )
        
        try:
            prob = (q_bid_acc + q_ask ) / (q_bid_acc + q_ask + q_bid_rej)
            return prob
        except:
            return 0
    
    def p_ask_accept(self, good, price):
        """ Estimates the probability an ask will be accepted given previous observations"""
        
        if price == 0:
            return 1
        elif price == 200:
            return 0
        
        q_ask_acc = sum( [ q[1] for q in Trader_eGD.history[good] if (q[0] >= price  and q[2] == True and q[3] == "ask" ) ] )
        q_bid = sum( [ q[1] for q in Trader_eGD.history[good] if (q[0] >= price and q[3] == "bid" )] )
        
        #Rejected asks
        q_ask_rej = sum( [ q[1] for q in Trader_eGD.history[good]if (q[0] <= price and q[2] == False and q[3] == "ask") ] )
                
        try:
            prob = (q_ask_acc + q_bid ) / (q_ask_acc + q_bid + q_ask_rej)
            return prob
        except:
            return 0  
        
    def GD_spline(self, good, action, a0, a1):
        
        if a0 > a1:
            raise ValueError("We need that a0 > a1")
        
        mat = np.array([ [a0**3, a0**2, a0, 1],
                         [a1**3, a1**2, a1, 1],
                         [3*a0**2, 2*a0, 1, 0],
                         [3*a1**2, 2*a1, 1, 0] ])
        
        inv_mat = np.linalg.inv(mat)
        
        #Here we assume that the probabilty that you can buy for 200 is 1 and 0 for 0
        if action == "bid":                       
            p0 = self.p_bid_accept(good, a0)
            p1 = self.p_bid_accept(good, a1)            
        elif action == "ask":
            p0 = self.p_ask_accept(good, a0)
            p1 = self.p_ask_accept(good, a1)
    
        p = np.array([p0, p1, 0, 0])
        
        coef = np.matmul(inv_mat, p)
        
        #Return the polynomial generated by the spline
        return lambda x: coef[0]*x**3 + coef[1]*x**2 + coef[2]*x + coef[3]
        
    
    def estimate_probability(self, good, action, lob):
        
        best_bid = (lob[good]["bid"][0] or 0)
        best_ask = (lob[good]["ask"][0] or 200)
        
        #Extract all the values for which p_ask_accept is defined and interpolate for the others
        his = Trader_eGD.history[good]
        
        
        # --------- BID VECTOR -------------
        if action == "bid":
            best_bid = (lob[good]["bid"][0] or 0)

            #Get unique observed prices
            prices_bid = np.unique( [h[0] for h in his if h[3] == "bid"] )
            
            #0 for [0: best_bid] so generate 0's and get rid of prices that are not > best_bid
            yb = np.repeat(0, best_bid + 1)

            prices_bid = prices_bid[prices_bid > best_bid ]
            #Apppend 200 since that is almost always a split
            prices_bid = np.append(prices_bid,200)
            
            #Split the numpy array into parts where numbers are consecutive if not then interpolate between them
            split_bid = np.split(prices_bid, np.where(np.diff(prices_bid) != 1)[0]+1)
            
            
            #Vectorize function so we can pass in arrays
            p_bid = np.vectorize(self.p_bid_accept)
            
            #If there is no best bid then interpolate from 0 till next known bid
            if best_bid == 0:
                spline = self.GD_spline(good, "bid", 0, split_bid[0][0])
                x = np.arange(1, split_bid[0][0])
                yb = np.append(yb , spline(x) )

            
            if len(split_bid) == 1:
                #We have no usable history so we interpolate from best_bid till 200
                spline = self.GD_spline(good, "bid", best_bid, 200)
                x = np.arange(best_bid + 1, 201)
                yb = np.append(yb , spline(x) )

            else:
                #Fill the gap between the best_bid if it exists and the first known bid
                if best_bid != split_bid[0][0] and best_bid != 0 :
                    spline = self.GD_spline(good, "bid", best_bid, split_bid[0][0])
                    x = np.arange(best_bid + 1, split_bid[0][0])
                    yb = np.append(yb , spline(x) )

                #Now calculate the values for the entire vector
                n = len(split_bid)
                for index in range(n):
                    #Add the consecutive values
                    yb = np.append(yb, p_bid(good, split_bid[index]) )

                    #Interpolate for the values in between
                    if index < n-1: #Check if we are not at the final split
                        #Get current value
                        current_val = split_bid[index][-1]
                        #Get the next value to interpolate on 
                        next_val = split_bid[index+1][0]
                        
                        #Get spline and values inbetween and calculate the values in between
                        spline = self.GD_spline(good, "bid", current_val, next_val)
                        x = np.arange(current_val + 1, next_val)
                        
                        yb = np.append(yb , spline(x) )
            return yb
            
        elif action == "ask":
            # --------- ASK VECTOR -------------
            #For asks its definded from [0,best_ask) hence interpolate from 0 to the first value and add the 0's later
            prices_ask = np.unique( [h[0] for h in his if h[3] == "ask"] )    
            
            #get rid of prices that are not < best_ask
            prices_ask = prices_ask[prices_ask < best_ask]
            split_ask = np.split(prices_ask, np.where(np.diff(prices_ask) != 1)[0]+1)
            p_ask = np.vectorize(self.p_ask_accept)
            
            #Interpolate between 0 and the first value
            
            if split_ask[0].size == 0:
                spline = self.GD_spline(good, "ask", 0, best_ask)
                x0 = np.arange(best_ask )
                ya = spline(x0)
            else:
                first_val = split_ask[0][0]
                spline = self.GD_spline(good, "ask", 0, first_val)
                x0 = np.arange(first_val)
                ya = spline(x0)
                #Interpolate over the remaining values
                n = len(split_ask)
                
                
                for index in range(n):
                    #Add the consecutive values
                    ya = np.append(ya, p_ask(good, split_ask[index]) )
                    
                    #Interpolate for the values in between
                    if index < n-1: #Check if we are not at the final split
                        #Get current value
                        current_val = split_ask[index][-1]
                        #Get the next value to interpolate on -1 as its the last known variable
                        next_val = split_ask[index+1][0]
                        
                        #Get spline and values inbetween and calculate the values in between
                        spline = self.GD_spline(good, "ask", current_val, next_val)
                        x = np.arange(current_val + 1, next_val)
                        ya = np.append(ya , spline(x) )
                last_val = prices_ask[-1]
                
                if best_ask != last_val:
                    spline = self.GD_spline(good, "ask", last_val, best_ask)
                    x = np.arange(last_val + 1, best_ask)
                    ya = np.append(ya , spline(x) )
            #Add the remaining zeros zo arrays are of equal length which is the 
            
            ya = np.append(ya , np.repeat(0, 201-best_ask))
            
            return ya
        else:
            raise ValueError(f" value {action} not valid please enter bid or ask ")
    
    def equilibrium_price(self, good, lob, verbose=False):
        """
            Estimating an equilibrium price by calculating where the probability of a bid acceptance is equal to an ask acceptance
            This is done by calculating a vector of bida/ask probilities for different prices and checking where the absolute difference is minimal.
        """
        
        #Extract all the values for which p_ask_accept is defined and interpolate for the others
        his = Trader_eGD.history[good]
        
        
        prices_bid =  [h[0] for h in his if h[3] == "bid"] 
        prices_ask =  [h[0] for h in his if h[3] == "ask"] 
        
        #If there is not enough history then return a random price
        if (len(prices_bid) < 10 or len(prices_bid) < 5):
            if good == "X":
                price = 20 + 60*random.random()
            elif good == "Y":
                price = 10 + 30*random.random()
            return price
        

        ya = self.estimate_probability(good, "ask", lob)
        yb = self.estimate_probability(good, "bid", lob)
        
        #Check where the absolute difference is smallest since there we have that pbid = pask
        absdiff = abs(ya -yb)
        
        
        eq_price = np.argmin(absdiff)
        
        return eq_price


    
    def get_order(self, time, lob, verbose=False):
        
        if self.active is True:
            quantity = 1 
            choices = self.get_feasible_choices(lob, False)
            possible_orders = []
            
            for choice in choices:
                
                action = choice[0]
                good = choice[1]
                #Add some randomness 
                offset = -1 + 2*random.random() 
                price = round(Trader_eGD.e_price[good] + offset)
                
                
                best_bid = (lob[good]["bid"][0] or 0)
                best_ask = (lob[good]["ask"][0] or 200)
                
                if action == "bid":
                    shout_price = round(price*(1-self.markup))
                    
                    #Check if you have enough money
                    if shout_price > self.balance["money"]:
                        shout_price = None
                    else:
                        #If your price is the same as best bid and the spread is very small accept the best ask
                        if shout_price == best_bid and ( best_ask - best_bid <= 1) :
                            shout_price = best_ask
                        elif shout_price < best_bid:
                            shout_price = None
                            
                        
                elif action == "ask":
                    shout_price = round(price*(1+self.markup))
                    if shout_price == best_ask and ( best_ask - best_bid <= 1):
                        shout_price = best_bid 
                    elif shout_price > best_ask:
                        shout_price = None
                    
                        
                if shout_price is not None:
                    order = Order(1, self.tid, action, good, shout_price, quantity, time)            
                    possible_orders.append( (self.utility_gain_order(order) , order ) )
                    
                self.possible_orders = possible_orders
            try:
                best = max(possible_orders,key=itemgetter(0))
            except:
                return None
            
            if best[0] >= 0:
                return best[1]
            elif best[0] < 0:
                #self.active = False
                return None
            
        else:
            return None
        

    
    def respond(self, time, lob, order):
        """
        """
        
        if Trader_eGD.new_turn:
            
            good = order.ptype

            for action in ["bid", "ask"]:                
                floor = lob[good][action]          
                prev =  self.last_lob[good][action]
                
                #Only add change if orderbook has changed
                if floor != prev:
                    #check if there is an order
                    if floor[0] is not None:
         
                        #Check if there was a previous order
                        if prev[0] != None:
                            prev_order =  (prev[0], prev[1], False, action, order.oid) 
                            
                            #Check if the floor was impoved if so the previous one was rejected
                            if action == "bid":
                                if prev[0] < floor[0]:
                                    Trader_eGD.history[good].append(prev_order)
                                    
                            elif action == "ask":
                                if prev[0] > floor[0]:
                                    Trader_eGD.history[good].append(prev_order)
                                    
                    elif floor[0] is None:
                        #Check if there was a previous floor if so then it was accepted                
                        if prev[0] != None:
                            prev_order =  (prev[0], prev[1], True, action, order.oid) 
                            Trader_eGD.history[good].append(prev_order)
                            #Trim the history if needed
                            self.trim_history(good)
            
            #Save new order book as previous
            self.last_lob = deepcopy(lob)
            Trader_eGD.new_turn = False
            
            
            try:
                #Save new equilibrium price
                Trader_eGD.e_price[good]  = self.equilibrium_price(good, lob)
            except:
                #Keep the old one
                pass
            
        else:
            pass
        


class Trader_GDZ(Trader_eGD):
    
    def __init__(self, tid, ttype, talgo):
        super().__init__(tid, ttype, talgo)
        self.next_order = None
        self.arbitrage_trades = []
        self.rejected_trades = []
        #Saves the order where you lost on so we can 
        self.arbitrage_order = None
        self.wait_time = None
    
    def reset_allocation(self):
        #Give starting balance given the trading type for the STABLE scarf economy
        if self.ttype == 1:
            balance = {"money":0,"X":10,"Y":0}
        elif self.ttype == 2:
            balance =  {"money":0,"X":0,"Y":20}
        elif self.ttype == 3:
            balance =  {"money":400,"X":0,"Y":0}
        else:
            raise ValueError(f"Trader type {self.ttype} is invalid, please choose 1,2 or 3.")
        self.balance = balance
        self.active = True
        self.utility = 0 
        
        #Check if we have outstanding arbitrage orders if so they are rejected
        for order in self.pending_orders:
            if order.strategic == True:
                try:
                    self.rejected_trades.append((order, self.arbitrage_order.price))
                except:
                    pass
        
        self.arbitrage_order = None
        self.wait_time = None
        
        
    def check_pending_orders(self, lob, trade):
        """Checks if orders are still pending in orderbook"""
        
        if len(self.pending_orders) > 0:
            still_pending_orders = []
            for order in self.pending_orders:
                if lob[order.ptype][order.otype] == (order.price, order.quantity):
                    still_pending_orders.append(order)
                else:
                    if order.strategic is True and trade is None:
                        try:
                            self.rejected_trades.append((order, self.arbitrage_order.price))
                        except:
                            pass
            
            self.pending_orders = still_pending_orders    
    
    
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
        self.utility = self.calc_utility(self.balance)
        
        if trade["arbitrage"] is True and self.tid == trade["taker"]:
            #Arbitrage trade has been successfull 
            t = deepcopy(trade)
            t["original_price"] = self.arbitrage_order.price
            
            #Add profit
            if self.arbitrage_order.otype == "ask":
                t["profit"] = t["original_price"] - t["price"] 
            elif self.arbitrage_order.otype == "bid":
                t["profit"] = t["price"] - t["original_price"] 
            
            
            #Waiting time 
            t["wait_time"] = self.wait_time
            
            #Append arbitrage trade and reset variables
            self.arbitrage_order = None
            self.wait_time = None
            
            self.arbitrage_trades.append(t)
            

        #Return new balance and utility level after transaction
        return [self.balance , self.utility]    
        
    def get_order(self, time, lob, verbose=False):
        
        #If we have an arbitrage order post that one else give regular one
        if self.next_order:
            order = deepcopy(self.next_order)
            self.next_order = None
            return order
        elif self.arbitrage_order is not None:
            #If we have an active arbitrage order then we wait 
            pass
        else:    
            quantity = 1 
            choices = self.get_feasible_choices(lob, False)
            possible_orders = []
            
            for choice in choices:
                
                action = choice[0]
                good = choice[1]
                #Add some randomness 
                offset = -1 + 2*random.random() 
                price = round(Trader_eGD.e_price[good] + offset)
                
                
                best_bid = (lob[good]["bid"][0] or 0)
                best_ask = (lob[good]["ask"][0] or 200)
                
                if action == "bid":
                    shout_price = round(price*(1-self.markup))
                    
                    #Check if you have enough money
                    if shout_price > self.balance["money"]:
                        shout_price = None
                    else:
                        #If your price is the same as best bid and the spread is very small accept the best ask
                        if shout_price == best_bid and ( best_ask - best_bid <= 1) :
                            shout_price = best_ask
                        elif shout_price < best_bid:
                            shout_price = None
                            
                        
                elif action == "ask":
                    shout_price = round(price*(1+self.markup))
                    if shout_price == best_ask and ( best_ask - best_bid <= 1):
                        shout_price = best_bid 
                    elif shout_price > best_ask:
                        shout_price = None
                    
                        
                if shout_price is not None:
                    order = Order(1, self.tid, action, good, shout_price, quantity, time)            
                    possible_orders.append( (self.utility_gain_order(order) , order ) )
                    
                self.possible_orders = possible_orders
    
            try:
                best = max(possible_orders,key=itemgetter(0))
            except:
                return None
            
            if best[0] >= 0:
                return best[1]
            elif best[0] < 0 and self.utility >= 0.1:
                
                try:
                    order = self.arbitrage_opportunity(time, lob)
                    return order
                except:
                    return None
            
        
    def arbitrage_opportunity(self, time, lob, verbose=False):
        
        options = []
        #Check in the lob if we can find a possible arbitrage trade
        
        for pair in [("X","bid"),("X","ask"),("Y","bid"),("Y","ask")]:
            mlob = deepcopy(lob)
            actions = ["ask", "bid"]
            good = pair[0]
            action = pair[1]
            price = lob[good][action][0]
            
            #remove the action and take the remaining one to get the opposite
            actions.remove(action)
            opposite_action = actions[0]
            
            
            
            if price is not None:
                
                #Calculate the utility of taking the outstanding floorprice
                order = Order(1, self.tid, opposite_action, good, price, 1, time) 
                util = self.utility_gain_order(order)
                
                if util < 0:
                    #We need to estimate the probability AFTER we take the trade
                    mlob[good][action] = [None, None]
                    
                    #Estimate the probability of buying/selling it back later for a higher price 
                    prob_accept = self.estimate_probability(good, action, mlob)
                    prob_reject = 1 -self.estimate_probability(good, opposite_action, mlob)
                    
                    x = np.arange(201)
                    #Create a vector of profit if sold at price x
                    if action == "ask":
                        denom = prob_accept+prob_reject
                        prob = np.divide(prob_accept, denom, out=np.zeros_like(prob_accept), where=denom!=0)
                        profits = x - np.repeat(price, 201)
                    elif action == "bid":
                        denom = prob_accept+prob_reject
                        prob = np.divide(prob_accept, denom, out=np.zeros_like(prob_accept), where=denom!=0)
                        profits = np.repeat(price, 201) -  x
                    #Set negative profits to 0
                    profits *= (profits > 0)
                    
                    #Calculate the expected profits and choose the best arbitrage trade
                    expected_profits = profits*prob
                    optimal_price = np.argmax(expected_profits)
                    expected_profit = expected_profits[optimal_price]
                    
                    #If optimal is positive then queue the arbitrage trade and buy/sell the good in the next order
                    if optimal_price > 0:
                        order = Order(1, self.tid, opposite_action, good, price, 1, time) 
                        next_order = Order(1, self.tid, action, good, optimal_price, 1, time)                        
                        next_order.strategic = True
                        
                        options.append( (expected_profit, order, next_order) )
                        
        if len(options) > 0:
            #Choose the best option
            best = max(options,key=itemgetter(0))
            
            if best[0] > 0:
                #Return the immediate buy/sell order and save the arbitrage offer for the next period
                self.next_order = best[2]
                self.arbitrage_order = best[1]
                return best[1]
            else:
                return None
                    
                    
#-------------------------- Other functions --------------------------------
def create_csv(file_name, dictionaries):
    """Creates csv file from a list of dictionaries"""
    #Get the keys of the dictionary as column names
    keys = dictionaries[0].keys()
    
    #Get date and time to save results
    now = datetime.now()
    dt_string = now.strftime(" %d-%m-%Y %H-%M-%S")
    
    #Get directory of file
    script_dir = os.path.dirname(os.path.realpath('__file__'))
    rel_path = "results"
    abs_file_path = os.path.join(script_dir, rel_path)
    
    #Check if results folder exists else make it
    if not os.path.exists(abs_file_path):
        os.makedirs(abs_file_path)
        
    file_path = os.path.join(abs_file_path, file_name+dt_string+".csv")
    
    #Create csv file with write access 
    file = open(file_path, "w", newline='')
    
    dict_writer = csv.DictWriter(file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(dictionaries)
    
    #Close the file
    file.close()

def trader_type(tid, ttype, talgo):
        """Function returns the correct trader object given the talgo value and trader type"""
                
        #Select the correct trader algorithm
        if talgo == 'ZI':
            return Trader_ZI(tid, ttype, talgo)
        elif talgo == 'ZIP':
            return Trader_ZIP(tid, ttype, talgo)
        elif talgo == 'eGD':
            return Trader_eGD(tid, ttype, talgo)
        elif talgo == 'GDZ':
            return Trader_GDZ(tid, ttype, talgo)
        else:
            raise ValueError(f"Trader of type {talgo} does not exist")

def generate_traders(spec):
    """Gives traders based on a list of tuples containing tradertype and how many multiples of 3 traders per type """
    
    traders = {}
    trader_pairs = []
    trader_id = 1 
    
    for s in spec:
        for i in range(s[1]):
            for j in [1,2,3]:
                # Add (traderid, tradertype, traderalgo) to traderpairs
                pair = (trader_id, j, s[0] )
                trader_pairs.append( pair )
                traders[trader_id] = trader_type( *pair )
                trader_id += 1
    return trader_pairs, traders

def online_average(old_avg, new_observation, n):
    """Calculates the new average when a new observation is added"""
    return old_avg*((n-1)/n) + new_observation/n
        
#-------------------------- END Other functions -----------------------------



endtime = 300
periods = 5
runs = 10


utility_levels_prev = []

excess_goods = []
trade_history = []
trades_arbitrage = []
rejected_arbitrage = []

for run in tqdm(range(1, runs+1) , desc="Run"):
    #---- Market Session ----
    #History of all succesfull trades
    orders = []
    lobs = []
    
    order_id = 1

    spec = [("eGD", 3)]
    trader_pairs, traders = generate_traders(spec)        
    exchange = Exchange(traders)
    
    utility_levels = []

        
  
    for period in tqdm(range(1, periods+1), desc="Periods" , leave=False, disable=False):
        
        #Reset allocation for all traders
        for i in range(1, len(traders)+1):
            traders[i].reset_allocation()
    
        
        for time in tqdm(range(1, endtime+1), desc="Timesteps", mininterval=1, leave=False, disable=True):
            
            #Calculate the average utility per Tradertype and Algorithm pair per timestep
            for s in spec:
                algo = s[0]
                for j in [1,2,3]:
                    util = [traders[pair[0]].utility for pair in trader_pairs if (pair[1] == j and pair[2] == algo) ]
                    avg = sum(util)/len(util)
                    utility_levels.append( {"avg_util": avg,
                                           "talgo": algo,
                                           "ttype": j,
                                           "time": time,
                                           "period": period} )
                
                
            
            lob = exchange.publish_alob()
            
            for i in range(1, len(traders)+1):
                try:
                    traders[i].choose_action(lob)
                except:
                    pass
            
            #To add the factor of speed we can alter this bucket to have a trader in there more than once
            #Depending on what speed score it has gotten
            
            #List of all trader ID's for selecting which one can act
            trader_list = [i for i in range(1, len(traders)+1)]
            
            #Pick without replacement from trader list each timestep
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
                    orders.append(order)
                    #Give order unique id and increment
                    order.oid = order_id
                    order_id += 1
                    

                    #Process the order
                    successful_order, trade = exchange.process_order(time, order)
                    
                    order.accepted = successful_order
                    #Check if the order improved/updated the lob and if so call respond function of all traders
                    if successful_order:
                        Trader_eGD.new_turn = True
                        Trader_GDZ.new_turn = True
                        alob = exchange.publish_alob()
                        #Add order to the list 
                        lobs.append(deepcopy(alob))
                        for i in range(1, len(traders)+1):
                            traders[i].respond(time, alob, order)
                            traders[i].check_pending_orders(alob, trade)
        
                        #Check if trade has occurred
                        if trade is not None:
                            #Update the balance and utility of the parties involved after the trade 
                            #and save the current values of their balance and utility level after the trade
                            seller_balance, seller_util = traders[ trade["seller_id"] ].bookkeep(trade)
                            buyer_balance, buyer_util = traders[ trade["buyer_id"] ].bookkeep(trade)    
                            
                            trade["period"] = period
                            trade["run"] = run
                            buyer_id = trade["buyer_id"]
                            seller_id = trade["seller_id"]
                        
                            #Add updated information to the trade
                            trade["buyer_algo"] = traders[buyer_id].talgo
                            trade["buyer_util"] = buyer_util
                            trade["buyer_balance"] = buyer_balance
                            trade["seller_algo"] = traders[seller_id].talgo
                            trade["seller_util"] = seller_util
                            trade["seller_balance"] = seller_balance
                            
                            # if trade['price'] > 150:
                            #     raise ValueError("What is going on here")
                
                            #Append it to the history using deepcopy 
                            trade_history.append(deepcopy(trade))   
                            if (seller_balance["money"] < 0 or buyer_balance["money"] < 0):
                                raise ValueError("money negative")
                                
                        elif trade is None:
                            #Add the order to the pending orders
                            trader.add_pending_order(order)
                else:
                    pass
                
        #Calculate the excess goods for each trader at the end of the period 
        for i in range(1, len(traders)+1):
            e = traders[i].excess()
            e["tid"] = traders[i].tid
            e['talgo'] = traders[i].talgo
            e['ttype'] = traders[i].ttype
            e['period'] = period
            excess_goods.append(e)

            
    if utility_levels_prev:
        for old, new in zip(utility_levels_prev, utility_levels):
            new["avg_util"] = online_average(old["avg_util"], new["avg_util"], run )
    
    for i in range(1, len(traders)+1):
        if traders[i].talgo == "GDZ":
            trades_arbitrage.extend(traders[i].arbitrage_trades)
            rejected_arbitrage.extend(traders[i].rejected_trades)
        
    utility_levels_prev = deepcopy(utility_levels)


#Create all the csv files for plotting
for pair in [("util", utility_levels_prev),("trade", trade_history),("excess", excess_goods),("arbitrage", trades_arbitrage)]:
    try:
        create_csv(*pair)
    except:
        pass

