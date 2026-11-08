import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import demo_data,normalize,detect,quality,evaluate
from services.faults import inject
from services.experiments import compare

def test_pipeline():
 df=demo_data(nodes=3,days=2)
 assert len(df)>100
 assert normalize(df).node_id.nunique()==3
 for m in ['Hampel','Isolation Forest','阈值法']:
  out=detect(df,method=m)
  assert len(out)==len(df)
  assert quality(out).shape[0]==3
  assert evaluate(out) is not None
 changed=inject(df,'NODE-01','持续偏移',10)
 assert len(changed)==len(df)
 assert len(compare(changed))==len(__import__("services.experiments",fromlist=["METHODS"]).METHODS)
if __name__=='__main__':test_pipeline();print('全部算法和数据流程测试通过')
