import concurrent.futures,html,json,re
from pathlib import Path
import requests
pattern=re.compile(r'mist_global-ota_full-(OS4\.\d+\.\d+\.\d+\.XPUMIXM)-user-17\.0-[a-f0-9]+\.zip',re.I)
known='mist_global-ota_full-OS4.0.8.0.XPUMIXM-user-17.0-3695aedf1f.zip'
pages=['https://mirom.ezbox.idv.tw/en/phone/mist/','https://mirom.ezbox.idv.tw/en/phone/mist/roms-global-stable/','https://droidforge.net/xiaomi/redmi-note-17-5g-mist?lang=en','https://mobileosupdates.com/hyperos/mist/version/OS4.0.8.0.XPUMIXM','https://findmyrom.com/devices/mist']
hosts=['bn.d.miui.com','bigota.d.miui.com','hugeota.d.miui.com','cdnorg.d.miui.com','ultimateota.d.miui.com']
def get(p):
    try:
        r=requests.get(p,timeout=35,headers={'User-Agent':'Mozilla/5.0'});r.raise_for_status()
        return p,html.unescape(r.text),None
    except requests.RequestException as e:return p,'',str(e)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: results=list(pool.map(get,pages))
names={known}
for _,body,_ in results:names.update(m.group(0) for m in pattern.finditer(body))
def ver(n):return tuple(map(int,pattern.fullmatch(n).group(1)[2:].split('.')[:4]))
report={'sources':[{'page':p,'error':e,'matches':[m.group(0) for m in pattern.finditer(b)]} for p,b,e in results],'probes':[]}
out=Path('reports/firmware-source.json')
for n in sorted(names,key=ver,reverse=True):
    for host in hosts:
        url=f'https://{host}/{pattern.fullmatch(n).group(1)}/{n}'
        try:
            with requests.get(url,headers={'Range':'bytes=0-15','Accept-Encoding':'identity'},stream=True,timeout=20) as r:
                ok=r.status_code in (200,206) and r.raw.read(4)==b'PK\x03\x04'
                report['probes'].append({'url':url,'status':r.status_code,'zip':ok})
            if ok:
                report['selected']=url
                if n==known:report['md5']='3695aedf1f96d96bbdac41bb247bc8bf'
                Path('rom-url.txt').write_text(url);print(url);raise SystemExit(0)
        except requests.RequestException as e:report['probes'].append({'url':url,'error':str(e)})
        finally:out.write_text(json.dumps(report,indent=2))
raise SystemExit('No reachable full HyperOS 4 OTA')
