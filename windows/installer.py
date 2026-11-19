import os,sys,subprocess,threading,tkinter as tk
from tkinter import ttk,messagebox
from pathlib import Path
base=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
APK=base/'CouchTV-Custom.apk'
ADB=base/'platform-tools'/'adb.exe'
root=tk.Tk();root.title('Couch TV Custom - Fire TV Installer');root.geometry('550x320')
tk.Label(root,text='Couch TV Custom Installer',font=('Segoe UI',18,'bold')).pack(pady=15)
tk.Label(root,text='Fire TV IP address (Settings > My Fire TV > About > Network)').pack()
ip=tk.StringVar()
tk.Entry(root,textvariable=ip,width=35).pack(pady=8)
status=tk.StringVar(value='Enable ADB Debugging on Fire TV first.')
tk.Label(root,textvariable=status,wraplength=500).pack(pady=8)
bar=ttk.Progressbar(root,mode='indeterminate',length=450);bar.pack(pady=8)
log=tk.Text(root,height=5,width=65);log.pack(padx=10,pady=8)
def say(s):
 root.after(0,lambda:(log.insert('end',s+'\\n'),log.see('end'),status.set(s)))
def work():
 host=ip.get().strip()
 if not host:say('Enter Fire TV IP');return
 def run():
  root.after(0,bar.start)
  try:
   if not APK.exists() or not ADB.exists():raise RuntimeError('Installer payload missing')
   say('Connecting to '+host)
   p=subprocess.run([str(ADB),'connect',host+':5555'],capture_output=True,text=True,timeout=35)
   say((p.stdout+p.stderr).strip())
   if 'connected' not in p.stdout.lower():raise RuntimeError('ADB connection failed; approve debugging on TV')
   say('Installing APK ...')
   p=subprocess.run([str(ADB),'-s',host+':5555','install','-r',str(APK)],capture_output=True,text=True,timeout=180)
   if p.returncode:raise RuntimeError((p.stdout+p.stderr).strip())
   say('Installation complete')
   root.after(0,lambda:messagebox.showinfo('Couch TV','Installed successfully'))
  except Exception as e:
   say('ERROR: '+str(e))
   root.after(0,lambda:messagebox.showerror('Error',str(e)))
  finally:root.after(0,bar.stop)
 threading.Thread(target=run,daemon=True).start()
tk.Button(root,text='Connect and Install',command=work,font=('Segoe UI',12,'bold')).pack()
root.mainloop()
