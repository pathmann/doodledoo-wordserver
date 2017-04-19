from configparser import ConfigParser

import pymysql

from googletrans import Translator


def translate(lang, srclang, sources, cursor, translator):
    if lang["issource"] == 1:
        for src in sources:
            cursor.execute("INSERT INTO translations (source, language, txt) "
                           "VALUES (%s, %s, %s)", (src["id"], lang["id"],
                                                   src["txt"]))
    else:
        srctxts = list(map(lambda x: x["txt"], sources))
        trans = translator.translate(srctxts, src=srclang["locale"],
                                     dest=lang["locale"])

        for i, t in enumerate(trans):
            cursor.execute("INSERT INTO translations (source, language, txt) "
                           "VALUES (%s, %s, %s)", (sources[i]["id"],
                                                   lang["id"], t.text))

    cursor.execute("UPDATE languages SET isready=1 WHERE id=%s", (lang["id"]))


def main():
    config = ConfigParser()
    config.read('doodledoo.ini')
    cfg = config["doodledoo"]

    con = pymysql.connect(host=cfg['dbhost'], user=cfg['dbuser'],
                          password=cfg['dbpassword'], db=cfg['dbname'],
                          charset='utf8mb4',
                          cursorclass=pymysql.cursors.DictCursor)

    cursor = con.cursor()

    cursor.execute("SELECT id, locale FROM languages WHERE issource=1")
    sourcelang = cursor.fetchall()

    if len(sourcelang) != 1:
        raise Exception("Multiple source languages found")

    sourcelang = sourcelang[0]

    cursor.execute("SELECT id, txt FROM sources")
    sources = cursor.fetchall()

    cursor.execute("SELECT id, locale, issource FROM languages WHERE "
                   "isready=0")
    langs = cursor.fetchall()

    trans = Translator()

    for l in langs:
        translate(l, sourcelang, sources, cursor, trans)

    con.commit()


if __name__ == "__main__":
    main()
