"""Controlled synthetic fault injection. Only injected samples get ground-truth labels."""
import numpy as np
from engine import normalize
KINDS=['尖峰','持续偏移','缓慢漂移','卡死','数据中断']

def inject(df,node,kind='尖峰',strength=8.0,seed=21,start_fraction=.3,duration_fraction=.12,field='temperature'):
    d=normalize(df)
    if kind not in KINDS:raise ValueError('未知故障类型')
    if field not in ('temperature','humidity','rssi'):raise ValueError('不支持的传感字段')
    if not 0<=start_fraction<1 or not 0<duration_fraction<=1:raise ValueError('时间比例必须在有效范围内')
    rng=np.random.default_rng(int(seed)); idx=d.index[d.node_id.eq(node)].to_numpy()
    if len(idx)<12:raise ValueError('目标节点至少需要12条记录')
    begin=int(len(idx)*start_fraction);span=max(2,int(len(idx)*duration_fraction))
    selected=idx[begin:min(len(idx),begin+span)]
    if len(selected)<2:raise ValueError('所选时间区间不足')
    if kind=='尖峰':
        selected=rng.choice(selected,size=max(1,len(selected)//4),replace=False)
        d.loc[selected,field]+=float(strength)*rng.choice([-1,1],len(selected))
    elif kind=='持续偏移':d.loc[selected,field]+=float(strength)
    elif kind=='缓慢漂移':d.loc[selected,field]+=np.linspace(float(strength)/len(selected),float(strength),len(selected))
    elif kind=='卡死':d.loc[selected,field]=d.loc[selected[0],field]
    elif kind=='数据中断':d.loc[selected,field]=np.nan
    # Do not manufacture labels for pre-existing unlabeled observations.
    if d['is_fault'].notna().all():
        d.loc[selected,'is_fault']=1
    else:
        d['is_fault']=np.nan
    d.loc[selected,'fault_type']=kind
    return d
