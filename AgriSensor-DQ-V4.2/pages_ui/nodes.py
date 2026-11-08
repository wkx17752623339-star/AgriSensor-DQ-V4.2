import streamlit as st
import plotly.express as px
from ui.theme import heading
from services.analytics import extra_quality

def render(df,det):
 heading('节点监控中心','查看每个传感器的历史曲线、信号强度和异常位置')
 node=st.selectbox('传感器节点',sorted(df.node_id.unique()),key='node_selected')
 g=det[det.node_id.eq(node)]
 a,b,c,d=st.columns(4)
 a.metric('记录条数',len(g));b.metric('平均温度',f'{g.temperature.mean():.1f} °C');c.metric('平均湿度',f'{g.humidity.mean():.1f}%');d.metric('异常记录',int(g.detected_fault.sum()))
 for col,label in [('temperature','温度'),('humidity','湿度'),('rssi','无线信号RSSI')]:
  st.subheader(label+'时序监控')
  fig=px.line(g,x='timestamp',y=col,template='plotly_white')
  fig.update_layout(height=260,margin=dict(l=5,r=5,t=10,b=5))
  st.plotly_chart(fig,use_container_width=True)
 st.subheader('节点质量概览')
 st.dataframe(extra_quality(g),hide_index=True,use_container_width=True)
