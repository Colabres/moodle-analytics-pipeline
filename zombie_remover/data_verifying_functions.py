import polars as pl

def good_for_training(data: pl.DataFrame) -> bool:
    if data.columns == ["courseid","visible","assignments","attendance","book","chats","choices","choicegroup","databases","feedbacks","folders","forums","glossaries","h5p","imscps","labels","lessons","ltis","pages","quizzes","resources","scorms","urls","wikis","workshops","students","insisu","activitysum","zombie"]:
        return True
    else:
        return False
    
def good_for_predictions(data: pl.DataFrame) -> bool:
    if data.columns == ['category', 'categoryparent', 'courseid', 'coursesisuid', 'visible', 'datecreated', 'lastaccess', 'assignments', 'assignmentsvisible', 'attendance', 'attendancevisible', 'book', 'bookvisible', 'chats', 'chatsvisible', 'choices', 'choicesvisible', 'choicegroup', 'choicegroupvisible', 'databases', 'databasesvisible', 'feedbacks', 'feedbacksvisible', 'folders', 'foldersvisible', 'forums', 'forumsvisible', 'glossaries', 'glossariesvisible', 'h5p', 'h5pvisible', 'imscps', 'imscpsvisible', 'labels', 'labelsvisible', 'lessons', 'lessonsvisible', 'ltis', 'ltisvisible', 'pages', 'pagesvisible', 'quizzes', 'quizzesvisible', 'resources', 'resourcesvisible', 'scorms', 'scormsvisible', 'urls', 'urlsvisible', 'wikis', 'wikisvisible', 'workshops', 'workshopsvisible', 'students']:
        return True
    else:
        return False


if __name__ == "__main__":
    # change path to your actual file
    file_path = "trainmoodlemodules_labeled.csv"

    df = pl.read_csv(file_path)

    print("Detected columns:")
    print(df.columns)

    print("\nFirst column repr (important):")
    print(repr(df.columns[0]))

    print("\nIs valid training file?")
    print(good_for_training(df))