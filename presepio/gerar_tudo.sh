#!/usr/bin/env bash
# Regenera todas as pecas (stl/), o relatorio de verificacao e os projetos Bambu (3mf/).
# Requisitos: python3 + pip install manifold3d trimesh numpy networkx scipy rtree
set -euo pipefail
cd "$(dirname "$0")"
python3 -I src/gerar.py origem/Objects stl
python3 -I src/montar_3mf.py origem stl 3mf
echo "OK - veja stl/relatorio.json (todas as colisoes/interferencias devem ser 0)"
