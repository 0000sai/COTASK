#!/usr/bin/env bash

# Create kubernetes cluster by using ekctl:
eksctl create cluster \
    --name kubernetescluster \
    --version 1.17 \
    --nodegroup-name kubernetes-nodes \
    --node-type t2.small \
    --nodes 2 \
    --nodes-min 1 \
    --nodes-max 3 \
    --node-volume-size=20 \
    --region us-west-2 \
    --zones us-west-2a \
    --zones us-west-2b \
    --zones us-west-2c \
    
    
# Config kubectl to connect to Amazon EKS cluster:
aws eks update-kubeconfig --name kubernetescluster --region us-west-2

