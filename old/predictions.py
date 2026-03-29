import polars as pl
from lightgbm import LGBMClassifier
import pickle

#form dataframe from the given data
def preprocess(raw_data: pl.DataFrame) -> pl.DataFrame:
    data = raw_data.clone()
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
def load_model(model_name: str) -> LGBMClassifier:
    with open(model_name, 'rb') as f:
        model = pickle.load(f)
    return model

#create probability predictions (how likely is this course to be a zombie)
def predict(preprocessed_data: pl.DataFrame, model: LGBMClassifier):
    probabilities = model.predict_proba(preprocessed_data)
    return probabilities[:,1]

#complies and writes the output file
def output_file_complier(raw_data: pl.DataFrame, new_file_name: str, probabilities: list):
    data = raw_data.clone()
    insisu = data["coursesisuid"].is_not_null().cast(pl.Int8)
    data = data.with_columns([pl.Series('zombie', probabilities), pl.Series("insisu", insisu)])
    column_order = ["zombie", "courseid", "insisu", "students", "category", "categoryparent", "visible", "datecreated", "lastaccess", "assignments", "assignmentsvisible", "attendance", "attendancevisible", "book", "bookvisible", "chats", "chatsvisible", "choices", "choicesvisible", "choicegroup", "choicegroupvisible", "databases", "databasesvisible", "feedbacks", "feedbacksvisible", "folders", "foldersvisible", "forums", "forumsvisible", "glossaries", "glossariesvisible", "h5p", "h5pvisible", "imscps", "imscpsvisible", "labels", "labelsvisible", "lessons", "lessonsvisible", "ltis", "ltisvisible", "pages", "pagesvisible", "quizzes", "quizzesvisible", "resources", "resourcesvisible", "scorms", "scormsvisible", "urls", "urlsvisible", "wikis", "wikisvisible", "workshops", "workshopsvisible"]
    data = data.select(column_order)
    data.write_csv(new_file_name)

#Preview function, probably not right???
def show_zombie_percent(raw_data: pl.DataFrame, limit: int = 200) -> pl.DataFrame:
    data = raw_data.clone()
    data = data.with_columns(pl.Series('zombie', probabilities))
    data = data.select(["courseid", "zombie"])
    return data.limit(limit)

#example
raw_data = pl.read_csv("moodlemodules_2026.csv", separator=";")
model = load_model("model.pkl")
preprocessed_data = preprocess(raw_data)
probabilities = predict(preprocessed_data, model)
print(show_zombie_percent(raw_data, 10))

