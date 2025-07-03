# Introduction

This is an example of mlops mvp project. The goal is personal learnings. Decide to start by exploring how to use 
* avro
* cloud scheduler for periodic training and inference

# Bike share

Bike sharing systems struggle with bikes being in the wrong place at the wrong time.
* Sometimes are empty
* Sometimes they are full and user cannot return the bikes

We want to predict bike net change per station to help rebalance bikes (ensure availability, reduce overflow).


NOTEs: for writting better later
* For simplicity we are overwritting previous models
* Assume training time are fast < 30minutes
