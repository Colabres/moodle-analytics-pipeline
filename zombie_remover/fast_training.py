import numpy as np
import polars as pl
import pandas as pd
from lightgbm import LGBMClassifier
import pickle

def form_train_dataframe(file):
    df = pl.read_csv(file, has_header=True)
    df = df.drop_nans()
    y_train = df["zombie"]
    x_train = df.drop(["zombie", "courseid", "activitysum"])  
    x_train = x_train.to_pandas()
    y_train = y_train.to_pandas()
    return x_train, y_train

#optimized hyperparameters
parameters = {'n_estimators': 1468, 'learning_rate': 0.005602358951035724, 'subsample': 0.6958987762879659, 'colsample_bytree': 0.99490517421889, 'min_child_samples': 15, 'num_leaves': 121}

#create training data sets
x_train, y_train = form_train_dataframe("trainmoodlemodules_labeled.csv")

#Train a model with the best parameters
model = LGBMClassifier(**parameters)
model.fit(x_train, y_train)

#save model
model_name = "model" #MODEL NAME AS INPUT HERE
with open(f'{model_name}.pkl','wb') as f:
    pickle.dump(model,f)