Louis Parmentier, Marianne Proux, Ethan Girard

# H1 - Composition Musicale Assistée par Contraintes

> Générer des partitions musicales (mélodies, harmonies) satisfaisant un ensemble de règles musicales encodées comme contraintes CP-SAT.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Modélisation musicale](#2-modélisation-musicale)
3. [Architecture du projet](#3-architecture-du-projet)
4. [Contraintes implémentées](#4-contraintes-implémentées)
5. [Soft constraints et styles](#5-soft-constraints-et-styles)
6. [Génération et export](#6-génération-et-export)
7. [Évaluation](#7-évaluation)
8. [Installation et utilisation](#8-installation-et-utilisation)

---

## 1. Vue d'ensemble

### Problématique

La composition musicale peut être vue comme un **problème de satisfaction de contraintes** : une pièce musicale valide est une séquence de notes et d'accords qui respecte simultanément des dizaines de règles issues de siècles de théorie musicale. Ces règles couvrent :

- la **hauteur** des notes (intervalles permis, résolutions obligatoires)
- l'**harmonie** (accords autorisés, progressions tonales)
- le **contrepoint** (mouvements entre voix, interdiction des quintes parallèles)
- le **rythme** (métrique, placement des temps forts/faibles)
- le **style** (baroque, jazz, contemporain)

L'objectif de ce projet est de modéliser ces règles dans OR-Tools CP-SAT et de générer automatiquement des partitions correctes, esthétiquement cohérentes et exportées en MIDI.

### Ce que le projet n'est pas

Ce projet n'est pas un modèle génératif (pas de réseau de neurones) : la créativité émerge ici de la **combinaison de contraintes strictes et de préférences assouplies (soft constraints)**, ce qui est fondamentalement différent d'une approche par apprentissage. L'idée est ici de réduire la dimension de notre espace de recherche afin de générer une partition musicalement cohérente.

---

## 2. Modélisation musicale

### 2.1 Représentation des notes

Chaque note est encodée par trois variables entières CP-SAT :

| Variable | Domaine | Description |
|----------|---------|-------------|
| `pitch[t]` | 0–127 (MIDI) | Hauteur de la note (60 = Do central) |
| `duration[t]` | {1, 2, 4, 8} | Durée en unités de doubles croches |
| `voice[t]` | 0–3 | Voix (soprano, alto, ténor, basse) |

### 2.2 Représentation harmonique

À chaque **temps fort** (beat), un accord est identifié :

| Variable | Domaine | Description |
|----------|---------|-------------|
| `root[b]` | 0–11 | Fondamentale de l'accord (0 = Do) |
| `quality[b]` | {MAJ, MIN, DOM7, DIM} | Qualité de l'accord |
| `degree[b]` | 1–7 | Degré dans la gamme courante |

### 2.3 Espace de recherche

Pour une mélodie de 16 mesures à 4 voix, en 4/4, l'espace est de l'ordre de :

```
(88 hauteurs × 4 durées × 4 voix)^(16 × 4 × 4) ≈ 10^180 combinaisons
```

Les contraintes réduisent cet espace à un ensemble fini et musicalement valide.

---

## 3. Architecture du projet

```
H1-music-constraints/
│
├── README.md
├── requirements.txt
│
├── core/
│   ├── model.py            # Modèle CP-SAT central
│   ├── variables.py        # Définition des variables (pitch, duration, accord)
│   ├── constraints/
│   │   ├── harmony.py      # Règles d'harmonie tonale
│   │   ├── counterpoint.py # Règles de contrepoint
│   │   ├── rhythm.py       # Contraintes métriques
│   │   └── voice_leading.py# Conduite des voix
│   └── soft_constraints/
│       ├── baroque.py      # Préférences style baroque
│       ├── jazz.py         # Préférences style jazz
│       └── contemporary.py # Préférences style contemporain
│
├── export/
│   └── midi_export.py      # Export vers fichier MIDI
│
├── evaluation/
│   ├── rule_checker.py     # Vérification quantitative des règles
│   └── diversity.py        # Mesure de diversité des générations
│
├── notebooks/
│   ├── H1-1-Harmony.ipynb       # Notebook 1 : contraintes d'harmonie
│   ├── H1-2-Counterpoint.ipynb  # Notebook 2 : contrepoint
│   ├── H1-3-Rhythm.ipynb        # Notebook 3 : rythme et métrique
│   ├── H1-4-Styles.ipynb        # Notebook 4 : soft constraints et styles
│   └── H1-5-Evaluation.ipynb    # Notebook 5 : évaluation
│
└── examples/ 
    └── *.mid
```

---

## 4. Contraintes implémentées

### 4.1 Contraintes d'harmonie tonale

Ces contraintes assurent que les notes s'inscrivent dans une tonalité et forment des accords cohérents.

**Appartenance à la gamme** : toute note doit appartenir aux 7 degrés de la gamme courante (ou de ses modes).

```python
# pitch % 12 ∈ scale_degrees
for t in range(n_notes):
    model.AddAllowedAssignments(
        [pitch_class[t]],
        [(d,) for d in scale_degrees[key]]
    )
```

**Contrainte de tonique** : la première et la dernière note de chaque phrase doivent être la tonique ou la dominante.

**Progressions d'accords autorisées** : on encode une matrice de transitions entre degrés (do→fa, fa→sol, sol→do autorisés ; sol→fa interdit en harmonie classique car sonne faux).

```python
# degree[b+1] doit être un successeur valide de degree[b]
for b in range(n_beats - 1):
    model.AddAllowedAssignments(
        [degree[b], degree[b+1]],
        allowed_progressions[style]
    )
```

**Résolution de la sensible** : le 7ème degré (sensible) doit monter par demi-ton vers la tonique.

### 4.2 Contraintes de contrepoint

Le contrepoint définit les règles de mouvement entre voix simultanées.

**Intervalles consonants** : les intervalles entre deux voix simultanées doivent être consonants (unisson, tierce, quinte, sixte, octave) aux temps forts.

```python
interval = model.NewIntVar(0, 127, f'interval_{t}_{v1}_{v2}')
model.Add(interval == pitch[t][v1] - pitch[t][v2])
# interval % 12 ∈ {0, 3, 4, 7, 8, 9} (consonances)
```

**Interdiction des quintes et octaves parallèles** : si deux voix forment une quinte (ou octave) juste, elles ne peuvent pas former le même intervalle au temps suivant par mouvement semblable.

```python
# Si interval[t] == 7 ET interval[t+1] == 7 ET même direction → INTERDIT
for t in range(n_beats - 1):
    for v1, v2 in voice_pairs:
        same_interval = model.NewBoolVar(...)
        same_direction = model.NewBoolVar(...)
        model.AddBoolOr([same_interval.Not(), same_direction.Not()])
```

**Interdiction du mouvement direct vers quinte/octave** : deux voix ne peuvent pas atteindre une quinte ou octave par mouvement semblable.

**Contrainte de tessiture** : chaque voix reste dans sa plage vocale naturelle pour éviter les transitions abruptes.

| Voix | Min (MIDI) | Max (MIDI) | Exemple |
|------|-----------|-----------|---------|
| Soprano | 60 (Do4) | 81 (La5) | |
| Alto | 53 (Fa3) | 74 (Ré5) | |
| Ténor | 48 (Do3) | 69 (La4) | |
| Basse | 40 (Mi2) | 62 (Ré4) | |

**Croisements de voix interdits** : la voix supérieure (main droite) doit toujours être plus haute que la voix inférieure (main gauche).

```python
for t in range(n_beats):
    model.Add(pitch[t][SOPRANO] >= pitch[t][ALTO])
    model.Add(pitch[t][ALTO]    >= pitch[t][TENOR])
    model.Add(pitch[t][TENOR]   >= pitch[t][BASS])
```

### 4.3 Contraintes rythmiques

**Contrainte métrique** : les temps forts (1er et 3ème temps en 4/4) reçoivent des notes plus longues ou des consonances.

**Syncope** : une syncope (note commençant sur un temps faible et prolongée sur un temps fort) est autorisée mais encodée explicitement et dépend du cas.

**Contrainte de durée totale** : la somme des durées par voix doit être égale au nombre de mesures × valeur de la mesure.

```python
model.Add(sum(duration[t] for t in voice_notes[v]) == n_measures * beats_per_measure)
```

**Dissonances de passage** : une dissonance est autorisée si elle est de courte durée (double croche ou croche) et se situe entre deux consonances par mouvement conjoint, celle-ci dépend du style ou autre contraintes spécifiques.

---

## 5. Soft Constraints et Styles

Les soft constraints permettent d'orienter la génération vers un style particulier **sans rendre la solution infaisable**. On les implémente via des **variables de coût** pénalisées dans la fonction objectif.

### Architecture des soft constraints

```python
# Chaque préférence génère un coût à minimiser
cost_vars = []

# Exemple : préférence pour les mouvements conjoints (baroque)
for t in range(n_notes - 1):
    leap = model.NewIntVar(0, 127, f'leap_{t}')
    model.AddAbsEquality(leap, pitch[t+1] - pitch[t])
    # Pénaliser les grands sauts
    leap_cost = model.NewIntVar(0, 100, f'leap_cost_{t}')
    model.AddMaxEquality(leap_cost, [leap - 2, model.NewConstant(0)])
    cost_vars.append(leap_cost)

model.Minimize(sum(cost_vars))
```

### Tableau d'exemple de préférences par style

| Préférence | Baroque | Jazz | Contemporain |
|-----------|---------|------|--------------|
| Mouvement conjoint favorisé | ✓✓ | ✓ | — |
| Accords de 7ème | rare | ✓✓ | ✓ |
| Accords de 9ème/11ème | ✗ | ✓✓ | ✓✓ |
| Chromatisme | rare | ✓ | ✓✓ |
| Syncopes | rare | ✓✓ | ✓ |
| Pédale de dominante | ✓✓ | ✓ | — |
| Microtonalité | ✗ | ✗ | ✓ |

### Gestion du compromis qualité/temps

Le solveur dispose d'un budget-temps configurable. Passé ce délai, il retourne la **meilleure solution trouvée** (pas nécessairement optimale) :

```python
solver.parameters.max_time_in_seconds = 30
solver.parameters.relative_gap_limit = 0.05  # Accepter solution à 5% de l'optimal
```

---

## 6. Génération et Export


### 6.1 MIDI

Le fichier MIDI permet l'écoute directe. On utilise la bibliothèque `midiutil` :

```python
from midiutil import MIDIFile
midi = MIDIFile(4)  # 4 pistes (voix)
for voice_id, notes in enumerate(solution):
    for pitch, duration, time in notes:
        midi.addNote(voice_id, 0, pitch, time, duration, velocity=80)
```

---

## 7. Évaluation

### 7.1 Évaluation quantitative

Un module `rule_checker.py` relit la solution générée et calcule :

| Métrique | Description | Cible |
|----------|-------------|-------|
| `hard_violation_rate` | % de contraintes hard violées | 0% |
| `consonance_rate` | % de consonances aux temps forts | > 90% |
| `parallel_fifth_count` | Nombre de quintes parallèles | 0 |
| `voice_crossing_count` | Nombre de croisements de voix | 0 |
| `scale_adherence` | % de notes dans la gamme | > 95% |
| `style_score` | Score moyen des soft constraints | maximisé |

### 7.2 Évaluation qualitative

Soumission des extraits générés (anonymisés, sans indiquer qu'ils sont générés par ordinateur) à des musiciens avec questions posées :

1. Cet extrait vous semble-t-il musicalement cohérent ? (1–5)
2. Reconnaissez-vous un style particulier ?
3. Quel est le défaut principal que vous percevez ?

### 7.3 Diversité des générations

Pour éviter que le solveur ne produise toujours la même solution, on utilise des **solution constraints** successives (interdire les solutions déjà trouvées) et on mesure la diversité via la distance de Hamming sur les séquences de hauteurs.

---

## 8. Installation et utilisation

### Dépendances

```bash
pip install ortools midiutil music21 numpy matplotlib
```

| Bibliothèque | Rôle |
|-------------|------|
| `ortools` | Solveur CP-SAT |
| `midiutil` | Export MIDI |
| `music21` | Analyse et notation musicale |
| `numpy` | Calculs matriciels (covariance, distances) |
| `matplotlib` | Visualisation (piano roll, histogrammes) |

### Lancement rapide

```bash
# Générer un choral baroque en Do majeur (16 mesures, 4 voix)
python -m core.model \
  --style baroque \
  --key Do \
  --mode majeur \
  --measures 16 \
  --voices 4 \
  --output examples/output_baroque

# Fichiers générés :
# examples/output_baroque.mid
# examples/output_baroque_solfege.txt   ← partition en Do Ré Mi…
```

### Lancer les notebooks

```bash
jupyter notebook notebooks/
```

Les notebooks sont numérotés dans l'ordre recommandé (H1-1 à H1-5).

---