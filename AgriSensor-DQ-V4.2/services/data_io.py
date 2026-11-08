from io import BytesIO
import pandas as pd
from engine import normalize

def read_upload(file):
 raw=file.getvalue()
 if len(raw)>12*1024*1024:raise ValueError('文件超过12MB，请先筛选或拆分数据')
 name=file.name.lower()
 if name.endswith('.csv'):
  last=None
  for enc in ('utf-8-sig','gb18030'):
   try:return _validate(normalize(pd.read_csv(BytesIO(raw),encoding=enc)))
   except UnicodeDecodeError as e:last=e
  raise ValueError(f'CSV编码错误: {last}')
 if name.endswith(('.xlsx','.xls')):return _validate(normalize(pd.read_excel(BytesIO(raw))))
 raise ValueError('仅支持 CSV / XLSX / XLS')

def csv_bytes(df):return df.to_csv(index=False).encode('utf-8-sig')


def _validate(df):
 if len(df)>100000:raise ValueError('最多导入100000行，请先分批处理')
 if df.empty:raise ValueError('数据文件为空或时间戳无效')
 return df
