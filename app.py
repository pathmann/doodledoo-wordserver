from flask import Flask, jsonify, request
from flaskext.mysql import MySQL
import pymysql

from configparser import ConfigParser

import datetime


config = ConfigParser()
config.read('doodledoo.ini')

app = Flask(__name__)
app.config['MYSQL_DATABASE_HOST'] = config.get('doodledoo', 'dbhost')
app.config['MYSQL_DATABASE_USER'] = config.get('doodledoo', 'dbuser')
app.config['MYSQL_DATABASE_PASSWORD'] = config.get('doodledoo', 'dbpassword')
app.config['MYSQL_DATABASE_DB'] = config.get('doodledoo', 'dbname')

MAXFETCH = config.getint('doodledoo', 'maxfetch')
MINCOMPLAIN = config.getint('doodledoo', 'mincomplain')
MAXUSERCOMPLAIN = config.getint('doodledoo', 'maxusercomplain')

mysql = MySQL()
mysql.init_app(app)


def fetchOneDict(cursor):
    data = cursor.fetchone()
    if data is None:
        return None

    desc = cursor.description

    d = {}

    for (name, value) in zip(desc, data):
        d[name[0]] = value

    return d


@app.route('/check')
def check():
    try:
        mysql.connect()
    except:
        return jsonify({"error": "internal server error"})

    return jsonify({"error": None})


@app.route('/<target>/complain')
def complain(target):
    if type(target) != str or len(target) != 2:
        return jsonify({"error": "no locale given"})

    con = mysql.connect()
    cursor = con.cursor()

    sender = request.remote_addr

    cursor.execute("SELECT id FROM complaints WHERE sender=%s", (sender))
    cs = cursor.fetchall()
    if cs is not None and len(cs) >= MAXUSERCOMPLAIN:
        return jsonify({"error": "maximum complaints exceeded"})

    word = request.args.get('word')
    reason = request.args.get('reason')

    if word is None or reason is None:
        return jsonify({"error": "invalid parameters"})

    cursor.execute("SELECT id from languages WHERE locale=%s AND isready=1",
                   (target))
    language = fetchOneDict(cursor)

    if language is None:
        return jsonify({"error": "locale not found"})

    cursor.execute("SELECT id FROM translations WHERE language=%s AND "
                   "txt=%s", (language["id"], word))
    trans = fetchOneDict(cursor)

    if not trans:
        return jsonify({"error": "word not found"})

    try:
        cursor.execute("INSERT INTO complaints (translation, reason, sender, "
                       "time) VALUES (%s, %s, %s, %s)", (trans["id"], reason,
                                                         sender, datetime.
                                                         datetime.now()))

        con.commit()
    except pymysql.err.IntegrityError:
        pass

    return jsonify({"error": None})


@app.route('/<target>/<int:count>')
def index(target, count):
    if type(target) != str or len(target) != 2:
        return jsonify({"error": "no locale given"})

    con = mysql.connect()
    cursor = con.cursor()

    cursor.execute("SELECT id, lastseen from sendercache WHERE addr=%s",
                   (request.remote_addr))
    sender = fetchOneDict(cursor)

    now = datetime.datetime.now()
    if sender is None:
        cursor.execute("INSERT INTO sendercache (addr, lastseen) VALUES "
                       "(%s, %s)", (request.remote_addr, now))
        con.commit()
    else:
        if sender["lastseen"] + datetime.timedelta(seconds=10) > now:
            return jsonify({"error": "requests in timedelta exceeded"})
        else:
            cursor.execute("UPDATE sendercache SET lastseen = %s WHERE id=%s",
                           (now, sender["id"]))
            con.commit()

    cursor.execute("SELECT id, issource, isready from languages "
                   "WHERE locale=%s", (target))
    language = fetchOneDict(cursor)

    if language is None:
        cursor.execute("INSERT INTO languages (locale, issource, isready) "
                       "VALUES (%s, 0, 0)", (target))
        con.commit()

        return jsonify({"error": "language has been requested, try again "
                        "in a few minutes"})
    elif language["isready"] == 0:
        return jsonify({"error": "language has been requested, try again "
                        "in a few minutes"})
    else:
        if count > MAXFETCH:
            count = MAXFETCH

        cursor.execute("SELECT txt FROM translations WHERE language=%s "
                       "AND active=1 ORDER BY RAND() LIMIT %s",
                       (language["id"], count))
        data = cursor.fetchall()

        if data is None:
            return jsonify({"error": "internal server error"})
        else:
            return jsonify({"error": None, "words": data})


if __name__ == "__main__":
    app.run(host='0.0.0.0')
