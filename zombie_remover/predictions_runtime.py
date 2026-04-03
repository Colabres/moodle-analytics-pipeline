import pickle
import polars as pl
import os

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
        "courseid",
    ]

    data = data.drop(dropped)
    return data


def load_model(model_name: str = "model"):
    with open(model_name, "rb") as f:
        model = pickle.load(f)
    return model


def predict(preprocessed_data: pl.DataFrame, model):
    probabilities = model.predict_proba(preprocessed_data)
    return probabilities[:, 1]


def predict_zombies(raw_data: pl.DataFrame, model_name: str = "model"):
    model = load_model(model_name)
    preprocessed_data = preprocess(raw_data)
    probabilities = predict(preprocessed_data, model)
    return probabilities


def show_zombie_percent(
    raw_data: pl.DataFrame,
    probabilities,
    limit: int = 200,
) -> pl.DataFrame:
    data = raw_data.clone()
    data = data.with_columns(pl.Series("zombie", probabilities))
    data = data.select(["courseid", "zombie"])
    return data.limit(limit)


def output_file_complier(
    raw_data: pl.DataFrame,
    new_file_name: str,
    probabilities,
):
    data = raw_data.clone()
    insisu = data["coursesisuid"].is_not_null().cast(pl.Int8)

    data = data.with_columns(
        [
            pl.Series("zombie", probabilities),
            pl.Series("insisu", insisu),
        ]
    )

    column_order = [
        "zombie",
        "courseid",
        "insisu",
        "students",
        "category",
        "categoryparent",
        "visible",
        "datecreated",
        "lastaccess",
        "assignments",
        "assignmentsvisible",
        "attendance",
        "attendancevisible",
        "book",
        "bookvisible",
        "chats",
        "chatsvisible",
        "choices",
        "choicesvisible",
        "choicegroup",
        "choicegroupvisible",
        "databases",
        "databasesvisible",
        "feedbacks",
        "feedbacksvisible",
        "folders",
        "foldersvisible",
        "forums",
        "forumsvisible",
        "glossaries",
        "glossariesvisible",
        "h5p",
        "h5pvisible",
        "imscps",
        "imscpsvisible",
        "labels",
        "labelsvisible",
        "lessons",
        "lessonsvisible",
        "ltis",
        "ltisvisible",
        "pages",
        "pagesvisible",
        "quizzes",
        "quizzesvisible",
        "resources",
        "resourcesvisible",
        "scorms",
        "scormsvisible",
        "urls",
        "urlsvisible",
        "wikis",
        "wikisvisible",
        "workshops",
        "workshopsvisible",
    ]

    data = data.select(column_order)
    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", new_file_name)
    data.write_csv(output_path)