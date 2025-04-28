from requests import Session
from info import createSoup
import re


def checkErr(answer, url):
    if not answer["postcode"].status_code:
        return {
            "error": {
                "code": -102,
                "msg": f"Возникла ошибка при отправке запроса на {url}",
            },
            "result": False,
        }
    if answer["postcode"].status_code >= 400:
        return {
            "error": {
                "code": -102,
                "msg": f"Возникла ошибка {answer['postcode']} при отправке запроса на {url}",
            },
            "result": False,
        }
    else:
        return {"answer": "Ok", "result": True}


def checkSubdomain(subdomain):
    session = Session()
    if not re.search(r"[a-zA-Z0-9]+", subdomain):
        return False
    url = f"https://{subdomain}.eljur.ru/"
    soup = createSoup(subdomain, url, session)
    if soup.find_all(["p"]):
        return False
    return True


def auth(subdomain, data):
    if not checkSubdomain(subdomain):
        return {
            "result": False,
            "session": None,
            "error_msg": "Неверный домен школы"
        }
    session = Session()
    url = f"https://{subdomain}.eljur.ru/ajaxauthorize"
    answer = session.post(url=url, data=data)
    data = {"session": session, "postcode": answer}
    error = checkErr(data, url)
    if not error["result"]:
        return {
            "result": False,
            "session": None,
            "error_msg": error["error"]["msg"]
        }
    else:
        return {
            "result": True,
            "session": session,
        }
