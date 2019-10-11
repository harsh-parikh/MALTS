#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 10 14:49:29 2018

@author: harshparikh
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Apr 11 19:55:55 2018

@author: Harsh
"""
import numpy as np
import scipy.optimize as opt
from sklearn import cluster as cluster
from matplotlib.pyplot import *
import time
import pandas as pd
import data_generation as dg
import distancemetriclearning as dml
import FLAMEbit as FLAME
import rpy2
from rpy2.robjects.vectors import StrVector
import rpy2.robjects.packages as rpack
from rpy2.robjects.packages import importr
import rpy2.robjects as robjects
import rpy2.robjects.lib as rlib
from rpy2.robjects.packages import SignatureTranslatedAnonymousPackage
import rpy2.robjects.numpy2ri
rpy2.robjects.numpy2ri.activate()
from rpy2.robjects import pandas2ri
pandas2ri.activate()
import InsaneLearner
#import ACIC_2
import warnings
warnings.filterwarnings('ignore')

K=5
currenttime = time.asctime(time.localtime())
currenttime = currenttime.replace(':','_')
log = open('Logs/log_Lalonde_'+currenttime+'.csv','w')

numExperiment = 1

#num_control = 500
#num_treated = 500
#num_cov_dense = 2
#num_covs_unimportant = 5
#numExample = num_control + num_treated
#num_covariates = num_cov_dense+num_covs_unimportant
#numVariable = num_covariates


print('num experiment: Lalonde', file=log)

    
#Data Generation
#LaLonde Experiment
df = pd.read_stata('lalonde.dta')
df = df.drop(columns='data_id')
df = df.sample(frac=1)
X,Y,T = np.array(df[df.columns[1:8]]), np.array(df['re78']), np.array(df['treat'])
n,m = X.shape
discrete = True

currenttime = time.asctime(time.localtime())
currenttime = currenttime.replace(':','_')

##InsaneLearning
insane = InsaneLearner.InsaneLearner(100)
insane.insaneLearning(X,Y,T)
t_hat_insane = insane.CATE(X)


#COBYLA Optimization
adknn_cobyla_diag = dml.distance_metric_learning(m,discrete=discrete)
optresult = adknn_cobyla_diag.optimize(X[:int(0.6*len(Y)),:],Y[:int(0.6*len(Y))],T[:int(0.6*len(Y))],numbatch=1)
LstarC_cobyla_diag = adknn_cobyla_diag.L
fLCcobyla_diag = lambda y: LstarC_cobyla_diag

dfC_cobyla_diag = pd.DataFrame(LstarC_cobyla_diag)
dcate_cobyla_diag, t_hat_cobyla_diag = adknn_cobyla_diag.CATE(X[int(0.6*len(Y)):,:],X[:int(0.6*len(Y)),:],Y[:int(0.6*len(Y))],T[:int(0.6*len(Y))],fLC=fLCcobyla_diag)
print("L matrix Control", file=log)
print(dfC_cobyla_diag, file=log)

var_array_C = np.average(np.array([ np.var(v[0][0],axis=0) for k,v in dcate_cobyla_diag.items() ]),axis=0)
var_array_T = np.average(np.array([ np.var(v[0][1],axis=0) for k,v in dcate_cobyla_diag.items() ]),axis=0)

fig = figure(figsize=(10,10))
rcParams.update({'font.size': 22})
rcParams['lines.linewidth'] = 5
plot(np.diag(LstarC_cobyla_diag))
#errorbar(x=np.arange(0,7),y=np.average(np.array(var_array_C),axis=0),yerr=np.std(np.array(var_array_C),axis=0))
#errorbar(x=np.arange(0,7),y=np.average(np.array(var_array_T),axis=0),yerr=np.std(np.array(var_array_T),axis=0))
xlabel('Covariate Indices')
ylabel('Average Variance')
legend(['matched groups in control','matched groups in treated'],loc=4)
tight_layout()
fig.savefig('Figures/Lalonde_Var_Match_Group_Plot_'+str(num_control)+'_'+str(num_treated)+'_'+str(num_cov_dense)+'_'+str(num_covs_unimportant)+'.jpg')


#Causal Random Forest
utils = importr('utils')
##packnames = ('MatchIt','grf')
##utils.install_packages(StrVector(packnames))
base = importr('base')
grf = importr('grf')
Ycrf = Y.reshape((len(Y),1))
Tcrf = T.reshape((len(T),1))
crf = grf.causal_forest(X,Ycrf,Tcrf)
tauhat = grf.predict_causal_forest(crf,X)
tau_hat = tauhat[0]
t_hat_crf = list(tau_hat)


##GenMatch
df.to_csv('non-constant-treatment-continuous.csv',index=False)
string = """
library('MatchIt')

mydata <- read.csv('non-constant-treatment-continuous.csv')

r <- matchit(treat ~ age+education+black+hispanic+married+nodegree+re75,
             methods = 'genetic', data = mydata)

mtch <- mydata[as.numeric(names(r$match.matrix[,])),]

hh <- mydata[as.numeric(names(r$match.matrix[,])),'re78']- mydata[as.numeric(r$match.matrix[,]),'re78']
"""
genmatch = SignatureTranslatedAnonymousPackage(string, "powerpack")
t_hat_genmatch = np.array(genmatch.hh)

##Nearest Neighbor Matching
string = """
library('MatchIt')

mydata <- read.csv('non-constant-treatment-continuous.csv')

r <- matchit(treat ~ age+education+black+hispanic+married+nodegree+re75,
             methods = 'nearest', data = mydata)

mtch <- mydata[as.numeric(names(r$match.matrix[,])),]

hh <- mydata[as.numeric(names(r$match.matrix[,])),'re78']- mydata[as.numeric(r$match.matrix[,]),'re78']
"""
nearest = SignatureTranslatedAnonymousPackage(string, "powerpack")
t_hat_nearest = np.array(nearest.hh)

##Exact
string = """
library('MatchIt')

mydata <- read.csv('non-constant-treatment-continuous.csv')

r <- matchit(treat ~ education+black+hispanic,
             methods = 'exact', data = mydata)

mtch <- mydata[as.numeric(names(r$match.matrix[,])),]

hh <- mydata[as.numeric(names(r$match.matrix[,])),'re78']- mydata[as.numeric(r$match.matrix[,]),'re78']
"""
exact = SignatureTranslatedAnonymousPackage(string, "powerpack")
t_hat_exact = np.array(exact.hh)

##CEM
string = """
library('MatchIt')

mydata <- read.csv('non-constant-treatment-continuous.csv')

r <- matchit(treat ~ age+education+black+hispanic+married+nodegree+re75,
             methods = 'cem', data = mydata)

mtch <- mydata[as.numeric(names(r$match.matrix[,])),]

hh <- mydata[as.numeric(names(r$match.matrix[,])),'re78']- mydata[as.numeric(r$match.matrix[,]),'re78']
"""
cem = SignatureTranslatedAnonymousPackage(string, "powerpack")
t_hat_cem = np.array(cem.hh)
#
#BARTS
Dc,Dt = adknn_cobyla_diag.split(X,Y,T)
Xc,Yc,Tc = Dc
Xt,Yt,Tt = Dt
dbarts = importr('dbarts')
bart_res_c = dbarts.bart(Xc,Yc,X,keeptrees=True,verbose=False)
y_c_hat_bart = np.array(bart_res_c.rx(8))
bart_res_t = dbarts.bart(Xt,Yt,X,keeptrees=True,verbose=False)
y_t_hat_bart = np.array(bart_res_t.rx(8))
t_hat_bart = list(y_t_hat_bart - y_c_hat_bart)[0]

print('Method, ATE Estimate, Estimation Bias (%)',file=log)
print('Truth,'+str(886)+','+str(0),file=log)
print('MALTS, '+ str( np.mean(t_hat_cobyla_diag) ) +','+str( (np.mean(t_hat_cobyla_diag) - 886)*100/886),file=log)
print('Difference of RF, '+ str(np.average(t_hat_insane) ) +','+str( (np.mean(t_hat_insane) - 886)*100/886),file=log)
print('CRF, '+ str( np.average(t_hat_crf))+','+str( (np.mean(t_hat_crf) - 886)*100/886),file=log)
print('Genmatch, '+ str( np.average(t_hat_genmatch))+','+str( (np.mean(t_hat_genmatch) - 886)*100/886),file=log)
print('Nearest Neighbor, '+ str( np.average(t_hat_nearest))+','+str( (np.mean(t_hat_nearest) - 886)*100/886),file=log)
print('CEM, '+ str( np.average(t_hat_cem))+','+str( (np.mean(t_hat_cem) - 886)*100/886),file=log)

fig = figure()
violinplot(t_hat_cobyla_diag,positions=[1])
#violinplot(t_hat_cobyla_full,positions=[2])
violinplot(t_hat_crf,positions=[3])
violinplot(t_hat_genmatch,positions=[4])
violinplot(t_hat_insane,positions=[5])
xticks([1,2,3,4,5],['MALTS (diag)','MALTS (full)','Causal Forest','GenMatch','Insane'])
fig.savefig('Figures/violinplot_cates_Lalonde'+'_'+str(currenttime)+'.jpg')

fig = figure(figsize=(10,10))
rcParams.update({'font.size': 36})
identity_line = np.linspace(min(min(t_hat_insane), min(t_hat_insane)), max(max(t_hat_insane), max(t_hat_insane)))
plot(identity_line, identity_line, color="black", linestyle="dashed", linewidth=3.0)
scatter(t_hat_cobyla_diag,t_hat_insane,alpha=0.15)
scatter(t_hat_cobyla_diag,t_hat_crf,alpha=0.15)
#scatter(t_true_cobyla_diag,t_hat_genmatch,alpha=0.15)
xlabel('MALTS ITE Prediction')
ylabel('Other method\'s ITE Prediction' )
tight_layout()
fig.savefig('Figures/CATE_Lalonde_'+str(currenttime)+'.jpg')

log.close()


