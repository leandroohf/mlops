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


# Architecture

```mermaid
flowchart TD
    A[CircleCI Build & Deploy Image] --> B[Docker Image Pushed to Artifact Registry]
    B --> C[GCP Cloud Run Job e.g. bike-pipeline-job]
    D[GCP Cloud Scheduler Triggers the Job Every hour] --> C

    classDef trigger fill:transparent,stroke:#333,stroke-width:1px;

    A:::trigger
    B:::trigger
    C:::trigger
    D:::trigger
```

# How to set google credentials on circleci


   1. Projedct Settings
   1. Enviroment variable
      ** Add a new env variable

   1. Copy the base64 contents of the security/gcp-bike-share-key.json

   ```sh
   base64 -i security/gcp-bike-share-key.json | pbcopy
   ```
