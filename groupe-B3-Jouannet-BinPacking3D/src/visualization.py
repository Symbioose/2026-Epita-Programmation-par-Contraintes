"""
Visualisation 3D d'une solution de Bin Packing avec Plotly.
"""

import plotly.graph_objects as go
import numpy as np
from typing import List
from .model import Item, Container

# Palette de couleurs distinctes pour les objets
COLORS = [
    '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
    '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990',
    '#dcbeff', '#9A6324', '#fffac8', '#800000', '#aaffc3',
]


def _box_mesh(x0, y0, z0, w, d, h, color, name):
    """Crée un mesh 3D représentant un parallélépipède."""
    x1, y1, z1 = x0 + w, y0 + d, z0 + h
    # 8 sommets du cube
    vx = [x0, x1, x1, x0, x0, x1, x1, x0]
    vy = [y0, y0, y1, y1, y0, y0, y1, y1]
    vz = [z0, z0, z0, z0, z1, z1, z1, z1]
    # 12 triangles (6 faces × 2)
    i_idx = [0,0,0,0,4,4,4,4,0,1,2,3]
    j_idx = [1,2,3,5,5,6,7,3,4,5,6,7]
    k_idx = [2,3,7,6,6,7,3,7,5,6,7,4]  # simplified — use proper winding
    i_idx = [7,0,0,0,4,4,6,6,4,0,3,2]
    j_idx = [3,3,1,2,5,7,5,2,0,1,7,3]
    k_idx = [0,7,2,3,1,0,1,1,5,4,0,6]
    # Faces correctes pour un cube
    i_idx = [0,0,1,1,2,2,3,3,4,4,5,5]
    j_idx = [1,2,2,5,3,6,7,0,5,7,6,4]
    k_idx = [2,3,5,6,6,7,0,4,7,6,7,5]

    return go.Mesh3d(
        x=vx, y=vy, z=vz,
        i=[0,0,0,0,7,7,7,7,0,1,2,3],
        j=[1,2,5,4,6,5,2,3,4,5,6,7],
        k=[2,5,4,1,5,2,3,0,5,6,7,4],
        color=color,
        opacity=0.6,
        name=name,
        showlegend=True,
    )


def plot_bin(items: List[Item], result: dict, bin_idx: int, container: Container):
    """Affiche le contenu d'un seul conteneur en 3D."""
    fig = go.Figure()

    # Contour du conteneur
    cW, cD, cH = container.W, container.D, container.H
    edges_x, edges_y, edges_z = [], [], []
    for a, b in [
        ((0,0,0),(cW,0,0)),((cW,0,0),(cW,cD,0)),((cW,cD,0),(0,cD,0)),((0,cD,0),(0,0,0)),
        ((0,0,cH),(cW,0,cH)),((cW,0,cH),(cW,cD,cH)),((cW,cD,cH),(0,cD,cH)),((0,cD,cH),(0,0,cH)),
        ((0,0,0),(0,0,cH)),((cW,0,0),(cW,0,cH)),((cW,cD,0),(cW,cD,cH)),((0,cD,0),(0,cD,cH)),
    ]:
        edges_x += [a[0], b[0], None]
        edges_y += [a[1], b[1], None]
        edges_z += [a[2], b[2], None]

    fig.add_trace(go.Scatter3d(
        x=edges_x, y=edges_y, z=edges_z,
        mode='lines',
        line=dict(color='black', width=2),
        name='Conteneur',
        showlegend=False,
    ))

    # Objets dans ce bin
    item_count = 0
    for i, (item, b) in enumerate(zip(items, result['assignment'])):
        if b != bin_idx:
            continue
        px, py, pz = result['positions'][i]
        color = COLORS[i % len(COLORS)]
        fig.add_trace(_box_mesh(px, py, pz, item.w, item.d, item.h, color, f'Objet {i}'))
        item_count += 1

    fig.update_layout(
        title=f'Conteneur {bin_idx} ({item_count} objets)',
        scene=dict(
            xaxis=dict(range=[0, cW], title='X (largeur)'),
            yaxis=dict(range=[0, cD], title='Y (profondeur)'),
            zaxis=dict(range=[0, cH], title='Z (hauteur)'),
            aspectmode='manual',
            aspectratio=dict(x=cW, y=cD, z=cH),
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def plot_all_bins(items: List[Item], result: dict, container: Container):
    """Retourne une liste de figures, une par conteneur utilisé."""
    n_bins = result['num_bins']
    return [plot_bin(items, result, b, container) for b in range(n_bins)]


def summary_table(items: List[Item], result: dict, container: Container) -> dict:
    """Résumé statistique de la solution."""
    n_bins = result['num_bins']
    total_vol = sum(item.volume for item in items)
    container_vol = container.volume
    efficiency = total_vol / (n_bins * container_vol) * 100

    return {
        'num_items': len(items),
        'num_bins': n_bins,
        'total_item_volume': total_vol,
        'container_volume': container_vol,
        'space_efficiency_pct': round(efficiency, 1),
        'solve_time_s': result.get('solve_time', None),
        'status': result.get('status', ''),
    }
