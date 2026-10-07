"""Gera todas as pecas do Arco Presepio v2 (versao LED e versao SEM LED).
Uso: python3 gerar.py <pasta_Objects_do_3mf_original> <pasta_saida>
Coordenadas de montagem: arco no plano XY (mm), espessura em Z (-3..+3), frente = +Z."""
import sys, math, json, os, numpy as np, trimesh
from manifold3d import Manifold, CrossSection, OpType
sys.path.insert(0, os.path.dirname(__file__))
from arte2d import P, rect, circ, elipse, arte_base, camara_led, argola_2d_lingueta, argola_original

MD, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

# ---------------- parametros (ajustar apos os testes) ----------------
T_METADE   = 3.0     # espessura de cada metade (arco colado = 6.0)
PELE_LED   = 0.8     # pele sobre a camara de luz (teste: 0.6 / 0.8 / 1.0)
CH_EXT     = 0.6     # chanfro da face de vitrine (sem LED)
CH_EXT_LED = 0.4     # chanfro da face de vitrine (LED, impresso na mesa)
CH_COLA    = 0.4     # chanfro da borda de colagem (forma o friso em V)
FILETE     = dict(recuo=0.9, largura=0.7, prof=0.4, largura_min=4.4)
D_CAVILHA, P_CAVILHA = 2.0, 2.0   # furo p/ cavilha de filamento 1.75 mm
FOLGA_ARGOLA, ESP_ARGOLA = 0.15, 4.0
# berco / encaixe do copo (pe do copo: D de raio 30.0, chanfro reto em x=28.5, ~4.7 mm de altura)
R_PE, X_CHANFRO_PE = 30.0, 28.5
FOLGA_PE   = 0.20    # folga radial do bolso D
INTERF     = 0.25    # interferencia da trava (teste: 0.15 / 0.25 / 0.35)
ROT_CHANFRO = 0.0    # graus; 0 = chanfro do pe virado para +X (direita), igual a base original
PROF_BOLSO = 6.0
R_BERCO    = 40.0
FOLGA_FENDA = 0.15   # por lado
DEDOS_ANG  = (30.0, 150.0, 270.0)
IMA_D, IMA_H = 8.0, 3.0           # PROVISORIO: confirmar o ima
CAIXA_PILHA = (38.0, 26.0, 12.0)  # PROVISORIO: medir a caixa de pilha do fio (C x L x A)
STEP = 0.2   # = altura de camada; chanfro em escada alinhado com as camadas

def save(m, name, info=None):
    me = m.to_mesh()
    tm = trimesh.Trimesh(me.vert_properties[:, :3], me.tri_verts, process=False)
    tm.export(os.path.join(OUT, name + '.stl'))
    b = tm.bounds
    rec = dict(arquivo=name + '.stl', estanque=bool(tm.is_watertight), manifold_ok=str(m.status()).endswith('NoError'), genus=m.genus(), volume_cm3=round(tm.volume / 1000, 2),
               dims_mm=[round(float(x), 1) for x in (b[1] - b[0])])
    if info: rec.update(info)
    REL.append(rec); print(rec)
REL = []

def ext(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])

def chanfrado(cs, h, c_base, c_topo):
    """Extruda cs de 0..h com chanfros 45 graus (escada de 0.1 mm) na base e no topo."""
    partes = []
    nb, nt = int(round(c_base / STEP)), int(round(c_topo / STEP))
    for k in range(nb):
        partes.append(ext(cs.offset(-(c_base - k * STEP)), k * STEP, (k + 1) * STEP))
    partes.append(ext(cs, nb * STEP, h - nt * STEP))
    for k in range(nt):
        z = h - nt * STEP + k * STEP
        partes.append(ext(cs.offset(-(k + 1) * STEP), z, z + STEP))
    return Manifold.batch_boolean(partes, OpType.Add)

def abertura(cs, r):
    return cs.offset(-r).offset(r)

def filete(art, excluir=None):
    f = FILETE
    g = (art.offset(-f['recuo']) - art.offset(-f['recuo'] - f['largura'])) ^ abertura(art, f['largura_min'] / 2)
    g = g - rect(-P['BERCO_X'] - 1, -120, P['BERCO_X'] + 1, -88)   # nada dentro do berco
    g = g - rect(-50, 55, 50, 120)                                   # area coberta pelo laco
    if excluir is not None: g = g - excluir
    # remove fragmentos pequenos
    keep = [c for c in g.decompose() if c.area() > 1.5]
    return CrossSection.compose(keep) if keep else CrossSection()

def pontos_cavilha(art, led, excluir):
    cand = [(-20, -97.75), (20, -97.75), (-78, -90), (78, -90), (-85, -88), (85, -88), (-62, -92), (62, -92)]
    if not led:
        ea, eb = P['ELIPSE_A'] - 2.3, P['ELIPSE_B'] - 2.3
        for ang in (25, 155, 62, 118, -25, 205):
            t = math.radians(ang); cand.append((ea * math.cos(t), P['ELIPSE_C'][1] + eb * math.sin(t)))
    ok = []
    seguro = art.offset(-(D_CAVILHA / 2 + 0.7))
    if excluir is not None: seguro = seguro - excluir.offset(D_CAVILHA / 2 + 0.8)
    for (x, y) in cand:
        if (seguro ^ circ(x, y, 0.2)).area() > 0.02: ok.append((x, y))
    return ok

def metade(led, frente):
    art = arte_base(MD, led)
    t = T_METADE
    ce = CH_EXT_LED if led else CH_EXT
    # local: h=0 face de colagem, h=t face de vitrine
    m = chanfrado(art, t, CH_COLA, ce)
    excl = None
    if led:
        cam = camara_led()
        ea, eb = P['ELIPSE_A'], P['ELIPSE_B']
        anel = (elipse(ea, eb) - elipse(ea, eb).offset(-P['ANEL_LED'])).offset(0.6)
        anel = anel - rect(-P['BERCO_X'], -120, P['BERCO_X'], -88)
        m = m - ext(cam, -1, t - PELE_LED)
        excl = anel + cam
    g = filete(art, excl)
    m = m - ext(g, t - FILETE['prof'], t + 1)
    cav = pontos_cavilha(art, led, excl)
    for (x, y) in cav:
        m = m - Manifold.cylinder(P_CAVILHA + 1, D_CAVILHA / 2, D_CAVILHA / 2, 32).translate([x, y, -1])
    lng = argola_2d_lingueta(MD)
    bolso = (lng + rect(-6, 104.5, 6, 107)).offset(FOLGA_ARGOLA)
    m = m - ext(bolso, -1, ESP_ARGOLA / 2 + 0.05)
    if frente:
        asm = m                                    # z 0..3
    else:
        asm = m.mirror([0, 0, 1])                  # z -3..0
    return asm, art, cav

def para_impressao(asm, led, frente):
    # LED: vitrine na mesa ; SEM LED: vitrine para cima
    vitrine_na_mesa = led
    if frente == vitrine_na_mesa:     # precisa virar 180 graus em X
        p = asm.rotate([180, 0, 0])
    else:
        p = asm
    bb = p.bounding_box()
    return p.translate([-(bb[0] + bb[3]) / 2, -(bb[1] + bb[4]) / 2, -bb[2]])

ASM = {}; ARTE = {}
for led in (False, True):
    tag = 'LED' if led else 'SEM_LED'
    for frente in (True, False):
        asm, art, cav = metade(led, frente)
        ASM[(led, frente)] = asm; ARTE[led] = art
        nome = f'{tag}_01_ARCO_{"FRENTE" if frente else "VERSO"}'
        save(para_impressao(asm, led, frente), nome, dict(cavilhas=len(cav)))

# ---------------- berco ----------------
def fenda_2d():
    zona = rect(-R_BERCO - 2, -130, R_BERCO + 2, -60)
    f = ((ARTE[False] + ARTE[True]) ^ zona).offset(0.2)
    # varredura vertical: tudo abaixo do contorno superior tambem e fenda (montagem por cima, sem pontes)
    f = CrossSection.batch_boolean([f.translate([0, -k * 0.25]) for k in range(0, 80)], OpType.Add)
    # sela: a fenda precisa ser aberta por baixo para o berco descer sobre o anel fechado
    return f + rect(-R_BERCO - 2, -130, R_BERCO + 2, P['SOLA_Y'][0] + 0.3)

F2 = fenda_2d()
pts = np.vstack([np.array(p) for p in (F2 ^ rect(-R_PE - 0.5, -130, R_PE + 0.5, -60)).to_polygons()])
S_TOPO = float(pts[:, 1].max())
Y_PISO = S_TOPO + 1.2
Y_TOPO = Y_PISO + PROF_BOLSO

def bolso_D():
    c = CrossSection.circle(R_PE + FOLGA_PE, 256) ^ rect(-50, -50, X_CHANFRO_PE + FOLGA_PE, 50)
    return c.rotate(ROT_CHANFRO)

def dedos_e_valas(topo):
    """Valas (removidas) e dedos flexiveis com trava (adicionados), coords locais do disco (u,v,w)."""
    r_in = R_PE + FOLGA_PE; t_d = 1.2; folga_vala = 0.8
    w_raiz = topo - 9.0
    valas, dedos = [], []
    for a in DEDOS_ANG:
        a = a + ROT_CHANFRO
        larg = 20.0; extra = math.degrees(folga_vala / r_in)
        prof_v = CrossSection([[(r_in - 0.8, w_raiz), (r_in + t_d + folga_vala, w_raiz),
                                (r_in + t_d + folga_vala, topo + 1), (r_in - 0.8, topo + 1)]])
        v = Manifold.revolve(prof_v, 96, larg + 2 * extra).rotate([0, 0, a - larg / 2 - extra])
        valas.append(v)
        r_l = R_PE - INTERF
        prof_d = CrossSection([[(r_in, w_raiz), (r_in + t_d, w_raiz), (r_in + t_d, topo),
                                (r_in, topo), (r_in, topo - 0.05), (r_l, topo - 0.45),
                                (r_l, topo - 0.65), (r_in, topo - 1.1)]])
        d = Manifold.revolve(prof_d, 96, larg).rotate([0, 0, a - larg / 2])
        dedos.append(d)
    return valas, dedos

def disco_base(y_b, y_t):
    h = y_t - y_b
    d = Manifold.cylinder(h, R_BERCO, R_BERCO, 256)
    sombra = CrossSection([[(R_BERCO - 2.0, -1), (R_BERCO + 1, -1), (R_BERCO + 1, 3.0), (R_BERCO, 3.0), (R_BERCO, 2.0), (R_BERCO - 2.0, 0.0)]])
    topo = CrossSection([[(R_BERCO - 1.5, h), (R_BERCO, h - 1.5), (R_BERCO + 1, h - 1.5), (R_BERCO + 1, h + 1), (R_BERCO - 1.5, h + 1)]])
    return d - Manifold.revolve(sombra, 256) - Manifold.revolve(topo, 256)

def fenda_local(y_b):
    f = Manifold.extrude(F2, 6.0 + 2 * FOLGA_FENDA).translate([0, 0, -(3.0 + FOLGA_FENDA)])
    return f.rotate([90, 0, 0]).translate([0, 0, -y_b])

def ima(u, v):
    return Manifold.cylinder(IMA_H + 0.2 + 1, IMA_D / 2 + 0.1, IMA_D / 2 + 0.1, 48).translate([u, v, -1])

def berco(led):
    if led:
        cl, cw, chh = CAIXA_PILHA
        y_b = Y_PISO - 1.2 - chh - 0.3 - 1.6
    else:
        y_b = -102.0
    h = Y_TOPO - y_b
    d = disco_base(y_b, Y_TOPO)
    d = d - fenda_local(y_b)
    bol = Manifold.extrude(bolso_D(), PROF_BOLSO + 1).translate([0, 0, h - PROF_BOLSO])
    lead = Manifold.extrude(bolso_D().offset(0.5), 0.5).translate([0, 0, h - 0.5])
    d = d - bol - lead
    valas, dedos = dedos_e_valas(h)
    for v in valas: d = d - v
    for k in dedos: d = d + k
    imas = [(0, -24), (0, 24)] if not led else [(0, -24), (28, 18), (-28, 18)]
    for (u, v) in imas: d = d - ima(u, v)
    extra = {}
    if led:
        cl, cw, chh = CAIXA_PILHA
        v0 = 3.0 + FOLGA_FENDA + 1.45
        comp = Manifold.cube([cl + 0.6, cw + 0.6, chh + 0.3 + 1.6]).translate([-(cl + 0.6) / 2, v0, -0.01])
        rebaixo = Manifold.cube([cl + 2.6, cw + 2.6, 1.6]).translate([-(cl + 2.6) / 2, v0 - 1.0, -0.01])
        canal = Manifold.cube([16, 7.0, 3.0]).translate([-32.5, 1.0, -0.01])
        d = d - comp - rebaixo - canal
        # tampa
        tp = Manifold.cube([cl + 2.6 - 0.3, cw + 2.6 - 0.3, 1.6]).translate([-(cl + 2.3) / 2, 0, 0])
        aro_ext = Manifold.cube([cl + 0.6 - 0.1, cw + 0.6 - 0.1, 3.0]).translate([-(cl + 0.5) / 2, (2.3 - 0.5) / 2 + 0.5, 1.6])
        aro_int = Manifold.cube([cl + 0.6 - 2.5, cw + 0.6 - 2.5, 3.2]).translate([-(cl - 1.9) / 2, (2.3 - 0.5) / 2 + 1.7, 1.5])
        unha = Manifold.cube([10, 2.0, 1.0]).translate([-5, -0.01, -0.01])
        tampa = (tp + (aro_ext - aro_int)) - unha
        save(tampa, 'LED_04_TAMPA_PILHA', dict(obs='caixa de pilha PROVISORIA: %s mm' % (CAIXA_PILHA,)))
        extra['caixa_pilha_provisoria'] = CAIXA_PILHA
    extra.update(altura_mm=round(h, 2), y_base=round(y_b, 2))
    return d, y_b, extra

BERCO = {}
for led in (False, True):
    d, y_b, extra = berco(led)
    BERCO[led] = (d, y_b)
    save(d, ('LED' if led else 'SEM_LED') + '_02_BERCO_COPO', extra)

# ---------------- pecas comuns ----------------
arg = argola_original(MD)
corte = Manifold.cube([40, 40, 10]).translate([-20, P['ARGOLA_CORTE'] - 40, -1])
save(arg - corte, 'COMUM_ARGOLA_DOURADA_v2', dict(cor='dourado'))
pino = Manifold.cylinder(2.0, 3.0, 3.0, 48) + Manifold.cylinder(2.0 + 8.0, 1.55, 1.55, 32)
save(pino, 'COMUM_PINO_LACO', dict(qtd_sem_led=2, qtd_led=1))
# plinto opcional (bancada)
L, W, H = 124.0, 66.0, 6.0
tt = np.linspace(0, 2 * np.pi, 256, endpoint=False)
el = CrossSection([np.c_[L / 2 * np.cos(tt), W / 2 * np.sin(tt)]])
pl = chanfrado(el, H, 0.4, 1.2)
pl = pl - Manifold.cylinder(2, R_BERCO + 0.3, R_BERCO + 0.3, 256).translate([0, 0, H - 1.2])
for (u, v) in [(0, -24), (0, 24), (28, 18), (-28, 18)]:
    pl = pl - Manifold.cylinder(IMA_H + 0.2 + 1, IMA_D / 2 + 0.1, IMA_D / 2 + 0.1, 48).translate([u, v, H - 1.2 - IMA_H - 0.2])
save(pl, 'COMUM_PLINTO_BANCADA_opcional')

# ---------------- testes ----------------
for i, it in enumerate((0.15, 0.25, 0.35)):
    INTERF = it
    h = 10.4
    anel = Manifold.cylinder(h, 34.0, 34.0, 256)
    anel = anel - Manifold.extrude(bolso_D(), PROF_BOLSO + 1).translate([0, 0, h - PROF_BOLSO])
    anel = anel - Manifold.cylinder(h, 24, 24, 128).translate([0, 0, -1])   # economia
    valas, dedos = dedos_e_valas(h)
    for v in valas: anel = anel - v
    for k in dedos: anel = anel + k
    for j in range(i + 1):
        anel = anel - Manifold.cube([1.2, 3, h + 2]).translate([-33.0 + j * 2.2 - 0.6, -34.5, -1]).rotate([0, 0, 180])
    save(anel, f'TESTE_ENCAIXE_COPO_{int(it*100):02d}', dict(interferencia_mm=it))
INTERF = 0.25

# ---------------- verificacoes de montagem ----------------
def perfil_copo():
    from arte2d import carregar_malha
    c = carregar_malha(MD + '/22_COPO_ADAPTA_FUNDO_M4_14.model')
    zs = np.arange(0.0, 85.0, 0.5); rs = []
    for z in zs:
        pol = c.slice(min(z + 0.01, 84.9)).to_polygons()
        rs.append(max(np.hypot(*(np.array(p) - [0, 0]).T).max() for p in pol) if pol else 0)
    return zs, np.array(rs)
zs, rs = perfil_copo()
pts = [(r, Y_PISO + z) for z, r in zip(zs, rs)] + [(-r, Y_PISO + z) for z, r in zip(zs[::-1], rs[::-1])]
sil = CrossSection([pts]).offset(1.0)
chk = {}
for led in (False, True):
    inter = (ARTE[led] ^ sil) - rect(-60, -130, 60, Y_PISO + 0.5)
    chk['colisao_copo_arco_' + ('LED' if led else 'SEM_LED') + '_mm2'] = round(inter.area(), 3)
chk['y_piso_copo'] = round(Y_PISO, 2); chk['y_topo_copo'] = round(Y_PISO + 85.0, 2)
chk['y_topo_berco'] = round(Y_TOPO, 2); chk['topo_da_fenda'] = round(S_TOPO, 2)
# arco dentro da fenda: interferencia 3D
for led in (False, True):
    d, y_b = BERCO[led]
    d_asm = d.translate([0, 0, y_b]).rotate([-90, 0, 0])  # local -> montagem
    for frente in (True, False):
        v = (ASM[(led, frente)] ^ d_asm).volume()
        chk[f'interf_berco_{"LED" if led else "SEM_LED"}_{"F" if frente else "V"}_mm3'] = round(v, 3)
json.dump(dict(pecas=REL, verificacoes=chk), open(os.path.join(OUT, 'relatorio.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(chk, indent=1))
