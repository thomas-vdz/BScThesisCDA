#Makes sure the working directory is the same directory as the file is in
library("rstudioapi")  
library("ggplot2")
library("tidyverse")
library("dplyr")
library("padr")
library("kableExtra")
library("scales")

#Set working directory to the location of the file
setwd(dirname(getActiveDocumentContext()$path))   

#Run data 
runs = 1000
periods = 5 
endtime = 200



#Function so we can read the latest csv file that has been generated.
# f(...) indicates we can pass any parameter into list.files
most_recent = function(...) {
  tail(list.files(...), 1)
} 

#----------------- Average Utility Plot ---------------------

#Open the most recent util.csv file in the results folder.
util_data = read.csv( paste0("results/",most_recent(path="results", pattern="util")) )
util_data = util_data[!(util_data$time == 1  & util_data$period == 1), ]

#Add x values for plotting
util_data$x = (util_data$time + (util_data$period-1)*endtime)
util_data$avg_util = ifelse(util_data$time  == 1, NA , util_data$avg_util)

#Convert ttype to string
util_data$ttype = as.character(util_data$ttype)


#Utility over time
ggplot(util_data, aes(x = x, y= avg_util, colour= ttype, linetype=talgo  ))+
  geom_line(size=0.75) +
  ylab("Average utility level") +
  xlab("Period") +
  scale_x_continuous(breaks=seq(0,endtime*periods,endtime), labels=c("0","1","2","3","4","5")) +
  theme(
    legend.text = element_text(size = 12),
    panel.background = element_rect(fill = "#BFD5E3", colour = "#6D9EC1",
                                    size = 2, linetype = "solid"),
    panel.grid.major = element_line(size = 0.5, linetype = 'solid',
                                    colour = "white"), 
    panel.grid.minor = element_line(size = 0.25, linetype = 'solid',
                                    colour = "white"),
    axis.text.x = element_text(face="bold", color="#000000", 
                               size=14, angle=45)
  )

#----------------- Trade/Price Plot ---------------------
 trade_data = read.csv( paste0("results/",most_recent(path="results", pattern="trade")) )

trade_data$x = trade_data$time + endtime*(trade_data$period-1)

#Make unique id for each timestep at each run
trade_data$id = (trade_data$x + (trade_data$run-1)*(periods*endtime))




#Separate x,y pricedata
trade_data_x = trade_data[ trade_data$ptype == "X", c("time", "price", 'ptype', 'x', 'id') ]

#Average prices per unique timestep
avg_price_x = tibble( unique( group_by(trade_data_x, id) %>% summarize(price = mean(price), x = x) ), .name_repair = make.unique )

#Fill in the missing ID's
avg_price_x = pad_int(avg_price_x, "id")
#If there is no price set is to the last known price
avg_price_x  = fill(avg_price_x , price)

#Get the correct x values
avg_price_x$x = ifelse(is.na(avg_price_x$x)==TRUE, avg_price_x$id %% (periods*endtime) , avg_price_x$x)

#Now calculate std deviation/
stats_x = data.frame(matrix(ncol=5,nrow=periods*endtime))


colnames(stats_x) = c("x","mean","stddev","lowerbound","upperbound")

#Calculate 95% confidence interval for each unique timestep
for (i in 1:(periods*endtime -1)){
  #Get all obs with x = i
  prices = avg_price_x[avg_price_x$x == i,]$price

  m = mean(prices)
  sd = sqrt(var(prices))
  n = length(prices)

  error = qt(0.975, df=n-1)*sd/sqrt(n)
  lower = m - error
  upper = m + error

  row = c(i, m, sd, lower, upper)
  stats_x[i,] = row
}

ggplot(stats_x, aes(x = x))+
  ggtitle("X")+
  geom_line(aes(y = mean, colour= "Mean"))+
  geom_ribbon(aes(ymin=lowerbound, ymax=upperbound, x=x, fill = "band"), alpha = 0.3)+
  xlab("Period") +
  ylab("Price") +
  scale_x_continuous(breaks=seq(0,endtime*periods,endtime), labels=c("0","1","2","3","4","5"))


# Y DATA


trade_data_y = trade_data[ trade_data$ptype == "Y", ]


#Separate x,y pricedata
trade_data_y = trade_data[ trade_data$ptype == "Y", c("time", "price", 'ptype', 'x', 'id') ]

#Average prices per unique timestep
avg_price_y = tibble( unique( group_by(trade_data_y, id) %>% summarize(price = mean(price), x = x) ), .name_repair = make.unique )

#Fill in the missing ID's
avg_price_y = pad_int(avg_price_y, "id")
#If there is no price set is to the last known price
avg_price_y  = fill(avg_price_y , price)

#Get the correct x values
avg_price_y$x = ifelse(is.na(avg_price_y$x)==TRUE, avg_price_y$id %% (periods*endtime) , avg_price_y$x)

#Now calculate std deviation/
stats_y = data.frame(matrix(ncol=5,nrow=periods*endtime))


colnames(stats_y) = c("x","mean","stddev","lowerbound","upperbound")

#Calculate 95% confidence interval for each unique timestep
for (i in 1:(periods*endtime -1)){
  #Get all obs with x = i
  prices = avg_price_y[avg_price_y$x == i,]$price

  m = mean(prices)
  sd = sqrt(var(prices))
  n = length(prices)

  error = qt(0.975, df=n-1)*sd/sqrt(n)
  lower = m - error
  upper = m + error

  row = c(i, m, sd, lower, upper)
  stats_y[i,] = row
}

ggplot(stats_y, aes(x = x))+
  ggtitle("Y")+
  geom_line(aes(y = mean, colour= "Mean"))+
  geom_ribbon(aes(ymin=lowerbound, ymax=upperbound, x=x, fill = "band"), alpha = 0.3)+
  xlab("Period") +
  ylab("Price") +
  scale_x_continuous(breaks=seq(0,endtime*periods,endtime), labels=c("0","1","2","3","4","5"))


#----------------- Excess Plot ---------------------

excess_data = read.csv( paste0("results/",most_recent(path="results", pattern="excess")))
#Convert ttype to string
excess_data$ttype = as.character(excess_data$ttype)

#Gives the average excess per period/algorithm/tradertype
average_excess = group_by(excess_data, ttype, talgo) %>% summarize(money = mean(money), X = mean(X), Y = mean(Y))


#Normalize to relative average_excess

convert_percent = label_percent()
average_excess$money = convert_percent(average_excess$money/400)
average_excess$X = convert_percent(average_excess$X/10)
average_excess$Y = convert_percent(average_excess$Y/20)
average_excess %>%
  kbl(caption="Normalized Average excess ",
      format="latex",
      col.names = c("Type","Algorithm","Money","X","Y"),
      align="r") %>%
  kable_classic(full_width = F,  html_font = "Source Sans Pro")



#----------------- Arbitrage Plot ---------------------
arbitrage_data = read.csv( paste0("results/",most_recent(path="results", pattern="arbitrage")))
rejected_data = read.csv( paste0("results/",most_recent(path="results", pattern="rejected")))
#Add target profit 
arbitrage_data$target_profit = ifelse(arbitrage_data$taker == arbitrage_data$buyer_id, arbitrage_data$original_price - arbitrage_data$target_price  , arbitrage_data$target_price - arbitrage_data$original_price )

#Add trader types
arbitrage_data$ttype = ifelse(arbitrage_data$taker%%3 == 0 , 3, arbitrage_data$taker%%3)

t_sum = trade_data %>% group_by(run) %>% summarize(n= n())
t_avg = round(mean(t_sum$n))

# Regular traders 
p_arbitrage = arbitrage_data[arbitrage_data$profit > 0, ]
p_sum = p_arbitrage %>% group_by(run ) %>% summarize(n= n())
p_n_avg = round(mean(p_sum$n))
p_row = c(p_n_avg, mean(p_arbitrage$profit), mean(p_arbitrage$target_profit), mean(p_arbitrage$wait_time))




l_arbitrage = arbitrage_data[arbitrage_data$profit <= 0, ]
l_sum = l_arbitrage %>% group_by(run) %>% summarize(n= n())
l_n_avg = round(mean(l_sum$n))
l_row = c(round(mean(l_sum$n)), mean(l_arbitrage$profit), mean(l_arbitrage$target_profit), mean(l_arbitrage$wait_time))

t_row = c(p_n_avg+l_n_avg, mean(arbitrage_data$profit), mean(arbitrage_data$target_profit), mean(arbitrage_data$wait_time))

rejected_data$target_profit = abs(rejected_data$price - rejected_data$target_price)

r_n_avg = round(length(rejected_data$run)/runs, 1)
r_row = c(r_n_avg, "-", round(mean(rejected_data$target_profit),3) , round(mean(rejected_data$time)))

arbitrage_table = rbind(t_row, p_row, l_row)
arbitrage_table = round(arbitrage_table, 3)
arbitrage_table = rbind(arbitrage_table, r_row)
colnames(arbitrage_table) = c("n", "Profit", "Target profit", "Wait time")
rownames(arbitrage_table) = c("Total", "Profit", "Loss", "Failed")
arbitrage_table %>%
  kbl(format="latex",
      align="r") %>%
  kable_classic(full_width = F,  html_font = "Source Sans Pro")

# ------ Arbitrage trader type split -------
arbitrage_table_split = NULL

for (i in 1:3){
  
  arbitrage_data_split = arbitrage_data[arbitrage_data$ttype == i,]
  # Regular traders 
  p_arbitrage = arbitrage_data_split[arbitrage_data_split$ profit > 0 , ]
  p_sum = p_arbitrage %>% group_by(run ) %>% summarize(n= n())
  p_n_avg = round(mean(p_sum$n))
  p_row = c(p_n_avg, mean(p_arbitrage$profit), mean(p_arbitrage$target_profit), mean(p_arbitrage$wait_time))
  
  
  
  l_arbitrage = arbitrage_data_split[arbitrage_data_split$profit <= 0 , ]
  l_sum = l_arbitrage %>% group_by(run) %>% summarize(n= n())
  l_n_avg = round(mean(l_sum$n))
  l_row = c(round(mean(l_sum$n)), mean(l_arbitrage$profit), mean(l_arbitrage$target_profit), mean(l_arbitrage$wait_time))
  
  t_row = c(p_n_avg+l_n_avg, mean(arbitrage_data_split$profit), mean(arbitrage_data_split$target_profit), mean(arbitrage_data_split$wait_time))
  
  rejected_data_split = rejected_data[rejected_data$ttype ==i, ]
  r_n_avg = round(length(rejected_data_split$run)/runs, 1)
  r_row = c(r_n_avg, "-", round(mean(rejected_data_split$target_profit),3) , round(mean(rejected_data_split$time)))
  
  arbitrage_table = rbind(t_row, p_row, l_row)
  arbitrage_table = round(arbitrage_table, 3)
  arbitrage_table = rbind(arbitrage_table, r_row)
  rownames(arbitrage_table) = c("Total", "Profit", "Loss", "Failed")
  if (is.null(arbitrage_table_split)){
    arbitrage_table_split = arbitrage_table
  }
  else{
  arbitrage_table_split  = rbind(arbitrage_table_split, arbitrage_table)
  }
}

arbitrage_table_split %>%  kbl(format="latex",
                              align="r") %>%
  kable_classic(full_width = F,  html_font = "Source Sans Pro")
