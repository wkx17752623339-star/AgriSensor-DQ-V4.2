"""Sensor quality analytics; deterministic demo and reproducible evaluations."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix

FIELDS=['timestamp','node_id','temperature','humidity','rssi','fault_type','is_fault']

def demo_data(nodes=8, days=3, seed=42, freq='15min'):
    rng=np.random.default_rng(seed)
    ts=pd.date_range('2026-10-01',periods=int(days*24*60/15),freq=freq)
    rows=[]
    for j in range(nodes):
        n=len(ts); hour=np.arange(n)/4
        temp=24+4*np.sin(2*np.pi*(hour-6)/24)+rng.normal(0,.35,n)+j*.08
        hum=68-12*np.sin(2*np.pi*(hour-6)/24)+rng.normal(0,1.4,n)
        rssi=-75-j*1.5+rng.normal(0,3,n)
        fault=np.array(['normal']*n,dtype=object)
        available=np.arange(10,n-10)
        if len(available)>30:
            spike=rng.choice(available,size=max(2,n//55),replace=False)
            temp[spike]+=rng.choice([-1,1],len(spike))*rng.uniform(9,16,len(spike));fault[spike]='spike'
            a=int(n*.36);b=min(n,a+max(6,n//16));temp[a:b]+=7;fault[a:b]='bias'
            a=int(n*.65);b=min(n,a+max(12,n//9));temp[a:b]+=np.linspace(0,8,b-a);fault[a:b]='drift'
            a=int(n*.83);b=min(n,a+max(4,n//24));temp[a:b]=np.nan;hum[a:b]=np.nan;fault[a:b]='missing'
        for k,t in enumerate(ts):
            rows.append((t,f'NODE-{j+1:02d}',temp[k],hum[k],rssi[k],fault[k],int(fault[k]!='normal')))
    return pd.DataFrame(rows,columns=FIELDS)

def normalize(df):
    df=df.copy(); aliases={'time':'timestamp','datetime':'timestamp','date':'timestamp','node':'node_id','sensor_id':'node_id','temp':'temperature','rh':'humidity','RSSI':'rssi'}
    df=df.rename(columns={k:v for k,v in aliases.items() if k in df.columns and v not in df.columns})
    required=['timestamp','node_id','temperature','humidity']
    absent=[c for c in required if c not in df.columns]
    if absent: raise ValueError('缺少必需列: '+', '.join(absent))
    df['timestamp']=pd.to_datetime(df['timestamp'],errors='coerce');df=df.dropna(subset=['timestamp','node_id'])
    for c in ['temperature','humidity','rssi']:
        if c not in df:df[c]=np.nan
        df[c]=pd.to_numeric(df[c],errors='coerce')
    if 'fault_type' not in df:df['fault_type']='unknown'
    if 'is_fault' not in df:df['is_fault']=np.nan
    df['is_fault']=pd.to_numeric(df['is_fault'],errors='coerce')
    return df.sort_values(['node_id','timestamp']).reset_index(drop=True)

def adaptive_profile(g, window=11, threshold=3.0, slot_hours=2, min_slot_samples=8):
    """Causal, node-local robust baseline with time-of-day seasonal fallback.

    Slot baseline uses only previous calendar days within the same time-of-day
    bucket. When history is insufficient, use a strictly past rolling median.
    No future samples or target sample enter the baseline. The returned
    thresholds are descriptive evidence, not calibrated probabilities.
    """
    x = pd.to_numeric(g['temperature'], errors='coerce').reset_index(drop=True)
    t = pd.to_datetime(g['timestamp']).reset_index(drop=True)
    w = max(11, int(window) * 3)
    history = x.shift(1)
    roll_center = history.rolling(w, min_periods=max(8, w//2)).median()
    roll_mad = (history - roll_center).abs().rolling(w, min_periods=max(8, w//2)).median()
    # Prior days, matching local time-of-day slot; at least 8 valid samples.
    bucket = (t.dt.hour * 60 + t.dt.minute) // (max(1, int(slot_hours)) * 60)
    day = t.dt.normalize()
    slot_center = pd.Series(np.nan, index=x.index, dtype=float)
    slot_mad = pd.Series(np.nan, index=x.index, dtype=float)
    # Compute once per (time slot, calendar day), not once per record.
    # Prior-day-only history preserves causal behavior and handles irregular sampling.
    valid = x.notna()
    groups = pd.DataFrame({'bucket': bucket, 'day': day, 'value': x})
    for _, slot in groups.groupby('bucket', sort=False):
        history_values = []
        for _, today in slot.groupby('day', sort=True):
            if len(history_values) >= min_slot_samples:
                values = np.asarray(history_values, dtype=float)
                median = float(np.median(values))
                deviation = float(np.median(np.abs(values - median)))
                slot_center.iloc[today.index] = median
                slot_mad.iloc[today.index] = deviation
            current = today.loc[today['value'].notna(), 'value'].to_numpy(dtype=float)
            history_values.extend(current.tolist())
    center = slot_center.combine_first(roll_center)
    mad = slot_mad.combine_first(roll_mad)
    sigma = (1.4826 * mad).clip(lower=.25)
    upper = center + float(threshold)*sigma
    lower = center - float(threshold)*sigma
    flag = ((x < lower) | (x > upper)).fillna(False)
    return pd.DataFrame({'adaptive_baseline':center.to_numpy(),
                         'adaptive_sigma':sigma.to_numpy(),
                         'adaptive_lower':lower.to_numpy(),
                         'adaptive_upper':upper.to_numpy(),
                         'adaptive_flag':flag.to_numpy(),
                         'baseline_type':np.where(slot_center.notna(),'历史同时段','历史滚动')},index=g.index)

def detect(df, method='Hampel', window=11, threshold=3.0, contamination=.08):
    df=normalize(df); results=[]
    for _,g in df.groupby('node_id',sort=False):
        g=g.copy(); x=g['temperature']; missing=x.isna() | g['humidity'].isna()
        if method=='阈值法':
            flag=((x<5)|(x>40)|(g['humidity']<10)|(g['humidity']>95)).fillna(False)
        elif method=='Hampel':
            med=x.rolling(window,center=True,min_periods=max(3,window//3)).median()
            mad=(x-med).abs().rolling(window,center=True,min_periods=max(3,window//3)).median()
            scale=(1.4826*mad).clip(lower=.15)
            flag=((x-med).abs()>threshold*scale).fillna(False)
        elif method=='卡死检测':
            # Exact repeated readings are suspicious only after a configurable run.
            # NaNs are handled separately as missing values.
            run = x.ne(x.shift()).cumsum()
            count = x.groupby(run).transform('size')
            flag = x.notna() & count.ge(max(3, int(window)))
        elif method=='漂移检测':
            # A sustained, monotonic residual slope relative to a longer baseline.
            # Rolling linear regression removes the need for supervised training.
            w = max(7, int(window) | 1)
            baseline = x.rolling(max(w*4, 29), min_periods=w).median().shift(1)
            residual = x - baseline
            # Closed-form rolling OLS slope using rolling sums (no Python callback
            # and no repeated np.polyfit calls). Complete finite windows only.
            positions = pd.Series(np.arange(len(residual), dtype=float), index=residual.index)
            clean = residual.replace([np.inf, -np.inf], np.nan)
            sum_y = clean.rolling(w, min_periods=w).sum()
            sum_ty = (clean * positions).rolling(w, min_periods=w).sum()
            sum_x = w * (w - 1) / 2.0
            denominator = w * (w * w - 1) / 12.0
            slopes = (sum_ty - (positions - w + 1) * sum_y - sum_x * sum_y / w) / denominator
            # threshold is the minimum change in degrees across one window.
            flag=(slopes.abs()*(w-1)>max(.2,float(threshold))) & residual.abs().gt(max(.3,float(threshold)))
            flag=flag.fillna(False)
        elif method=='场景自适应':
            profile=adaptive_profile(g,window=window,threshold=threshold)
            for col in ('adaptive_baseline','adaptive_sigma','adaptive_lower','adaptive_upper','baseline_type'):
                g[col]=profile[col]
            limits=((x<5)|(x>40)|(g['humidity']<10)|(g['humidity']>95)).fillna(False)
            flag=profile['adaptive_flag'] | limits
        elif method=='综合检测':
            # Preserve independent diagnostic types rather than fitting on injected labels.
            adaptive=detect(g,method='场景自适应',window=window,threshold=threshold)['detected_fault'].astype(bool)
            spike=detect(g,method='Hampel',window=window,threshold=threshold)['detected_fault'].astype(bool)
            stuck=detect(g,method='卡死检测',window=window)['detected_fault'].astype(bool)
            drift=detect(g,method='漂移检测',window=window,threshold=threshold)['detected_fault'].astype(bool)
            limits=((x<5)|(x>40)|(g['humidity']<10)|(g['humidity']>95)).fillna(False)
            flag=spike.to_numpy()|stuck.to_numpy()|drift.to_numpy()|adaptive.to_numpy()|limits.to_numpy()
            flag=pd.Series(flag,index=g.index)
        elif method=='Isolation Forest':
            features=g[['temperature','humidity','rssi']].copy().ffill().bfill()
            if features.isna().all().any() or len(features)<8:flag=pd.Series(False,index=g.index)
            else:
                features=features.fillna(features.median()).fillna(0)
                flag=pd.Series(IsolationForest(n_estimators=120,contamination=contamination,random_state=42).fit_predict(features)==-1,index=g.index)
        else:raise ValueError('未知算法')
        g['detected_fault']=(flag|missing).astype(int)
        g['diagnosis']=np.where(missing,'数据缺失',np.where(flag,'疑似异常','正常'))
        if method=='场景自适应':
            g['diagnostic_evidence']=np.where(missing,'温湿度缺失',
                np.where(flag,'超出历史动态阈值或物理边界','处于历史动态阈值范围内'))
        elif method=='卡死检测':
            g['diagnostic_evidence']=np.where(flag,'连续重复读数达到窗口长度','未达到连续重复阈值')
        elif method=='漂移检测':
            g['diagnostic_evidence']=np.where(flag,'历史基线残差出现持续趋势','未检出持续趋势')
        else:
            g['diagnostic_evidence']=np.where(flag,'当前方法判定异常','当前方法未检出异常')
        results.append(g)
    return pd.concat(results).sort_values(['node_id','timestamp']).reset_index(drop=True)

def quality(df):
    d=normalize(df);rows=[]
    for node,g in d.groupby('node_id'):
        missing=(g['temperature'].isna()|g['humidity'].isna()).mean()
        anomalies=g['detected_fault'].mean() if 'detected_fault' in g else 0
        dup=g.duplicated('timestamp').mean()
        score=max(0,100*(1-.5*missing-.4*anomalies-.1*dup))
        rows.append({'node_id':node,'records':len(g),'missing_rate':missing,'detected_rate':anomalies,'duplicate_rate':dup,'health_score':round(score,1)})
    return pd.DataFrame(rows)

def evaluate(df):
    if 'detected_fault' not in df or 'is_fault' not in df:return None
    mask=df['is_fault'].notna()
    if not mask.any():return None
    y=df.loc[mask,'is_fault'].astype(int);p=df.loc[mask,'detected_fault'].astype(int)
    precision,recall,f1,_=precision_recall_fscore_support(y,p,average='binary',zero_division=0)
    tn,fp,fn,tp=confusion_matrix(y,p,labels=[0,1]).ravel()
    return {'Precision':round(float(precision),4),'Recall':round(float(recall),4),'F1':round(float(f1),4),'TP':int(tp),'FP':int(fp),'FN':int(fn),'TN':int(tn),'samples':len(y)}
