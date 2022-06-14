#Makes sure the working directory is the same directory as the file is in
library("rstudioapi")  
library("ggplot2")
setwd(dirname(getActiveDocumentContext()$path))   


#Open file
data = read.csv("util.csv")

#Add x values for plotting
data$x = data$time + (data$period-1)*300


#Price over time 
p = ggplot(data, aes(x = x, y= x))


#Test on Allocations
