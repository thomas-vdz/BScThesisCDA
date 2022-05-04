# -*- coding: utf-8 -*-
"""
Created on Tue May  3 10:22:34 2022

@author: Gebruiker
"""

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

testorder = Order(1,1,"bid", "X", 5, 10, 1)
print(testorder)

class Orderbook:
    #Define min/max price so 

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
        #Test if there is a best-ask/bid present and report it in the anon_lob else return a empty tuple
        #For loop to avoid writing the same line 4 times
        for pair in [("X","bid"),("X","ask"),("Y","bid"),("Y","ask")]:
            if self.lob[pair[0]].get(pair[1]) is not None:
                order = self.lob[pair[0]].get(pair[1])                
                self.alob[pair[0]][pair[1]] = [order.price, order.quantity]
            else:
                #return empty tuple
                self.alob[pair[0]][pair[1]] = []
                
                
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
                if order.price < self.lob[order.ptype]["ask"].price:
                    self.lob[order.ptype][order.otype] = order
                else:
                    #ignore the order
                    pass
        #Update the anonymous lob
        self.anon_lob()
             
    
    
    
    

class Exchange(Orderbook):
    
    
    
    def __init__(self):
        
        self.ob = Orderbook()
        #Agents and their endowments [#money,#productX,#productY]
        self.agents = {
            1:{"money":1000,"X":1000,"Y":1000},
            2:{"money":1000,"X":100,"Y":100},
            3:{"money":1000,"X":100,"Y":100},
            }
        
    
    def process_order(self, order):        
        
        if order.otype == "ask":
            #Check if they have enough to post the offer
            if order.quantity <= self.agents[order.tid][order.ptype]:
                                 
                #Then check if the ask crosses the bid
                if order.price <= self.ob.lob[order.ptype]["bid"].price:
                    
                    #Get ID of counterparty                                       
                    buyer_id = self.ob.lob[order.ptype]["bid"].tid 
                    
                    #Partial sell: update quantity
                    if order.quantity < self.ob.lob[order.ptype]["bid"].quantity:
                        self.ob.lob[order.ptype]["bid"].quantity -= order.quantity                        
                        quant_sold = order.quantity
                        price_sold = self.ob.lob[order.ptype]["ask"].price
                        
                    
                    #Full sell: remove order
                    else:                        
                        #If we offer more than is able to be bought do we create a new transaction and give it as best bid
                        quant_sold = self.ob.lob[order.ptype]["bid"].quantity
                        price_sold = self.ob.lob[order.ptype]["ask"].price
                        del self.ob.lob[order.ptype]["bid"]
                    
                    #Update endowments
                   
                    self.agents[order.tid][order.ptype] -= quant_sold
                    self.agents[order.tid]["money"] += quant_sold * price_sold
                    
                    self.agents[buyer_id][order.ptype] += quant_sold
                    self.agents[buyer_id]["money"] -= quant_sold * price_sold
                                                        
                else:
                    self.add_order_lob(order)
        
            else:
                print("Not enough goods")
                
        elif order.otype == "bid":
            #Check if they have enough money to post the bid
            if (order.price * order.quantity) <= self.agents[order.tid]["money"]:
                                 
                #Then check if the bid crosses the ask
                if order.price >= self.ob.lob[order.ptype]["ask"].price:
                    #Get id of counterparty
                    seller_id = self.ob.lob[order.ptype]["ask"].tid 
                    
                    #Partial buy: update quantity
                    if order.quantity < self.ob.lob[order.ptype]["ask"].quantity:
                        self.ob.lob[order.ptype]["ask"].quantity -= order.quantity                        
                        quant_sold = order.quantity
                        price_sold = self.ob.lob[order.ptype]["ask"].price
                        
                    
                    #Full buy: remove order
                    else:                        
                        #If we offer more than is able to be bought do we create a new transaction and give it as best ask
                        quant_sold = self.ob.lob[order.ptype]["ask"].quantity
                        price_sold = self.ob.lob[order.ptype]["ask"].price
                        del self.ob.lob[order.ptype]["ask"]
                    
                    #Update endowments
                                                        
                    self.agents[order.tid][order.ptype] += quant_sold
                    self.agents[order.tid]["money"] -= quant_sold * price_sold
                    
                    self.agents[seller_id][order.ptype] -= quant_sold
                    self.agents[seller_id]["money"] += quant_sold * price_sold                                        
                
                else:
                    self.add_order_lob(order)
            else:
                print("Not enough money")
        else:
            print("Something is wrong with the order")
        
    
    def publish_alob(self):
        self.ob.anon_lob()
        return self.ob.alob
    
    def print_endowments(self):        
        print(self.agents)
    

     
o = Exchange()

o.ob.add_order_lob(Order(1,1,"bid", "X", 5, 10, 1))   
o.ob.add_order_lob(Order(2,1,"bid", "X", 7, 10, 2))   
o.ob.add_order_lob(Order(3,1,"ask", "X", 20, 10, 3))   
o.ob.add_order_lob(Order(4,1,"ask", "X", 15, 10, 4))
o.ob.add_order_lob(Order(1,1,"bid", "Y", 5, 10, 1))   
o.ob.add_order_lob(Order(2,1,"bid", "Y", 7, 10, 2))   
o.ob.add_order_lob(Order(3,1,"ask", "Y", 20, 10, 3))   
o.ob.add_order_lob(Order(4,1,"ask", "Y", 15, 10, 4))

print(o.publish_alob())


o.process_order(Order(1,2,"ask", "X", 6, 5000, 2))


print(o.publish_alob())

o.print_endowments()

        