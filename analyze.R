#Makes sure the working directory is the same directory as the file is in
library("rstudioapi")  
library("ggplot2")
setwd(dirname(getActiveDocumentContext()$path))   


#Open file
data = read.csv("util.csv")
data = data[!(data$time == 1  & data$period == 1), ]

#Add x values for plotting
data$x = (data$time + (data$period-1)*300)
data$avg_util = ifelse(data$time  == 1, NA , data$avg_util)

#Convert ttype to string
data$ttype = as.character(data$ttype)

#Res

#Price over time 
ggplot(data, aes(x = x, y= avg_util, colour= ttype, linetype=talgo  ))+
  geom_line(size=0.75) +
  ylab("Average utility level") +
  xlab("Period") +
  scale_x_continuous(breaks=seq(0,900,300), labels=c("0","1","2","3")) +
  theme(
    legend.text = element_text(size = 12),
    panel.background = element_rect(fill = "#BFD5E3", colour = "#6D9EC1",
                                    size = 2, linetype = "solid"),
    panel.grid.major = element_line(size = 0.5, linetype = 'solid',
                                    colour = "white"), 
    panel.grid.minor = element_line(size = 0.25, linetype = 'solid',
                                    colour = "white"),
    axis.text.x = element_text(face="bold", color="#993333", 
                               size=14, angle=45)
  )



#Test on Allocations
