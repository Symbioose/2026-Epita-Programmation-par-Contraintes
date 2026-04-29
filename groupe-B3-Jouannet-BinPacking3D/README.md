# B3 — Chargement de conteneurs (Bin Packing 3D)

**Auteur** : Emile Jouannet (solo)
**Soutenance** : Vendredi 22 mai — 16h15

## Problème

Placer un ensemble d'objets parallélépipédiques dans un nombre minimal de conteneurs, en respectant :
- Non-chevauchement des objets
- Orientations autorisées
- Contraintes de fragilité (objets fragiles en haut)
- Poids maximum par conteneur

## Structure

```
src/
  model.py          # Modèle CP-SAT (OR-Tools)
  heuristic.py      # Heuristique de référence (First Fit Decreasing)
  visualization.py  # Visualisation 3D (plotly)
notebook/
  exploration.ipynb # Notebook principal : modèle, benchmarks, analyse
slides/             # Slides de soutenance (PDF)
demo/               # Démos préparées
data/               # Instances PACKLIB
```

## Installation

```bash
pip install ortools plotly numpy pandas
```

## Lancement rapide

```python
from src.model import Item, Container, solve
from src.visualization import plot_solution

container = Container(W=10, D=10, H=10)
items = [Item(w=3, d=4, h=5), Item(w=6, d=2, h=3), Item(w=4, d=4, h=4)]
result = solve(items, container)
print(f"Bins utilisés : {result['num_bins']}")
```

## Références

- Martello, Pisinger, Vigo (2000). *The Three-Dimensional Bin Packing Problem*. Operations Research.
- PACKLIB benchmarks : http://people.brunel.ac.uk/~mastjjb/jeb/orlib/binpackinfo.html
- OR-Tools CP-SAT : https://developers.google.com/optimization/cp/cp_solver
