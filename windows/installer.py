import concurrent.futures, ipaddress, re, socket, subprocess, sys, threading, tkinter as tk
from pathlib import Path
from tkinter import messagebox

base=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
ADB=base/'platform-tools'/'adb.exe'
APK=base/'CouchTV-Custom.apk'
root=tk.Tk()
root.title('Couch TV — Custom Installer')
root.geometry('660x440')
root.configure(bg='#101218')
tk.Label(root,text='Couch TV',fg='#f5eee2',bg='#101218',font=('Segoe UI',28,'bold')).pack(pady=(20,5))
tk.Label(root,text='Automatically discover Fire TV and install your custom APK',fg='#c9d0dc',bg='#101218').pack(pady=(0,15))
panel=tk.Frame(root,bg='#1c2029',padx=22,pady=18)
panel.pack(fill='both',expand=True,padx=28,pady=(0,25))
tk.Label(panel,text='Available Fire TV devices',fg='white',bg='#1c2029',font=('Segoe UI',13,'bold')).pack(anchor='w')
devices={}
listbox=tk.Listbox(panel,bg='#101218',fg='white',selectbackground='#d99b36',font=('Segoe UI',11),height=7)
listbox.pack(fill='both',expand=True,pady=12)
status=tk.StringVar(value='Preparing network scan…')
tk.Label(panel,textvariable=status,fg='#d7e0ea',bg='#1c2029',wraplength=570,justify='left').pack(fill='x',pady=12)
buttons=tk.Frame(panel,bg='#1c2029')
buttons.pack(fill='x')
def ui(message):root.after(0,lambda:status.set(message))
def adb(*args,timeout=30,serial=None):
    cmd=[str(ADB)]+(['-s',serial] if serial else [])+list(args)
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return p.returncode,(p.stdout+'\n'+p.stderr).strip()
def scan_worker():
    found={}
    try:
        if not ADB.is_file() or not APK.is_file():raise RuntimeError('Missing ADB or custom APK in EXE payload')
        adb('start-server',timeout=15)
        _,output=adb('devices','-l')
        for line in output.splitlines()[1:]:
            parts=line.split()
            if len(parts)>1 and parts[1]=='device' and ':' in parts[0]:found[parts[0]]='Connected device'
        candidates=set()
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
                s.connect(('192.0.2.1',80))
                local=s.getsockname()[0]
            candidates.update((str(h),5555) for h in ipaddress.ip_network(local+'/24',strict=False).hosts())
        except OSError:pass
        _,output=adb('mdns','services',timeout=12)
        for line in output.splitlines():
            if '_adb' in line:
                match=re.search(r'((?:\d{1,3}\.){3}\d{1,3}):(\d+)',line)
                if match:candidates.add((match.group(1),int(match.group(2))))
        def probe(item):
            try:
                with socket.create_connection(item,timeout=0.4):return item
            except OSError:return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
            for item in pool.map(probe,candidates):
                if item:found[f'{item[0]}:{item[1]}']='ADB endpoint'
        if not found:ui('No Fire TV found. Enable ADB debugging and connect both devices to the same Wi-Fi, then scan again.')
        else:ui(f'Found {len(found)} device(s). Select your Fire TV and click Install.')
    except Exception as e:ui('Scan error: '+str(e))
    def finish():
        devices.clear();devices.update(found)
        listbox.delete(0,tk.END)
        for serial,label in devices.items():listbox.insert(tk.END,f'{serial}  —  {label}')
        if devices:listbox.selection_set(0)
        scan_btn.config(state='normal')
    root.after(0,finish)
def scan():
    scan_btn.config(state='disabled')
    ui('Searching your local network for Fire TV…')
    threading.Thread(target=scan_worker,daemon=True).start()
def install_worker(serial):
    try:
        ui('Connecting. Approve ADB debugging on the TV if requested…')
        rc,out=adb('connect',serial,timeout=35)
        if rc or ('connected' not in out.lower()):raise RuntimeError('ADB connection: '+out)
        rc,out=adb('get-state',serial=serial,timeout=15)
        if rc or out.strip()!='device':raise RuntimeError('TV not authorized: '+out)
        ui('Installing custom Couch TV…')
        rc,out=adb('install','-r',str(APK),serial=serial,timeout=240)
        if rc or 'success' not in out.lower():raise RuntimeError('Install failed: '+out)
        rc,out=adb('shell','pm','path','dev.couchtv.ontv',serial=serial)
        if rc or 'package:' not in out:raise RuntimeError('Package verification failed: '+out)
        ui('Configuring Couch TV as the home screen…')
        grants=[
            ('pm','enable','dev.couchtv.ontv/.HomeAlias'),
            ('pm','grant','dev.couchtv.ontv','android.permission.WRITE_SECURE_SETTINGS'),
            ('appops','set','dev.couchtv.ontv','SYSTEM_ALERT_WINDOW','allow'),
            ('appops','set','dev.couchtv.ontv','GET_USAGE_STATS','allow'),
            ('cmd','package','set-home-activity','dev.couchtv.ontv/.HomeAlias')
        ]
        failures=[]
        for command in grants:
            try:
                code,output=adb('shell',*command,serial=serial,timeout=15)
                if code: failures.append(' '.join(command)+': '+output[:150])
            except Exception as exc: failures.append(' '.join(command)+': '+str(exc))
        # Launch Couch TV after granting permissions; its service can then
        # enable the accessibility watcher for Amazon Home interception.
        adb('shell','am','start','-n','dev.couchtv.ontv/.HomeActivity',serial=serial,timeout=20)
        if failures:
            ui('Installed. Some Home-screen permissions could not be applied; check Fire TV settings.')
            root.after(0,lambda details='\\n'.join(failures):messagebox.showwarning('Couch TV home setup','Couch TV installed, but some automatic Home setup steps failed:\\n'+details))
        else:
            ui('Installed. Couch TV Home permissions configured; reboot test recommended.')

        root.after(0,lambda:messagebox.showinfo('Couch TV','Custom Couch TV installed successfully.'))
    except Exception as e:
        ui('Error: '+str(e))
        root.after(0,lambda msg=str(e):messagebox.showerror('Couch TV',msg))
    finally:root.after(0,lambda:install_btn.config(state='normal'))
def install():
    selected=listbox.curselection()
    if not selected:ui('Select a Fire TV first.');return
    serial=list(devices)[selected[0]]
    install_btn.config(state='disabled')
    threading.Thread(target=install_worker,args=(serial,),daemon=True).start()
scan_btn=tk.Button(buttons,text='Scan again',command=scan,bg='#3c4555',fg='white',relief='flat',padx=18,pady=9)
scan_btn.pack(side='left')
install_btn=tk.Button(buttons,text='Install custom APK',command=install,bg='#f2b54a',fg='#101218',relief='flat',padx=18,pady=9)
install_btn.pack(side='right')
root.after(250,scan)
root.mainloop()
