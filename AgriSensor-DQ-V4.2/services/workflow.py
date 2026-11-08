"""Persistent datasets and reproducible experiment records."""
from pathlib import Path
import json, sqlite3, hashlib, zipfile, io, re
from datetime import datetime, timezone
import pandas as pd
from engine import normalize
from services.storage import DB, init, CLOUD
BASE=DB.parent

def setup():
    if CLOUD:return
    init()
    (BASE/'datasets').mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS datasets (id TEXT PRIMARY KEY, name TEXT, source TEXT, created TEXT, rows INTEGER, nodes INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT, dataset_id TEXT, method TEXT, parameters TEXT, metrics TEXT)")

def save_dataset(df,name,source):
    if CLOUD: raise RuntimeError('公网模式不保存共享数据，请下载CSV备份')
    setup();d=normalize(df)
    digest=hashlib.sha256(d.to_csv(index=False).encode('utf-8')).hexdigest()[:16]
    path=BASE/'datasets'/f'{digest}.csv'
    d.to_csv(path,index=False,encoding='utf-8-sig')
    with sqlite3.connect(DB) as c:
        c.execute('INSERT OR REPLACE INTO datasets VALUES (?,?,?,?,?,?)',(digest,str(name),str(source),datetime.now(timezone.utc).isoformat(),len(d),int(d.node_id.nunique())))
    return digest

def list_datasets():
    if CLOUD:return pd.DataFrame(columns=['id','name','source','created','rows','nodes'])
    setup()
    with sqlite3.connect(DB) as c:return pd.read_sql_query('SELECT * FROM datasets ORDER BY created DESC',c)

def load_dataset(dataset_id):
    if CLOUD: raise RuntimeError('公网模式不支持共享数据恢复')
    setup();path=BASE/'datasets'/f'{dataset_id}.csv'
    if not path.is_file():raise FileNotFoundError('数据集文件不存在')
    return normalize(pd.read_csv(path))

def save_run(dataset_id,method,parameters,metrics):
    if CLOUD: raise RuntimeError('公网模式不保存共享实验，请下载实验结果')
    setup()
    with sqlite3.connect(DB) as c:
        cur=c.execute('INSERT INTO runs(created,dataset_id,method,parameters,metrics) VALUES(?,?,?,?,?)',(datetime.now(timezone.utc).isoformat(),dataset_id,method,json.dumps(parameters,ensure_ascii=False),json.dumps(metrics,ensure_ascii=False)))
        return cur.lastrowid

def list_runs():
    if CLOUD:return pd.DataFrame(columns=['id','created','dataset_id','method','parameters','metrics'])
    setup()
    with sqlite3.connect(DB) as c:return pd.read_sql_query('SELECT * FROM runs ORDER BY id DESC',c)

# Persistent active dataset selection (independent of Streamlit session state).
def set_active_dataset(dataset_id):
    if CLOUD: return
    setup()
    # Verify the dataset can actually be restored before updating the pointer.
    load_dataset(dataset_id)
    with sqlite3.connect(DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        c.execute('INSERT OR REPLACE INTO app_state(key,value) VALUES (?,?)', ('active_dataset_id', str(dataset_id)))


def get_active_dataset():
    if CLOUD:return None
    setup()
    with sqlite3.connect(DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        row = c.execute('SELECT value FROM app_state WHERE key=?', ('active_dataset_id',)).fetchone()
    return row[0] if row else None


def clear_active_dataset():
    if CLOUD: return
    setup()
    with sqlite3.connect(DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        c.execute('DELETE FROM app_state WHERE key=?', ('active_dataset_id',))


def delete_dataset(dataset_id):
    """Remove one local catalog item and its dataset file."""
    if CLOUD: raise RuntimeError('公网演示不支持持久化删除')
    setup()
    with sqlite3.connect(DB) as c:
        row=c.execute('SELECT id FROM datasets WHERE id=?',(dataset_id,)).fetchone()
        if not row: raise KeyError('未找到数据集')
        c.execute('DELETE FROM datasets WHERE id=?',(dataset_id,))
        c.execute('DELETE FROM app_state WHERE key=? AND value=?',('active_dataset_id',dataset_id)) if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_state'").fetchone() else None
    (BASE/'datasets'/f'{dataset_id}.csv').unlink(missing_ok=True)


def export_backup():
    """Portable ZIP of local datasets and metadata; no secrets or database file."""
    if CLOUD: raise RuntimeError('公网模式请下载当前数据CSV')
    catalog=list_datasets()
    manifest={'format':'agrisensor-datasets-v1','datasets':[]}
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for row in catalog.to_dict('records'):
            did=row['id']
            path=BASE/'datasets'/f'{did}.csv'
            if not path.exists(): continue
            z.write(path,f'datasets/{did}.csv')
            manifest['datasets'].append(row)
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    return out.getvalue()


def import_backup(raw):
    """Restore a ZIP created by export_backup, validating paths and content."""
    if CLOUD: raise RuntimeError('公网模式不支持恢复到共享磁盘')
    if len(raw)>40*1024*1024:raise ValueError('备份ZIP超过40MB')
    setup();count=0
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries=z.namelist()
        if len(entries)>205:raise ValueError('备份包含过多文件')
        manifest=json.loads(z.read('manifest.json'))
        if manifest.get('format')!='agrisensor-datasets-v1':raise ValueError('备份格式不支持')
        datasets=manifest.get('datasets',[])
        if len(datasets)>200:raise ValueError('最多恢复200个数据集')
        for row in datasets:
            did=str(row['id'])
            if not re.fullmatch(r'[0-9a-f]{16}',did):raise ValueError('无效数据集标识')
            filename=f'datasets/{did}.csv'
            info=z.getinfo(filename)
            if info.file_size>25*1024*1024:raise ValueError('单个数据集过大')
            raw_csv=z.read(filename)
            d=normalize(pd.read_csv(io.BytesIO(raw_csv)))
            if d.empty or len(d)>100000:raise ValueError('备份数据集不符合记录数限制')
            actual=hashlib.sha256(raw_csv.decode('utf-8-sig').encode('utf-8')).hexdigest()[:16]
            if actual!=did:raise ValueError('备份内容校验失败：'+did)
            (BASE/'datasets'/f'{did}.csv').write_bytes(raw_csv)
            with sqlite3.connect(DB) as c:
                c.execute('INSERT OR REPLACE INTO datasets VALUES (?,?,?,?,?,?)',
                    (did,str(row.get('name','导入数据集'))[:100],str(row.get('source','备份恢复'))[:200],
                     str(row.get('created',datetime.now(timezone.utc).isoformat())),len(d),int(d.node_id.nunique())))
            count+=1
    return count
