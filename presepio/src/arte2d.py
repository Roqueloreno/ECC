"""Arte 2D do arco do presepio (plano XY, mm). Base: 01_ARCO_FRENTE do projeto original.
Origem: centro do arco original. Elipse externa: centro (0,-5.28), a=117, b=100.19."""
import math, re, numpy as np
from manifold3d import Manifold, Mesh, CrossSection, JoinType

P = dict(
    ELIPSE_C=(0.0, -5.28), ELIPSE_A=117.0, ELIPSE_B=100.19,
    ANEL_LED=7.6,            # largura do anel na versao LED (original ~4.6)
    PAREDE_CAMARA=1.2,       # parede lateral da camara de luz
    BERCO_X=39.5,            # meia-largura da zona que fica dentro do berco
    SOLA_Y=(-100.5, -95.0),  # sola achatada (escondida no berco)
    FURO_LACO=[(0.0, 100.46), (0.0, 92.46)], D_FURO_LACO=3.4,
    ARGOLA_DY=106.96, ARGOLA_CORTE=-10.6,   # argola original deslocada; lingueta cortada
    ORELHA_ESTRELA=(0.0, 81.8), D_ORELHA=1.6,
)

def rect(x0, y0, x1, y1):
    return CrossSection.square([x1-x0, y1-y0]).translate([x0, y0])

def elipse(a, b, c=None, n=720):
    c = c or P['ELIPSE_C']
    t = np.linspace(0, 2*math.pi, n, endpoint=False)
    return CrossSection([np.c_[c[0]+a*np.cos(t), c[1]+b*np.sin(t)]])

def circ(x, y, d, n=64):
    return CrossSection.circle(d/2, n).translate([x, y])

def carregar_malha(f):
    s = open(f).read()
    v = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', s), np.float32)
    t = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', s), np.uint32)
    v[:, 2] -= v[:, 2].min()
    return Manifold(Mesh(vert_properties=v, tri_verts=t))

def arte_original(model_dir):
    return carregar_malha(model_dir + '/01_ARCO_FRENTE_12.model').slice(1.5)

def argola_original(model_dir):
    return carregar_malha(model_dir + '/21_ARGOLA_ESTRUTURAL_DOURADA_29.model')

def arte_base(model_dir, led):
    a = arte_original(model_dir)
    bx = P['BERCO_X']; s0, s1 = P['SOLA_Y']
    # remove a lingueta inferior antiga (encaixe M4) e furos
    a = a - rect(-15.5, -106, 15.5, -79.5)
    # achata a base do anel dentro do berco e cria a sola de colagem
    a = a - rect(-bx, -110, bx, s0)
    a = a + rect(-bx, s0, bx, s1)
    if led:
        ea, eb = P['ELIPSE_A'], P['ELIPSE_B']
        anel = elipse(ea, eb) - elipse(ea, eb).offset(-P['ANEL_LED'])
        anel = anel - rect(-bx, -110, bx, s0)
        a = a + anel
    # aba superior: prolonga para baixo + orelha da estrela
    ox, oy = P['ORELHA_ESTRELA']
    a = a + rect(-9, 84.5, 9, 90.0)
    a = a + rect(ox-3, oy, ox+3, 88.0) + circ(ox, oy, 6.0)
    a = a - circ(ox, oy, P['D_ORELHA'])
    furos = P['FURO_LACO'] if not led else P['FURO_LACO'][:1]
    for (x, y) in P['FURO_LACO']:
        a = a - circ(x, y, P['D_FURO_LACO'])     # furos sempre vazados na arte
    if led:   # furo inferior do laco nao existe na versao LED (camara passa ali)
        x, y = P['FURO_LACO'][1]
        a = a + circ(x, y, P['D_FURO_LACO'] + 0.2)
    return a.simplify(0.01)

def camara_led():
    ea, eb = P['ELIPSE_A'], P['ELIPSE_B']; w = P['PAREDE_CAMARA']; bx = P['BERCO_X']
    s0, s1 = P['SOLA_Y']
    c = elipse(ea, eb).offset(-w) - elipse(ea, eb).offset(-(P['ANEL_LED'] - w))
    c = c - rect(-bx, -110, bx, -60)            # para antes do berco nos dois lados
    # lado esquerdo: desce pela sola e sai pela base (x ~ -30)
    yb = -98.9; yt = -96.3
    c = c + rect(-bx-6, yb, -28.7, yt) + rect(-31.3, -102, -28.7, yt)
    # liga o anel (que entra na zona do berco em x=-bx) ao canal da sola
    seg = (elipse(ea, eb).offset(-w) - elipse(ea, eb).offset(-(P['ANEL_LED'] - w)))
    c = c + (seg ^ rect(-bx-8, -110, -bx+0.01, -60))
    return c

def argola_2d_lingueta(model_dir):
    m = argola_original(model_dir)
    cs = m.slice(2.0).translate([0, P['ARGOLA_DY']])
    return cs ^ rect(-20, P['ARGOLA_DY'] + P['ARGOLA_CORTE'], 20, 105.46)
