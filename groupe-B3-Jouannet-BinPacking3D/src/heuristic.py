"""
Heuristique de référence : First Fit Decreasing (FFD) en 3D simplifié.

Les objets sont triés par volume décroissant, puis placés dans le premier
conteneur où ils entrent, en empilant le long de l'axe z (hauteur).
C'est une baseline naïve — pas optimale, mais rapide et déterministe.
"""

from typing import List
from .model import Item, Container


def first_fit_decreasing(items: List[Item], container: Container) -> dict:
    """
    Heuristique FFD simplifiée : empilement 1D le long de z.
    Sert uniquement de baseline pour comparer avec CP-SAT.
    """
    # Tri par volume décroissant
    order = sorted(range(len(items)), key=lambda i: -items[i].volume)

    bins: List[List[tuple]] = []  # chaque bin : liste de (item_idx, x, y, z)
    bin_heights: List[int] = []   # hauteur cumulée utilisée dans chaque bin

    for i in order:
        item = items[i]
        placed = False

        for b_idx, height in enumerate(bin_heights):
            if (item.w <= container.W
                    and item.d <= container.D
                    and height + item.h <= container.H):
                bins[b_idx].append((i, 0, 0, height))
                bin_heights[b_idx] += item.h
                placed = True
                break

        if not placed:
            bins.append([(i, 0, 0, 0)])
            bin_heights.append(item.h)

    # Reconstruction des résultats
    assignment = [0] * len(items)
    positions = [(0, 0, 0)] * len(items)
    for b_idx, bin_items in enumerate(bins):
        for (idx, px, py, pz) in bin_items:
            assignment[idx] = b_idx
            positions[idx] = (px, py, pz)

    return {
        'num_bins': len(bins),
        'assignment': assignment,
        'positions': positions,
    }
