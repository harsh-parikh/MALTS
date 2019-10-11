#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 18 20:17:07 2018

@author: harshparikh
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from torch.autograd import Variable
from . import data_generation as dg

torch.set_default_tensor_type('torch.DoubleTensor')

class adknnLoss(nn.Module):
    def __init__(self,net):
        super(adknnLoss, self).__init__()
        self.net = net
        
    def forward(self,L,X,Y):
        n,m = X.size()
        l = torch.zeros([n])
        for i in range(0,n):
            drum = torch.ones([n])
            for j in range(0,n):
                drum[j] = torch.exp( -torch.norm( ( L[i] * X[i] ) - ( net(X[j]) * X[j] ) ) )
            l[i] = (Y[i] - (torch.matmul(drum,Y)/torch.matmul(torch.ones([n]),drum)))**2
        loss = torch.sum(l)
        return loss
    


class neuralnet(nn.Module):
    
    def __init__(self,inputsize,outputsize,sizeofhiddenlayers):
        super(neuralnet, self).__init__()
        self.layer0 = nn.Linear(inputsize,sizeofhiddenlayers)
        self.layer1 = nn.Linear(sizeofhiddenlayers,outputsize)
        self.optimizer = optim.SGD(self.parameters(), lr=0.01)
        
    def forward(self,x):
        x = torch.tensor(x,requires_grad=True)
        y = F.softplus(self.layer0(x))
        y = self.layer1(y)
        return y
    
    def train(self,X,Y,iter=10):
        lossfn = adknnLoss(self)
        for i in range(0,iter):
            self.optimizer.zero_grad() 
            L = self(X)
            loss = lossfn(L,X,Y)
            print(loss)
            loss.backward()
            #print(self.layer0.bias.grad)
            self.optimizer.step()
            if(loss <= torch.tensor(1.00000e-28)):
                break
            
class flexibleMALTS:
    def __init__(self,X,Y,T):
        def split(X,Y,T):
            n,m = X.shape
            Xc,Tc,Yc = [],[],[]
            Xt,Tt,Yt = [],[],[]
            for i in range(0,n):
                if T[i] == 0:
                    Xc.append(X[i,:])
                    Yc.append(Y[i])
                    Tc.append(T[i])
                elif T[i] == 1:
                    Xt.append(X[i,:])
                    Yt.append(Y[i])
                    Tt.append(T[i])
            #print Xc is None,Yc is None,Tc is None,Xt is None,Yt is None,Tt is None
            return np.array(Xc),np.array(Yc),np.array(Tc),np.array(Xt),np.array(Yt),np.array(Tt)
        def makeTensor(a):
            return Variable(torch.tensor(a),requires_grad=True)
        self.Xc, self.Yc, self.Tc, self.Xt, self.Yt, self.Tt = split(X,Y,T)
        self.Xc, self.Yc, self.Tc, self.Xt, self.Yt, self.Tt = makeTensor(self.Xc), makeTensor(self.Yc), makeTensor(self.Tc), makeTensor(self.Xt), makeTensor(self.Yt), makeTensor(self.Tt)
        
        
    def fit(self,net):
        for itr in range(0,5):
            net.train(self.Xc,self.Yc)
            net.train(self.Xt,self.Yt)
        return net
        


num_control = 1000
num_treated = 1000
num_cov_dense = 10
num_covs_unimportant = 20
numExample = num_control + num_treated
num_covariates = num_cov_dense+num_covs_unimportant
numVariable = num_covariates
    
data = dg.data_generation_dense_2(num_control, num_treated, num_cov_dense, num_covs_unimportant)
df, dense_bs, treatment_eff_coef = data
X,Y,T = np.array(df[df.columns[0:num_covariates]]), np.array(df['outcome']), np.array(df['treated'])

malts = flexibleMALTS(X,Y,T)
n,p = malts.Xc.size()
net = neuralnet(p,p,p)
net = malts.fit(net)

#X = Variable(torch.tensor(np.array(df[df.columns[0:num_covariates]])),requires_grad=True)
#Y = Variable(torch.tensor(np.array(df['outcome'])),requires_grad=True)
#T = Variable(torch.tensor(np.array(df['treated'])),requires_grad=True)
#n,m = X.shape
#Xtest = np.random.normal(1, 1, size=(5000, num_covariates))
#t_true = np.dot((Xtest[:,:len(treatment_eff_coef)]),treatment_eff_coef) + np.sum(dg.construct_sec_order(Xtest[:,:num_cov_dense]), axis=1)
#discrete = False
#
#net = neuralnet(num_covariates,num_covariates,4*num_covariates)
#net.train(X,Y)
