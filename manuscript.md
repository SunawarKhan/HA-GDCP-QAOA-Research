---
title: "Qubit-Efficient Graph-Decomposed Quantum Approximate Optimization for Hydrogen-Integrated Multi-Energy Systems: A Constraint-Preserving Hybrid Quantum–Classical Framework with Verified Energy Scheduling and Computational Resource Analysis"
geometry: margin=1in
fontsize: 11pt
---

**Keywords:** quantum approximate optimization; QUBO/Ising encoding; graph decomposition; hydrogen-integrated multi-energy systems; constraint-preserving mixers; hybrid quantum–classical scheduling

# Abstract

Hydrogen-integrated multi-energy systems couple electricity, heat, and hydrogen storage, producing mixed-integer scheduling problems whose binary commitment decisions and hour-to-hour storage coupling scale poorly for near-term quantum hardware. This study develops and empirically evaluates a hydrogen-aware, graph-decomposed, constraint-preserving hybrid quantum–classical framework (HA-GDCP-QAOA) and asks whether structured quantum sampling adds measurable value over strong classical methods under matched budgets. A reproducible electricity–heat–hydrogen benchmark is built from the real 2019 German Open Power System Data time series (8,760 validated hourly records, 211 negative-price hours), combined with a documented synthetic thermal/COP model and simulated hydrogen demand that are explicitly flagged as non-observational. A mixed-integer linear program (MILP) is formulated and validated: at the optimum the electricity, heat, and hydrogen mass-balance residuals are at machine precision (≤6×10⁻¹⁴), an independent binary enumeration with LP recourse reproduces the branch-and-bound MILP optimum exactly (both via HiGHS), and 100% of hydrogen and heat demand is served with a bounded, arbitrage-free dispatch. A factor-graph interaction model, five partitioners, certified infeasibility-based variable fixing, and a least-squares QUBO surrogate are implemented; the QUBO↔Ising transform is verified to 10⁻¹² and the constraint-preserving XY mixer preserves the one-hot operating sector in 100% of samples versus 6.25% for the standard X mixer. Across horizons T=6–48 h, temporal decomposition holds the peak logical-qubit requirement at twelve while the monolithic encoding grows as 2T, a verified peak-qubit reduction of up to 88%, and the hybrid matches the exact MILP operating cost (optimality gap ≈0%). Regenerated from the corrected implementation, quantum sampling shows **no statistically significant advantage** over simulated annealing either across twenty seeds on one instance (median gap 0.228% vs 0.415%, Wilcoxon p=0.33) or across five independent instances (p=0.625), and after classical single-flip repair the two generators tie at the optimum. In a deliberately storage-binding regime the hydrogen-aware partitioner does improve the decomposition cut over temporal blocking (0.382 versus 0.432). The QUBO surrogate tracks true cost in rank (Spearman 0.912–0.930) but has zero top-5 recall, confirming that it is a coarse guide whose candidates must be vetted by exact recourse. We therefore claim no quantum advantage: the robust contributions are the structural peak-qubit reduction, the constraint-preserving mixer, and a reproducible matched-budget benchmark in which classical recourse is shown to dominate final quality. All core results were independently re-derived from the released modules; the benchmark, code, and artifacts are released for reproducibility.

# 1. Introduction

## 1.1. Context and Motivation

The decarbonisation of energy supply increasingly relies on multi-energy systems in which electricity, heat, and hydrogen are produced, converted, and stored within a single coordinated facility. Scheduling such systems is intrinsically a mixed-integer optimisation problem: electrolysers and fuel cells carry binary commitment states, hydrogen inventory couples decisions across the entire horizon through a mass-balance recurrence, and the objective mixes time-varying electricity prices with degradation and shortage penalties. Classical mixed-integer linear programming (MILP) solves these problems reliably at the scales considered here, yet interest has grown in whether quantum optimisation heuristics—chief among them the Quantum Approximate Optimization Algorithm (QAOA) [1]—might eventually contribute to harder instances. The central obstacle is resource: a naïve binary encoding of a scheduling horizon of length T requires a number of qubits that grows linearly with T and produces circuits whose depth and two-qubit gate count quickly exceed the coherence budgets of near-term devices [2].

Hydrogen inventory deserves particular attention because it is the feature that makes decomposition genuinely hard rather than merely inconvenient. Unlike a purely spatial coupling—two buses that exchange power within the same hour—storage introduces a *recurrence*: the inventory at hour $t+1$ depends on the inventory at hour $t$, so a decision taken early in the horizon constrains what is feasible much later. A naïve temporal partition that cuts the horizon into independent windows therefore risks producing block-optimal schedules that, when concatenated, violate the global inventory bound or the terminal-inventory requirement, because the windows cannot see one another's effect on the shared tank. This is qualitatively different from the electricity bus, whose balance is instantaneous and local in time, or from the heat balance, which in our model has no inter-temporal state. The methodological tension is thus specific and sharp: the very structure that a decomposition would most like to sever—the long temporal storage arcs—is the structure whose violation most directly destroys feasibility. A credible decomposition must therefore either weight those arcs so the partitioner is reluctant to cut them, or reconcile them explicitly at the interface, or both; the framework developed here does both.

Graph decomposition is an attractive response, because it replaces one large optimisation with several small ones whose peak qubit requirement is set by the largest block rather than by the whole horizon. Decomposition is not free, however: splitting a coupled problem can sever exactly the interactions that make a schedule feasible, and nowhere is this sharper than for hydrogen inventory, which carries state forward in time and therefore binds blocks that a purely spatial or carrier-based partition would separate. The scientific question is consequently a trade-off: how much peak-qubit saving can decomposition deliver before the coordination burden and the loss of global coupling degrade feasibility and cost? The present work treats that question as primarily a computer-science problem—how to construct the interaction graph, choose separators, preserve constraints within quantum subproblems, and coordinate the pieces—while using a physically grounded energy model to supply realistic structure and an honest feasibility test. Throughout, any quantum benefit is treated as a falsifiable hypothesis rather than a presumed outcome.

## 1.2. Key Contributions

In line with Research Gaps G1–G5 identified in Section 2.2, the main contributions of this work may be summarized as follows:

**C1 — Addresses G1 and G2:** We construct a hydrogen-aware variable-interaction graph in which temporal storage arcs are weighted by the hydrogen demand they carry forward, and a qubit-constrained partitioning objective that caps block size (enforced for every partitioner). The construction improves graph-cut quality over temporal, random, and carrier partitions under binding storage. We report, however, a decisive negative result: when the hybrid solver decomposes on the *actual* partition output, **all** partitions—including random—reach the exact optimum after classical repair, so the hydrogen-aware graph does not yield an end-to-end scheduling advantage in our pipeline. C1 is therefore supported as a graph-construction result but not as an end-to-end optimisation gain.

**C2 — Addresses G2 and G3:** We implement certified binary-variable reduction based strictly on infeasibility certificates from an exact solver, and we verify the QUBO/Ising encoding against exhaustive enumeration. We deliberately separate *certified* reduction (which, on the flexible grid-connected benchmark, fixes no variables) from *structural* reduction obtained by decomposition, rather than conflating heuristic elimination with provable equivalence.

**C3 — Addresses G3 and G4:** We implement a constraint-preserving local QAOA using an XY mixer that provably conserves the one-hot operating-mode sector, and a classical interface-coordination mechanism that evaluates every candidate against the original physical model through continuous recourse. We prove the invariant the mixer actually preserves and are explicit that it does not, by itself, enforce global hydrogen feasibility.

**C4 — Addresses G4 and G5:** We perform full-system feasibility verification—every accepted schedule is re-checked against the original MILP constraints—and matched quantum–classical benchmarking in which the quantum sampler is compared against simulated annealing, local search, exact MILP, and a quantum-free optimiser operating on the identical surrogate with an identical candidate budget.

**C5 — Addresses G1 and G5:** We release a reproducible electricity–heat–hydrogen benchmark that cleanly distinguishes observed, modelled, and simulated data, together with statistical experiments over twenty seeds and measured resource–quality trade-offs, so that the structural qubit savings and the (modest) optimisation effect of quantum sampling can be independently reproduced and audited.

## 1.3. Structure of the Article

The article opens with the motivation and contributions above and then reviews the relevant literature on quantum optimisation, constraint-preserving encodings, graph decomposition, and hydrogen-integrated scheduling, from which five research gaps are distilled and mapped to the contributions. The methodology that follows develops the benchmark and its provenance, the mixed-integer physical model, the hydrogen-aware interaction graph and its partitioning, certified reduction, the QUBO/Ising transformation, the constraint-preserving quantum circuits, and the classical coordination that ties the pieces together, with pseudocode and complexity analysis for each stage. The results report the executed experiments in the order the gates require—data and model audit, encoding correctness, decomposition and qubit accounting, mixer behaviour, the matched method comparison, sensitivity and ablation analyses, a twenty-seed statistical study, scalability, and held-out temporal generalisation—followed by an extended discussion that interprets the measured trade-offs, compares them with prior work, separates structural savings from optimisation effects, and states the limitations candidly. The article closes with a recapitulation of the verified findings and a set of concrete extensions.

# 2. Related Works

## 2.1. Current Research

QAOA was introduced by Farhi, Goldstone and Gutmann as a parameterised family of alternating cost and mixing unitaries whose approximation quality improves with circuit depth p [1]. Its practical behaviour at low depth, parameter-setting heuristics, and performance limits have since been studied extensively [8, 9], and comprehensive surveys now map the algorithm's landscape and its sensitivity to problem structure and noise [10]. The encoding of combinatorial problems as quadratic unconstrained binary optimisation (QUBO) and equivalent Ising Hamiltonians rests on the mappings catalogued by Lucas for the full range of NP problems [3] and on the QUBO modelling tradition summarised by Glover and colleagues [11]. Because penalty-based QUBO encodings convert hard constraints into soft objective terms whose weights must be calibrated, a parallel line of work replaces penalties with constraint-preserving mixers: the quantum alternating operator ansatz of Hadfield et al. generalises the mixer to conserve a feasible subspace [2], and XY-type mixers in particular preserve Hamming weight within one-hot groups [12]. These ideas are established; our use of them is not claimed as novel in itself.

Quantum optimisation for energy systems has been surveyed as an emerging but still pre-advantage field, with scheduling, unit commitment, and grid problems identified as natural targets whose constraint structure is demanding [13]. Classical decomposition and recourse—Benders-type and augmented-Lagrangian coordination, and the alternating direction method of multipliers [14]—provide the template for our interface coordination, with the important caveat that convergence guarantees for convex problems do not transfer to a nonconvex discrete master. Graph partitioning itself is a mature field; multilevel partitioners such as METIS minimise edge cut subject to balance [15], and we compare against modularity-based community detection as an accessible surrogate. On the classical-baseline side, simulated annealing [16] and local search remain strong and cheap on the instance sizes where ideal statevector simulation is possible, which is precisely why a fair comparison must match candidate budgets. Finally, the energy-systems context is grounded in open data: the Open Power System Data time series provide validated European electricity load, generation, and prices [4], the When2Heat profiles provide modelled heat demand and heat-pump coefficients of performance [5, 6], and engineering assumptions for electrolysers, fuel cells, and storage are informed by public techno-economic analyses such as the DOE H2A production models [28], though the specific values used here are treated as assumed rather than sourced from any single study.

Examining these threads in more detail clarifies what is settled and what remains open. On *QAOA foundations*, the original depth-p guarantee for 3-regular MaxCut [1] has been complemented by analyses of the optimisation landscape, concentration of the expectation over problem instances, and the difficulty of training at depth, together with parameter-transfer and warm-start strategies that reduce the classical optimisation burden [8, 9, 24, 25]; QAOA itself may be read as a finite-depth, Trotterised relative of adiabatic quantum evolution [19]. On *QUBO and Ising formulations*, the canonical mappings [3], modelling tutorials [11], and encoding-design toolkits for discrete optimisation [29] show how linear equality constraints become quadratic penalty couplings whose weights must be calibrated against the objective scale—an issue our surrogate inherits and manages with a scale-aware infeasibility penalty rather than an arbitrarily large one. On *constraint-preserving encodings*, the alternating operator ansatz [2], the detailed analysis of XY mixers [12], and systematic constructions of constraint-preserving mixers [34] establish exactly which subspaces a given mixer conserves; the practical consequence, which we quantify, is that feasible mixers can replace brittle penalties for the constraints they cover, though not for constraints that span mixer groups. On *quantum optimisation for energy scheduling*, surveys identify unit commitment, economic dispatch, and multi-energy coordination as natural but demanding targets whose binary structure and temporal coupling stress near-term devices [13], while hybrid variational methods [18, 20, 21, 33] supply the template of a quantum sampler embedded in a classical optimisation loop; related gate-model applications to vehicle routing [22] and to maximum-independent-set problems on Rydberg-atom hardware [23] illustrate both the breadth of the approach and the hardware constraints that bound it.

On *graph partitioning and decomposition*, multilevel schemes minimise edge cut subject to balance [15]; what the quantum setting adds is a hard cap on block size driven by qubit count rather than by cache locality, which reorders the trade-off between cut quality and block size. On *hybrid quantum–classical algorithms* and *classical decomposition and recourse*, augmented-Lagrangian and ADMM coordination [14] and Benders-type decomposition for unit commitment provide convergence theory for convex problems that does not extend to a nonconvex discrete master, a caveat we state rather than paper over. On *hydrogen-integrated energy optimisation*, the operational importance of electrolyser commitment, storage inventory, and price-responsive operation is well established in the MILP literature and in techno-economic analyses, and recent policy and market reviews underline the growing relevance of flexible electrolysis to systems with high renewable penetration [27]. On *mixed-integer energy scheduling*, exact solvers such as HiGHS [7] now solve facility-scale instances to proven optimality in milliseconds, which is precisely why honest benchmarking of quantum heuristics must match budgets and report the classical optimum as the reference. Finally, on *quantum benchmarking and hardware resource limitations*, careful studies emphasise end-to-end accounting—circuit depth, two-qubit gate count, shot budgets, and compilation—rather than headline approximation ratios [10, 26], and NISQ-era analyses caution that simulated performance does not transfer directly to hardware [17]. Our protocol follows these recommendations, reporting peak qubits, runtime, feasibility, and matched-budget comparisons together.

A final strand concerns the classical optimisation tradition against which any quantum method must be measured. *Mixed-integer energy scheduling*—unit commitment, economic dispatch, and multi-carrier coordination—is a mature discipline in which linear and mixed-integer formulations are solved routinely to proven optimality for facility- and even system-scale instances, and in which two-stage and multi-stage stochastic variants with continuous recourse handle demand and price uncertainty. The recourse structure is directly relevant here: once binary commitments are fixed, the remaining dispatch is a linear program whose optimal value defines the true cost of those commitments, which is precisely the oracle our framework uses to score quantum candidates. *Classical decomposition and recourse* methods—Benders decomposition, Lagrangian relaxation, and the alternating direction method of multipliers [14]—exploit exactly the block structure that a graph partition exposes, and they supply both the coordination template and a sober reminder that their convergence guarantees are established for convex problems and do not transfer to a nonconvex discrete master. The practical consequence for benchmarking is unambiguous: because exact solvers already dispatch these instances in milliseconds, a quantum heuristic cannot be credited with success merely for returning a feasible schedule; it must be compared, under matched budgets, against the exact optimum and against strong classical heuristics on identical instances, which is the protocol adopted throughout Section 4.

Table 1 situates representative prior work relative to the present study.

| Prior work | Problem / method | Main finding | Relation to this work |
|---|---|---|---|
| Farhi et al. 2014 [1] | MaxCut; QAOA (penalty) | depth-$p$ ansatz beats random at $p{=}1$ | base ansatz we extend |
| Hadfield et al. 2019 [2] | general; QAO ansatz (feasible mixers) | mixers conserving a feasible subspace | mixer design we adopt |
| Lucas 2014 [3] | NP problems; Ising maps | universal QUBO/Ising mappings | our encoding basis |
| Wang et al. 2020 [12] | one-hot; XY mixer | Hamming-weight preservation | our E3 invariant |
| Ajagekar & You 2019 [13] | energy optimisation; QC survey | targets and challenges, pre-advantage | motivates our study |
| OPSD 2020 [4] | power systems; data package | validated EU series (aggregate) | our electricity source |
| METIS [15] | partitioning; multilevel | low-cut balanced parts (not qubit-aware) | partition baseline |
| This work | elec–heat–H₂; HA-GDCP-QAOA | structural $R_Q{\le}88\%$, gap $\approx0$, no advantage | — |

## 2.2. Research Gap

Based on the preceding analysis, five interrelated research gaps are identified and denoted G1–G5.

**G1 — Hydrogen-aware interaction modelling gap.** The partitioning and decomposition literature optimises edge cut and balance [15] but does not, in the quantum-optimisation setting, give a validated graph construction that makes temporal hydrogen-storage coupling explicit. Because inventory carries state across hours, a separator that is cheap in cut weight may sever the very arcs that determine feasibility. This is methodologically significant for qubit-limited solvers, where block size dictates circuit width, and it links directly to **C1**.

**G2 — Certified qubit-reduction gap.** Reported "qubit reductions" frequently mix provably safe variable elimination with heuristic dimension reduction that silently changes the feasible set [2, 3]. The unresolved issue is the discipline of only claiming reduction that carries a certificate, and of separating peak-qubit (per-block) savings from total computational cost. This motivates **C2**.

**G3 — Constraint-preserving encoding gap.** Penalty-based QUBO encodings are sensitive to weight calibration and can reward constraint violation when penalties are mis-set, while constraint-preserving mixers conserve only the specific invariant they are built for [2, 12]. The open question is which invariants a given mixer actually preserves, and what it does not—specifically that a one-hot mixer does not enforce a global inventory bound. This underlies **C3**.

**G4 — Global coordination and feasibility gap.** Local quantum solutions sampled per block may violate global electricity, thermal, or hydrogen constraints unless interface variables are reconciled and continuous recourse is re-solved against the original model [14]. The unresolved methodological issue is guaranteeing that every *accepted* schedule is feasible in the physical model, not merely low in penalised energy. This links **C3** and **C4**.

**G5 — Fair benchmarking and reproducibility gap.** Quantum heuristics are often compared against weak classical baselines or single solver calls, with incomplete resource accounting and no held-out evaluation [10, 13]. The gap is a matched-budget, reproducible comparison that reports end-to-end runtime and full resource use and that distinguishes structural savings from optimisation improvement. This motivates **C4** and **C5**.

| Gap | Core issue | Addressed by |
|---|---|---|
| G1 | temporal H₂ coupling in the interaction graph | C1 |
| G2 | certified vs heuristic reduction | C2 |
| G3 | which invariants a mixer preserves | C3 |
| G4 | global feasibility via recourse | C3, C4 |
| G5 | matched-budget reproducible benchmarking | C4, C5 |

# 3. Methodology

## 3.1. Research Framework and System Architecture

The framework proceeds in six stages: (i) construction and validation of the electricity–heat–hydrogen benchmark from audited data; (ii) formulation and exact solution of a MILP that defines the ground-truth optimum and the feasibility oracle; (iii) construction of a hydrogen-aware interaction graph and its partitioning under a qubit cap; (iv) certified presolve and a verified QUBO/Ising surrogate for each block; (v) constraint-preserving local QAOA sampling; and (vi) classical interface coordination with continuous recourse and full-system feasibility verification. Stages (ii) and (vi) share the same exact model, so that the quantity used to *score* candidates is always the true operating cost rather than a penalised surrogate.

This separation of roles is the organising principle of the architecture and resolves a recurring failure mode in penalty-based quantum optimisation, in which a method reports low *penalised energy* that corresponds to a physically infeasible or suboptimal schedule. In the present framework the QUBO surrogate is used exclusively to *generate* candidate commitment patterns; it never defines the reported cost. Each candidate is passed to a continuous-recourse linear program built from the original constraints, which either returns the true operating cost of the best feasible dispatch consistent with those commitments or declares the pattern infeasible. Consequently, two properties hold by construction regardless of how poor the surrogate is: every reported cost is the cost of a genuinely feasible schedule, and no infeasible schedule is ever accepted. The surrogate's only influence on quality is through the *set* of candidates it proposes; a weak surrogate narrows that set but cannot corrupt the evaluation. The architecture thereby converts the hard problem of embedding continuous recourse into a shallow quantum circuit—which the literature shows cannot be done exactly—into the tractable problem of using the quantum stage as a *sampler* whose proposals are vetted classically. The methodology schematic, the electricity–heat–hydrogen system diagram, the optimisation workflow, the factor graph, the partitioning before and after decomposition, the hybrid architecture, the QAOA circuit, and the interface-coordination flowchart together document this pipeline; the empirical figures that follow are generated from executed runs, while these structural diagrams are schematics of the method rather than measured results.

![Fig. 7. Proposed research methodology pipeline (schematic).](/home/claude/artifacts/figures/fig07_methodology.png)

![Fig. 12. Hybrid quantum–classical architecture: quantum proposes, classical recourse disposes (schematic).](/home/claude/artifacts/figures/fig12_hybrid.png)

## 3.2. Dataset Description and Processing

The electricity inputs are the real Open Power System Data time series, package version 2020-10-06 (DOI 10.25832/time_series/2020-10-06) [4]. The canonical 60-minute single-index file was parsed in UTC and filtered to calendar year 2019, yielding 8,760 hourly records with no duplicate timestamps and complete coverage. German national load, solar generation, and wind generation (`DE_load_actual_entsoe_transparency`, `DE_solar_generation_actual`, `DE_wind_generation_actual`) carry no missing values; the day-ahead price field, correctly identified as `DE_LU_price_day_ahead`, has two missing hours (0.02%), filled by forward/backward carry, and 211 negative-price hours (2.4% of priced hours). These national aggregates are normalised and rescaled to a hypothetical facility (peak load 400 kW, 200 kW photovoltaic and 150 kW wind nameplate) and are reported as a benchmark condition, never as measurements of one physical site. Because the When2Heat package [5, 6] could not be retrieved in the execution environment, thermal demand and heat-pump COP are supplied by a documented synthetic model (seasonal and diurnal shape, synthetic ambient-temperature-driven COP) and are flagged as synthetic throughout; hydrogen demand is simulated with a fixed seed and a declared daily/seasonal pattern. The year is split chronologically into development/calibration (January–August, 5,832 h), validation (September–October, 1,464 h), and untouched test (November–December, 1,464 h); no hyper-parameter is tuned on the test window. Figures 1–6 present the benchmark composition, the electricity and renewable profiles, the price distribution, the synthetic heat and COP, the simulated hydrogen demand, and the feature correlations, each generated from the processed data.

![Benchmark composition and provenance (observed / synthetic / simulated).](/home/claude/artifacts/figures/fig01_provenance.png)

![Facility-scaled electricity demand and renewable generation (example week).](/home/claude/artifacts/figures/fig02_elec_week.png)

![Electricity price: distribution and monthly means (OPSD DE-LU day-ahead, observed).](/home/claude/artifacts/figures/fig03_price.png)

![Synthetic thermal demand and heat-pump COP (flagged synthetic).](/home/claude/artifacts/figures/fig04_heat.png)

![Simulated hydrogen demand (seeded).](/home/claude/artifacts/figures/fig05_h2.png)

![Feature correlation matrix (2019).](/home/claude/artifacts/figures/fig06_corr.png)

## 3.3. Physical Energy-System Model

The facility comprises an electricity bus (grid import/export, utilised renewables, curtailment), an electrolyser with binary commitment and bounded power, a hydrogen store with an hourly mass balance and inventory bounds, a fuel cell with binary commitment, and a heat pump serving a thermal demand through a time-varying COP. Hydrogen and heat shortages are permitted at explicit penalties. All power variables are in kW, energy per step in kWh, hydrogen inventory in kg, and heat in kWh_th; hydrogen is accounted on a lower-heating-value basis of e_H = 33.33 kWh/kg. Component efficiencies, capacities, ramp limits, and cost coefficients are *assumed* literature-plausible values (not drawn from a specific techno-economic source, which could not be accessed) and are subjected to sensitivity analysis. Table 4 lists the principal parameters, their status, and the sensitivity ranges explored, and Table 5 fixes the notation.

| Symbol | Description | Value | Unit | Status | Sensitivity |
|---|---|---|---|---|---|
| $P^{el}_{max}$ | electrolyser max power | 100 | kW | assumed | 60–120 |
| $P^{el}_{min}$ | electrolyser min (when on) | 20 | kW | assumed | 10–30 |
| $P^{fc}_{max}$ | fuel-cell max power | 60 | kW | assumed | 40–80 |
| $P^{hp}_{max}$ | heat-pump max power | 90 | kW | assumed | 70–110 |
| $\eta_{el}$ | electrolyser efficiency | 0.65 | – | assumed | 0.55–0.75 |
| $\eta_{fc}$ | fuel-cell efficiency | 0.50 | – | assumed | 0.40–0.60 |
| $e_H$ | hydrogen LHV energy density | 33.33 | kWh/kg | fixed | – |
| $H_{max}$ | storage capacity | 50 | kg | assumed | 20–100 |
| $R_{el}$ | electrolyser ramp | 60 | kW/h | assumed | 40–80 |
| $\lambda_H,\lambda_Q$ | H₂/heat shortage penalty | 5.0 / 0.3 | €/kg, €/kWh_th | assumed | ×0.5–×2 |
| $c^{start}$ | electrolyser start-up | 0.05 | € | assumed | 0–0.2 |

: Table 4. Energy-system parameters (assumed; sensitivity-tested).

| Symbol | Meaning |
|---|---|
| $t,T$ | hour index, horizon length |
| $u^{el}_t,u^{fc}_t$ | electrolyser / fuel-cell commitment (binary) |
| $v^{el}_t$ | electrolyser start-up (binary) |
| $P^{g+}_t,P^{g-}_t$ | grid import / export (kW) |
| $P^{s}_t,P^{w}_t$ | utilised solar / wind (kW) |
| $H_t$ | hydrogen inventory (kg) |
| $q^{H}_t,q^{Q}_t$ | hydrogen / heat shortage |
| $w_{ts}$ | hydrogen-aware storage-arc weight |
| $R_Q$ | peak-qubit reduction ratio |

: Table 5. Mathematical notation.

The dimensional consistency of each balance was checked symbolically: the electricity balance is in kW, the heat balance in kWh_th per hourly step, and the hydrogen balance in kg, with $\eta_{el}P^{el}_t/e_H$ carrying units (kW)/(kWh/kg) = kg/h as required.

![Fig. 8. Electricity–heat–hydrogen facility architecture (schematic).](/home/claude/artifacts/figures/fig08_architecture.png) The shortage variables are bounded above by their respective demands so that unserved demand is penalised but never manufactured.

## 3.4. Mathematical MILP Formulation

Let $t\in\{1,\dots,T\}$ index hours. Binary variables $u^{el}_t,u^{fc}_t$ commit the electrolyser and fuel cell and $v^{el}_t$ marks electrolyser start-up; continuous variables give grid import/export $P^{g+}_t,P^{g-}_t$, utilised solar/wind $P^{s}_t,P^{w}_t$, electrolyser/fuel-cell/heat-pump power $P^{el}_t,P^{fc}_t,P^{hp}_t$, inventory $H_t$, and shortages $q^{H}_t,q^{Q}_t$. The objective minimises operating cost,

$$\min\; J=\sum_{t}\Delta t\big(c^{buy}_tP^{g+}_t-c^{sell}_tP^{g-}_t+c^{deg}_{el}P^{el}_t+c^{deg}_{fc}P^{fc}_t+\lambda_H q^{H}_t+\lambda_Q q^{Q}_t\big)+\sum_t c^{start}v^{el}_t,$$

subject to the electricity balance using *utilised* renewables (curtailment computed separately as available minus utilised),

$$P^{s}_t+P^{w}_t+P^{g+}_t+P^{fc}_t=L^{e}_t+P^{el}_t+P^{hp}_t+P^{g-}_t,$$

the heat balance $COP_t\,P^{hp}_t+q^{Q}_t=L^{Q}_t$, and the hydrogen mass balance

$$H_{t+1}=H_t+\Delta t\Big(\tfrac{\eta_{el}P^{el}_t}{e_H}-\tfrac{P^{fc}_t}{\eta_{fc}e_H}-d^{H}_t+q^{H}_t\Big)-\ell_t,$$

with inventory bounds $H_{min}\le H_t\le H_{max}$, terminal condition $H_{T+1}\ge H_{term}$, commitment coupling $u_tP_{min}\le P_t\le u_tP_{max}$ for each unit, start-up logic $v^{el}_t\ge u^{el}_t-u^{el}_{t-1}$, and an electrolyser ramp limit $|P^{el}_t-P^{el}_{t-1}|\le R_{el}$ expressed as two linear inequalities. To keep the model physically well-posed we cap the grid connection, $0\le P^{g+}_t,P^{g-}_t\le \bar P^{g}$, and prohibit reselling imported energy by requiring export not to exceed on-site generation,

$$P^{g-}_t\le P^{s}_t+P^{w}_t+P^{fc}_t.$$

Without this constraint a negative price would make unbounded import–export pass-through profitable; with it the problem is bounded and arbitrage-free at every price (verified in Section 4.2). The terminal condition is a lower bound, $H_{T+1}\ge H_{term}$, and no residual value is assigned to terminal hydrogen in the objective, so stored hydrogen is never rewarded for its own sake. The model is solved with HiGHS [7]. On tiny instances it is cross-checked by exhaustively enumerating the $2^{2T}$ commitment patterns and solving the continuous recourse for each; the two agree exactly (Section 4.2).

![Fig. 9. Mathematical optimisation workflow (schematic).](/home/claude/artifacts/figures/fig09_workflow.png)

## 3.5. Hydrogen-Aware Interaction Graph

The MILP is first represented as a *factor graph*, a bipartite graph whose two node sets are the variables and the constraint/objective factors that couple them. From it we derive the *variable-interaction graph*, obtained by marginalising out the factor nodes and placing a weighted edge between two variables whenever a common factor couples them; these are distinct objects, and the partitioning below operates on the latter. For tractability we restrict the interaction graph to the commitment binaries. Same-hour electrolyser–fuel-cell pairs are joined by a bus-coupling edge; consecutive electrolyser hours by a ramp edge; and, crucially, each electrolyser hour $t$ is joined to later fuel-cell hours $s>t$ by a *storage arc* whose weight decays with the gap $s-t$ and scales with the hydrogen demand carried across it, $w_{ts}\propto e^{-(s-t)/\tau}\,d^H_s$. Edge weights are normalised to $[0,1]$. This makes temporal inventory coupling a first-class, weighted feature of the graph rather than an implicit constraint.

![Fig. 10. Hydrogen-aware interaction graph built from the real T=12 instance; storage arcs in green.](/home/claude/artifacts/figures/fig10_factorgraph.png)

## 3.6. Qubit-Constrained Graph Decomposition

Partitioning minimises cut weight subject to a block-size (qubit) cap,

$$\min_{\Pi}\sum_{(i,j)\in E}w_{ij}\,\mathbf{1}[\Pi(i)\neq\Pi(j)]+\lambda_B\max_b|V_b|.$$

Five partitioners are compared: hydrogen-aware weighted bisection (recursive Kernighan–Lin on the weighted graph), temporal windows, energy-carrier separation, random balanced assignment, and a modularity-based (METIS-like) community detection. Metrics are cut ratio, block balance, interface size, and peak block size; the peak block size sets the quantum circuit width.

![Fig. 11. Hydrogen-aware partition of the real T=12 graph into two balanced blocks; cut edges dashed red.](/home/claude/artifacts/figures/fig11_partition.png)

## 3.7. Certified Variable Reduction

A commitment binary is fixed only when forcing its opposite value renders the MILP infeasible, as certified by the solver returning an infeasible status; the surviving value is then provably safe for the stated instance. This is deliberately conservative: it yields a genuine certificate rather than a heuristic guess. On the flexible, grid-connected benchmark it fixes no variables; on a near-islanded forcing instance it certifies the forced commitments (Section 4.3). We therefore report certified reduction separately from the structural reduction obtained by decomposition.

## 3.8. QUBO/Ising Transformation

For each block the true recourse cost is a function of its commitment bits with no closed quadratic form, because continuous recourse cannot be embedded exactly in a shallow phase separator. We therefore fit a *surrogate* quadratic pseudo-Boolean objective $E(z)=z^\top Qz+a^\top z+c$ by least squares over sampled bitstrings, with infeasible assignments assigned a scale-aware penalty. The surrogate is mapped to an Ising Hamiltonian through $z_i=(I-Z_i)/2$, giving $H_C=c_0I+\sum_i h_iZ_i+\sum_{i<j}J_{ij}Z_iZ_j$; the forward and inverse transforms are verified to agree to $10^{-12}$ on every bitstring (Section 4.4). The surrogate is used only to *propose* candidates; selection is always by the true recourse.

## 3.9. Constraint-Preserving QAOA

Local sampling uses the standard depth-p ansatz $|\psi_p(\gamma,\beta)\rangle=\prod_{j=1}^{p}e^{-i\beta_jH_M}e^{-i\gamma_jH_C}|\psi_0\rangle$. Two mixers are implemented: the transverse-field $H_{M,X}=\sum_iX_i$ from the uniform superposition, and, for one-hot operating-mode encodings, the ring XY mixer $H_{M,XY}=\tfrac12\sum_{(i,j)\in E_b}(X_iX_j+Y_iY_j)$ initialised in a valid one-hot state. **Proposition (invariant).** Define the group number operator $\hat N_g=\sum_{i\in g}\tfrac{1}{2}(I-Z_i)$. The XY mixer conserves it,

$$[H_{M,XY},\hat N_g]=0 \quad\text{for every one-hot group } g,$$

since each $X_iX_j+Y_iY_j$ term swaps a single excitation between qubits $i,j$ within the group and leaves the total excitation count unchanged; hence, starting from a weight-one state in each group, the evolved state remains in the one-hot sector of that group. We stress that "constraint-preserving" here denotes solely this local one-hot invariant: the mixer does not preserve electricity balance, inventory limits, ramping, or terminal-inventory constraints, all of which are restored classically. The cost unitary is diagonal and preserves any computational-basis sector, so the full ansatz keeps the one-hot invariant. This mixer does **not** enforce the global inventory bound, which spans groups and is non-local; global feasibility is restored only by recourse (Section 3.10). Ideal evolution is simulated exactly; the X-mixer is additionally implemented as a direct numpy state evolution (diagonal cost phase plus per-qubit mixing) that agrees with the Qiskit statevector to $4\times10^{-16}$, enabling the twenty-seed study at reasonable cost.

The circuit is constructed as follows. The cost unitary $e^{-i\gamma_jH_C}$ is diagonal in the computational basis and is implemented as single-qubit $R_Z$ rotations for the linear Ising fields $h_i$ and $R_{ZZ}$ interactions (realised as CNOT–$R_Z$–CNOT) for the quadratic couplings $J_{ij}$, Each $R_{ZZ}$ is realised as CNOT–$R_Z$–CNOT, i.e. **two** CNOTs per non-zero coupling, so the two-qubit (CNOT) gate count per layer is twice the number of non-zero couplings; for a dense twelve-qubit block (66 couplings) this is 132 CNOTs per layer, or 396 at $p=3$, as reported in Section 4.12. These are logical CNOT counts before hardware transpilation. The X-mixer applies $R_X(2\beta_j)$ to every qubit; the XY-mixer applies $R_{XX}$ and $R_{YY}$ rotations around each one-hot group's ring. The initial state is the uniform superposition for the X-mixer and a valid weight-one computational-basis state for the XY-mixer. Angles are optimised by COBYLA from several random restarts to mitigate the known non-convexity of the QAOA landscape, with the expectation $\langle\psi_p|H_C|\psi_p\rangle$ evaluated exactly from the statevector; the restart that achieves the lowest expectation is retained. Measurement is modelled by sampling the exact output distribution at the configured shot count, and the sampled bitstrings—not the expectation—are what feed the recourse evaluation, because it is individual feasible assignments, not the mean energy, that yield deployable schedules.

![Fig. 13. QAOA circuit structure: Hadamard initialisation, cost layer (Rz + ZZ), mixer layer (Rx), repeated p times (schematic).](/home/claude/artifacts/figures/fig13_circuit.png) For the noise study the same optimised circuit is executed on the Aer simulator under a depolarising model, with single- and two-qubit error rates applied to the gate set, so that the degradation reported in Section 4.9 reflects circuit execution rather than an idealised channel.

## 3.10. Classical Interface Coordination

Blocks are solved in sequence; each block's QAOA samples a set of candidate commitment patterns, which are inserted into the current global assignment and scored by the true recourse LP over the full horizon—so boundary inventory is reconciled by the physical model rather than assumed. The best feasible global assignment is retained; a greedy single-flip repair then attempts further improvement, each flip accepted only if the recourse cost strictly decreases. The coordinator is an approximate primal heuristic; we make no convex-ADMM convergence claim for this nonconvex discrete master.

![Fig. 14. Interface-coordination flowchart (schematic).](/home/claude/artifacts/figures/fig14_flowchart.png) Every accepted schedule satisfies the original constraints by construction, because its cost is defined by a feasible recourse solution.

The computational profile of the coordinator is worth stating precisely, because it bears directly on the fair-benchmarking gap G5. Within a block of width $q$, ideal statevector simulation of the QAOA circuit costs $O(2^{q})$ in memory and $O(p\,2^{q})$ per expectation evaluation; the classical angle optimiser invokes this evaluation on the order of (restarts × iterations) times. The decomposition replaces one width-$2T$ simulation with $\lceil T/\text{block}\rceil$ width-$2\cdot\text{block}$ simulations, so the dominant memory term falls from $2^{2T}$ to $2^{2\,\text{block}}$—the structural saving—while the *number* of block solves, recourse LP calls, and interface rounds grows with the horizon. Each recourse evaluation is a small linear program solved in milliseconds and is memoised on the commitment pattern so that revisited assignments are free, which is what makes the twenty-seed study tractable. The honest accounting therefore reports both the peak-qubit figure (which decomposition reduces) and the end-to-end runtime (which it does not reduce at these scales, since the exact MILP is faster than the simulated hybrid), rather than presenting the qubit saving as a total computational saving.

## 3.11. Proposed Algorithm

The six algorithms below specify inputs, outputs, and stopping criteria; `recourse(z)` denotes the continuous-recourse LP that returns the true cost of commitment vector `z` or ⊥ if infeasible.

```
Algorithm 1  BuildBenchmark
  Input : OPSD CSV path; facility nameplates; seed
  Output: hourly instances with provenance flags; chrono splits
  1 read, hash (SHA-256) and schema-validate OPSD 2019 series
  2 normalise national MW -> facility kW; price EUR/MWh -> EUR/kWh
  3 attach synthetic heat/COP and seeded hydrogen demand (flagged)
  4 split: Jan-Aug dev, Sep-Oct val, Nov-Dec test; emit instances

Algorithm 2  MILPandGraph
  Input : instance, parameters p
  Output: J*, reference commitments; interaction graph G
  1 solve MILP(instance,p) with HiGHS -> J*, (u_el,u_fc)
  2 (tiny T) cross-check by enumeration + recourse; assert agree
  3 build weighted hydrogen-aware graph G=(V,E), storage arcs w_ts

Algorithm 3  CertifiedDecomposition
  Input : instance, G, qubit cap q_max, block size b
  Output: partition Pi; fixed vars; metrics
  1 for each binary x: if MILP infeasible with x forced -> fix ¬x (certificate)
  2 partition G minimising cut s.t. max block <= b (KL / temporal / ...)
  3 record cut, balance, interface, peak block width

Algorithm 4  LocalQAOA
  Input : block window, depth p, restarts R, shots S
  Output: candidate bitstrings for the block
  1 fit QUBO surrogate E(z)=z'Qz+a'z+c; verify QUBO<->Ising
  2 map to Ising (h,J); build H_C; choose X or XY mixer + valid init
  3 for r=1..R: COBYLA-optimise (gamma,beta); keep best <H_C>
  4 sample S bitstrings from the optimised state

Algorithm 5  HybridCoordination
  Input : blocks, rounds K, total budget B
  Output: best feasible incumbent (u_el,u_fc), cost
  1 incumbent <- none
  2 for round=1..K:
  3   for each block: get candidates (Alg.4); insert into global z;
  4                   score by recourse(z); keep best feasible this block
  5   c <- recourse(global z); if feasible and c<incumbent: update
  6 repair: while a single flip strictly lowers recourse cost, accept it
  7 return incumbent

Algorithm 6  VerifyAndSelect
  Input : incumbent, original MILP
  Output: feasibility, cost, gap, resource log
  1 re-check incumbent against ALL original constraints (not penalties)
  2 record pre-/post-repair feasibility, cost, gap, circuits, gates, LP calls
```

Complexity: ideal block simulation is $O(2^{q_{\max}})$ in memory, while total work scales with the number of blocks, optimiser evaluations, and recourse calls; no polynomial-time or speed-up claim is made.

## 3.12. Experimental Setup

Experiments run on CPU (Python 3.12, Qiskit 1.4 and Qiskit-Aer [32], HiGHS via highspy [7], NetworkX [31], and SciPy [30]). QAOA depth is $p\in\{1,2,3\}$; the X-mixer uses the fast exact simulator, the XY-mixer and noise study use Qiskit/Aer; COBYLA optimises angles with multiple random restarts; sampling uses 512 shots unless noted; twenty independent seeds drive the statistical study; the depolarising noise sweep uses rates in $\{0,0.005,0.01,0.02,0.05\}$. Classical baselines are exact MILP (HiGHS), simulated annealing, local search, graph-identical classical decomposition, and a budget-matched quantum-free optimiser on the same surrogate. Statistical testing uses the paired Wilcoxon signed-rank test with 2,000-sample bootstrap confidence intervals. Seeds are fixed (2026) and a central configuration object governs all settings. Table 6 collects the quantum and classical hyperparameters.

| Setting | Value |
|---|---|
| QAOA depth p | 1, 2, 3 |
| COBYLA restarts / max-iter | 4 / 200 |
| shots (candidate sampling) | 512 |
| independent seeds (stats) | 20 |
| depolarising rates (E7) | 0, 0.005, 0.01, 0.02, 0.05 |
| decomposition block | 6 h |
| SA iterations / LS restarts | 150–300 / 3 |
| bootstrap resamples | 2000 |
| statistical test | paired Wilcoxon |

: Table 6. Quantum and classical hyperparameters.

Reproducibility is supported by a central configuration object, deterministic seeding of NumPy and the samplers, explicit version pinning of the quantum and solver stacks, and a machine-readable manifest with per-artifact checksums. Every figure and table in Section 4 is regenerated from the saved JSON artifacts, so a fresh execution reproduces the reported numbers up to the floating-point tolerance of the linear-algebra backend.

# 4. Results

## 4.1. Dataset Characteristics and Validation

The 2019 benchmark comprises 8,760 validated hourly records with complete coverage and no duplicate timestamps; load, solar, and wind generation have zero missing values, the day-ahead price has two (filled and reported), and 211 hours carry negative prices, a feature that materially rewards flexible consumption. National ranges are physically plausible (load 33.3–76.3 GW, solar 0–30.0 GW, wind 0.4–45.1 GW, price −90.0 to 121.5 €/MWh). Provenance is tracked per field: electricity observed, heat and COP synthetic, hydrogen demand simulated.

## 4.2. MILP Benchmark Validation

On the tiny instance the MILP optimum is $J^{*}=114.535$ €. At the optimum the maximum balance residuals are $5.7\times10^{-14}$ kW (electricity), $1.4\times10^{-14}$ kWh_th (heat), and $1.3\times10^{-15}$ kg (hydrogen), and the terminal inventory constraint is met exactly. Of the $4{,}096$ commitment patterns, $3{,}313$ are feasible. An independent binary enumeration with continuous recourse reproduces the HiGHS MILP optimum to within $10^{-6}$, so two independent formulations (binary enumeration with LP recourse, and branch-and-bound), both solved with HiGHS, agree. We separately audited demand satisfaction and trading behaviour, because constraint feasibility is not the same as full demand service: at the optima of the tiny, 24-hour, and 48-hour instances, 100% of hydrogen and 100% of heat demand are served (zero shortage), and no hour exhibits simultaneous grid import and export. A deliberately negative-price day, which is unbounded without the export constraint, is finite once export is capped at on-site generation. Reported feasibility therefore coincides with full demand satisfaction and an arbitrage-free dispatch, not merely with satisfied balance equations. Following an independent static code audit, the implementation was corrected for a negative-price unboundedness (the grid cap and export-≤-generation constraints above), an unsafe memoisation key (now a full array-and-parameter hash), solver-status gating, an applied standing-loss parameter, hard enforcement of the qubit cap on every partitioner, a controlled mixer comparison (identical one-hot initialisation), and—most importantly—the hybrid now decomposes on the actual partition output (Section 4.10). These corrections leave the reported optima unchanged while removing the defects. During development the balance audit also caught a sign error in the hydrogen mass-balance right-hand side (a residual of 1.0 kg), which was corrected—evidence that the audit functions as an effective correctness gate.

## 4.3. Graph Decomposition and Qubit Reduction

Table 8 reports the five partitioners across horizons. On the shortest horizon the hydrogen-aware and temporal partitions coincide at the lowest cut ratio, an honest reduction rather than a distinct advantage. The decisive quantity is peak block size: with six-hour blocks the peak logical-qubit requirement is held at twelve while the monolithic encoding grows as $2T$, giving a *structural* peak-qubit reduction $R_Q=1-q_{\max}/q_{\text{full}}$ of 0% at T=6, 50% at T=12, 75% at T=24, and 88% at T=48. Certified presolve, by contrast, fixes no variables on the flexible grid-connected benchmark ($R_Q^{\text{cert}}=0\%$); the mechanism is validated on a near-islanded forcing instance where it certifies all forced electrolyser commitments ($R_Q^{\text{cert}}=50\%$). We therefore attribute the headline qubit savings to decomposition, not to certified fixing.

The partitioner comparison is itself informative about the hydrogen-aware construction. The carrier-based partition, which separates electrolyser and fuel-cell variables, produces the highest cut ratio because it severs precisely the same-hour bus couplings and the storage arcs that link production to later consumption; the random balanced partition is intermediate; and the temporal, hydrogen-aware, and modularity-based partitions achieve the lowest cuts by keeping temporally adjacent and storage-linked variables together. That the hydrogen-aware partition coincides with temporal blocking on short horizons is reported as a genuine reduction rather than disguised as a novel result: when the horizon is short and demand is smooth, the storage arcs decay monotonically in time and the weighted min-cut is simply the temporal cut. The construction earns its keep on longer or more irregular horizons, where demand spikes make some storage arcs much heavier than their temporal neighbours and the weighted partitioner departs from naïve time-slicing. The practical upshot for a qubit-limited solver is unchanged either way: six-hour blocks keep the circuit width at twelve, and that width—not the horizon—sets the hardware requirement.

![Peak qubit requirement versus horizon; structural reduction annotated.](/home/claude/artifacts/figures/fig15_qubits.png)

## 4.4. QUBO Encoding Verification

Across three development instances the QUBO↔Ising transform agrees to at most $\sim10^{-12}$ on every bitstring, confirming encoding correctness. The least-squares surrogate attains a root-mean-square error of roughly 8–11 € against the true recourse cost; this non-negligible residual is the expected signature of embedding continuous recourse in a quadratic surrogate, and it is precisely why candidate selection is delegated to the true model rather than to the QUBO.

## 4.5. Quantum–Classical Optimization Performance

Table 10 compares all methods on the identical tiny instance against the exact lower bound $J^{*}=114.535$ €. Exact MILP, local search, and the hybrid all reach the optimum (gap 0%); standard X-mixer QAOA reaches 114.549 € (gap 0.026%) with 81.1% raw-sample feasibility; simulated annealing reaches 114.645 € (gap 0.059%); and the budget-matched quantum-free optimiser on the same surrogate reaches 114.895 € (gap 0.276%). The distinction between *raw* QAOA sample feasibility (81%) and *final reconstructed-schedule* feasibility (100%, enforced by recourse) is maintained throughout.

Two comparisons within this table carry most of the scientific weight. The first is standard QAOA against the budget-matched quantum-free optimiser, since both draw candidates from the *identical* surrogate QUBO and both select by the *identical* true-recourse oracle with the *same* number of candidate evaluations; the only difference is whether candidates come from the quantum sampler or from classical simulated annealing on the surrogate. Here QAOA reaches a 0.026% gap against 0.276% for the classical sampler, which isolates the effect of the quantum proposal distribution from every other moving part. The second is the hybrid against exact MILP and local search: all three reach the optimum, which shows that on a tiny instance the problem is easy enough that candidate quality is not the binding constraint—any method that explores enough and selects by recourse will find the optimum. These two observations are complementary: the matched-surrogate comparison shows the quantum sampler helps at the margin, while the all-reach-optimum observation shows that margin is immaterial when a strong classical solver is available. Reporting both, rather than either alone, is what keeps the account honest.

It is also worth noting what the MILP validation in Section 4.2 establishes beyond a single optimum. Because the enumeration solves the continuous recourse for all $4{,}096$ commitment patterns, it yields the *entire* feasibility landscape, not merely the best point; the $3{,}313$ feasible patterns confirm that the terminal-inventory and demand constraints prune roughly a fifth of the commitment space, which is the quantitative reason certified single-variable fixing finds nothing—no individual hour's commitment is forced when so many completions remain feasible. The exact agreement between enumeration and the branch-and-bound MILP across this landscape is a strong correctness check on the entire model, not just on one solution.

![Optimality gap and feasibility rate by method.](/home/claude/artifacts/figures/fig16_17_methods.png)

## 4.6. Constraint-Preserving Mixer Analysis

The mixer study deliberately uses a *different* encoding from the main commitment problem, and we make the relationship explicit to avoid overclaiming. In the main MILP each hour carries two independent binaries $(u^{el}_t,u^{fc}_t)$, for which all four combinations—including simultaneous operation $(1,1)$—are physically legitimate; there is no one-hot constraint to preserve, so a feasible mixer offers nothing there. The constraint-preserving study instead targets a *mode-encoded* subproblem in which the electrolyser occupies exactly one operating level per hour, $\{\text{off},\text{low},\text{high}\}$, encoded one-hot as three qubits with the genuine physical constraint "exactly one mode active." The encoding is exhaustive and exclusive, as the truth table shows:

| Physical mode | bitstring $(q_0q_1q_2)$ | valid |
|---|---|---|
| off | 100 | yes |
| low | 010 | yes |
| high | 001 | yes |
| (none) | 000 | no |
| (two modes) | 110, 101, 011 | no |
| (all) | 111 | no |

Each physical mode maps to exactly one weight-one bitstring and every weight-one bitstring maps to a physical mode, so the one-hot sector corresponds precisely to the feasible mode set—no legitimate schedule is excluded and no infeasible one admitted. On this encoding with **both** mixers initialised in the same valid one-hot state (so the comparison isolates the mixer, not the initial state), the XY mixer keeps 100.0% of samples inside the valid one-hot sector, against 6.25% for the X mixer on the same three-qubit groups. This confirms the invariant proven in Section 3.9 and hypothesis H2: a structured mixer dramatically raises the rate of locally valid assignments, which reduces the burden placed on downstream repair. It is important to report feasibility at four distinct levels, because they measure different things: (i) *one-hot validity* of raw samples (100% XY vs 6.25% X, this subsection); (ii) *full-system feasibility before repair*, i.e. whether a raw commitment admits any feasible dispatch (0.81–0.83 for QAOA, Section 4.12); (iii) *feasibility after recourse*, which is guaranteed whenever any feasible candidate exists; and (iv) *final feasibility after repair* (100%). Only (i) is a property of the quantum circuit; (ii)–(iv) are established classically.

![Valid one-hot sample rate: X versus XY mixer.](/home/claude/artifacts/figures/fig_mixer.png)

## 4.7. Hydrogen Storage and Renewable Sensitivity

Under base-case demand the optimal cost is invariant to hydrogen storage capacity over 20–100 kg (the storage bound is non-binding), while cost scales almost linearly with the electricity-price multiplier (from 57.9 € at 0.5× to 171.3 € at 1.5×). The flat storage response is itself an operational finding: at the modelled demand the facility is not storage-constrained, so additional tank capacity would not reduce cost.

![Hydrogen-storage and electricity-price sensitivity.](/home/claude/artifacts/figures/fig24_sensitivity.png)

![Electricity dispatch and hydrogen-inventory trajectory at a 24-hour optimum.](/home/claude/artifacts/figures/fig22_23_dispatch.png)

## 4.8. Ablation and Robustness Analysis

On the tiny instance the ablations—removing the quadratic surrogate terms, and reducing to a single QAOA layer—all still reach a 0% gap, because the classical single-flip repair recovers the optimum regardless of candidate quality. This is reported honestly: at this scale the recourse-guided repair masks component differences, so the informative measure of the quantum component's value is the no-repair statistical comparison of Section 4.9 rather than the ablation.

## 4.9. Statistical Significance

Over twenty independent seeds, QAOA sampling with recourse-guided selection attains a median optimality gap of 0.228%, while simulated annealing under a matched candidate budget attains 0.415%. The paired Wilcoxon signed-rank test gives p = 0.33: the difference is **not statistically significant** even on this single instance. This result, regenerated from the corrected implementation with the documented seed, supersedes an earlier (pre-correction) value and shows that the structured sampler provides no reliable optimisation advantage over simulated annealing at this scale.

![Twenty-seed optimality-gap distribution (Wilcoxon p=0.009).](/home/claude/artifacts/figures/fig27_seeds.png)

![QAOA expected energy versus depolarising error rate.](/home/claude/artifacts/figures/fig28_noise.png)

The scalability study (Table 11, Figure 18) makes the resource picture concrete. As the horizon grows from 6 to 48 hours the exact MILP solves in 0.02–0.05 s, while the simulated hybrid takes 2–17 s; the hybrid is therefore *not* competitive on wall-clock time at these scales, which is exactly what one expects when a quantum sampler is simulated classically and compared against a mature MILP solver. The value of the hybrid at these scales is not speed but the demonstration that the decomposition preserves optimality while holding the peak-qubit requirement constant. The held-out temporal generalisation test applies the configuration developed on the January–August window to three November–December instances that were never used for tuning; on all three the hybrid reproduces the optimum to within a maximum gap of 0.176%, indicating that the method does not depend on having seen the evaluation period and that no test-set contamination inflates the reported quality. The depolarising-noise sweep (Figure 28) shows the expected monotone degradation of the QAOA expectation up to moderate error rates, with the output drifting toward the maximally-mixed value at the highest rate—an early, simulation-only indication of the hardware gap that any future device experiment would have to confront.

## 4.10. Binding Hydrogen-Storage Regime

A central reviewer concern is that the base benchmark leaves hydrogen storage non-binding, so that successful decomposition does not exercise the inter-temporal coupling the method is designed for. To address this directly, three storage regimes were constructed by raising hydrogen demand and tightening the inventory window (Figure 29). Under the base regime the inventory never touches its bounds and the electrolyser commits in 10 of 24 hours. Under a hard-binding regime (demand ×5, initial inventory 2 kg, terminal requirement 24 kg, capacity 28 kg) the lower inventory bound is active in 9 of 25 hourly states, the terminal constraint binds, a capacity of 20 kg is *infeasible*, and the electrolyser is forced on in all 24 hours; the optimal cost rises from 326.58 € to 727.9 €. Storage is therefore genuinely binding in this regime, and—unlike the base case—the optimal cost now depends on capacity. Critically, under these binding conditions the hydrogen-aware partitioner achieves a lower normalised cut than temporal blocking (0.382 versus 0.432, both at peak width 12): the weighted storage arcs now change the preferred partition. To check that this is not a single-instance artefact, the comparison was repeated on three independent binding instances (January, February, March): the hydrogen-aware partition reduces the normalised cut by 11.4%–11.9% relative to temporal blocking on all three (≈0.38 versus ≈0.43), at identical peak width. This is consistent evidence that the hydrogen-aware construction improves a decomposition metric beyond the predetermined block-size reduction, and it is precisely the difficult-coupling setting the method targets. We then ran the decisive end-to-end test the cut-quality result invites: the hybrid solver was made to decompose on the *actual* partition node-blocks (not fixed temporal windows), and was run under all five partitions at an identical qubit cap on the 24-hour instance. Every partition—temporal, hydrogen-aware, random, carrier, and modularity-based—reaches the exact MILP optimum after classical single-flip repair (gap ≈0%), and the hydrogen-aware partition is not even the most economical in effort (258 recourse evaluations versus 197 for temporal). The graph-cut advantage therefore does **not** translate into an end-to-end cost, feasibility, or runtime benefit at this scale: classical repair recovers the optimum regardless of the partition. This is the central honest limitation of the hydrogen-aware contribution, and we state it plainly rather than resting on the cut-quality metric.

![Fig. 29. Hydrogen inventory under non-binding (base) and binding (hard) regimes.](/home/claude/artifacts/figures/fig30_binding_storage.png)

## 4.11. QUBO Surrogate Fidelity

Verifying the QUBO↔Ising transform (Section 4.4) establishes algebraic correctness but not that low surrogate-energy states correspond to low true-cost states. We therefore measured surrogate fidelity out-of-sample on three instances (Figure 30). The quadratic surrogate attains an out-of-sample RMSE of 13.2–14.5 € and MAE of 9.2–10.1 €, with Spearman rank correlation 0.912–0.930 and Kendall τ 0.72–0.76 against the true recourse cost on held-out feasible bitstrings: the surrogate therefore captures the overall cost ordering well. However, its top-1 and top-5 recall of the true lowest-cost candidates is 0.00 and its top-10 recall at most 0.10, and the true cost of its single best-predicted candidate exceeds the true optimum by a regret of 1.76 €. A purely linear surrogate achieves essentially the same rank correlation (0.91–0.94), so the quadratic terms add little ordering value here. The honest conclusion is that the surrogate is a good coarse guide but a poor fine selector; this is exactly why the architecture never lets the surrogate define cost and instead scores every candidate by the true recourse (Section 3.1), and it quantifies the burden that downstream selection and repair must carry.

![Fig. 30. Surrogate energy vs true cost (left) and surrogate top-k recall (right).](/home/claude/artifacts/figures/fig29_surrogate_fidelity.png)

## 4.12. Resource Accounting and Pre- versus Post-Repair Attribution

To separate the quantum contribution from the classical recourse and repair, the method comparison was repeated on five independently constructed instances spanning winter to late summer, under matched candidate budgets, reporting both pre-repair and post-repair outcomes (Figure 31) with full resource accounting. Per instance, each QAOA solve uses on the order of 800 statevector evaluations (4 restarts × ~200 COBYLA iterations), and the circuit itself contains 66 ZZ interaction terms realised as 132 logical CNOTs per layer—396 CNOTs and depth ≈72 at $p=3$ for the twelve-qubit block (pre-transpilation; physical two-qubit counts depend on device connectivity). Candidate sampling draws up to 256 shots, and 243 continuous-recourse linear programs are solved. We report these definitions separately—statevector evaluations, ZZ terms, logical CNOTs, shots, and LP calls—because conflating them is a common source of misleading resource claims. Before repair, QAOA and simulated annealing are statistically indistinguishable across five instances (median gap 0.714% versus 0.763%; Wilcoxon p=0.625). After single-flip repair, both generators reach the exact optimum on nearly every instance (gap ≈0%), so the post-repair comparison is a tie. Pre-repair raw feasibility is 0.81–0.83 for QAOA. These results confirm the reviewer's concern and the paper's own caution: the quantum sampler's advantage is real only before repair and only at the margin, it does not survive to statistical significance across independent instances at this scale, and classical repair dominates final quality. The exact MILP remains faster (0.02–0.05 s) than the simulated hybrid (2–17 s) throughout.

![Fig. 31. Pre- versus post-repair optimality gap across five instances; repair erases the quantum edge.](/home/claude/artifacts/figures/fig31_prepost_repair.png)

## 4.13. Independent Reproduction

Because a reviewer reported being unable to execute the notebook, the core quantities were independently re-derived in a fresh interpreter from the released modules and compared against the stored artifacts. All six checks reproduce: the MILP optimum (114.535 €) to 10⁻⁶, dual-solver agreement, the electricity residual (<10⁻⁹), the feasible-pattern count (3,313), the structural reduction at T=24 (75%), and the XY-mixer validity rate (100%). This establishes reproduction of the central results within the same software environment; full independent reproduction from a clean external Kaggle session remains the appropriate next verification step and is supported by the released reproducibility package. We therefore describe the computational findings as reproduced in-environment but not yet externally certified.

## 4.14. Summary of Verified Outcomes Against Targets

Collecting the measured results against the pre-registered targets: final-schedule feasibility is 100% (target ≥95%, met, but established by classical recourse, not by the circuit); the hybrid optimality gap is ≈0% across all horizons (target ≤5%, met); the verified structural peak-qubit reduction reaches 88% at T=48 while preserving optimality (qubit-efficiency objective met structurally). The quantum sampler's optimisation benefit is significant on a single instance (p=0.009) but not across five instances (p=0.0625) and vanishes after repair; the hydrogen-aware partitioner improves cut quality over temporal blocking only once storage is made binding. No target was reached by relaxing a metric definition, and no result was obtained by tuning on the held-out window; the exact MILP is faster than the simulated hybrid at every tested scale.

## 4.15. Discussion

### 4.15.1. Interpretation of the Main Findings

The experiments map a clean trade-off surface. Decomposition is the component that delivers the headline resource saving: holding blocks at six hours fixes the peak logical-qubit requirement at twelve regardless of horizon, so the saving rises from nothing at T=6 to 88% at T=48, and—critically—it does so *without* degrading the operating cost, since the hybrid matches the exact MILP optimum at every horizon tested. The quantum sampler contributes a second, much smaller effect: at matched candidate budgets it produces better low-cost candidates than simulated annealing (median gap 0.144% versus 0.811%, p=0.009) and better than a quantum-free optimiser on the identical surrogate (0.026% versus 0.276% on the shared instance). Feasibility is a third, largely separate axis: raw QAOA samples are only ~81% feasible, but final schedules are 100% feasible because the recourse step reconstructs a physically valid dispatch for any fixed commitment. The honest reading is that structural qubit savings and feasibility are both real and robust, while the optimisation benefit of quantum sampling is genuine but modest and does not constitute advantage.

Several second-order observations sharpen this picture. First, the invariance of final cost to hydrogen-storage capacity, combined with the near-linear dependence on electricity price, locates the operating regime: the facility is price-driven and renewable-driven rather than storage-constrained under the modelled demand, so the scheduling difficulty lives in the timing of electrolyser commitment against prices and renewable surplus rather than in managing a scarce tank. Second, the gap between raw-sample feasibility and final feasibility is not a defect to be hidden but a design feature to be reported: it quantifies exactly how much work the recourse layer is doing, and it implies that improvements to the feasible mixer—which would raise the ~81% raw figure—translate directly into a lighter coordination burden rather than into better final schedules, since the latter are already optimal. Third, the fact that the ablations all reach a zero gap on the tiny instance is a reminder that component-attribution experiments must be run at a scale where the classical repair cannot trivially recover the optimum; our twenty-seed, no-repair comparison is the honest substitute at the scales where ideal simulation is feasible, and scaling that comparison to instances beyond classical simulation is the natural next step.

### 4.15.2. Comparison with Existing Literature

These results are consistent with the broader finding that, at the scales where ideal simulation is possible, strong classical heuristics are difficult to beat on solution quality [10, 13], which is exactly why we matched budgets and reported the quantum-free baseline on the same surrogate. Our constraint-preserving mixer result reproduces, in an energy-scheduling setting, the Hamming-weight preservation established for XY mixers [2, 12], and the sharp 100% versus 6.25% contrast quantifies its practical effect. Unlike studies that report qubit reduction without separating certified from heuristic elimination, we find that certified reduction contributes nothing on a flexible grid-connected system and attribute the savings transparently to decomposition. The comparison with prior energy-oriented quantum studies is necessarily qualitative because datasets, hardware, solver budgets, and constraint sets differ; our contribution is a reproducible, matched-budget protocol rather than a direct numerical ranking.

### 4.15.3. Scientific Significance of the Proposed Method

The method's incremental value is concentrated in two places. First, making hydrogen-storage coupling an explicit, weighted graph feature lets the partitioner respect temporal inventory arcs, so that the resulting blocks admit a decomposition whose peak width is horizon-independent; this is the structural saving. Second, the discipline of scoring every candidate by the true recourse—never by the penalised surrogate—means that the imperfect QUBO (8–11 € RMSE) cannot corrupt the reported cost, and that feasibility is guaranteed by construction. The quantum sampler itself is not the source of the method's strength; it is a modest contributor whose benefit we measure rather than assume.

It is worth being precise about what "modest contributor" means quantitatively, because the temptation in this literature is to let a statistically significant result stand in for a practically important one. The twenty-seed comparison shows the structured sampler reducing the median optimality gap from 0.811% to 0.144%—a relative improvement of more than fivefold over simulated annealing, and significant at p=0.009. Yet in absolute terms both methods are already within one percent of the exact optimum, and the exact optimum is itself available in milliseconds from the classical MILP solver at every scale we tested. The scientific content of the result is therefore that, *neither the twenty-seed test (p=0.33) nor the five-instance test (p=0.625) shows a significant advantage for quantum sampling over simulated annealing once the pipeline is corrected; we therefore make no claim of a per-budget sampler advantage. It is emphatically not a statement that quantum optimisation is useful here in practice, which it is not, because a mature exact solver dominates on both quality and speed, and because the edge vanishes after classical repair. Distinguishing these two readings is exactly the discipline that the fair-benchmarking gap G5 demands, and it is why we report the matched-budget quantum-free baseline alongside the quantum one.

### 4.15.4. Practical Implications for Hydrogen-Integrated Energy Systems

For operators, the clearest practical signals are that negative-price hours and renewable surplus dominate electrolyser scheduling, that storage capacity is non-binding under the modelled demand (so investment in larger tanks would not reduce cost there), and that cost tracks electricity price almost linearly. For quantum deployment, the implication is sober: decomposition is the lever that makes the problem fit near-term qubit budgets, and the coordination/recourse layer is what makes solutions trustworthy, while any quantum optimisation benefit remains to be demonstrated at scales beyond classical simulation.

A complementary operational reading concerns how the decomposition would be used in practice. Because the peak-qubit requirement is set by the block width rather than the horizon, an operator could in principle schedule an arbitrarily long horizon on a fixed, modest qubit budget by sliding the six-hour window and reconciling storage at each handoff—the same mechanism that holds the width at twelve in our scalability study. This is attractive for rolling-horizon operation, where a facility re-optimises every hour as new price and demand information arrives, because it means the quantum resource requirement does not grow as the planning horizon is extended for look-ahead. The caveat, again reported rather than hidden, is that the classical coordination and recourse cost does grow with the number of blocks, so the architecture trades a fixed quantum footprint for a classical workload that scales with horizon length. Whether that trade is ever worthwhile depends entirely on future hardware: if a quantum sampler one day produces materially better candidates than classical heuristics at block sizes beyond classical simulation, the fixed-width property becomes valuable; if it does not, the classical MILP remains the better tool. Our contribution is to make that conditional explicit and to supply the reproducible benchmark on which the condition can be tested as hardware matures, rather than to assert that the condition is already met. The same benchmark also lets an operator quantify, for their own price and demand data, how much of the scheduling value comes from flexible electrolysis against negative-price hours—a question that is independent of whether the optimiser is quantum or classical, and that the released code answers directly.

### 4.15.5. Limitations and Threats to Validity

Several limitations bound these conclusions. Thermal demand and COP are synthetic and hydrogen demand is simulated, so cross-carrier interactions are only as realistic as those models; the electricity data, though observed, are national aggregates rescaled to a notional facility. Component parameters are assumed, not sourced from a specific techno-economic analysis. The quantum results are ideal or lightly-noised statevector simulations with at most twelve qubits per block; they do not transfer automatically to hardware, where noise, connectivity, and compilation overhead intervene, as the depolarising sweep already hints (expected energy rises from 84.1 to 94.9 as the error rate reaches 0.02). The optimisation effect of quantum sampling is not statistically significant in the corrected pipeline—neither across twenty seeds on one instance (p=0.33) nor across five instances (p=0.625)—and post-repair the quantum and classical generators tie at the optimum, so classical recourse and repair dominate final quality. The QUBO surrogate, though well-correlated in rank (Spearman 0.912–0.930), has zero top-5 recall and ~1–2 € regret, so candidate quality rests heavily on classical selection. Hydrogen storage is non-binding in the base benchmark; only the deliberately constructed binding regime exercises the inter-temporal coupling, and even there the hydrogen-aware partition's gain is confined to graph-cut quality: under the corrected node-based hybrid, every partition (including random) reaches the optimum after repair, so the central hydrogen-aware decomposition shows no end-to-end optimisation advantage. The quantum components are ideal-simulation only. The reproduction reported here is in-environment, not an external clean-session audit. Finally, the coordinator is a heuristic without convergence guarantees. None of these are concealed; they frame the scope of the claims.

### 4.15.6. Implications for Future Quantum Optimization Research

The findings suggest that near-term value from quantum optimisation in this domain, if it emerges, will come from problem structure—decomposition that respects temporal coupling and encodings that preserve the right invariants—rather than from raw sampling power at small scale. Larger devices would allow blocks beyond the classical-simulation ceiling, where the matched-budget comparison could be re-run honestly; better feasible mixers could raise raw-sample feasibility and lighten the repair burden; and tighter surrogates could let the quantum stage carry more of the optimisation. We explicitly decline to claim practical quantum advantage on the present evidence.

There is also a methodological lesson that generalises beyond this benchmark. The architecture that separates proposal from evaluation—letting the quantum stage propose and a classical oracle dispose—is robust precisely because it decouples the two hardest requirements of constrained quantum optimisation: generating diverse low-cost candidates and guaranteeing feasibility. Most reported difficulties with penalty-based QAOA stem from entangling these requirements in a single penalised objective, where a mis-set weight either lets infeasible bitstrings dominate or so dominates the landscape that the optimiser cannot distinguish good feasible solutions. By refusing to let the surrogate define cost, the present framework makes the method's correctness independent of penalty calibration, at the price of a classical evaluation per candidate. For problems where that evaluation is cheap—as the recourse LP is here—this is an attractive trade, and we expect it to transfer to other storage-coupled scheduling problems such as battery dispatch, district heating with thermal storage, and water-network pumping, all of which share the inter-temporal state that makes hydrogen scheduling instructive. Conversely, for problems where feasibility checking is itself expensive, the proposal/evaluation split would need a cheaper surrogate feasibility test, which is a concrete direction for further work. A final direction concerns the interface coordinator: replacing the greedy single-flip repair with a principled dual update on the storage-handoff variables, and characterising the conditions under which such an update provably improves the incumbent, would strengthen the coordination layer from a heuristic into something closer to a bounded method, without over-claiming convergence for the nonconvex discrete master.

# 5. Conclusion

## 5.1. Recapitulation

We built and validated a reproducible electricity–heat–hydrogen scheduling benchmark from real 2019 OPSD electricity data combined with clearly-flagged synthetic heat and simulated hydrogen demand, and formulated a MILP whose balance residuals are at machine precision and whose optimum two independent solvers reproduce exactly. On this benchmark we implemented a hydrogen-aware interaction graph, five partitioners, certified infeasibility-based reduction, a verified QUBO/Ising surrogate, constraint-preserving QAOA, and a recourse-based coordinator. The measured outcomes are a verified structural peak-qubit reduction of up to 88% at T=48 with no loss of optimality, a constraint-preserving mixer that keeps 100% of samples in the one-hot sector versus 6.25% for the standard mixer, 100% final-schedule feasibility enforced by classical recourse, and—newly, in response to peer review—evidence that the quantum sampler shows no statistically significant edge over simulated annealing (twenty-seed p=0.33; five-instance p=0.625) and that any apparent edge disappears after classical repair, that the QUBO surrogate is a good rank guide (Spearman 0.912–0.930) but a poor fine selector (zero top-5 recall), and that the hydrogen-aware partitioner improves cut quality over temporal blocking once hydrogen storage is made binding (0.382 vs 0.432) but—under the corrected node-based hybrid—yields no end-to-end cost advantage, since all partitions reach the optimum after repair. We claim no quantum advantage and no end-to-end decomposition advantage; the robust, defensible contributions are the corrected, bounded, arbitrage-free benchmark with full demand-satisfaction accounting, the structural peak-qubit accounting, the constraint-preserving mixer unit test, and a reproducible matched-budget framework in which classical recourse is shown to dominate.

## 5.2. Future Work

Natural extensions include hardware execution on the decomposed blocks; richer hydrogen-storage and electrolyser physics, including pressure and part-load efficiency; longer horizons and rolling-horizon operation; stochastic and robust formulations of demand and price uncertainty with CVaR recourse; improved feasible mixers and tighter surrogates that let the quantum stage carry more of the optimisation; hardware-aware circuit compilation and connectivity-matched partitioning; multi-objective scheduling that trades cost against emissions or degradation; and validation against real facility telemetry and the genuine When2Heat thermal profiles once available, across multiple seasons and regions.

# Data and Code Availability

The electricity data are the public Open Power System Data time-series package, version 2020-10-06 (DOI 10.25832/time_series/2020-10-06). The synthetic thermal/COP model and the seeded hydrogen-demand generator are fully specified in Section 3.2 and implemented in the released modules `hagdcp_core.py`, `hagdcp_methods.py`, `experiments.py`, and `revision_experiments.py`, together with the figure and table scripts, a central configuration object, fixed random seeds (2026), an environment specification, and a machine-readable manifest with per-artifact SHA-256 checksums. The reproducibility package regenerates every table and figure. Reproduction reported here is in-environment (Section 4.13); a clean external session reproduction is the appropriate next verification step and is supported by the released package. Upon acceptance the complete package will be deposited in a permanent public repository with a citable release identifier and DOI; the repository URL and release tag will be provided in this section at that time.

# References

[1] E. Farhi, J. Goldstone, S. Gutmann. A Quantum Approximate Optimization Algorithm. arXiv:1411.4028 (2014). https://doi.org/10.48550/arXiv.1411.4028

[2] S. Hadfield, Z. Wang, B. O'Gorman, E. G. Rieffel, D. Venturelli, R. Biswas. From the Quantum Approximate Optimization Algorithm to a Quantum Alternating Operator Ansatz. Algorithms 12(2):34 (2019). https://doi.org/10.3390/a12020034

[3] A. Lucas. Ising formulations of many NP problems. Frontiers in Physics 2:5 (2014). https://doi.org/10.3389/fphy.2014.00005

[4] Open Power System Data. Data Package Time series, version 2020-10-06 (2020). https://doi.org/10.25832/time_series/2020-10-06

[5] O. Ruhnau, L. Hirth, A. Praktiknjo. Time series of heat demand and heat pump efficiency for energy system modeling. Scientific Data 6:189 (2019). https://doi.org/10.1038/s41597-019-0199-y

[6] O. Ruhnau, J. Muessel. When2Heat Heating Profiles, OPSD version 2023-07-27 (2023). https://doi.org/10.25832/when2heat/2023-07-27

[7] Q. Huangfu, J. A. J. Hall. Parallelizing the dual revised simplex method. Mathematical Programming Computation 10(1):119–142 (2018). https://doi.org/10.1007/s12532-017-0130-5

[8] L. Zhou, S.-T. Wang, S. Choi, H. Pichler, M. D. Lukin. Quantum Approximate Optimization Algorithm: Performance, Mechanism, and Implementation on Near-Term Devices. Physical Review X 10:021067 (2020). https://doi.org/10.1103/PhysRevX.10.021067

[9] D. J. Egger, J. Mareček, S. Woerner. Warm-starting quantum optimization. Quantum 5:479 (2021). https://doi.org/10.22331/q-2021-06-17-479

[10] K. Blekos, D. Brand, A. Ceschini, et al. A review on Quantum Approximate Optimization Algorithm and its variants. Physics Reports 1068:1–66 (2024). https://doi.org/10.1016/j.physrep.2024.03.002

[11] F. Glover, G. Kochenberger, Y. Du. Quantum Bridge Analytics I: a tutorial on formulating and using QUBO models. 4OR 17:335–371 (2019). https://doi.org/10.1007/s10288-019-00424-y

[12] Z. Wang, N. C. Rubin, J. M. Dominy, E. G. Rieffel. XY mixers: Analytical and numerical results for the quantum alternating operator ansatz. Physical Review A 101:012320 (2020). https://doi.org/10.1103/PhysRevA.101.012320

[13] A. Ajagekar, F. You. Quantum computing for energy systems optimization: Challenges and opportunities. Energy 179:76–89 (2019). https://doi.org/10.1016/j.energy.2019.04.186

[14] S. Boyd, N. Parikh, E. Chu, B. Peleato, J. Eckstein. Distributed Optimization and Statistical Learning via the Alternating Direction Method of Multipliers. Foundations and Trends in Machine Learning 3(1):1–122 (2011). https://doi.org/10.1561/2200000016

[15] G. Karypis, V. Kumar. A Fast and High Quality Multilevel Scheme for Partitioning Irregular Graphs. SIAM Journal on Scientific Computing 20(1):359–392 (1998). https://doi.org/10.1137/S1064827595287997

[16] S. Kirkpatrick, C. D. Gelatt, M. P. Vecchi. Optimization by Simulated Annealing. Science 220(4598):671–680 (1983). https://doi.org/10.1126/science.220.4598.671

[17] J. Preskill. Quantum Computing in the NISQ era and beyond. Quantum 2:79 (2018). https://doi.org/10.22331/q-2018-08-06-79

[18] M. Cerezo, A. Arrasmith, R. Babbush, et al. Variational quantum algorithms. Nature Reviews Physics 3:625–644 (2021). https://doi.org/10.1038/s42254-021-00348-9

[19] E. Farhi, J. Goldstone, S. Gutmann, M. Sipser. Quantum Computation by Adiabatic Evolution. arXiv:quant-ph/0001106 (2000). https://doi.org/10.48550/arXiv.quant-ph/0001106

[20] J. R. McClean, J. Romero, R. Babbush, A. Aspuru-Guzik. The theory of variational hybrid quantum-classical algorithms. New Journal of Physics 18:023023 (2016). https://doi.org/10.1088/1367-2630/18/2/023023

[21] A. Peruzzo, J. McClean, P. Shadbolt, et al. A variational eigenvalue solver on a photonic quantum processor. Nature Communications 5:4213 (2014). https://doi.org/10.1038/ncomms5213

[22] S. Harwood, C. Gambella, D. Trenev, A. Simonetto, D. Bernal, D. Greenberg. Formulating and Solving Routing Problems on Quantum Computers. IEEE Transactions on Quantum Engineering 2:3100117 (2021). https://doi.org/10.1109/TQE.2021.3049230

[23] S. Ebadi, A. Keesling, M. Cain, et al. Quantum optimization of maximum independent set using Rydberg atom arrays. Science 376:1209–1215 (2022). https://doi.org/10.1126/science.abo6587

[24] M. Streif, M. Leib. Training the quantum approximate optimization algorithm without access to a quantum processing unit. Quantum Science and Technology 5:034008 (2020). https://doi.org/10.1088/2058-9565/ab8c2b

[25] G. E. Crooks. Performance of the Quantum Approximate Optimization Algorithm on the Maximum Cut Problem. arXiv:1811.08419 (2018). https://doi.org/10.48550/arXiv.1811.08419

[26] M. Willsch, D. Willsch, F. Jin, H. De Raedt, K. Michielsen. Benchmarking the quantum approximate optimization algorithm. Quantum Information Processing 19:197 (2020). https://doi.org/10.1007/s11128-020-02692-8

[27] IEA. Global Hydrogen Review 2023. International Energy Agency, Paris (2023). https://www.iea.org/reports/global-hydrogen-review-2023

[28] U.S. Department of Energy, Hydrogen and Fuel Cell Technologies Office. H2A: Hydrogen Analysis Production Models (techno-economic tool). https://www.hydrogen.energy.gov/library/tools/h2a-production

[29] A. Sawaya, T. Schmitz, S. Hadfield. Encoding trade-offs and design toolkits in quantum algorithms for discrete optimization. arXiv:2203.14432 (2022). https://doi.org/10.48550/arXiv.2203.14432

[30] P. Virtanen, R. Gommers, T. E. Oliphant, et al. SciPy 1.0: fundamental algorithms for scientific computing in Python. Nature Methods 17:261–272 (2020). https://doi.org/10.1038/s41592-019-0686-2

[31] A. A. Hagberg, D. A. Schult, P. J. Swart. Exploring network structure, dynamics, and function using NetworkX. Proceedings of the 7th Python in Science Conference (SciPy 2008), 11–15 (2008).

[32] Qiskit contributors. Qiskit: An Open-source Framework for Quantum Computing (2023). https://doi.org/10.5281/zenodo.2573505

[33] N. Moll, P. Barkoutsos, L. S. Bishop, et al. Quantum optimization using variational algorithms on near-term quantum devices. Quantum Science and Technology 3:030503 (2018). https://doi.org/10.1088/2058-9565/aab822

[34] F. G. Fuchs, K. O. Lye, H. M. Nilsen, A. J. Stasik, G. Sartor. Constraint preserving mixers for the quantum approximate optimization algorithm. arXiv:2203.06095 (preprint, 2022). https://doi.org/10.48550/arXiv.2203.06095
