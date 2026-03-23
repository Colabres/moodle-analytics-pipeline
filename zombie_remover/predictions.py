import polars as pl
import pickle

#form dataframe from the given data
def form_dataframe(file):
    data = pl.read_csv(file, separator=";")
    data = data.fill_nan(0)
    data = data.with_columns(
    pl.col("coursesisuid").is_not_null().cast(pl.Int8).alias("insisu")
    )
    dropped = [
        "coursesisuid",
        "datecreated",
        "lastaccess",
        "category",
        "categoryparent",
        "assignmentsvisible",
        "attendancevisible",
        "bookvisible",
        "chatsvisible",
        "choicesvisible",
        "choicegroupvisible",
        "databasesvisible",
        "feedbacksvisible",
        "foldersvisible",
        "forumsvisible",
        "glossariesvisible",
        "h5pvisible",
        "imscpsvisible",
        "labelsvisible",
        "lessonsvisible",
        "ltisvisible",
        "pagesvisible",
        "quizzesvisible",
        "resourcesvisible",
        "scormsvisible",
        "urlsvisible",
        "wikisvisible",
        "workshopsvisible",
        "courseid"
        ]
    data = data.drop(dropped)
    return data

#Load saved classifier
def load_model(model_name):
    with open(model_name, 'rb') as f:
        model = pickle.load(f)
    return model

#create probability predictions (how likely is this course to be a zombie)
def predict(data, model):
    probabilities = model.predict_proba(data)
    return probabilities[:,1]

#Remove courses that are zombie with given probability treshold
def zombie_remover(file, new_file_name, treshold, probabilities):
    data = pl.read_csv(file, separator=";")
    data = data.with_columns(pl.Series('zombie', probabilities))
    data = data.filter(pl.col('zombie') <= treshold)
    data.write_csv(new_file_name)

#Preview function, probably not right???
def show_zombie_percent(data: pl.DataFrame, limit: int = 200):
    data = data.with_columns(pl.Series('zombie', probabilities))
    data = data.select(["courseid", "zombie"])
    return data.limit(limit)

#example
data = form_dataframe("moodlemodules_2026.csv")
model = load_model("model.pkl")
probabilities = predict(data, model)
zombie_remover("moodlemodules_2026.csv", "predictions_proba.csv", 0.5, probabilities)


