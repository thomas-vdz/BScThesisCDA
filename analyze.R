#Makes sure the working directory is the same directory as the file is in
library("rstudioapi")  
library("ggplot2")

library("dplyr")

setwd(dirname(getActiveDocumentContext()$path))   


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
util_data$x = (util_data$time + (util_data$period-1)*300)
util_data$avg_util = ifelse(util_data$time  == 1, NA , util_data$avg_util)

#Convert ttype to string
util_data$ttype = as.character(util_data$ttype)


#Price over time 
ggplot(util_data, aes(x = x, y= avg_util, colour= ttype, linetype=talgo  ))+
  geom_line(size=0.75) +
  ylab("Average utility level") +
  xlab("Period") +
  scale_x_continuous(breaks=seq(0,1500,300), labels=c("0","1","2","3","4","5")) +
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
trade_data$x = (trade_data$time + (trade_data$period-1)*300)
ggplot(trade_data, aes(x = x, y= price, colour= ptype  )) +
  geom_line(size=1) +
  xlab("Period") +
  scale_x_continuous(breaks=seq(0,1500,300), labels=c("0","1","2","3","4","5")) +
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


#----------------- Excess Plot ---------------------

excess_data = read.csv( paste0("results/",most_recent(path="results", pattern="excess")))
#Convert ttype to string
excess_data$ttype = as.character(excess_data$ttype)

#Gives the average excess per period/algorithm/tradertype
average_excess = group_by(excess_data, ttype, talgo, period) %>% summarize(money = mean(money), X = mean(X), Y = mean(Y))

#Sort by period 
average_excess = average_excess[order(average_excess$period),]
average_excess

ggplot(excess_data, aes(x = period, y= money, colour= ttype, linetype=talgo  ))+
  geom_line(size=0.75)
