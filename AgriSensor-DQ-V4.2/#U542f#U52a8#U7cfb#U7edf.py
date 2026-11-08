import os
os.environ["AGRISENSOR_CLOUD_DEMO"] = "0"
"""PyCharm直接运行此文件；自动启动Streamlit并打开浏览器。"""
import os,sys,subprocess,webbrowser,time,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PORT=8501

def free(port):
 with socket.socket() as s:return s.connect_ex(('127.0.0.1',port))!=0

def main():
 try:import streamlit
 except ImportError:
  print('缺少依赖。请先双击「首次安装依赖.bat」安装一次，或在PyCharm安装requirements.txt。');input('按回车退出...');return
 port=next((p for p in range(PORT,PORT+20) if free(p)),None)
 if port is None:print('8501-8520端口均被占用');return
 url=f'http://localhost:{port}'
 cmd=[sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),'--server.port',str(port),'--server.headless','true','--browser.gatherUsageStats','false']
 print('AgriSensor-DQ 正在启动...\n浏览器地址:',url,'\n关闭本窗口或Ctrl+C停止服务。')
 proc=subprocess.Popen(cmd,cwd=str(ROOT),env={**os.environ,'STREAMLIT_BROWSER_GATHER_USAGE_STATS':'false'})
 try:
  for _ in range(40):
   time.sleep(.35)
   if not free(port):break
   if proc.poll() is not None:print('服务异常退出，请检查依赖和错误信息');return
  webbrowser.open(url)
  proc.wait()
 except KeyboardInterrupt:
  proc.terminate()
if __name__=='__main__':main()
