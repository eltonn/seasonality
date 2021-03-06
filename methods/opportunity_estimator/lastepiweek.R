# Calculate number of year's last week
source('../data_filter/episem.R')
lastepiweek <- function(ano){
  
  # Calcula o valor da última semana do ano
  
  diafim <- as.Date(paste(ano,'12','31',sep='-')) #Ultimo dia do ano
  diasem <- as.numeric(format(diafim,"%w"))       #dia semana do ultimo dia
  
  ewd <- ifelse (diasem < 3, diafim - diasem - 1, diafim + 6 - diasem) # Obtém a data do último sábado
  ewd <- as.Date(ewd,origin = '1970-01-01') # ultima semana epi do ano
  
  episem(ewd,retorna='W')
}
