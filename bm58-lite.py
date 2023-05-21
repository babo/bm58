#!/usr/bin/env python3
#
# Read measurements from Beurer BM-58 blood pressure monitor and save results to sqlite
#
import argparse
import datetime
import sqlite3

import serial


def convert_reading(m):
    when = datetime.datetime(2000 + m[8], m[4], m[5], m[6], m[7])
    systolic = 25 + m[1]
    diastolic = 25 + m[2]
    pulse = m[3]
    return (when, systolic, diastolic, pulse)


def save_measurements(measurements, dbname):
    with sqlite3.connect(dbname) as db:
        all_in = [convert_reading(m) for m in measurements]
        cur = db.cursor().execute(
            "CREATE TABLE IF NOT EXISTS bp (ts NOT NULL, sys NOT NULL, dia NOT NULL, pulse NOT NULL, PRIMARY KEY (ts, sys, dia) ON CONFLICT IGNORE);"
        )
        if all_in:
            cur = cur.executemany("INSERT OR IGNORE INTO bp VALUES(?, ?, ?, ?)", all_in)
            db.commit()

        cur = cur.execute("SELECT COUNT(*) FROM bp;")
        count = cur.fetchone()[0]
        print(f"Total number of records in the database: {count}")

        if count:
            cur = cur.execute("""SELECT AVG(sys), AVG(dia), AVG(pulse) FROM (SELECT sys, dia, pulse FROM bp ORDER BY ts DESC LIMIT 2);""")
            a = cur.fetchone()
            print(f"Average values from the last 2 measurement\n    Sys: {a[0]:0.1f} Dia: {a[1]:0.1f} Pulse: {a[2]:0.1f}")


def read_measurements(port):
    with serial.Serial(
        port=port,
        baudrate=4800,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0.5,
    ) as ser:
        a = ser.write([0xAA])
        assert a == 1, "Failed to write initial message"
        b = ser.read(size=1)
        assert b == b"\x55", "Failed to connect"
        ser.write([0xA4])
        print(ser.readline().decode("utf8"))

        ser.write([0xA2])
        num_records = ord(ser.read(size=1))
        print(f"Available records: {num_records}")

        measurements = []
        for i in range(num_records):
            a = ser.write([0xA3, 0x01 + i])
            response = ser.read(9)
            if len(response) == 9:
                measurements.append(response)

        return measurements


def display(measurements):
    measurements = list(enumerate(measurements, 1))
    measurements.reverse()
    for i, m in measurements:
        print(f"{i:2} - 20{m[8]:02}-{m[4]:02}-{m[5]:02} {m[6]:02}:{m[7]:02} Sys={25 + m[1]:3} Dia={25+m[2]:3} Pulse={m[3]}")


def get_args():
    desc = """Beurer BM-58 blood pressure readings to sqlite"""
    parser = argparse.ArgumentParser(add_help=True, description=desc)
    parser.add_argument("-p", "--port", dest="port", help="USB device name", default="/dev/cu.usbserial-1140")
    parser.add_argument("-d", "--db", dest="dbname", help="Sqlite3 database name", default="bm58.sqlite")
    return parser.parse_args()


def main():
    args = get_args()
    measurements = read_measurements(args.port)
    display(measurements)
    save_measurements(measurements, args.dbname)


if __name__ == "__main__":
    main()
