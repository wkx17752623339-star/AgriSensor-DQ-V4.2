from pathlib import Path
import sqlite3
import pandas as pd
BASE=Path(__file__).resolve().parents[1]
import os
DB=BASE/'data'/'agrisensor.db'
CLOUD=os.getenv('AGRISENSOR_CLOUD_DEMO','1')=='1'
def init():
 if CLOUD:return
 DB.parent.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(DB) as c:
  c.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, node_id TEXT, category TEXT, details TEXT)')
def log(node,category,details):
 if CLOUD:return
 init()
 with sqlite3.connect(DB) as c:c.execute("INSERT INTO events(time,node_id,category,details) VALUES(datetime('now'),?,?,?)",(node,category,details))
def events():
 if CLOUD:return pd.DataFrame(columns=['time','node_id','category','details'])
 init()
 with sqlite3.connect(DB) as c:return pd.read_sql_query('SELECT time,node_id,category,details FROM events ORDER BY id DESC LIMIT 200',c)
