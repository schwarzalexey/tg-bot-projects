from PIL import Image, ImageDraw, ImageFont

global semibold_font
global regular_font

semibold_font = ImageFont.truetype("fonts/Inter-SemiBold.ttf", 18)
regular_font = ImageFont.truetype("fonts/Inter-Regular.ttf", 14)


def toFixed(numObj, digits=0):
    return f"{numObj:.{digits}f}"


def drawJournal(data, user_id):
    max_len_lesson = max(
        [len(f"{x}. {y['name']}") * 7 for x, y in data["lessons"].items()]
    )
    max_len_hw = max(
        [
            len(
                data["lessons"][str(i)]["hometask"]
                if data["lessons"][str(i)]["hometask"] is not None
                else ""
            )
            * 7
            for i in range(1, (len(data["lessons"]) + 1))
        ]
    )
    max_len = max_len_hw + max_len_lesson + 120
    image = Image.new(
        "RGB", (max_len, 50 * (len(data["lessons"]) + 1)), (255, 255, 255)
    )
    draw = ImageDraw.Draw(image)
    draw.text(
        (10, 14), f"{data['day']}, {data['date']}", fill=(0, 0, 0), font=semibold_font
    )
    ht_logo = Image.open("fonts/ht.png").convert("RGBA").resize((20, 20))
    for x, y in data["lessons"].items():
        x = x if x != "" else "-1"
        if int(x) % 2:
            draw.rectangle(
                [(0, 50 * int(x)), (max_len, 50 * int(x) + 50)],
                fill=(230, 230, 230),
                outline=(230, 230, 230),
            )
        draw.text(
            (10, 16 + 50 * int(x)),
            f"{x}. {y['name']}",
            fill=(0, 0, 0),
            font=regular_font,
        )
        image.paste(ht_logo, (max_len_lesson + 25, 15 + 50 * int(x)), ht_logo)
        if y["hometask"] is None:
            y["hometask"] = "Нет"
        draw.text(
            (max_len_lesson + 50, 16 + 50 * int(x)),
            y["hometask"],
            fill=(0, 0, 0),
            font=regular_font,
        )
        if y["mark"] is not None:
            mark = y["mark"] if y["mark"] != "" else "Н"
            draw.rounded_rectangle(
                [(max_len - 45, 10 + 50 * int(x)), (max_len - 15, 40 + 50 * int(x))],
                radius=10,
                outline=(150, 150, 150),
                width=1,
            )
            draw.text(
                (max_len_lesson + max_len_hw + 85, 16 + 50 * int(x)),
                mark,
                fill=(0, 0, 0),
                font=regular_font,
            )
    image.save(f"journalLists/day_{user_id}.jpg", quality=95)


def drawGradeList(data, user_id):
    if data["themes"] is None:
        return False
    data = data["themes"]

    max_lesson_length = (
        int(regular_font.getlength(max(list(data.keys()), key=lambda x: len(x)))) + 15
    )
    max_x = (max_lesson_length + 25 * len(list(data.values())[0]) + int(semibold_font.getlength("Средняя"))) + 25
    image = Image.new("RGB", (max_x, 25 * len(data) + 50), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        [(0, 0), (max_x, 50)],
        fill=(230, 230, 230),
        outline=(230, 230, 230),
    )
    draw.text((10, 20), "Предмет", fill=(0, 0, 0), font=semibold_font)
    draw.text(
        (max_x - 10 - int(semibold_font.getlength("Средняя")), 20),
        "Средняя",
        fill=(0, 0, 0),
        font=semibold_font,
    )

    multiplied_font = ImageFont.truetype("fonts/Inter-Regular.ttf", 10)

    avg_data = {}

    for lesson, marks in data.items():
        avg_sum, count = 0, 0
        for mark in marks:
            if not mark["isMark"]:
                continue
            multiplier = 1
            if "x" in mark["mark"]:
                multiplier = int(mark["mark"].split("x")[1])
            avg_sum += int(mark["mark"].split("x")[0]) * multiplier
            count += multiplier
        result = str(toFixed(avg_sum / count, 2)) if count else ""
        avg_data.update({lesson: result})

    i = 0
    for lesson, marks in data.items():
        y = 25 * i + 50
        if i % 2:
            draw.rectangle(
                [(0, y), (max_x, y + 25)],
                fill=(230, 230, 230),
                outline=(230, 230, 230),
            )
        draw.text((10, 4 + y), lesson, fill=(0, 0, 0), font=regular_font)
        draw.line([(0, y), (max_x, y)], fill=(150, 150, 150))

        j = 0
        for mark in marks:
            x = max_lesson_length + 25 * j + 5
            draw.line([(x, 0), (x, (25 * (len(data)) + 5) + 50)], fill=(150, 150, 150))
            if mark["mark"] is None:
                j += 1
                continue
            if "x" not in mark["mark"]:
                draw.text(
                    (max_lesson_length + 25 * j + 13, 4 + y),
                    mark["mark"],
                    fill=(0, 0, 0),
                    font=regular_font,
                )
            else:
                draw.text(
                    (max_lesson_length + 25 * j + 9, 7 + y),
                    mark["mark"],
                    fill=(0, 0, 0) if mark["mark"].split("x")[0] == "Н" else (70, 70, 255),
                    font=multiplied_font,
                )
            j += 1

        x = max_lesson_length + 25 * j + 5

        draw.line([(x, 0), (x, (25 * (len(data)) + 5) + 50)], fill=(150, 150, 150))
        i += 1

    i = 0
    for lesson, mark in avg_data.items():
        length = int(regular_font.getlength(mark))
        draw.text(
            (
                max_x - length - (20 + int(semibold_font.getlength("Средняя")) - length) // 2,
                4 + 25 * i + 50,
            ),
            mark,
            fill=(0, 0, 0),
            font=regular_font,
        )
        i += 1

    image.save(f"gradeLists_out/gl_{user_id}.jpg", quality=95)
