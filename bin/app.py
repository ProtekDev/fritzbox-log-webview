from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, timedelta
import subprocess
import threading
import time
import os

# Set the working directory to the directory of the current script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from variables import Var


app = Flask(__name__)
# Variable to store the last and next update timestamps
last_update = None
next_update = None

def update_database():
    global last_update, next_update
    last_update = datetime.now(Var.timezone)
    next_update = last_update + timedelta(hours=1)
    subprocess.Popen(['python', 'get_log.py'])

def start_automatic_updates():
    """
    Hourly background job for automatic database updates.
    This function runs in parallel with Flask.
    """
    while True:
        global last_update, next_update
        if last_update == None:
            update_database() # Initial update
        else:
            if next_update <= datetime.now(Var.timezone):    
                update_database()
        time.sleep(10)  # Delay for 10 seconds

def get_logs(time_filter='all', type_filter='all', sort_column='date', sort_order='DESC', limit=1000):
    conn = sqlite3.connect(Var.db_name)
    cursor = conn.cursor()

    query = '''SELECT date, time, type, ref, message FROM logs WHERE 1=1'''
    params = []

    if time_filter == 'week':
        week_ago = datetime.now(Var.timezone) - timedelta(weeks=1)
        query += ' AND date >= ?'
        params.append(week_ago.strftime('%Y-%m-%d'))
    elif time_filter == 'month':
        month_ago = datetime.now(Var.timezone) - timedelta(days=30)
        query += ' AND date >= ?'
        params.append(month_ago.strftime('%Y-%m-%d'))

    if type_filter != 'all':
        query += ' AND "type" = ?'
        params.append(type_filter)

    # Sort by date and time
    query += f' ORDER BY date {sort_order}, time {sort_order} LIMIT {limit}'

    cursor.execute(query, params)
    logs = cursor.fetchall()
    conn.close()
    
    return logs

@app.route('/run_script', methods=['POST'])
def run_script():
    print("POST request received at /run_script")

    try:
        update_database()
        time.sleep(5)
        return redirect(url_for('index'))
    except Exception as e:
        return render_template('index.html', message=f"Fehler beim Ausführen des Skripts: {str(e)}")


@app.route('/restart_fritzbox', methods=['POST'])
def restart_fritzbox():
    update_database()
    
    conn = sqlite3.connect(Var.db_name)
    cursor = conn.cursor()

    current_time = datetime.now(Var.timezone).strftime('%H:%M:%S')  # HH:MM:SS
    current_date = datetime.now(Var.timezone).strftime('%d.%m.%y')  # Format: tt.mm.yy

    cursor.execute('''INSERT INTO logs (date, time, type, ref, message)
					  VALUES (?, ?, ?, ?, ?)''', (current_date, current_time, 'net', 'script', 'Fritzbox wird neugestartet.'))

    conn.commit()
    conn.close()

    time.sleep(5)
    subprocess.Popen(['python', 'restart_router.py'])

    return redirect(url_for('index'))

@app.route('/', methods=['GET'])
def index():
    time_filter = request.args.get('time_filter', 'all')
    type_filter = request.args.get('type_filter', 'all')
    sort_column = request.args.get('sort_column', 'date')
    sort_order = request.args.get('sort_order', 'DESC')

    logs = get_logs(time_filter, type_filter, sort_column, sort_order)

    # Calculate the countdown for the next automatic update
    global next_update
    countdown = (next_update - datetime.now(Var.timezone)).total_seconds() if next_update else 0
    next_update_time = next_update.strftime('%d.%m.%Y %H:%M:%S') if next_update else "Keine Aktualisierung geplant"

    return render_template('index.html', logs=logs, time_filter=time_filter,
                           type_filter=type_filter, sort_column=sort_column,
                           sort_order=sort_order, countdown=countdown,
                           next_update_time=next_update_time)

if __name__ == '__main__':
    if not os.path.exists('data'):
        os.makedirs('data')

    # Start the automatic update thread
    threading.Thread(target=start_automatic_updates, daemon=True).start()
    app.run(host='0.0.0.0', port=5588)