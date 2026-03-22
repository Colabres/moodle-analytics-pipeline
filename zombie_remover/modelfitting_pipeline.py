import numpy as np
import pandas as pd
import polars as pl
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
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

#objective functions
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

def objective_xgb(trial):
    parameters = {
        "n_estimators": trial.suggest_int("n_estimators", 10, 2000),
        "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.1, log=True),
        "subsample": trial.suggest_float("subsample", 0.05, 1),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.05, 1),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 100),
        "max_depth": trial.suggest_int("max_depth", 1, 10),
        }
    classifier = XGBClassifier(**parameters)
    return np.mean(cross_val_score(classifier, x_train, y_train, cv = kf, scoring="neg_log_loss"))

#optimize hyperparameters
results = {}
best_params = {}
print("Training data ready")
print("Finding best hyperparameters for different models")
classifier = RandomForestClassifier()
results["rf"] = np.mean(cross_val_score(classifier, x_train, y_train, cv = kf, scoring="neg_log_loss"))
print("Model 1/3 optimized")
study = optuna.create_study(direction="maximize")
study.optimize(objective_lgbm, n_trials=100)
results["lgbm"] = study.best_value
best_params["lgbm"] = study.best_params
print("Model 2/3 optimized")
study = optuna.create_study(direction="maximize")
study.optimize(objective_xgb, n_trials=100)
results["xgb"] = study.best_value
best_params["xgb"] = study.best_params
print("Model 3/3 optimized")

#compare models and use the best one
best_model = [model for model, value in sorted(results.items(), key=lambda item:item[1])][-1]
if best_model == "lgbm":
    model = LGBMClassifier(**best_params["lgbm"])
elif best_model == "xgb":
    model = XGBClassifier(**best_params["xgb"])
else:
    model = RandomForestClassifier()
model.fit(x_train, y_train)

#save model
model_name = "model" #MODEL NAME AS INPUT HERE
with open(f'{model_name}.pkl','wb') as f:
    pickle.dump(model,f)