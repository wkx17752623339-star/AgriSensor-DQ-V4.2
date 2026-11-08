"""Batch fault-injection benchmarking on independent copies of a real dataset.
Injected-hit rate is NOT a full supervised recall/precision metric.
"""
import time
import pandas as pd
from engine import normalize, detect, evaluate
from services.faults import inject, KINDS

METHODS = ['阈值法', 'Hampel', 'Isolation Forest', '卡死检测', '漂移检测', '场景自适应', '综合检测']

def compare(df):
    df=normalize(df)
    if not df['is_fault'].notna().all():
        return pd.DataFrame()
    rows=[]
    for name in METHODS:
        result=detect(df,method=name)
        score=evaluate(result)
        if score:rows.append({'算法':name,**score})
    return pd.DataFrame(rows)

def batch_compare(df, node, kinds=None, methods=None, repeats=5, strength=8.0,
                  start_fraction=.30, duration_fraction=.12, field='temperature',
                  seed=21, window=11, threshold=3.0, contamination=.08,
                  progress=None):
    """Return per-run results; each run uses a fresh copy of the SAME baseline.

    Only newly injected indices are treated as known positive labels. Other
    records are unlabeled, so precision/recall/F1 are intentionally omitted.
    """
    base=normalize(df)
    kinds=list(kinds if kinds is not None else KINDS)
    methods=list(methods if methods is not None else METHODS)
    if not kinds or not methods:raise ValueError('至少选择一种故障和一种检测算法')
    if node not in set(base.node_id):raise ValueError('节点不在当前数据集中')
    if not 1<=int(repeats)<=20:raise ValueError('重复次数应为1至20')
    rows=[];total=len(kinds)*int(repeats)*len(methods);done=0
    if total>240: raise ValueError('单次实验最多240组，请减少故障类型、算法或重复次数')
    # Fault-type markers are used only for this controlled experiment. Existing
    # markers, if present, are overwritten on the experiment baseline copy.
    base=base.copy();base['fault_type']='unknown';base['is_fault']=float('nan')
    baseline_flags={}
    for method in methods:
        baseline_flags[method]=detect(base,method=method,window=int(window),threshold=float(threshold),contamination=float(contamination))['detected_fault'].to_numpy().astype(bool)
    for kind in kinds:
        for rep in range(int(repeats)):
            run_seed=int(seed)+rep
            modified=inject(base,node,kind=kind,strength=float(strength),seed=run_seed,
                            start_fraction=float(start_fraction),duration_fraction=float(duration_fraction),field=field)
            injected=(modified['fault_type']==kind)&modified['node_id'].eq(node)
            n_injected=int(injected.sum())
            for method in methods:
                start=time.perf_counter()
                result=detect(modified,method=method,window=int(window),threshold=float(threshold),contamination=float(contamination))
                elapsed=time.perf_counter()-start
                # Both normalize and detect sort by node and timestamp, preserving
                # row positions; compare using their normalized positional order.
                predictions=result['detected_fault'].to_numpy().astype(bool)
                hit=int((predictions & injected.to_numpy()).sum())
                new_hit=int((predictions & ~baseline_flags[method] & injected.to_numpy()).sum())
                total_detected=int(result['detected_fault'].sum())
                rows.append({'节点':node,'故障类型':kind,'算法':method,'重复序号':rep+1,
                             '随机种子':run_seed,'注入点数':n_injected,'命中注入点数':hit,
                             '注入点检出率':hit/n_injected if n_injected else float('nan'),
                             '新增检出注入点数':new_hit,
                             '新增注入点检出率':new_hit/n_injected if n_injected else float('nan'),
                             '其他位置检出数':total_detected-hit,'全部检出数':total_detected,
                             '检测耗时(秒)':round(elapsed,5),'字段':field,'故障强度':strength,
                             '开始比例':start_fraction,'持续比例':duration_fraction,
                             'Hampel窗口':window,'Hampel敏感度':threshold,
                             'IF异常比例':contamination})
                done+=1
                if progress:progress(done,total)
    return pd.DataFrame(rows)
