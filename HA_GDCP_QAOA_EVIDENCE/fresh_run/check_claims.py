"""Numerical manuscript validator. Extracts each claimed number from the manuscript via an
anchored regex and compares it to results_authoritative.json within a documented tolerance.
Detects deliberately altered numbers (run `python check_claims.py --selftest`).
Usage: python check_claims.py [--manuscript manuscript.md]  (falls back to pdftotext of the PDF)
Exit code: 0 if all PASS, 1 otherwise."""
import json, re, sys, subprocess, os

def load_manuscript(path=None):
    if path and os.path.exists(path): return open(path).read()
    if os.path.exists('manuscript.md'): return open('manuscript.md').read()
    for pdf in ['HA_GDCP_QAOA_Research_Paper.pdf','HA_GDCP_QAOA_Research_Paper(1).pdf']:
        if os.path.exists(pdf):
            return subprocess.run(['pdftotext',pdf,'-'],capture_output=True,text=True).stdout
    raise FileNotFoundError('no manuscript.md or PDF found')

def jpath(R,p):
    v=R
    for k in p.split('.'): v=v[k]
    return v

# each claim: (id, json path/literal, regex w/ 1 capture, abs tolerance, scale applied to json value)
def build_claims(R):
    return [
     ('opt_6h (EUR)',            jpath(R,'E0.opt_6h'),            r'J\^\{\*\}=([\d.]+)',                 0.01, 1),
     ('feasible_patterns',       jpath(R,'E0.feasible_patterns'),r'\$3\{,\}([\d]+)\$ are feasible',     0,    1, 3000),  # special offset
     ('neg_price_hours',         jpath(R,'data.neg_price_hours'),r'(\d+) negative-price hours',         0,    1),
     ('XY_valid_rate (%)',       jpath(R,'mixer.XY_valid_rate'), r'XY mixer keeps ([\d.]+)% of samples',0.1,  100),
     ('X_valid_rate (%)',        jpath(R,'mixer.X_valid_rate'),  r'against ([\d.]+)% for the X mixer',  0.1,  100),
     ('spearman_min',            jpath(R,'encoding.spearman_min'),r'Spearman ([\d.]+)[–-][\d.]+',       0.005,1),
     ('spearman_max',            jpath(R,'encoding.spearman_max'),r'Spearman [\d.]+[–-]([\d.]+)',       0.005,1),
     ('20-seed Wilcoxon p',      jpath(R,'stats_20seed.wilcoxon_p'),r'test gives p = ([\d.]+)',         0.01, 1),
     ('5-instance Wilcoxon p',   jpath(R,'stats_5instance.wilcoxon_p'),r'independent instances \(p=([\d.]+)\)',0.01,1),
     ('24h optimum (EUR)',       jpath(R,'H14.milp_24h'),        r'rises from ([\d.]+) € to',           0.1,  1),
     ('binding hard cost (EUR)', jpath(R,'binding.hard_cost'),   r'€ to ([\d.]+) €',                    0.5,  1),
     ('lower-bound-active hrs',  jpath(R,'binding.lower_bound_active_hrs'),r'active in (\d+) of 25',     0,    1),
     ('R_Q at T=48 (%)',         jpath(R,'scalability.T48_R_Q'), r'peak-qubit reduction of up to (\d+)%',0.6, 1),
     ('held-out max gap (%)',    jpath(R,'heldout.max_gap'),     r'maximum gap of ([\d.]+)%',           0.01, 1),
     ('binding h2aware cut',     jpath(R,'binding.h2aware_cut'), r'\(([\d.]+) versus [\d.]+',            0.005,1),
     ('binding temporal cut',   jpath(R,'binding.temporal_cut'),r'\([\d.]+ versus ([\d.]+)',            0.005,1),
    ]

def run(ms,R,verbose=True):
    claims=build_claims(R); fails=0; missing=0
    if verbose:
        print('='*78); print('NUMERICAL CLAIM CHECK  model=%s seed=%s results_sha=%s'%(
            R['_meta']['model'],R['_meta']['seed'],R['_meta']['results_sha256'][:12])); print('='*78)
    for c in claims:
        cid,jval,rx,tol,scale=c[0],c[1],c[2],c[3],c[4]; offset=c[5] if len(c)>5 else 0
        m=re.search(rx,ms)
        if not m:
            missing+=1; fails+=1
            if verbose: print(f'  [MISSING] {cid:26s} pattern not found in manuscript'); continue
        msval=float(m.group(1).replace(',',''))+offset
        exp=float(jval)*scale
        ok=abs(msval-exp)<=tol
        if not ok: fails+=1
        if verbose: print(f'  [{"PASS" if ok else "FAIL"}] {cid:26s} manuscript={msval:<10g} authoritative={exp:<10g} tol={tol}')
    if verbose:
        print('-'*78); print('RESULT:', 'ALL %d CLAIMS PASS'%len(claims) if fails==0 else f'{fails} FAIL(S) / {len(claims)}')
    return fails

def main():
    R=json.load(open('results_authoritative.json'))
    msarg=None
    if '--manuscript' in sys.argv: msarg=sys.argv[sys.argv.index('--manuscript')+1]
    ms=load_manuscript(msarg)
    if '--selftest' in sys.argv:
        # tamper: corrupt the 6h optimum in a copy; checker MUST catch it
        bad=re.sub(r'(J\^\{\*\}=)[\d.]+', r'\g<1>999.999', ms, count=1)
        print('--- SELF-TEST: injected wrong optimum (999.999); checker must FAIL ---')
        f=run(bad,R,verbose=False)
        print('tamper detected:', 'YES (checker caught it)' if f>0 else 'NO -- checker is BROKEN')
        sys.exit(0 if f>0 else 2)
    sys.exit(1 if run(ms,R)>0 else 0)

if __name__=='__main__': main()
