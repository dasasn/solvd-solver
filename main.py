import sys,json,time,subprocess,os
sys.path.insert(0,'/workspace/solvd/loop')
from common import *
END=time.time()+3*3600-120
OLD=json.load(open('/workspace/solvd/old_challenge.json'))['rules']
tok=None
def auth():
    global tok
    for _ in range(3):
        tok=login()
        if tok: return
        time.sleep(10)
def stop(msg):
    log('STOP',msg); open('/workspace/solvd/loop/RESULT','w').write(msg); sys.exit(0)
def mint(tx,auth_=None):
    ok = tx['to'].lower()==SOLVD.lower() and str(tx['value'])=='0' and int(tx['chainId'])==56 and tx['data'].startswith('0x7aaa1174') and (auth_ is None or auth_['to'].lower()==ME.lower())
    log('TXCHECK',ok,json.dumps(tx)[:200])
    if not ok: stop('TX_CHECK_FAILED '+json.dumps(tx)[:500])
    rc,out,j=baw('contract-call','preview','--binanceChainId','56','--from',ME,'--to',tx['to'],'--value','0','--inputData',tx['data'],'--json')
    open('/workspace/solvd/loop/preview.json','w').write(out); log('PREVIEW',out[:1500])
    rid=find(j,'requestId') if j else None
    if not (j and j.get('success') and rid): stop('PREVIEW_FAILED '+out[:1500])
    risks=find(j,'riskDetails') or find(j,'riskBehaviors')
    if risks: stop('RISK '+out[:1500])
    rc,out,j=baw('contract-call','execute','--requestId',rid,'--json',timeout=300)
    open('/workspace/solvd/loop/execute.json','w').write(out); log('EXECUTE',out[:1500])
    stop('EXECUTED '+out[:1500])
auth()
while time.time()<END:
    if not tok: auth()
    c,s=http('GET','/challenge/status',token=tok)
    if c==401: log('401 relogin'); tok=None; continue
    if c!=200: log('status',c,str(s)[:120]); time.sleep(40 if c==0 else 60); continue
    reason=s.get('reason'); log('status',reason,'retryAfter',s.get('retryAfter'),'supply',s.get('supply'))
    if reason=='ALREADY_MINTED': stop('ALREADY_MINTED')
    if reason=='AUTH_PENDING':
        pa=s.get('pendingAuth') or {}
        if pa.get('tx'): mint(pa['tx'],pa.get('auth'))
        time.sleep(max(60,min(int(s.get('retryAfter') or 60),600))); continue
    if reason in ('NOT_AGENT','SOLD_OUT','PHASE_CLOSED'): stop(reason+' '+json.dumps(s)[:400])
    if reason not in (None,'OPEN_CHALLENGE'):
        time.sleep(max(60,min(int(s.get('retryAfter') or 60)+2,900))); continue
    # request
    c,ch=http('POST','/challenge/request',token=tok,timeout=40)
    if c==401: tok=None; continue
    if 'boards' not in ch: log('request',c,str(ch)[:200]); time.sleep(max(60,min(int(ch.get('retryAfter') or 60) if isinstance(ch.get('retryAfter'),(int,float)) else 60,900))); continue
    json.dump(ch,open('/workspace/solvd/loop/ch.json','w'))
    log('GOT challenge',ch.get('challengeId'),'tier',ch.get('tier'),'exp',ch.get('expiresAt'),'now',int(time.time()),[(b['width'],b['height']) for b in ch['boards']])
    if ch.get('type')!='nonogram': stop('TYPE_CHANGED '+str(ch.get('type')))
    p=subprocess.run(['timeout',str(max(30,ch['expiresAt']-int(time.time())-15)),'python3','/workspace/solvd/v2/psolve.py','/workspace/solvd/loop/ch.json','/workspace/solvd/loop/answer.json'],capture_output=True,text=True,cwd='/workspace/solvd/v2')
    log('solver rc',p.returncode,p.stdout[-300:],p.stderr[-500:])
    if p.returncode!=0: log('solve failed; not submitting'); time.sleep(60); continue
    if ch.get('rules')!=OLD: stop('RULES_CHANGED answer ready, not submitted: '+str(ch.get('rules'))[:3000])
    body=open('/workspace/solvd/loop/answer.json','rb').read()
    for k in range(4):
        c,r=http('POST','/challenge/submit',token=tok,raw=body,timeout=60)
        open('/workspace/solvd/loop/submit.json','w').write(json.dumps(r)); log('SUBMIT',c,json.dumps({x:y for x,y in r.items() if x!='signature'})[:800])
        if c==401: tok=login(); continue
        if r.get('error')=='bad_timing' or c==0: time.sleep(2); continue
        break
    if r.get('ok'): mint(r['tx'],r.get('auth'))
    e=r.get('error')
    if e in ('row_mismatch','col_mismatch','bad_shape','bad_row','bad_padding'): stop('REJECTED '+json.dumps(r)[:500])
    if e=='tier_closed': continue
    if e=='used': continue
    time.sleep(60)
stop('TIMEOUT_3H')
