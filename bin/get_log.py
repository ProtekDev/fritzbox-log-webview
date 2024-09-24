import requests
import hashlib
from lxml import etree
from dotenv import load_dotenv
from datetime import datetime, timedelta
import sqlite3
import os
import sys

from variables import Var

if not os.path.exists('data'):
   os.makedirs('data')

SID_FILE = 'data/sid.txt'

def calculate_md5(challenge, password):
    challenge_b = f"{challenge}-{password}".encode('utf-16le')
    md5_hash = hashlib.md5(challenge_b).hexdigest()
    return f"{challenge}-{md5_hash}"

def save_sid(sid):
    with open(SID_FILE, 'w') as file:
        file.write(sid)

def load_sid():
    if os.path.exists(SID_FILE):
        with open(SID_FILE, 'r') as file:
            return file.read().strip()
    return None

def get_sid():
    sid = load_sid()    
    if sid:
        return sid  # Use the stored SID
    return login() # New login if no SID is found

def login():
    # Login process for the FritzBox
    response = requests.get(f"{Var.baseurl}/login_sid.lua")
    xml_root = etree.fromstring(response.content)
    
    sid = xml_root.findtext("SID")
    if sid != "0000000000000000":
        save_sid(sid)
        return sid  # Already authenticated or no authentication required

    challenge = xml_root.findtext("Challenge")
    response_hash = calculate_md5(challenge, Var.router_password)
    
    login_data = {
        "username": Var.router_user,
        "response": response_hash
    }
    login_response = requests.get(f"{Var.baseurl}/login_sid.lua", params=login_data)
    login_root = etree.fromstring(login_response.content)
    sid = login_root.findtext("SID")
    
    if sid == "0000000000000000":
        raise Exception("Login fehlgeschlagen. Bitte Zugangsdaten überprüfen.")
    
    save_sid(sid)
    
    return sid

def setup_database():
    conn = sqlite3.connect(Var.db_name)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        time TEXT,
                        type TEXT,
                        ref INTEGER,
                        message TEXT
                      )''')

    conn.commit()
    conn.close()

def log_exists(date, time, message):
    """
    This Functions search for duplicates.
    Even if the Time is in a specific range (+- 1 second)
    """
    current_time = datetime.strptime(f"{date} {time}", "%d.%m.%y %H:%M:%S")

    conn = sqlite3.connect(Var.db_name)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT time FROM logs 
        WHERE date = ? AND message = ?
    ''', (date, message))
    
    existing_times = cursor.fetchall()
    conn.close()

    # Check if any existing times are within ±1 second
    for (existing_time,) in existing_times:
        existing_datetime = datetime.strptime(f"{date} {existing_time}", "%d.%m.%y %H:%M:%S")
        if abs((existing_datetime - current_time).total_seconds()) <= 1:
            return True  # Duplicate found
        
    return False  # No duplicates found

def save_logs_to_db(log_entries):
    conn = sqlite3.connect(Var.db_name)
    cursor = conn.cursor()

    counter = 0
    for entry in log_entries:        
        date = entry.get('date')
        time = entry.get('time')
        type = entry.get('group')
        ref = entry.get('id')
        message = entry.get('msg')

        # Skip ignored entries
        ignore_found = False
        for id in Var.ignore_refs:
            if ref == id:
                ignore_found = True
                break
        if ignore_found:
            continue # ignore id found, skip outer for
        
        if log_exists(date, time, message):
            continue  # Duplicate found, skip

        cursor.execute('''INSERT INTO logs (date, time, type, ref, message)
                          VALUES (?, ?, ?, ?, ?)''', (date, time, type, ref, message))
        counter += 1

    conn.commit()
    conn.close()
    print(f"{counter} Log-Einträge wurden erfolgreich in die Datenbank gespeichert.")

def get_fritzbox_logs():
    sid = get_sid()
    
    # Retrieve event logs from the FritzBox with the SID
    log_data = {
        "xhr": "1",
        "lang": "de",
        "page": "log",
        "sid": sid,
        "filter": "all"  # Explicitly set filter to "all" to get all logs
    }
    response = requests.post(f"{Var.baseurl}/data.lua", data=log_data)

    # Re-login if the SID has expired
    if "0000000000000000" in response.text:
        print("SID abgelaufen, melde mich neu an...")
        sid = login()  # Re-login
        log_data["sid"] = sid  # Insert new SID
        response = requests.post(f"{Var.baseurl}/data.lua", data=log_data)

    log_entries = response.json().get("data", {}).get("log", [])
    
    if log_entries:
        save_logs_to_db(log_entries)

        if __debug__: # Print results when actively developing
            for entry in log_entries:        
                date = entry.get('date')
                time = entry.get('time')
                type = entry.get('group')
                ref = entry.get('id')
                message = entry.get('msg')
                print(date, time, type, ref, message)
    else:
        print("Warnung: Keine Log-Einträge gefunden.")

try:
    setup_database()
    get_fritzbox_logs()
except Exception as e:
    print(f"Fehler: {str(e)}")