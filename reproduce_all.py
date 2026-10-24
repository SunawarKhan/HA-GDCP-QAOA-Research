"""SINGLE authoritative reproduction. One clean run regenerates EVERY section of
results_authoritative.json from kaggle_hagdcp.py (seed=CONFIG['seed']), with full
provenance (data SHA-256, dependency versions, seed, runtime, result checksum)."""
import json, time, itertools, hashlib, platform, sys, numpy as np
from scipy.stats import wilcoxon
import kaggle_hagdcp as K
from kaggle_hagdcp import (find_opsd, build_year, split_chrono, make_instance, milp_exact, milp_highs,
    lp_recourse, balance_residuals, demand_audit, build_interaction_graph, get_partition,
    partition_metrics, build_qubo_surrogate, qubo_to_ising, qubo_energy, energy_vector,
    optimize_qaoa_x, sample_bits, hybrid_solve, mixer_experiment, PARAMS, CONFIG)

t0=time.time(); SEED=CONFIG['seed']
def sha256_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def deps():
    import highspy,qiskit,networkx,scipy,pandas
    return dict(python=sys.version.split()[0],numpy=np.__version__,scipy=scipy.__version__,
        pandas=pandas.__version__,networkx=networkx.__version__,qiskit=qiskit.__version__,
        highspy=getattr(highspy,'__version__','?'))
def ising_energy(h,J,const,z):
    s=1-2*np.asarray(z); e=const
    for i in range(len(s)):
        e+=h[i]*s[i]
        for j in range(i+1,len(s)): e+=J[i,j]*s[i]*s[j]
    return e
def sa_candidates(inst,nn,budget,seed):
    Q,c0,_,_=build_qubo_surrogate(inst,seed=seed); efn=lambda z:qubo_energy(Q,c0,z)
    rng=np.random.default_rng(seed); z=list(rng.integers(0,2,nn)); e=efn(z); cand=set()
    for _ in range(budget):
        i=rng.integers(nn); z2=z[:]; z2[i]^=1; e2=efn(z2)
        if e2<e or rng.random()<np.exp(-(e2-e)/max(abs(e),1)): z=z2; e=e2
        cand.add(tuple(z))
    return cand

csv=find_opsd(); df=build_year(csv,seed=SEED); dev,val,test=split_chrono(df); R={}

inst=make_instance(dev,'2019-01-15 06:00',6)
ex=milp_exact(inst); hi=milp_highs(inst); _,sched=lp_recourse(inst,ex['uel'],ex['ufc'],return_sched=True)
da=demand_audit(inst,ex['uel'],ex['ufc']); br=balance_residuals(inst,sched)
R['E0']=dict(opt_6h=round(ex['J'],4),feasible_patterns=ex['feasible_patterns'],total_patterns=ex['total_patterns'],
    resid_elec=br['elec'],resid_heat=br['heat'],resid_h2=br['h2'],dual_formulation_agree=bool(abs(ex['J']-hi['J'])<1e-6),
    pct_h2_served=da['pct_H2_served'],pct_heat_served=da['pct_heat_served'],
    simultaneous_grid_hrs=da['simultaneous_grid_hrs'],simultaneous_el_fc_hrs=da['simultaneous_el_fc_hrs']); print('[1/10] E0')

R['data']=dict(rows=len(df),neg_price_hours=int((df['price_eur_kwh']<0).sum()),dev=len(dev),val=len(val),test=len(test))

neg_days=sorted(set(df[df['price_eur_kwh']<0].index.floor('D'))); stat={}
for d in neg_days[:20]:
    st=milp_highs(make_instance(df,str(d),24))['status']; stat[st]=stat.get(st,0)+1
R['H1']=dict(days_checked=min(20,len(neg_days)),status_breakdown=stat,unbounded=stat.get('Unbounded',0)); print('[2/10] H1')

Q,c0,n,fit=build_qubo_surrogate(inst,seed=SEED); h,J,const=qubo_to_ising(Q,c0)
qerr=max(abs(qubo_energy(Q,c0,z)-ising_energy(h,J,const,z)) for z in itertools.product([0,1],repeat=n))
sp=[]; rm=[]
for day,spl in [('2019-01-15 06:00',dev),('2019-05-20 06:00',dev),('2019-09-12 06:00',val)]:
    _,_,_,f=build_qubo_surrogate(make_instance(spl,day,6),seed=SEED); sp.append(f['spearman_oos']); rm.append(f['oos_rmse'])
R['encoding']=dict(qubo_ising_maxerr=qerr,spearman_min=round(min(sp),3),spearman_max=round(max(sp),3),
    oos_rmse_min=round(min(rm),2),oos_rmse_max=round(max(rm),2))
allz=list(itertools.product([0,1],repeat=12)); true=[lp_recourse(inst,z[:6],z[6:]) for z in allz]
fe=[(z,c) for z,c in zip(allz,true) if c is not None]; pred=[qubo_energy(Q,c0,z) for z,_ in fe]; tc=[c for _,c in fe]
ot=np.argsort(tc); op=np.argsort(pred)
R['surrogate']=dict(top1_recall=int(len(set(ot[:1])&set(op[:1]))),top5_recall=round(len(set(ot[:5])&set(op[:5]))/5,2),
    regret_eur=round(float(tc[op[0]]-tc[ot[0]]),3)); print('[3/10] encoding+surrogate')

mx=mixer_experiment(seed=SEED)
R['mixer']=dict(X_valid_rate=round(mx['X_valid_rate'],4),XY_valid_rate=round(mx['XY_valid_rate'],4),init='one-hot both (controlled)'); print('[4/10] mixer')

R['partition']={}
for T in [6,12,24,48]:
    G=build_interaction_graph(make_instance(dev,'2019-01-15 00:00',T))
    R['partition'][f'T{T}']=dict(h2aware_cut=partition_metrics(G,get_partition('h2aware',G,T,6))['cut_ratio'],
        temporal_cut=partition_metrics(G,get_partition('temporal',G,T,6))['cut_ratio'],R_Q=round(100*(1-min(12,2*T)/(2*T)),1))
print('[5/10] partition')

base24=make_instance(dev,'2019-01-15 00:00',24)
def bind(mult,H0,Hterm,Hmax):
    i=dict(base24); i['h2d']=base24['h2d']*mult; p=dict(PARAMS); p['H0']=H0; p['Hterm']=Hterm; p['Hmax']=Hmax
    r=milp_highs(i,p); _,s=lp_recourse(i,r['uel'],r['ufc'],p,return_sched=True); Hi=lambda t:24*9+t
    Hs=np.array([s[Hi(t)] for t in range(25)]); return r['J'],int((Hs<=p['Hmin']+1e-6).sum()),i
Jb,loact,ib=bind(5.0,2,24,28); Jbase,_,_=bind(1.0,10,10,50); Gb=build_interaction_graph(ib); imps=[]
for day in ['2019-01-15 00:00','2019-02-10 00:00','2019-03-05 00:00']:
    b=make_instance(dev,day,24); i=dict(b); i['h2d']=b['h2d']*5.0; G=build_interaction_graph(i)
    t=partition_metrics(G,get_partition('temporal',G,24,6))['cut_ratio']; hh=partition_metrics(G,get_partition('h2aware',G,24,6))['cut_ratio']; imps.append(round(100*(t-hh)/t,1))
R['binding']=dict(base_cost=round(Jbase,1),hard_cost=round(Jb,1),lower_bound_active_hrs=loact,
    h2aware_cut=partition_metrics(Gb,get_partition('h2aware',Gb,24,6))['cut_ratio'],
    temporal_cut=partition_metrics(Gb,get_partition('temporal',Gb,24,6))['cut_ratio'],cut_improvement_pct=imps); print('[6/10] binding')

ref24=milp_highs(base24)['J']; G24=build_interaction_graph(base24); R['H14']={'milp_24h':round(ref24,2)}
for nm in ['temporal','h2aware','random','carrier','metis-like']:
    hy=hybrid_solve(base24,get_partition(nm,G24,24,6),qp=2,shots=64,seed=1)
    R['H14'][nm]=dict(gap=round(100*(hy['cost_post_repair']-ref24)/abs(ref24),3),recourse=hy['resources']['recourse_calls'],
        peak_qubits=hy['resources']['peak_qubits'],two_qubit_gates=hy['resources']['two_qubit_gates'],circuit_evals=hy['resources']['circuit_evals'])
print('[7/10] H14')

T=6; LB=ex['J']; gap=lambda c:100*(c-LB)/abs(LB); ev=energy_vector(lambda z:qubo_energy(Q,c0,z),n)
qa=[]; sa=[]
for sd in range(20):
    r=optimize_qaoa_x(ev,3,n,4,sd,200); qs=set(sample_bits(r['probs'],n,256,np.random.default_rng(100+sd)))
    qf=[lp_recourse(inst,z[:T],z[T:]) for z in qs]; qa.append(gap(min([c for c in qf if c is not None])))
    sc=sa_candidates(inst,n,256,sd); sf=[lp_recourse(inst,z[:T],z[T:]) for z in sc]; sa.append(gap(min([c for c in sf if c is not None])))
R['stats_20seed']=dict(instance='2019-01-15 06:00',QAOA_median=round(float(np.median(qa)),3),SA_median=round(float(np.median(sa)),3),wilcoxon_p=round(float(wilcoxon(qa,sa).pvalue),4),n=20)
qg=[]; sg=[]
for day in ['2019-01-15 06:00','2019-03-10 06:00','2019-05-20 06:00','2019-07-15 06:00','2019-08-25 06:00']:
    ins=make_instance(dev,day,6); lb=milp_exact(ins)['J']; g=lambda c:100*(c-lb)/abs(lb)
    Qi,ci,ni,_=build_qubo_surrogate(ins,seed=SEED); evi=energy_vector(lambda z:qubo_energy(Qi,ci,z),ni)
    r=optimize_qaoa_x(evi,3,ni,4,1,200); qs=set(sample_bits(r['probs'],ni,256,np.random.default_rng(1)))
    qg.append(g(min([c for c in (lp_recourse(ins,z[:6],z[6:]) for z in qs) if c is not None])))
    sc=sa_candidates(ins,ni,256,1); sg.append(g(min([c for c in (lp_recourse(ins,z[:6],z[6:]) for z in sc) if c is not None])))
R['stats_5instance']=dict(QAOA_median=round(float(np.median(qg)),3),SA_median=round(float(np.median(sg)),3),wilcoxon_p=round(float(wilcoxon(qg,sg).pvalue),4),n=5); print('[8/10] statistics')

qs=list(set(sample_bits(optimize_qaoa_x(ev,3,n,4,1,200)['probs'],n,512,np.random.default_rng(1))))
qf=[lp_recourse(inst,z[:6],z[6:]) for z in qs]; qff=[c for c in qf if c is not None]
R['E4']=dict(LB_6h=round(LB,4),QAOA_feas_rate=round(len(qff)/len(qs),3),QAOA_gap=round(gap(min(qff)),3))
held=[]
for day in ['2019-11-10 06:00','2019-12-05 06:00','2019-12-20 06:00']:
    ins=make_instance(test,day,6); exi=milp_exact(ins); G=build_interaction_graph(ins)
    hy=hybrid_solve(ins,get_partition('h2aware',G,6,6),qp=3,shots=256,seed=1)
    held.append(round(100*(hy['cost_post_repair']-exi['J'])/abs(exi['J']),3))
R['heldout']=dict(gaps=held,max_gap=max(held)); print('[9/10] E4+heldout')

G48=build_interaction_graph(make_instance(dev,'2019-01-15 00:00',48))
hy48=hybrid_solve(make_instance(dev,'2019-01-15 00:00',48),get_partition('temporal',G48,48,6),qp=2,shots=32,seed=1)
R['scalability']=dict(T48_R_Q=round(100*(1-12/96),1),T48_peak_qubits=hy48['resources']['peak_qubits'],
    T48_two_qubit_gates=hy48['resources']['two_qubit_gates'],T48_circuit_evals=hy48['resources']['circuit_evals']); print('[10/10] scalability')

R['_meta']=dict(model='kaggle_hagdcp.py',seed=SEED,timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
    runtime_s=round(time.time()-t0,1),dataset_file=csv,dataset_sha256=sha256_file(csv),dependencies=deps(),
    params={k:PARAMS[k] for k in PARAMS},sections=[k for k in R if k!='_meta'])
content=json.dumps({k:v for k,v in R.items() if k!='_meta'},sort_keys=True,default=float).encode()
R['_meta']['results_sha256']=hashlib.sha256(content).hexdigest()
json.dump(R,open('results_authoritative.json','w'),indent=2,default=float)
print('\nWROTE results_authoritative.json (%d sections, %.1fs)'%(len(R['_meta']['sections']),R['_meta']['runtime_s']))
print('sections:',R['_meta']['sections'])
