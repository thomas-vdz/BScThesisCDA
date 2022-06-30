
import csv
import random
from tqdm import tqdm, trange
from copy import deepcopy
import os
from datetime import datetime
from operator import itemgetter
import numpy as np



class Order:
    """Object containing all information that an order requires."""
    
    def __init__(self, oid, tid, otype, ptype, price, quantity, time):
        """Intitializes the Order object.

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
            Number indicating in which time-step the order was posted.
        accepted : bool, optional
            Indicates if the order was accepted by the exchange
        strategic : bool, optional
            Indicates if the order was a strategic order.
        arbitrage : bool, optional
            Indicates if the order was an arbitrage order.
        target_price : int, optional
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
        self.arbitrage = False
        self.target_price = None


    def __str__(self):
        return f"Order{self.oid}: trader{self.tid} posted a {self.otype} {self.price} per unit for {self.quantity} of good {self.ptype} at t={self.time}, {self.accepted}"


class Orderbook:
    """Class defining the orderbook of the exchange where current open orders are saved.
    
    The orderbook has a depth of one meaning if a better order is posted the old one is deleted.
    
    """
    def __init__(self):
        """Intitializes the Orderbook object.

        Parameters
        ----------
        lob : dict
            Contains the order objects for goods X and Y.
        alob : dict
            An anonimized version of the orderbook to publish to traders.
        """
        self.lob = {
            "X":{},
            "Y":{},
            }
        self.alob = {
            "X":{"bid":{},"ask":{}},
            "Y":{"bid":{},"ask":{}},
            }

    def anon_lob(self):
        """Converts the orderbook to the anonymized version."""
        #Test if there is a best-ask/bid present and report it in the anon_lob else return a empty list
        for pair in [("X","bid"),("X","ask"),("Y","bid"),("Y","ask")]:

            #Check for each pair if there is an order in the orderbook and anonymize it
            if self.lob[pair[0]].get(pair[1]) is not None:
                order = self.lob[pair[0]].get(pair[1])
                self.alob[pair[0]][pair[1]] = (order.price, order.quantity)
            else:
                #return empty order
                self.alob[pair[0]][pair[1]] = (None , None)

    def add_order_lob(self, order):
        """Adds the order to the orderbook or rejects it if it does not meet the requirements.
        
        Function adds an order to the orderbook only if it improves the best bid/ask of the given good.
        It improves an ask if its lower than the current ask.
        It improves a bid if its higher than the current bid. 
        
        Parameters
        ----------
        order, Order object
            Specifies the order object to be processed.
            
        Returns
        -------
        bool
            If the order was added to the orderbook return True.
            If the order was rejected return False.
        """
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
                    #Order is rejected
                    return False
            elif order.otype == "ask":
                #If the ordertype is ask replace the current bid if the price of the offer is lower
                if order.price < self.lob[order.ptype]["ask"].price:
                    self.lob[order.ptype][order.otype] = order
                    return True
                else:
                    #Order is rejected
                    return False

    def del_order_lob(self, ptype, otype):
        """Deletes order from the orderbook and updates the anonymous orderbook.
        
                
        Parameters
        ----------
        ptype : str {"X", "Y"}
            Product type of the order.
        otype : str {"ask", "bid"}
            Order type indicating if its a bid or an ask.  
            
        """
        del self.lob[ptype][otype]
        #Update the anonymous lob
        self.anon_lob()


class Exchange():
    """Class responsible for processing orders by traders.

    """

    def __init__(self, traders, minprice=1, maxprice=201):
        """Intitializes the Exchange object.

        Parameters
        ----------
        minprice : int, default = 1
            Minimum price allowed in the exchange.
        maxprice : int, default = 201
            Maximum price allowed in the exchange.
        traders: list
            List of trader objects containing all traders of the session.
        ob : Orderbook, default Orderbook
            Orderbook object to save the orders that pass through the exchange.
        """
        self.minprice = minprice  
        self.maxprice = maxprice  
        self.traders = traders
        self.ob = Orderbook() 

    def process_order(self, time, period, run, order):
        """Processes an order given by a trader.
        
        Possible outcomes:
            - Order results in a trade.
            - Order gets accepted and added to the orderbook.
            - Order gets rejected.
            
        ...
        Parameters
        ----------
        time : int
            Time-step in which the order was processed.
        period : int
            Period in which the order was processed.
        run : int
            Run in which the order was processed.
        order: Order
            The order to be processed by the exchange.
            
        Returns
        -------
        trade : dict
            If order is accepted return trade information.
        successful_order: bool
            Indicates if the order was accepted or not .
        """
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

                        if self.ob.lob[order.ptype]["bid"].arbitrage is True:
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

                        #Create trade for book keeping
                        trade = {"time" : time,
                                 "period":period,
                                 "run":run,
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
                successful_order = False

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

                        if self.ob.lob[order.ptype]["ask"].arbitrage is True:
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

                        #Create trade for book keeping
                        trade = {"time" : time,
                                 "period":period,
                                 "run":run,
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
                successful_order = False

        else:
            raise ValueError("Offer was neither a bid nor an ask")

        return successful_order, trade


    def reset_allocations(self):
        """Resets the allocation of all traders and clears the orderbook"""
        #Resets allocation for all traders
        for i in range(1, len(traders)+1):
            traders[i].reset_allocation()
            
        #Clears orderbook
        self.ob = Orderbook()

    def publish_alob(self):
        """Updates anonymous orderbook.
        
        ...
        Returns
        -------
        dict
            The new anoymized orderbook.
        """
        self.ob.anon_lob()
        return self.ob.alob



#--------------------------- Traders -------------------------------------------------

#Main trader class
class Trader:
    """Trader object can interact with the exchange to trade goods using orders."""

    def __init__(self, tid, ttype, talgo):
        """Intitializes the Trader object.

        Parameters
        ----------
        minprice : int, default = 0
            Minimum price allowed in the exchange.
        maxprice : int, default = 200
            Maximum price allowed in the exchange.
        tid: int
            Unique identifier for each instance of traders.
        ttype: int {1,2,3}
            Number indicating which type the trader is.
        talgo: str
            Name of the algorithm the trader uses.
        balance: dict
            Contains the balance for each good: Money,X and Y.
        blotter: list
            All executed trades.
        pending_orders: list
            All orders that are currently pending in the exchange.
        utility: float, default = 0 
            The utility level of the trader.
        active: bool
            Indicates if the trader is willing to trade.
            
            
        """
        self.minprice = 0  
        self.maxprice = 200  
        self.tid = tid 
        self.ttype = ttype 
        self.talgo = talgo 
        self.balance = {}  
        self.blotter = [] 
        self.pending_orders = []
        self.utility = 0 
        self.active = False
        #Reset the allocation so traders start with the correct balance
        self.reset_allocation()

    def __str__(self):
        return f"Trader{self.tid}: Money:{self.balance['money']}, X:{self.balance['X']}, Y, {self.balance['Y']}"

    def reset_allocation(self):
        """Resets the allocation and utility of a trader depending on the trader's type."""
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
           
        ...
        Parameters
        ----------
        balance: dict
            Balance of each good.
            
        Returns
        -------
        utility : float
            Utility level given trader type.
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
        """Returns the excess allocation of the given the balance.
        
        The excess allocation is defined as all the goods it could "give away" without losing utility.
        
        ...     
        Returns
        -------
        excess: dict
            Excess for each good.
        """
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

    def get_feasible_choices(self, orderbook, do_nothing=True, arbitrage=False):
        """Returns a list of all feasible options a trader has given the restiction that it should always improve the orderbook.
           
        If the argument arbitrage is True it looks for possible strategic orders given the tradertype.
        
        ...
        Parameters
        ----------
        orderbook : dict
            Current anonymous orderbook.
        do_nothing : bool, default = True
            Indicates if do nothing should be included in feasible choices.
        arbitrage : bool, default = False
            Indicates if we should look for possible strategic orders.
            
        Returns
        -------
        choices : list
            List of tuples of the form (action,good) for each feasible choice.
        """
        if arbitrage is True:
            choices = []

            #For each trader type give the offer pair so that we can do the action with probability 1
            if self.ttype == 1:
                #Check if we can sell y
                if orderbook["Y"]["bid"][0] is not None and self.balance["Y"] > 0:
                    choices.append(("ask", "Y"))
                #Check if we can buy x immediatly and have enough money
                elif orderbook["X"]["ask"][0] is not None and self.balance["money"] >= (orderbook["X"]["ask"][0] or 2000):
                    choices.append(("bid", "X") )

            elif self.ttype == 2:
                #Check if we can buy y immediatly and have enough money
                if orderbook["Y"]["ask"][0] is not None and self.balance["money"] >= (orderbook["Y"]["ask"][0] or 2000):
                    choices.append(("bid", "Y"))
                #Check if we can sell x
                elif orderbook["X"]["bid"][0] is not None and self.balance["X"] > 0:
                    choices.append(("ask", "X") )

            elif self.ttype == 3:
                #Check if we can sell y
                if orderbook["Y"]["bid"][0] is not None and self.balance["Y"] > 0:
                    choices.append(("ask", "Y"))
                #Check if we can sell x
                elif orderbook["X"]["bid"][0] is not None and self.balance["X"] > 0:
                    choices.append(("ask", "X") )

            return choices

        else:
            if do_nothing:
                choices = [("do nothing"," ")]
            else:
                choices = []
            
            #If we have the good we can sell it.
            if self.balance["X"] > 0:
                choices.append( ("ask", "X") )
            if self.balance["Y"] > 0:
                choices.append( ("ask", "Y") )

            #Check if we can improve best bid so we can buy it.
            if self.balance["money"] > (orderbook["X"]["bid"][0] or 0):
                choices.append( ("bid", "X") )

            if self.balance["money"] >  (orderbook["Y"]["bid"][0] or 0):
                choices.append( ("bid", "Y") )
                
            return choices

    def add_pending_order(self, order):
        """Adds pending order to the list"""
        self.pending_orders.append(order)

    def check_pending_orders(self, lob, trade):
        """Checks if orders are still pending in orderbook if not deletes them."""

        if len(self.pending_orders) > 0:
            still_pending_orders = []
            for order in self.pending_orders:
                if lob[order.ptype][order.otype] == (order.price, order.quantity):
                    still_pending_orders.append(order)

            self.pending_orders = still_pending_orders



    def utility_gain_order(self, order):
        """Function takes in an order and calculates the utility difference before and after assuming the order would result in an transaction.
                 
        ...
        Parameters
        ----------
        order: Order
            Potential order to be posted.
            
        Returns
        -------
        float
            Difference between current utility and utility if order resulted in an transaction.
        """
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
        """Updates the balance of the trader and adds the trade to the blotter.
                 
        ...
        Parameters
        ----------
        trade: dict
            Contains trade information.
            
        """
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
        pass

    #This method will be overwritten by the different traders
    def respond(self, time, lob, order):
        pass


class Trader_ZI(Trader):
    """Trader with no intelligence restricted to posting offers it can complete"""
    
    def get_order(self, time, lob):
        """Gets the order the trader wants to submit to the exchange.
        
        The ZI trader calculates possible orders and chooses one randomly.
                 
        ...
        Parameters
        ----------
        time: time
            Current time-step
        lob: dict
            Current anonymized orderbook
            
        Returns
        -------
        Order
            The order the the trader wants to submit to the exchange.
        """
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
        """Intitializes the Trader_ZIP object.

        Parameters
        ----------
        last_price_bid: dict
            Saves the last bid price for each good.
        last_price_ask: dict
            Saves the last ask price for each good.
        gamma: float
            Parameter used in formula default = Uniform[0.2,0.8].
        cgamma_old: dict
            Saves old gamma for each good.
        kappa: float
            Parameter used in formula default = Uniform[0.1,0.5].
        gamma: float
            Parameter used in formula default = Uniform[0.2,0.8].
        shout_price : dict
           Saves shoutprice price default: X  = Uniform[20,80], Y = Uniform[10,40].   
        choice : tuple
            Choice (action, good) for order this time-step.
        buyer : bool
            Indicates if buyer or seller.
        """
        Trader.__init__(self, tid, ttype, talgo)
        self.last_price_bid = {"X":None, "Y": None}
        self.last_price_ask = {"X":None, "Y": None}
        self.gamma = 0.2 + 0.6 * random.random()
        self.cgamma_old = {"X":0, "Y": 0}
        self.kappa = 0.1 + 0.4 * random.random()
        self.shout_price = {"X": 20 + 60*random.random(), "Y": 10 + 30*random.random()}
        self.choice = None
        self.buyer = True

    def get_order(self, time, lob):
        """Gets the order the trader wants to submit to the exchange
        
        The ZIP trader gets a list of feasible choices and chooses one randomly.
        Then it returns the order given its internal shoutprice.
                 
        ...
        Parameters
        ----------
        time: time
            Current time-step.
        lob: dict
            Current anonymized orderbook.
            
        Returns
        -------
        Order
            The order the the trader wants to submit to the exchange.
        """
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
        """Chooses a random action at the beginning of the timestep to determine if it is a buyer or seller"""
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
        """Updates internal parameters.
        
        The ZIP trader updates an internal shoutprice. 
                 
        ...
        Parameters
        ----------
        time: time
            Current time-step.
        lob: dict
            Current anonymized orderbook.
        order: Order
            Current order.
            
        """

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
    """Class responsible for processing orders by traders
    
    ...

    Attributes
    ----------
    history : dict
        Saves the history of observed orders 
    last_lob : dict
        The previous orderbook
    new_turn : bool, default = False
        Keeps track if there is a new turn
    e_price : dict
       Saves estimated equilibrium price, default: X  = Uniform[20,80], Y = Uniform[10,40].

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
        """Intitializes the Trader_eGD object.

        Parameters
        ----------
        markup: float, default = 0
            Markup to apply to the order .
        memory: int, default = 30
            All orders are saved inbetween the last n=memory orders.
        
        """
        Trader.__init__(self, tid, ttype, talgo)
        self.markup = 0 #0.01 + 0.01 * random.random()
        self.memory = 30


    def trim_history(self, good):
        """Trims the history to the correct length given by amount of memory.
                 
        ...
        Parameters
        ----------
        good: str {"X","Y"}
            The type of good.
            
        """
        n_trades = len([t for t in Trader_eGD.history[good] if t[2]==True])

        if n_trades > self.memory:
            #Get the index of the first trade
            index = [t[2] for t in Trader_eGD.history[good]].index(True)
            #Forget the history that happend before and including the last trade
            Trader_eGD.history[good] = Trader_eGD.history[good][index+1:]


    def p_bid_accept(self, good, price):
        """ Estimates the probability a bid will be accepted given previous observations.
                 
        ...
        Parameters
        ----------
        good: str {"X","Y"}
            The type of good.
        price: int
            Price to caculate the probability for.
            
        Returns
        -------
        float
            probability the bid will be accepted.
        """
        #Assume 0 prob for minprice and 1 prob for maxprice
        if price == self.minprice:
            return 0
        elif price == self.maxprice:
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
        """ Estimates the probability a ask will be accepted given previous observations.
                 
        ...
        Parameters
        ----------
        good: str {"X","Y"}
            The type of good.
        price: int
            Price to caculate the probability for.
            
        Returns
        -------
        float
            probability the ask will be accepted.
        """
        #Assume 1 prob for minprice and 0 prob for maxprice
        if price == self.minprice:
            return 1
        elif price == self.maxprice:
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
        """ Creates a cubic polynomial between two prices
        
        This spline has the following properties:
            - f(a0) = a0
            - f(a1) = a1
            - f'(a0) = 0
            - f'(a1) = 0
        We assume that a0 < a1.
        
        ...
        Parameters
        ----------
        good: str {"X","Y"}
            The type of good.
        price: int
            Price to caculate the probability for.
        a0: int
            Lower price.
        a1: int
            Larger price.
        
            
        Returns
        -------
        function
            returns the cubic polynomial which can be used to calculate the values in between.
        """
        if a0 > a1:
            raise ValueError("We need that a0 > a1")

        mat = np.array([ [a0**3, a0**2, a0, 1],
                         [a1**3, a1**2, a1, 1],
                         [3*a0**2, 2*a0, 1, 0],
                         [3*a1**2, 2*a1, 1, 0] ])

        inv_mat = np.linalg.inv(mat)

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
        """ Creates a probability vector from minprice to maxprice
        
        This function uses the p_bid and p_ask functions to calculate the probability 
        for all observed values of a bid or ask and interpolates for the missing
        values in between.
        
        ...
        Parameters
        ----------
        good: str {"X","Y"}
            The type of good.
        action: str {"bid", "ask"}
            Bid or Ask
        
        Returns
        -------
        array
            probabilites the ask/bid will be accepted for each price from 0 to the maxprice.
        """
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

    def equilibrium_price(self, good, lob):
        """Estimating an equilibrium price by calculating where the probability of a bid acceptance is equal to an ask acceptance
        
        This is done by calculating a vector of bida/ask probilities for different prices and checking where the absolute difference is minimal.
       
        ...
        Parameters
        ----------
        good: str {"X","Y"}
            The type of good.
        lob: dict
            Current orderbook.
        
        Returns
        -------
        int
            Estimated equilibrium price
        """
        #Extract all the values for which p_ask_accept is defined and interpolate for the others
        his = Trader_eGD.history[good]
        
        prices_bid =  [h[0] for h in his if h[3] == "bid"]
        prices_ask =  [h[0] for h in his if h[3] == "ask"]

        #If there is not enough history then return a random price
        if (len(prices_bid) < 10 or len(prices_ask) < 5):
            if good == "X":
                price = 20 + 60*random.random()
            elif good == "Y":
                price = 10 + 30*random.random()
            return price
        

        ya = self.estimate_probability(good, "ask", lob)
        yb = self.estimate_probability(good, "bid", lob)

        #Check for what price the absolute difference is smallest since there we have that pbid = pask
        absdiff = abs(ya -yb)

        eq_price = np.argmin(absdiff)

        return eq_price



    def get_order(self, time, lob):
        """Gets the order the trader wants to submit to the exchange
        
        The eGD trader gets a list of feasible choices and chooses one randomly.
        Pricing is based on an expectaion price which is calculated using the GD belief functions.
                 
        ...
        Parameters
        ----------
        time: time
            Current time-step
        lob: dict
            Current anonymized orderbook
            
        Returns
        -------
        Order
            The order the the trader wants to submit to the exchange
        """
        if self.active is True:
            quantity = 1
            choices = self.get_feasible_choices(lob, False)
            possible_orders = []

            #Might set traders to inactive if they reached optimal utility ie excess is minimal.

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
        """Updates internal parameters
        
        The eGD trader calculates new expected equilibrium price.
        Different instances of eGD share the same equilibrium price.
                 
        ...
        Parameters
        ----------
        time: time
            Current time-step
        lob: dict
            Current anonymized orderbook
        order: Order
            
            
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
    """
    Class responsible for processing orders by traders
    
    ...

    Attributes
    ----------
    lob : dict
        Contains the order objects for goods X and Y.
    alob : dict
        An anonimized version of the orderbook to publish to traders
    """
    def __init__(self, tid, ttype, talgo): 
        """Intitializes the Trader_eGD object.

        Parameters
        ----------
        arbitrage_trades: list
            Saves all completed arbitrage trades in the run.
        rejected_trades: list
            Saves all rejected arbitrage trades in the run.
        strategic_order: Order, default = None
            Saves the current strategic order
        arbitrage_order: Order, default = None
            Saves the current arbitrage order
        min_probability: float, default = 0.5
            Parameter that controls risk aversion
        
        """
        self.arbitrage_trades = []
        self.rejected_trades = []
        #Saves the order where you lost on so we can
        self.strategic_order = None
        self.arbitrage_order = None
        self.min_probability = 0.5
        super().__init__(tid, ttype, talgo)

    def reset_allocation(self):
        """Resets the allocation and utility and arbitrage/strategic trades"""
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

        #Check if we have outstanding arbitrage orders if so they failed
        if self.strategic_order is not None:
            self.rejected_trades.append(self.strategic_order)

        self.strategic_order = None
        self.arbitrage_order = None



    def bookkeep(self, trade):
        """Modified from Trader class: 
        Updates balances and resets arbitrage order if it was successful.
        It also saves the completed arbitrage trade to arbitrage_orders.
                 
        ...
        Parameters
        ----------
        trade: dict
            Contains trade information.
            
        """
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

            t["original_price"] = self.strategic_order.price


            #Add profit
            if self.strategic_order.otype == "ask":
                t["profit"] = t["original_price"] - t["price"]
            elif self.strategic_order.otype == "bid":
                t["profit"] = t["price"] - t["original_price"]

            
            #Waiting time
            t["wait_time"] = t["time"] - self.strategic_order.time
            t["target_price"] = self.strategic_order.target_price
            #Append arbitrage trade and reset variables
            self.strategic_order = None
            self.arbitrage_trade = None

            self.arbitrage_trades.append(t)


        #Return new balance and utility level after transaction
        return [self.balance , self.utility]

    def get_order(self, time, lob, second_order=False):
        """Gets the order the trader wants to submit to the exchange
        
        The GDZ trader behaves as eGD trader 80% of the time 
        but has an 20% probability to look at an arbitrage opportunity.
                 
        ...
        Parameters
        ----------
        time: time
            Current time-step
        lob: dict
            Current anonymized orderbook
        second_order: bool, default = False
            Tells the trader if it has an order which it must immediatly post. 
            
            
        Returns
        -------
        Order
            The order the the trader wants to submit to the exchange
        """
        order = None
        
        #If we have an arbitrage order post that one else give regular one
        if second_order is True:
            order = self.arbitrage_order
            return order
        
        elif self.strategic_order is not None:
            target_price = self.arbitrage_order.price
            good = self.strategic_order.ptype
            action = self.strategic_order.otype
           
            actions = ["ask", "bid"]
            actions.remove(action)
            arbitrage_action = actions[0]
            
            price_orderbook = lob[good][arbitrage_action][0]
            if price_orderbook is None:
                #This means our arbitrage offer got rejected but by the time we could respond it was gone by someone else
                
                old_price = self.arbitrage_order.price
                #We can two things if the price is higher/lower we just accept the bid since we made a profit with certainty or post the previous offer again
                new_arbitrage_order = Order(1, self.tid, arbitrage_action, good, old_price, 1, time)
                new_arbitrage_order.arbitrage = True
                self.arbitrage_order = new_arbitrage_order
                return new_arbitrage_order
            

            #Check if arbitrage order is still in the orderbook/ still in the orderbook if price is the same
            elif price_orderbook == target_price:
                return None    
            
            #Check if someone improved our offer if so  MAYBE ADD A WAITING TIME HERE SO THIS IS NOT ALWAYS DONE
            elif price_orderbook != target_price:
                #Undercut or overbid 
                if arbitrage_action == "bid":
                    new_price = price_orderbook + 1 
                elif arbitrage_action == "ask":
                    new_price = price_orderbook - 1
                
                new_arbitrage_order = Order(1, self.tid, arbitrage_action, good, new_price, 1, time)
                new_arbitrage_order.arbitrage = True
                
                #Save arbitrage order and post the new one
                self.arbitrage_order = new_arbitrage_order
                return new_arbitrage_order    
                
            
            pass
        elif random.random() < 0.2 and time>10:
            #20% chance of looking at arbitrage
            try:
                order = self.arbitrage_opportunity(time, lob)
            except:
                #singular matrix error 
                order = None
            #If we do not spot an arbitrage opportunity we get regular order
            if order is None:
                order = self.regular_order(time, lob)

        else:
            #80% change of doing a regular eGD order
            order = self.regular_order(time, lob)
            
        return order    
            



    def regular_order(self, time, lob):
        """Returns a regular order following the eGD rules
        
        ...
        Parameters
        ----------
        time: time
            Current time-step
        lob: dict
            Current anonymized orderbook
            
        Returns
        -------
        Order
            The order the the trader wants to submit to the exchange
        """
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


        try:
            best = max(possible_orders,key=itemgetter(0))
        except:
            return None

        if best[0] >= 0:
            return best[1]
        else:
            return None
        
    def arbitrage_opportunity(self, time, lob):
        """Calculates a feasible arbitrage move.
        It returns the corresponding strategic and saves the arbitrage trade.
        
        ...
        Parameters
        ----------
        time: time
            Current time-step
        lob: dict
            Current anonymized orderbook
            
        Returns
        -------
        Order
            The strategic order to post
        """
        choices = self.get_feasible_choices(lob, do_nothing=False, arbitrage=True)
        #Check in the lob if we can find a possible arbitrage trade
        options = []
        for choice in choices:
            mlob = deepcopy(lob)
            #remove the action and take the remaininng one to get the opposite
            
            actions = ["ask", "bid"]
            action = choice[0]
            actions.remove(action)
            opposite_action = actions[0]
            
            good = choice[1]

            #Check if we can complete the strategic offer with probability one
            if lob[good][opposite_action][0] is not None:
                price = lob[good][opposite_action][0]
    
                #We need to estimate the probability AFTER we take the trade
                mlob[good][opposite_action] = [None, None]
    
                #Estimate the probability of buying/selling it back later for a better price
                prob_accept = self.estimate_probability(good, opposite_action, mlob)
                prob_reject = self.estimate_probability(good, action, mlob)
                
                prob = (prob_accept)/(prob_accept+prob_reject)
                x = np.arange(201)
                #Create a vector of profit if sold at price x
                if opposite_action == "ask":
                    profits = x - np.repeat(price, 201)
    
                elif opposite_action == "bid":
                    profits = np.repeat(price, 201) -  x
    
    
                #Set all probabilities that do not meet the minimal probability requirement to 0
                prob = np.where(prob >= self.min_probability, prob, 0)
    
                #Calculate the expected profits and choose the best arbitrage trade
                expected_profits = profits*prob
                optimal_price = np.argmax(expected_profits)
                expected_profit = expected_profits[optimal_price]
    
                #If expected profit is positive then queue the arbitrage trade and buy/sell the good in the next order
                if expected_profit > 0:
                    order = Order(1, self.tid, action, good, price, 1, time)
                    order.strategic = True
                    order.target_price = optimal_price
    
                    next_order = Order(1, self.tid, opposite_action, good, optimal_price, 1, time)
                    next_order.arbitrage = True
    
                    options.append( (expected_profit, order, next_order) )

        if len(options) > 0:
            #Choose the best option
            best = max(options,key=itemgetter(0))

            if best[0] > 0:
                #Return the immediate buy/sell order and save the arbitrage offer for the next period
                self.strategic_order = deepcopy(best[1])
                self.arbitrage_order = deepcopy(best[2])
                return best[1]
            else:
                return None


#-------------------------- Other functions --------------------------------
def create_csv(file_name, dictionaries):
    """Creates csv file from a list of dictionaries
    
    It generates the csv file in the /results folder where the file lives.
    Also appends the timestamp when the results were generated.
    
    ...
    Parameters
    ----------
    file_name: str
        Current time-step
    dictionaries: list
        List of dictionaries makes a row for each dictionary
        
    Returns
    -------
    Order
        The order the the trader wants to submit to the exchange
    """
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
        """Function returns the correct trader object given the talgo value and trader type
        
        ...
        Parameters
        ----------
        ttype: int
            Trader Type
        talgo: str
            Name of the algorithm
            
        Returns
        -------
        Trader Object
            The correct trader object corresponding to ttype and talgo
        """
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
    """Gives traders based on a list of tuples containing tradertype and how many multiples of 3 traders per type
    ...
    Parameters
    ----------
    spec: list
        List of tuples specifing trader algorithm and amount (talgo, n).
        
    Returns
    -------
    list
        List of traders given the spec
    """
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
    """Calculates the new average when a new observation is added.
    ...
    Parameters
    ----------
    old_avg: float
        The average from n-1
    new_observation: float
        The new observation that has to be added to the average.
    n: int
        Current n after adding new_observation.
        
    Returns
    -------
    float
        The new average.
    """
    return old_avg*((n-1)/n) + new_observation/n

#-------------------------- END Other functions -----------------------------



endtime = 200
periods = 5
runs = 1


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

    spec = [("ZIP", 3),("eGD", 2)]
    trader_pairs, traders = generate_traders(spec)
    exchange = Exchange(traders)

    utility_levels = []



    for period in tqdm(range(1, periods+1), desc="Periods" , leave=False, disable=True):

        #Reset allocation for all traders
        exchange.reset_allocations()


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
                    successful_order, trade = exchange.process_order(time, period, run, order)
                    
                    if order.strategic is True and successful_order is False:
                        print("kk")
                    
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
                            

                            #Append it to the history using deepcopy
                            trade_history.append(deepcopy(trade))
                            if (seller_balance["money"] < 0 or buyer_balance["money"] < 0):
                                raise ValueError("money negative")
                        
                            if trader.talgo == "GDZ" and order.strategic is True:
                                #Allow trader to post the arbitrage trade immediatly
                                a_order = trader.get_order(time, lob, second_order=True)
                                successful_order, trade = exchange.process_order(time, period, run, a_order)
                                a_order.oid = order_id
                                order_id += 1
                                orders.append(order)
                                
                                if successful_order == False:
                                    #raise Exception("Something went wrong")
                                    pass
                                else:
                                    alob = exchange.publish_alob()
                                    for i in range(1, len(traders)+1):
                                        traders[i].respond(time, alob, a_order)
                        
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

