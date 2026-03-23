import numpy as np
import pandas as pd
import polars as pl
from lightgbm import LGBMClassifier
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import KFold
import optuna
import pickle

#format training data
def form_train_dataframe(file):
    df = pl.read_csv(file, has_header=True)
    df = df.drop_nans()
    y_train = df["zombie"]
    x_train = df.drop(["zombie", "courseid", "activitysum"])  
    x_train = x_train.to_pandas()
    y_train = y_train.to_pandas()
    return x_train, y_train

#create training data sets
x_train, y_train = form_train_dataframe("trainmoodlemodules_labeled.csv")
kf = KFold(shuffle=True)

#objective function
def objective_lgbm(trial):
    parameters = {
        "n_estimators": trial.suggest_int("n_estimators", 10, 2000),
        "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.1, log=True),
        "subsample": trial.suggest_float("subsample", 0.05, 1),
        "subsample_freq": 1,
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.05, 1),
        "min_child_samples": trial.suggest_int("min_child_samples", 1, 100),
        "num_leaves": trial.suggest_int("num_leaves", 2, 2**10),
        }
    classifier = LGBMClassifier(**parameters, verbose=-1)
    return np.mean(cross_val_score(classifier, x_train, y_train, cv = kf, scoring="neg_log_loss"))

#optimize hyperparameters
study = optuna.create_study(direction="maximize")
study.optimize(objective_lgbm, n_trials=100)

#Train a model with the best parameters
model = LGBMClassifier(**study.best_params)
model.fit(x_train, y_train)

#save model
model_name = "model" #MODEL NAME AS INPUT HERE
with open(f'{model_name}.pkl','wb') as f:
    pickle.dump(model,f)