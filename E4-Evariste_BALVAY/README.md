# Affectation de validateurs PoS en comites (CP-SAT)

## Contexte

Dans une blockchain Proof-of-Stake (ex: Ethereum 2.0), les validateurs sont repartis en comites qui attestent les blocs.
Cette repartition doit etre:

- Equitable: chaque validateur doit participer a un nombre similaire de comites.
- Valide: chaque comite doit respecter une taille minimale et maximale.
- Robuste: les validateurs d'un meme operateur doivent etre separes autant que possible (anti-affinite), pour limiter les risques de pannes corrigees ou de centralisation.

Le probleme se modelise naturellement comme un Bin Packing avec contraintes additionnelles d'equilibre et d'anti-affinite, resolu en Programmation par Contraintes (CP-SAT).

## Objectifs du projet

1. Modeliser l'affectation de validateurs comme un Bin Packing avec contraintes d'equilibre et d'anti-affinite en CP-SAT.
2. Implementer les contraintes de taille de comite, d'equilibre (variance minimale), et de separation des operateurs.
3. Ajouter une dynamique temporelle: comites periodiques, entrees/sorties de validateurs, minimisation du churn.
4. Evaluer sur des donnees Ethereum Beacon Chain (validateurs reels, operateurs connus).
5. Comparer les performances avec:
   - l'algorithme actuel d'Ethereum (random shuffled),
   - un modele PLNE (Programmation Lineaire en Nombres Entiers).

## Formulation du probleme

### Donnees

- Ensemble des validateurs: `V`
- Ensemble des comites: `C`
- Ensemble des operateurs: `O`
- Operateur d'un validateur `v`: `op(v)`
- Taille cible d'un comite: `target_size`
- Bornes de taille: `min_size`, `max_size`
- Horizon temporel discret: `t = 1..T`

### Variables de decision

- `x[v, c, t] in {0,1}`: 1 si le validateur `v` est assigne au comite `c` au temps `t`.

Variables derivees (optionnelles selon le niveau de detail du modele):

- `load[v]`: nombre total d'affectations du validateur `v`.
- `n_op[o, c, t]`: nombre de validateurs de l'operateur `o` dans le comite `c` au temps `t`.
- `churn[v, t]`: 1 si l'affectation de `v` change entre `t-1` et `t`.

### Contraintes principales

1. Affectation unique (ou cardinalite imposee) par pas de temps:

- `sum_c x[v, c, t] = 1` (ou `<= 1` selon le scenario).

2. Capacite des comites:

- `min_size <= sum_v x[v, c, t] <= max_size`.

3. Equilibre global des charges:

- `load[v] = sum_{t,c} x[v, c, t]`.
- Minimisation d'une mesure de dispersion (variance, ecart absolu moyen, max-min).

4. Anti-affinite operateur:

- Limiter `n_op[o, c, t]` pour chaque operateur/comite/temps.
- Penaliser les regroupements excessifs d'un meme operateur dans un comite.

5. Dynamique temporelle (si active):

- Stabilité: minimiser `sum_{v,t} churn[v,t]`.
- Support des entrees/sorties: activer/desactiver des validateurs selon leur disponibilite.

### Fonction objectif (multi-critere)

Minimiser une combinaison ponderee:

- Desequilibre des charges entre validateurs.
- Concentration des operateurs dans les comites.
- Churn temporel (si dynamique).

Exemple:

`min alpha * imbalance + beta * anti_affinity_penalty + gamma * churn`

avec `alpha, beta, gamma` calibres experimentalement.

## Approche technique

### Solveur principal

- OR-Tools CP-SAT (Google), adapte aux contraintes combinatoires et booleennes.

### Baseline 1: Ethereum random shuffled

- Simulation d'une repartition aleatoire melangee, representative de l'approche standard actuelle.

### Baseline 2: PLNE

- Modele MILP resolu avec un solveur lineaire entier (ex: CBC, Gurobi, CPLEX selon disponibilite).

## Metriques d'evaluation

- Faisabilite: taux de solutions valides.
- Equite: variance des charges par validateur.
- Decentralisation: concentration des operateurs (max par comite, indice de Gini/Herfindahl optionnel).
- Robustesse: proportion de comites affectes par la panne d'un operateur majeur.
- Stabilite temporelle: taux de churn inter-epoques.
- Performance algorithmique: temps de resolution, gap, scalabilite.

## Jeux de donnees

- Donnees Beacon Chain (validateurs reels).
- Mapping validateur -> operateur (sources publiques, labels de pools/staking providers).
- Scenarios synthetiques pour tests de stress:
  - concentration forte de gros operateurs,
  - churn eleve,
  - augmentation rapide du nombre de validateurs.

## Structure de projet (proposee)

```text
E4-Evariste_BALVAY/
	README.md
	data/
		raw/
		processed/
	src/
		model_cp_sat.py
		model_milp.py
		ethereum_baseline.py
		dynamics.py
		metrics.py
		experiments.py
	notebooks/
		exploration.ipynb
	results/
		figures/
		tables/
	report/
		paper.pdf
```

## Plan d'execution

1. Formaliser le modele statique CP-SAT (sans dynamique).
2. Ajouter l'objectif multi-critere et calibrer les poids.
3. Integrer la dynamique temporelle (entrees/sorties + churn).
4. Implementer les deux baselines (random shuffled + PLNE).
5. Lancer la campagne experimentale sur donnees reelles et synthetiques.
6. Analyser, visualiser et documenter les resultats.

## Criteres de reussite

- Modele CP-SAT faisable sur des tailles proches de cas reels.
- Amelioration mesurable de l'equite et/ou de l'anti-affinite vs random shuffled.
- Comparaison quantitative claire avec PLNE (qualite/temps).
- Analyse temporelle demonstrant la gestion du churn sans degradation majeure.

## Livrables attendus

- Code source reproductible.
- Scripts d'experimentation et de generation des figures.
- Jeux de donnees prepares (ou instructions de reconstruction).
- Rapport final avec protocole, resultats, limites, pistes futures.

## Limites et extensions possibles

- Prise en compte de la latence reseau/geographie des validateurs.
- Contraintes cryptoeconomiques additionnelles (slashing risk model).
- Optimisation robuste/stochastique pour pannes aleatoires.
- Approche hybride CP-SAT + heuristiques pour tres grandes instances.

## References utiles

- Ethereum Consensus Specs (Beacon Chain)
- OR-Tools CP-SAT documentation
- Litterature Bin Packing contraint / anti-affinite / load balancing
