"""
HA-GDCP-QAOA — corrected, self-contained implementation.
Addresses code-audit findings H1-H14. No machine-specific paths; auto-discovers OPSD.
"""
import os, glob, zipfile, hashlib, itertools, time, json
import numpy as np, pandas as pd, networkx as nx, highspy
from scipy.optimize import minimize
from scipy.stats import spearmanr, kendalltau, wilcoxon

# ============================ CONFIG (H16: configurable paths) ============================
def find_opsd():
    env=os.environ.get('OPSD_CSV')
    if env and os.path.exists(env): return env
    pats=['/kaggle/input/**/time_series_60min_singleindex.csv',
          './**/time_series_60min_singleindex.csv',
          os.path.expanduser('~/**/time_series_60min_singleindex.csv')]
    for p in pats:
        hits=glob.glob(p,recursive=True)
        if hits: return hits[0]
    zips=glob.glob('/kaggle/input/**/*.zip',recursive=True)+glob.glob('./*.zip')
    for z in zips:
        with zipfile.ZipFile(z) as f: f.extractall('opsd_data')
    hits=glob.glob('./**/time_series_60min_singleindex.csv',recursive=True)
    if hits: return hits[0]
    raise FileNotFoundError('OPSD time_series_60min_singleindex.csv not found')

CONFIG=dict(seed=2026, block=6, qaoa_p=3, restarts=4, maxiter=200, shots=256,
            allow_simultaneous_el_fc=True,   # H6: documented policy (never optimal; verified)
            facility=dict(load_peak_kw=400.0, pv_kw=200.0, wind_kw=150.0))

PARAMS=dict(Pel_max=100.0,Pel_min=20.0,Pfc_max=60.0,Pfc_min=12.0,Php_max=90.0,
    eta_el=0.65,eta_fc=0.50,e_H=33.33,R_el=60.0,Hmin=0.0,Hmax=50.0,H0=10.0,Hterm=10.0,
    self_discharge=0.0,   # H8: fractional standing loss, APPLIED in balance (default 0)
    cdeg_el=0.004,cdeg_fc=0.006,cstart=0.05,lamH=5.0,lamQ=0.3,csell=0.9,dt=1.0,Pgrid_max=500.0)

# ============================ data / benchmark ============================
def build_year(csv, params=PARAMS, seed=2026):
    cols=['utc_timestamp','DE_load_actual_entsoe_transparency','DE_solar_generation_actual',
          'DE_wind_generation_actual','DE_LU_price_day_ahead']
    df=pd.read_csv(csv,usecols=cols,parse_dates=['utc_timestamp']).set_index('utc_timestamp').sort_index()
    m=(df.index>=pd.Timestamp('2019-01-01',tz='UTC'))&(df.index<pd.Timestamp('2020-01-01',tz='UTC'))
    d=df.loc[m].copy(); d['DE_LU_price_day_ahead']=d['DE_LU_price_day_ahead'].ffill().bfill()
    out=pd.DataFrame(index=d.index)
    out['load_kw']=d['DE_load_actual_entsoe_transparency']/d['DE_load_actual_entsoe_transparency'].max()*params['Pel_max']*0+ \
                   d['DE_load_actual_entsoe_transparency']/d['DE_load_actual_entsoe_transparency'].max()*400.0
    out['solar_kw']=d['DE_solar_generation_actual']/30028.0*200.0
    out['wind_kw']=d['DE_wind_generation_actual']/45085.0*150.0
    out['price_eur_kwh']=d['DE_LU_price_day_ahead']/1000.0
    doy=out.index.dayofyear.values; hod=out.index.hour.values
    seasonal=0.5+0.5*np.cos(2*np.pi*(doy-15)/365.0); diurnal=0.6+0.4*np.sin(2*np.pi*(hod-7)/24.0).clip(min=-1)
    out['heat_kwth']=(20.0+70.0*seasonal)*(0.7+0.3*diurnal)
    amb=5.0+15.0*(1-seasonal)-4.0*np.cos(2*np.pi*(hod-14)/24.0); out['cop']=(2.2+0.08*amb).clip(1.8,4.5)
    rng=np.random.default_rng(seed); base=0.45+0.25*seasonal; daily=0.8+0.4*((hod>=6)&(hod<=20))
    out['h2_demand_kg_h']=(base*daily*rng.normal(1.0,0.05,len(out)).clip(0.85,1.15)).round(3)
    return out
def split_chrono(df): return df.loc[:'2019-08-31'],df.loc['2019-09-01':'2019-10-31'],df.loc['2019-11-01':]
def make_instance(df,start,T):
    w=df.loc[start:].iloc[:T]
    return dict(key=f'{start}|{T}',ts=w.index,load=w['load_kw'].values,solar=w['solar_kw'].values,
        wind=w['wind_kw'].values,price=w['price_eur_kwh'].values,heat=w['heat_kwth'].values,
        cop=w['cop'].values,h2d=w['h2_demand_kg_h'].values,T=T)

# ============================ H2: safe cache key (full hash) ============================
_LP_CACHE={}
def _inst_hash(inst,p):
    h=hashlib.sha256()
    for k in ['load','solar','wind','price','heat','cop','h2d']:
        h.update(np.ascontiguousarray(inst[k],dtype=np.float64).tobytes())
    for k in sorted(p): h.update(f'{k}={p[k]}'.encode())
    h.update(str(inst['T']).encode())
    return h.hexdigest()

# ============================ H1,H6,H7,H8: continuous recourse LP ============================
INF=highspy.kHighsInf
def lp_recourse(inst,uel,ufc,p=PARAMS,return_sched=False,use_cache=True):
    T=inst['T']
    if use_cache and not return_sched:
        ck=(_inst_hash(inst,p),tuple(int(x) for x in uel),tuple(int(x) for x in ufc))
        if ck in _LP_CACHE: return _LP_CACHE[ck]
    load,sol,wnd,price=inst['load'],inst['solar'],inst['wind'],inst['price']
    heat,cop,h2d=inst['heat'],inst['cop'],inst['h2d']
    h=highspy.Highs(); h.setOptionValue('output_flag',False)
    nv=9; idx=lambda t,j:t*nv+j; base=T*nv; Hi=lambda t:base+t; N=base+(T+1)
    lo=np.zeros(N); up=np.full(N,INF); cost=np.zeros(N)
    for t in range(T):
        up[idx(t,0)]=p['Pgrid_max']; up[idx(t,1)]=p['Pgrid_max']            # H1 grid cap
        up[idx(t,2)]=max(sol[t],0); up[idx(t,3)]=max(wnd[t],0)
        up[idx(t,4)]=p['Pel_max']*uel[t]; lo[idx(t,4)]=p['Pel_min']*uel[t]
        up[idx(t,5)]=p['Pfc_max']*ufc[t]; lo[idx(t,5)]=p['Pfc_min']*ufc[t]
        up[idx(t,6)]=p['Php_max']; up[idx(t,7)]=h2d[t]
        cost[idx(t,0)]=price[t]*p['dt']; cost[idx(t,1)]=-p['csell']*max(price[t],0)*p['dt']
        cost[idx(t,4)]=p['cdeg_el']; cost[idx(t,5)]=p['cdeg_fc']; cost[idx(t,7)]=p['lamH']; cost[idx(t,8)]=p['lamQ']
    for t in range(T+1): lo[Hi(t)]=p['Hmin']; up[Hi(t)]=p['Hmax']
    lo[Hi(0)]=up[Hi(0)]=p['H0']; lo[Hi(T)]=max(p['Hterm'],p['Hmin'])
    h.addVars(N,lo,up); h.changeColsCost(N,np.arange(N),cost)
    starts=[];ind=[];val=[];rl=[];ru=[]
    def row(pairs,l,u):
        starts.append(len(ind))
        for c,v in pairs: ind.append(int(c)); val.append(float(v))
        rl.append(l); ru.append(u)
    sd=p['self_discharge']
    for t in range(T):
        row([(idx(t,2),1),(idx(t,3),1),(idx(t,0),1),(idx(t,5),1),(idx(t,4),-1),(idx(t,6),-1),(idx(t,1),-1)],load[t],load[t])
        row([(idx(t,6),cop[t]),(idx(t,8),1)],heat[t],heat[t])
        # H8: H[t+1] = (1-sd)H[t] + dt(eta_el Pel/eH - Pfc/(eta_fc eH) - d + qH)
        row([(Hi(t+1),1),(Hi(t),-(1-sd)),(idx(t,4),-p['dt']*p['eta_el']/p['e_H']),
             (idx(t,5),p['dt']/(p['eta_fc']*p['e_H'])),(idx(t,7),-p['dt'])],-p['dt']*h2d[t],-p['dt']*h2d[t])
        row([(idx(t,1),1),(idx(t,2),-1),(idx(t,3),-1),(idx(t,5),-1)],-INF,0.0)   # H1 export<=generation
        if t>0: row([(idx(t,4),1),(idx(t-1,4),-1)],-p['R_el'],p['R_el'])
    h.addRows(len(rl),np.array(rl),np.array(ru),len(ind),np.array(starts),np.array(ind,dtype=np.int32),np.array(val))
    h.run()
    st=h.modelStatusToString(h.getModelStatus())                               # H7 status check
    if st!='Optimal':
        res=(None,None) if return_sched else None
        if use_cache and not return_sched: _LP_CACHE[ck]=None
        return res
    start_cost=sum(p['cstart']*max(0,uel[t]-(uel[t-1] if t>0 else 0)) for t in range(T))
    J=h.getObjectiveValue()+start_cost
    if return_sched: return J,np.array(h.getSolution().col_value)
    if use_cache: _LP_CACHE[ck]=J
    return J

# ============================ exact MILP (H6 optional mutual-excl, H7 status) ============================
def milp_highs(inst,p=PARAMS,time_limit=60.0,mutual_excl=None):
    if mutual_excl is None: mutual_excl=not CONFIG['allow_simultaneous_el_fc']
    T=inst['T']; load,sol,wnd,price=inst['load'],inst['solar'],inst['wind'],inst['price']
    heat,cop,h2d=inst['heat'],inst['cop'],inst['h2d']
    h=highspy.Highs(); h.setOptionValue('output_flag',False); h.setOptionValue('time_limit',time_limit)
    nv=9; idx=lambda t,j:t*nv+j; baseH=T*nv; Hi=lambda t:baseH+t
    baseB=baseH+(T+1); Uel=lambda t:baseB+t; Ufc=lambda t:baseB+T+t; Vel=lambda t:baseB+2*T+t; N=baseB+3*T
    lo=np.zeros(N); up=np.full(N,INF); cost=np.zeros(N); integ=np.zeros(N,dtype=np.int32)
    for t in range(T):
        up[idx(t,0)]=p['Pgrid_max']; up[idx(t,1)]=p['Pgrid_max']
        up[idx(t,2)]=max(sol[t],0); up[idx(t,3)]=max(wnd[t],0)
        up[idx(t,4)]=p['Pel_max']; up[idx(t,5)]=p['Pfc_max']; up[idx(t,6)]=p['Php_max']; up[idx(t,7)]=h2d[t]
        cost[idx(t,0)]=price[t]*p['dt']; cost[idx(t,1)]=-p['csell']*max(price[t],0)*p['dt']
        cost[idx(t,4)]=p['cdeg_el']; cost[idx(t,5)]=p['cdeg_fc']; cost[idx(t,7)]=p['lamH']; cost[idx(t,8)]=p['lamQ']
    for t in range(T+1): up[Hi(t)]=p['Hmax']
    lo[Hi(0)]=up[Hi(0)]=p['H0']; lo[Hi(T)]=max(p['Hterm'],0.0)
    for t in range(T):
        for b in (Uel(t),Ufc(t),Vel(t)): up[b]=1.0; integ[b]=1
        cost[Vel(t)]=p['cstart']
    h.addVars(N,lo,up); h.changeColsCost(N,np.arange(N),cost); h.changeColsIntegrality(N,np.arange(N),integ)
    starts=[];ind=[];val=[];rl=[];ru=[]
    def row(pairs,l,u):
        starts.append(len(ind))
        for c,v in pairs: ind.append(int(c)); val.append(float(v))
        rl.append(l); ru.append(u)
    sd=p['self_discharge']
    for t in range(T):
        row([(idx(t,2),1),(idx(t,3),1),(idx(t,0),1),(idx(t,5),1),(idx(t,4),-1),(idx(t,6),-1),(idx(t,1),-1)],load[t],load[t])
        row([(idx(t,6),cop[t]),(idx(t,8),1)],heat[t],heat[t])
        row([(Hi(t+1),1),(Hi(t),-(1-sd)),(idx(t,4),-p['dt']*p['eta_el']/p['e_H']),
             (idx(t,5),p['dt']/(p['eta_fc']*p['e_H'])),(idx(t,7),-p['dt'])],-p['dt']*h2d[t],-p['dt']*h2d[t])
        row([(idx(t,4),1),(Uel(t),-p['Pel_max'])],-INF,0.0); row([(idx(t,4),1),(Uel(t),-p['Pel_min'])],0.0,INF)
        row([(idx(t,5),1),(Ufc(t),-p['Pfc_max'])],-INF,0.0); row([(idx(t,5),1),(Ufc(t),-p['Pfc_min'])],0.0,INF)
        if t==0: row([(Vel(t),1),(Uel(t),-1)],0.0,INF)
        else: row([(Vel(t),1),(Uel(t),-1),(Uel(t-1),1)],0.0,INF)
        if t>0: row([(idx(t,4),1),(idx(t-1,4),-1)],-p['R_el'],p['R_el'])
        row([(idx(t,1),1),(idx(t,2),-1),(idx(t,3),-1),(idx(t,5),-1)],-INF,0.0)
        if mutual_excl: row([(Uel(t),1),(Ufc(t),1)],-INF,1.0)   # H6 u_el+u_fc<=1
    h.addRows(len(rl),np.array(rl),np.array(ru),len(ind),np.array(starts),np.array(ind,dtype=np.int32),np.array(val))
    h.run(); st=h.modelStatusToString(h.getModelStatus())
    if st!='Optimal':                                           # H7: do not read garbage
        return dict(J=None,status=st,uel=None,ufc=None)
    solv=np.array(h.getSolution().col_value); info=h.getInfo()
    return dict(J=h.getObjectiveValue(),status=st,
                bound=getattr(info,'mip_dual_bound',None),gap=getattr(info,'mip_gap',None),
                uel=tuple(int(round(solv[Uel(t)])) for t in range(T)),
                ufc=tuple(int(round(solv[Ufc(t)])) for t in range(T)))

def milp_exact(inst,p=PARAMS):
    T=inst['T']
    if 2**(2*T)<=4096:
        best=None; feas=0
        for bits in itertools.product([0,1],repeat=2*T):
            uel=bits[:T]; ufc=bits[T:]
            if (not CONFIG['allow_simultaneous_el_fc']) and any(a and b for a,b in zip(uel,ufc)): continue
            c=lp_recourse(inst,uel,ufc,p)
            if c is not None:
                feas+=1
                if best is None or c<best[0]: best=(c,uel,ufc)
        return dict(J=best[0],uel=best[1],ufc=best[2],feasible_patterns=feas,total_patterns=2**(2*T),method='enum')
    return milp_highs(inst,p)

def balance_residuals(inst,sched,p=PARAMS):
    T=inst['T']; nv=9; idx=lambda t,j:t*nv+j; Hi=lambda t:T*nv+t
    load,sol,wnd=inst['load'],inst['solar'],inst['wind']; heat,cop,h2d=inst['heat'],inst['cop'],inst['h2d']; sd=p['self_discharge']
    re=rh=rH=0.0
    for t in range(T):
        e=sched[idx(t,2)]+sched[idx(t,3)]+sched[idx(t,0)]+sched[idx(t,5)]-sched[idx(t,4)]-sched[idx(t,6)]-sched[idx(t,1)]-load[t]
        hq=cop[t]*sched[idx(t,6)]+sched[idx(t,8)]-heat[t]
        Hb=sched[Hi(t+1)]-(1-sd)*sched[Hi(t)]-p['dt']*(p['eta_el']*sched[idx(t,4)]/p['e_H']-sched[idx(t,5)]/(p['eta_fc']*p['e_H'])-h2d[t]+sched[idx(t,7)])
        re=max(re,abs(e)); rh=max(rh,abs(hq)); rH=max(rH,abs(Hb))
    return dict(elec=re,heat=rh,h2=rH)

def demand_audit(inst,uel,ufc,p=PARAMS):
    T=inst['T']; _,s=lp_recourse(inst,uel,ufc,p,return_sched=True,use_cache=False)
    nv=9; idx=lambda t,j:t*nv+j
    uH=sum(s[idx(t,7)] for t in range(T)); uQ=sum(s[idx(t,8)] for t in range(T))
    simult_grid=sum(1 for t in range(T) if s[idx(t,0)]>1e-6 and s[idx(t,1)]>1e-6)
    simult_elfc=sum(1 for t in range(T) if uel[t] and ufc[t])
    return dict(pct_H2_served=round(100*(1-uH/max(inst['h2d'].sum(),1e-9)),3),
                pct_heat_served=round(100*(1-uQ/max(inst['heat'].sum(),1e-9)),3),
                simultaneous_grid_hrs=simult_grid, simultaneous_el_fc_hrs=simult_elfc)

# ============================ interaction graph ============================
def build_interaction_graph(inst):
    T=inst['T']; G=nx.Graph(); h2d=inst['h2d']; H2=max(h2d.mean(),1e-6)
    for t in range(T): G.add_node(('el',t)); G.add_node(('fc',t))
    for t in range(T):
        G.add_edge(('el',t),('fc',t),weight=1.0,kind='bus')
        if t>0: G.add_edge(('el',t),('el',t-1),weight=0.8,kind='ramp')
    for t in range(T):
        for s in range(t+1,T):
            w=np.exp(-(s-t)/max(T/3,1))*(h2d[s]/H2)
            if w>0.05: G.add_edge(('el',t),('fc',s),weight=round(0.6*w,4),kind='storage')
    ws=[d['weight'] for *_,d in G.edges(data=True)]; mx=max(ws) if ws else 1
    for *_,d in G.edges(data=True): d['weight']=round(d['weight']/mx,4)
    return G

# ============================ H4: partitioners that ALL enforce the qubit cap ============================
def _enforce_cap(parts, cap_nodes):
    """Split any block exceeding cap_nodes into chunks of <= cap_nodes (deterministic)."""
    from collections import defaultdict
    groups=defaultdict(list)
    for n,b in parts.items(): groups[b].append(n)
    newp={}; nid=0
    for b,nodes in groups.items():
        nodes=sorted(nodes,key=lambda x:(x[1],x[0]))
        for i in range(0,len(nodes),cap_nodes):
            for n in nodes[i:i+cap_nodes]: newp[n]=nid
            nid+=1
    return newp
def partition_temporal(G,T,block):  return {n:(n[1]//block) for n in G.nodes()}
def partition_carrier(G,T,block):   return {n:(0 if n[0]=='el' else 1)*((T//block)+1)+(n[1]//block) for n in G.nodes()}
def partition_random(G,T,block,seed=0):
    rng=np.random.default_rng(seed); nodes=list(G.nodes()); rng.shuffle(nodes)
    k=max(1,len(nodes)//(2*block)); return {n:i%k for i,n in enumerate(nodes)}
def partition_h2aware(G,T,block):
    target=2*block; parts={}; nid=[0]
    def rec(sub):
        if len(sub)<=target or len(sub)<=2:
            pid=nid[0]; nid[0]+=1
            for n in sub: parts[n]=pid
            return
        H=G.subgraph(sub)
        try: A,B=nx.algorithms.community.kernighan_lin_bisection(H,weight='weight',seed=1)
        except Exception: A=set(list(sub)[:len(sub)//2]); B=set(sub)-A
        rec(list(A)); rec(list(B))
    rec(list(G.nodes())); return parts
def partition_metis_like(G,T,block):
    comms=list(nx.algorithms.community.greedy_modularity_communities(G,weight='weight'))
    parts={}
    for i,c in enumerate(comms):
        for n in c: parts[n]=i
    return parts
def get_partition(name,G,T,block):
    cap=2*block
    raw={'temporal':partition_temporal,'carrier':partition_carrier,'random':partition_random,
         'h2aware':partition_h2aware,'metis-like':partition_metis_like}[name]
    parts=raw(G,T,block,0) if name=='random' else raw(G,T,block)
    return _enforce_cap(parts,cap)   # H4: hard cap for EVERY partitioner
def partition_metrics(G,parts):
    cut=tot=0.0; interface=set()
    for u,v,d in G.edges(data=True):
        tot+=d['weight']
        if parts[u]!=parts[v]: cut+=d['weight']; interface.add(u); interface.add(v)
    sizes={}
    for n,b in parts.items(): sizes[b]=sizes.get(b,0)+1
    s=list(sizes.values())
    return dict(cut_ratio=round(cut/tot,4) if tot else 0,n_blocks=len(sizes),
                max_block=max(s),min_block=min(s),interface_size=len(interface))

# ============================ QUBO surrogate (H11: held-out fidelity) ============================
def build_qubo_surrogate(inst,p=PARAMS,seed=0,holdout=0.3):
    """Fit degree-2 QUBO surrogate. Uses UNIQUE bitstrings with a disjoint train/test split
    (no leakage; verified). For n<=12 enumerates all 2^n; else samples unique rows."""
    T=inst['T']; n=2*T; rng=np.random.default_rng(seed)
    if n<=12:
        Z=np.array(list(itertools.product([0,1],repeat=n)))
    else:
        seen=set(); rows=[]
        while len(rows)<min(2**n,2000):
            z=tuple(int(x) for x in rng.integers(0,2,n))
            if z not in seen: seen.add(z); rows.append(z)
        Z=np.array(rows)
    raw=[lp_recourse(inst,tuple(z[:T]),tuple(z[T:]),p) for z in Z]
    fc=[c for c in raw if c is not None]; cmin,cmax=min(fc),max(fc); rc=max(cmax-cmin,1.0)
    inf_t=cmax+3*rc; y=np.array([c if c is not None else inf_t for c in raw])
    idx=np.arange(len(Z)); rng.shuffle(idx); cut=int((1-holdout)*len(idx)); tr,te=idx[:cut],idx[cut:]
    assert len(set(map(tuple,Z[tr]))&set(map(tuple,Z[te])))==0, 'train/test overlap!'  # zero-leakage check
    def feats(ii):
        cols=[np.ones(len(ii))]
        for i in range(n): cols.append(Z[ii,i].astype(float))
        for i in range(n):
            for j in range(i+1,n): cols.append((Z[ii,i]*Z[ii,j]).astype(float))
        return np.array(cols).T
    A=feats(tr); coef,*_=np.linalg.lstsq(A,y[tr],rcond=None)
    Q=np.zeros((n,n)); c0=coef[0]
    for i in range(n): Q[i,i]=coef[1+i]
    kk=1+n
    for i in range(n):
        for j in range(i+1,n): Q[i,j]=coef[kk]; kk+=1
    pred_te=feats(te)@coef; oos_rmse=float(np.sqrt(np.mean((pred_te-y[te])**2)))
    feas_te=np.array([raw[i] is not None for i in te])
    sp=float(spearmanr(pred_te[feas_te],y[te][feas_te]).correlation) if feas_te.sum()>2 else np.nan
    return Q,c0,n,dict(oos_rmse=oos_rmse,spearman_oos=sp,n_train=len(tr),n_test=len(te),unique=True)

def qubo_energy(Q,c0,z):
    z=np.asarray(z,float); e=c0; n=len(z)
    for i in range(n):
        e+=Q[i,i]*z[i]
        for j in range(i+1,n): e+=Q[i,j]*z[i]*z[j]
    return float(e)
def qubo_to_ising(Q,c0):
    n=Q.shape[0]; h=np.zeros(n); J=np.zeros((n,n)); const=c0
    for i in range(n):
        h[i]+=-Q[i,i]/2; const+=Q[i,i]/2
        for j in range(i+1,n): J[i,j]+=Q[i,j]/4; h[i]+=-Q[i,j]/4; h[j]+=-Q[i,j]/4; const+=Q[i,j]/4
    return h,J,const
def energy_vector(efn,n): return np.array([efn([(k>>(n-1-q))&1 for q in range(n)]) for k in range(2**n)])

# ============================ fast exact QAOA (X mixer) ============================
def fast_qaoa_probs(evec,params,p,n):
    g=params[:p]; b=params[p:]; psi=np.ones(2**n,dtype=complex)/np.sqrt(2**n); shp=[2]*n
    for l in range(p):
        psi=psi*np.exp(-1j*g[l]*evec); psi=psi.reshape(shp); cb,sb=np.cos(b[l]),np.sin(b[l])
        for q in range(n): psi=cb*psi-1j*sb*np.flip(psi,axis=q)
        psi=psi.reshape(-1)
    return np.abs(psi)**2
def optimize_qaoa_x(evec,p,n,restarts=4,seed=0,maxiter=200):
    rng=np.random.default_rng(seed); best=None; f=lambda x:float(fast_qaoa_probs(evec,x,p,n)@evec)
    for _ in range(restarts):
        r=minimize(f,rng.uniform(0,np.pi,2*p),method='COBYLA',options={'maxiter':maxiter})
        if best is None or r.fun<best.fun: best=r
    probs=fast_qaoa_probs(evec,best.x,p,n); return dict(params=best.x,probs=probs,nfev=best.nfev)
def sample_bits(probs,n,shots,rng):
    ks=rng.choice(len(probs),size=shots,p=probs/probs.sum())
    return [tuple((int(k)>>(n-1-q))&1 for q in range(n)) for k in ks]

# ============================ H14: node-based hybrid on ACTUAL partition; H5 safe failure ============================
def _node_surrogate(inst,nodes,cur_uel,cur_ufc,p,seed):
    """Fit a QUBO over the block's commitment NODES (others held at current values).
    nodes: list of ('el'|'fc', t). Returns Q,c0,k and a decoder."""
    k=len(nodes); rng=np.random.default_rng(seed)
    Z=np.array(list(itertools.product([0,1],repeat=k))) if k<=10 else rng.integers(0,2,(400,k))
    def apply(z):
        tu=list(cur_uel); tf=list(cur_ufc)
        for bit,(c,t) in zip(z,nodes):
            if c=='el': tu[t]=int(bit)
            else: tf[t]=int(bit)
        return tu,tf
    raw=[]
    for z in Z:
        tu,tf=apply(z); raw.append(lp_recourse(inst,tu,tf,p))
    fc=[c for c in raw if c is not None]
    if not fc: return None
    cmin,cmax=min(fc),max(fc); rc=max(cmax-cmin,1.0); inf_t=cmax+3*rc
    y=np.array([c if c is not None else inf_t for c in raw])
    cols=[np.ones(len(Z))]
    for i in range(k): cols.append(Z[:,i].astype(float))
    for i in range(k):
        for j in range(i+1,k): cols.append((Z[:,i]*Z[:,j]).astype(float))
    A=np.array(cols).T; coef,*_=np.linalg.lstsq(A,y,rcond=None)
    Q=np.zeros((k,k)); c0=coef[0]
    for i in range(k): Q[i,i]=coef[1+i]
    kk=1+k
    for i in range(k):
        for j in range(i+1,k): Q[i,j]=coef[kk]; kk+=1
    return Q,c0,k,apply

def hybrid_solve(inst,partition,p=PARAMS,qp=3,shots=256,seed=0):
    """Decompose on the partition's actual node-blocks (H14). Each block's qubits = its node count (<=cap).
    Returns status + (uel,ufc) or None (H5). Logs resources (H13,H15)."""
    T=inst['T']; rng=np.random.default_rng(seed)
    blocks={}
    for node,b in partition.items(): blocks.setdefault(b,[]).append(node)
    node_blocks=[sorted(v,key=lambda x:(x[1],x[0])) for v in blocks.values()]
    peak=max(len(b) for b in node_blocks)   # qubits = nodes in largest block (<= cap)
    cur_uel=[0]*T; cur_ufc=[0]*T
    res=dict(circuit_evals=0,two_qubit_gates=0,recourse_calls=0,peak_qubits=peak,
             n_blocks=len(node_blocks),total_circuit_depth=0)
    for nodes in node_blocks:
        sg=_node_surrogate(inst,nodes,cur_uel,cur_ufc,p,seed)
        if sg is None: continue
        Q,c0,k,apply=sg; h,J,const=qubo_to_ising(Q,c0)
        efn=lambda z:qubo_energy(Q,c0,z); ev=energy_vector(efn,k)
        r=optimize_qaoa_x(ev,qp,k,CONFIG['restarts'],seed,CONFIG['maxiter'])
        res['circuit_evals']+=r['nfev']; res['two_qubit_gates']+=2*(k*(k-1)//2)*qp
        res['total_circuit_depth']+=(2*(k-1)+2)*qp
        loc=None
        for z in set(sample_bits(r['probs'],k,shots,rng)):
            tu,tf=apply(z); c=lp_recourse(inst,tu,tf,p); res['recourse_calls']+=1
            if c is not None and (loc is None or c<loc[0]): loc=(c,tu,tf)
        if loc: _,cur_uel,cur_ufc=loc
    pre=lp_recourse(inst,cur_uel,cur_ufc,p); res['recourse_calls']+=1
    if pre is None:
        return dict(status='infeasible',uel=None,ufc=None,cost_pre_repair=None,cost_post_repair=None,resources=res)
    c=pre; bu=list(cur_uel); bf=list(cur_ufc); improved=True
    while improved:
        improved=False
        for i in range(T):
            for arr in (bu,bf):
                arr[i]^=1; c2=lp_recourse(inst,bu,bf,p); res['recourse_calls']+=1
                if c2 is not None and c2<c-1e-9: c=c2; improved=True
                else: arr[i]^=1
    return dict(status='ok',uel=tuple(bu),ufc=tuple(bf),cost_pre_repair=pre,cost_post_repair=c,resources=res)

# ============================ H3: controlled XY vs X (SAME one-hot init) ============================
def mixer_experiment(seed=0,shots=1024):
    """One-hot electrolyser modes {off,low,high}, 3 hours -> 9 qubits.
    BOTH X and XY start from the SAME valid one-hot state (isolates mixer effect)."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    Thr=3; n=3*Thr; groups=[[3*t,3*t+1,3*t+2] for t in range(Thr)]
    rng=np.random.default_rng(seed); h=rng.normal(0,0.5,n)
    for g in groups: h[g[1]]-=0.4; h[g[2]]-=0.8
    def onehot_valid(z): return all(sum(z[q] for q in g)==1 for g in groups)
    def run(mixer):
        qc=QuantumCircuit(n)
        for g in groups: qc.x(g[0])            # SAME one-hot init for both
        beta=0.7; gamma=0.5
        for i in range(n):
            if abs(h[i])>1e-12: qc.rz(2*gamma*h[i],i)
        if mixer=='X':
            for i in range(n): qc.rx(2*beta,i)
        else:
            for g in groups:
                for a,b in zip(g,g[1:]+g[:1]): qc.rxx(2*beta,a,b); qc.ryy(2*beta,a,b)
        sv=Statevector.from_instruction(qc)
        probs=(np.abs(sv.data)**2).reshape([2]*n).transpose(list(range(n))[::-1]).reshape(-1)
        rr=np.random.default_rng(1); ks=rr.choice(len(probs),size=shots,p=probs/probs.sum())
        samp=[tuple((int(k)>>(n-1-q))&1 for q in range(n)) for k in ks]
        return float(np.mean([onehot_valid(z) for z in samp]))
    return dict(init='one-hot (both)',X_valid_rate=run('X'),XY_valid_rate=run('XY'),note='controlled for initialization (H3)')
