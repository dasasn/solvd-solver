import json,subprocess,time,urllib.request,urllib.error,os
API='https://api.solvd.fun/v3'; ME='0x75705E249E3856f4C64c77b267f76df392C6d904'
BAW='/home/box/.local/bin/baw'; SOLVD='0x59661d7F8f996F687CD98c116cCaf66eFd254076'
def log(*a):
    print(time.strftime('%H:%M:%S'),*a,flush=True)
def http(method,path,body=None,token=None,timeout=20,raw=None):
    h={'content-type':'application/json','user-agent':'curl/8.5.0','accept':'*/*'}
    if token: h['authorization']='Bearer '+token
    data=raw if raw is not None else (json.dumps(body).encode() if body is not None else (b'' if method=='POST' else None))
    req=urllib.request.Request(API+path,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: code=r.status; txt=r.read().decode()
    except urllib.error.HTTPError as e: code=e.code; txt=e.read().decode()
    except Exception as e: return 0,{'_neterr':str(e)[:120]}
    try: return code,json.loads(txt)
    except Exception: return code,{'_text':txt[:200]}
def baw(*args,timeout=120):
    p=subprocess.run([BAW,*args],capture_output=True,text=True,timeout=timeout)
    out=(p.stdout or '')+(p.stderr or '')
    try: j=json.loads(p.stdout)
    except Exception: j=None
    return p.returncode,out,j
def login():
    c,n=http('POST','/auth/nonce',{'address':ME})
    if c!=200 or 'typedData' not in n: log('nonce fail',c,str(n)[:200]); return None
    td=n['typedData']; d=td['domain']; m=td['message']
    assert d.get('name')=='SOLVDLogin' and str(d.get('version'))=='1' and int(d.get('chainId'))==56, d
    assert td['primaryType']=='Login' and m['account'].lower()==ME.lower() and m['nonce']==n['nonce'], td
    sr=json.loads(n['signRequest']) if isinstance(n['signRequest'],str) else n['signRequest']
    # signRequest must carry the same typed data
    p=sr['params']; tdj=json.loads(p[1]) if isinstance(p[1],str) else p[1]
    assert p[0].lower()==ME.lower() and tdj['domain']==td['domain'] and tdj['message']==td['message'] and tdj['primaryType']=='Login', sr
    srs=n['signRequest'] if isinstance(n['signRequest'],str) else json.dumps(n['signRequest'])
    rc,out,j=baw('sign-message','preview','--binanceChainId','56','--signType','EIP712','--message',srs,'--json')
    rid=find(j,'requestId') if j else None
    if not rid: log('sign preview fail',out[:400]); return None
    rc,out,j=baw('sign-message','execute','--requestId',rid,'--json')
    sig=find(j,'signature') if j else None
    if sig and not sig.startswith('0x') and len(sig)==128:
        v=int(find(j,'signatureRecovery') or '0',16); v=v+27 if v<27 else v
        sig='0x'+sig+'%02x'%v
    elif sig and not sig.startswith('0x'): sig='0x'+sig
    if not sig: log('sign exec fail',out[:400]); return None
    c,t=http('POST','/auth/login',{'address':ME,'nonce':n['nonce'],'signature':sig,'signType':'EIP712'})
    if c!=200 or 'token' not in t: log('login fail',c,str(t)[:200]); return None
    log('login ok exp',t.get('expiresAt')); return t['token']
def find(j,key):
    if isinstance(j,dict):
        if key in j and j[key]: return j[key]
        for v in j.values():
            r=find(v,key)
            if r: return r
    if isinstance(j,list):
        for v in j:
            r=find(v,key)
            if r: return r
    return None
