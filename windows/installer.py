import sys, subprocess, threading, tkinter as tk, http.server, socketserver, json, webbrowser
from pathlib import Path
from tkinter import messagebox
base=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
APK=base/'CouchTV-Custom.apk'
ADB=base/'platform-tools'/'adb.exe'
HTML=base/'setup.html'
root=tk.Tk()
root.title('Couch TV — Custom Setup')
root.geometry('680x460')
root.configure(bg='#0b0b0d')
tk.Label(root,text='Couch TV',fg='#f2ead8',bg='#0b0b0d',font=('Segoe UI',28,'bold')).pack(pady=(22,4))
tk.Label(root,text='Fire TV installation & original Couch TV setup',fg='#bdb6a7',bg='#0b0b0d').pack(pady=(0,20))
panel=tk.Frame(root,bg='#16161a',padx=24,pady=20);panel.pack(fill='x',padx=35)
tk.Label(panel,text='Fire TV IP address',bg='#16161a',fg='#f2ead8',font=('Segoe UI',13,'bold')).pack(anchor='w')
ip=tk.StringVar()
tk.Entry(panel,textvariable=ip,font=('Segoe UI',13),bg='#0f0f12',fg='white',insertbackground='white').pack(fill='x',pady=12)
status=tk.StringVar(value='Enable ADB debugging in Fire TV settings.')
tk.Label(panel,textvariable=status,bg='#16161a',fg='#ffb52e',wraplength=550).pack(anchor='w')
def cmd(args,timeout=120):
 p=subprocess.run([str(ADB)]+args,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError((p.stdout+p.stderr).strip())
 return (p.stdout+p.stderr).strip()
def install():
 host=ip.get().strip()
 if not host:status.set('Enter the IP address.');return
 def run():
  try:
   root.after(0,lambda:status.set('Connecting — approve ADB authorization on the TV ...'))
   result=cmd(['connect',host+':5555'],40)
   if 'connected' not in result.lower():raise RuntimeError(result)
   root.after(0,lambda:status.set('Installing custom Couch TV ...'))
   cmd(['-s',host+':5555','install','-r',str(APK)],180)
   root.after(0,lambda:status.set('Installed. Opening original TV Setup ...'))
   cmd(['-s',host+':5555','shell','am','start','-n','dev.couchtv.ontv/.SetupActivity'],30)
   root.after(0,lambda:messagebox.showinfo('Couch TV','Installed. Original setup is open on the TV.'))
  except Exception as e:
   root.after(0,lambda:status.set('Error: '+str(e)))
 threading.Thread(target=run,daemon=True).start()
def open_setup():
 host=ip.get().strip()
 if not host:status.set('Enter IP first.');return
 def run():
  try:
   cmd(['connect',host+':5555'],40)
   cmd(['-s',host+':5555','shell','am','start','-n','dev.couchtv.ontv/.SetupActivity'],30)
   root.after(0,lambda:status.set('Original setup opened on Fire TV.'))
  except Exception as e:root.after(0,lambda:status.set(str(e)))
 threading.Thread(target=run,daemon=True).start()
def button(label,action):
 tk.Button(panel,text=label,command=action,bg='#ffb52e',fg='#111',activebackground='#ffca65',relief='flat',font=('Segoe UI',12,'bold'),pady=10).pack(fill='x',pady=7)
button('Install Couch TV Custom',install)
button('Open original Couch TV Setup on Fire TV',open_setup)
tk.Label(root,text='Original setup screen and all device settings remain inside the installed TV app.',bg='#0b0b0d',fg='#bdb6a7',wraplength=600).pack(pady=20)
root.mainloop()
