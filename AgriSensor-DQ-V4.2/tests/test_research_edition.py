from engine import demo_data, normalize, detect
from services.experiments import batch_compare, METHODS
from services.analytics import extra_quality

def test_adaptive_and_composite():
    d=demo_data(nodes=2,days=2)
    for name in ('场景自适应','综合检测'):
        r=detect(d,method=name)
        assert len(r)==len(d)
        assert set(r.detected_fault.unique()).issubset({0,1})
    assert len(extra_quality(d))==2

def test_reproducible_experiment():
    d=demo_data(nodes=2,days=2)
    args=dict(node='NODE-01',kinds=['尖峰'],methods=['Hampel','场景自适应'],repeats=2,seed=13)
    a=batch_compare(d,**args)
    b=batch_compare(d,**args)
    assert len(a)==4
    assert a['新增注入点检出率'].equals(b['新增注入点检出率'])
    assert (a['新增检出注入点数']<=a['命中注入点数']).all()
    assert '场景自适应' in METHODS


def test_adaptive_profile_is_causal_and_node_local():
    import pandas as pd
    from engine import adaptive_profile
    t=pd.date_range('2026-09-01',periods=24*12,freq='h')
    a=pd.DataFrame({'timestamp':t,'node_id':'A','temperature':[20+4*((i%24)>=12) for i in range(len(t))]})
    p1=adaptive_profile(a,window=11)
    a2=a.copy();a2.loc[250:,'temperature']=1000
    p2=adaptive_profile(a2,window=11)
    assert p1.loc[:249,'adaptive_baseline'].equals(p2.loc[:249,'adaptive_baseline'])
    assert (p1['baseline_type']=='历史同时段').any()
    assert p1['adaptive_baseline'].notna().any()
