from requests import Session
from bs4 import BeautifulSoup

roman = {1: "I", 2: "II", 3: "III", 4: "IV"}


def createSoup(subdomain, url, session: Session):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.114 YaBrowser/22.9.1.1095 Yowser/2.5 Safari/537.36"
    }
    getInfo = session.post(url=url, data=None, headers=headers)
    soup = BeautifulSoup(getInfo.text, "lxml")
    return soup


def getInfo(subdomain, session: Session):
    url = f"https://{subdomain}.eljur.ru/journal-user-preferences-action"

    soup = createSoup(subdomain, url, session)
    if "error" in soup:
        return soup

    label = None
    info = {}
    for tag in soup.find_all(["label", "input"], class_=["ej-form-label", "field field--fill"]):
        print(tag.contents)
        if tag.contents:
            if tag.contents[0].strip() in ("СНИЛС", "Пол"):
                break

        if tag.name == "label":
            label = tag.contents[0].strip()
            info.update([(label, None)])

        if tag.name == "input":
            info[label] = tag["value"]

    return info


def getJournal(subdomain, session: Session, week=0):
    url = f"https://{subdomain}.eljur.ru/journal-app/week.{week * -1}"

    soup = createSoup(subdomain, url, session)
    if "error" in soup:
        return soup

    info = {}
    i = 1
    for day in soup.find_all("div", class_="dnevnik-day"):
        title = day.find("div", class_="dnevnik-day__title")
        week, date = title.contents[0].strip().replace("\n", "").split(", ")

        if day.find("div", class_="page-empty"):
            info.update(
                {
                    "day": week,
                    "date": date,
                    "isEmpty": True,
                    "comment": "Нет уроков",
                    "lessons": {},
                }
            )
            continue

        if day.find("div", class_="dnevnik-day__holiday"):
            info.update(
                {
                    "day": week,
                    "date": date,
                    "isEmpty": True,
                    "comment": "Выходной",
                    "lessons": {},
                }
            )
            continue

        lessons = day.find_all("div", class_="dnevnik-lesson")
        lessonsDict = {}
        if lessons:
            for lesson in lessons:
                lessonNumber = lesson.find("div", class_="dnevnik-lesson__number")
                if lessonNumber:
                    lessonNumber = (
                        lessonNumber.contents[0].replace("\n", "").strip()[:-1]
                    )
                if lessonNumber == "":
                    continue

                lessonName = lesson.find(
                    "span", class_="js-rt_licey-dnevnik-subject"
                ).contents[0]

                lessonHomeTask = lesson.find("div", class_="dnevnik-lesson__task")
                if lessonHomeTask:
                    lessonHomeTask = (
                        lessonHomeTask.contents[2].replace("\n", "").strip()
                    )

                lessonMark = lesson.find("div", class_="dnevnik-mark")
                if lessonMark:
                    lessonMark = lessonMark.contents[1].attrs["value"]

                lessonsDict.update(
                    [
                        (
                            lessonNumber,
                            {
                                "name": lessonName,
                                "hometask": lessonHomeTask,
                                "mark": lessonMark,
                            },
                        )
                    ]
                )
            info.update(
                {
                    str(i): {
                        "day": week,
                        "date": date,
                        "isEmpty": False,
                        "comment": "Выходной",
                        "lessons": lessonsDict,
                    }
                }
            )
            i += 1

    return info


def getGradeList(subdomain, session: Session, quarter=1):
    if quarter == 'latest':
        url = f"https://{subdomain}.eljur.ru/journal-student-grades-action/u.0/"
    else:
        url = f"https://{subdomain}.eljur.ru/journal-student-grades-action/u.0/sp.{roman[quarter]}+четверть"

    soup = createSoup(subdomain, url, session)
    if "error" in soup:
        return soup

    info = {"themes": {}}

    if soup.find("div", class_="page-empty"):
        return {"themes": None}

    for column in soup.find_all("div", class_="cells_marks"):
        cells = column.find_all("div", class_="cell")
        for cell in cells:
            content = cell.contents
            if "id" not in cell.attrs.keys():
                continue
            if content[1].contents[0] == "\xa0":
                mark = {"mark": None, "date": None, "isMark": False}
            elif (
                cell.find("sub")
                and cell.find("div", class_="cell-corner-4").contents != []
            ):
                mark = {
                    "mark": cell.find("div", class_="cell-corner-4").contents[0] + cell.find("sub").contents[0],
                    "date": cell["mark_date"],
                    "isMark": False,
                }
                mark["mark"] = mark["mark"].replace("✕", "x")
            elif cell.find("sub"):
                mark = {
                    "mark": cell.find("div", class_="cell-data").contents[0] + cell.find("sub").contents[0],
                    "date": cell["mark_date"],
                    "isMark": True,
                }
                mark["mark"] = mark["mark"].replace("✕", "x")
            else:
                mark = {
                    "mark": content[1].contents[0],
                    "date": cell["mark_date"],
                    "isMark": True if content[1].contents[0] != "Н" else False,
                }
            if cell["name"] not in info["themes"].keys():
                info["themes"].update({cell["name"]: [mark]})
            else:
                info["themes"][cell["name"]].append(mark)
    return info
