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
# folgas validadas no teste de 07/10: furo +0.3 nao entrou, +0.5 (0.25 radial) entrou
D_CAVILHA, P_CAVILHA = 2.25, 2.0  # furo p/ cavilha de filamento 1.75 mm (0.25 radial)
FOLGA_ARGOLA, ESP_ARGOLA = 0.25, 4.0
D_PINO = 2.9                      # haste do pino do laco (furos de 3.4)
# berco / assento do copo: vaso "Copo luminoso" na escala do arquivo (80.9 x 80.9 x 80; perfil em copo_perfil.json)
COPO = json.load(open(os.path.join(os.path.dirname(__file__), 'copo_perfil.json')))
ALT_ASSENTO  = 4.5    # altura do abraco (a arte do copo comeca em ~4.8 mm)
FOLGA_ASSENTO = 0.20  # folga radial no cone (abraco leve)
CHAPA_COPO   = 0.0    # opcional: espessura de chapinha metalica sob o copo (so se usar imas)
R_IMA_COPO = 16.0   # raio dos imas: colados POR DENTRO do copo, no piso (1.3 mm), escondidos sob a vela
IMAS_ASSENTO = [(R_IMA_COPO * math.cos(math.radians(a)), R_IMA_COPO * math.sin(math.radians(a))) for a in (30, 150, 270)]   # 3 pares de ima copo/berco
R_BERCO    = 40.0
FOLGA_FENDA = 0.25   # por lado
# luz (versao LED)
MODO_ESTRELA = 'furo'     # FINAL: vazada (luz sai e cintila) | 'janela' = pele fina so na estrela
PELE_JANELA  = 0.4
PASSO_ESTRELA = 9.0       # mm ao longo do anel
PASSO_JANELA_BORDA = 18.0 # janelas na borda externa (luz saindo para fora)
IMA_D, IMA_H = 3.95, 1.89          # imas do cliente (bolso: +0.2 no diametro, +0.2 na altura)
CAIXA_PILHA = (28.55, 18.50, 12.35)  # caixa de pilha do fio anjo (medida pelo cliente, C x L x A)
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

def estrela4(x, y, R, r, giro=0.0):
    pts = []
    for i in range(8):
        a = math.radians(90 + giro + i * 45); rr = R if i % 2 == 0 else r
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return CrossSection([pts])

def pontos_anel(a, b, passo, fase=0.0):
    t = np.linspace(0, 2 * math.pi, 4000)
    c = P['ELIPSE_C']; x = a * np.cos(t); y = c[1] + b * np.sin(t)
    s = np.r_[0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
    out = []
    for d in np.arange(fase, s[-1], passo):
        i = np.searchsorted(s, d); i = min(i, len(t) - 1)
        nx, ny = math.cos(t[i]) / a, math.sin(t[i]) / b; n = math.hypot(nx, ny)
        out.append((x[i], y[i], nx / n, ny / n))
    return out

def zona_livre(x, y):
    if abs(x) < 46 and y < -60: return False          # dentro/junto do berco
    if abs(x) < 52 and y > 50: return False           # atras do laco
    return True

def luz_led(misto=False):
    ea, eb = P['ELIPSE_A'], P['ELIPSE_B']; w = P['ANEL_LED']
    jan_e, fur_e = [], []
    cc = P['PAREDE_EXT'] + (w - P['PAREDE_EXT'] - P['PAREDE_CAMARA']) / 2   # centro da camara
    for k, (x, y, nx, ny) in enumerate(pontos_anel(ea - cc, eb - cc, PASSO_ESTRELA)):
        if not zona_livre(x, y): continue
        R = 2.0 if k % 2 == 0 else 1.5
        st = estrela4(x, y, R, R * 0.36, 0 if k % 2 == 0 else 45)
        modo = ('janela' if y > 0 else 'furo') if misto else MODO_ESTRELA
        (jan_e if modo == 'janela' else fur_e).append(st)
    jb = []
    for (x, y, nx, ny) in pontos_anel(ea - 0.6, eb - 0.6, PASSO_JANELA_BORDA, PASSO_JANELA_BORDA / 2):
        if not zona_livre(x, y) or y < -68: continue
        tx, ty = -ny, nx; L, Wd = 3.2, 2.4
        cx, cy = x - nx * 0.6, y - ny * 0.6
        q = [(cx + tx * Wd / 2 * sx + nx * L / 2 * sy, cy + ty * Wd / 2 * sx + ny * L / 2 * sy) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        ar = sum(q[i][0] * q[(i + 1) % 4][1] - q[(i + 1) % 4][0] * q[i][1] for i in range(4))
        jb.append(CrossSection([q if ar > 0 else q[::-1]]))
    f = lambda L: CrossSection.batch_boolean(L, OpType.Add) if L else None
    return f(jan_e), f(fur_e), f(jb)

def metade(led, frente, misto=False):
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
        est_j, est_f, jan = luz_led(misto)
        if est_j is not None: m = m - ext(est_j, t - PELE_LED - 0.05, t - PELE_JANELA)
        if est_f is not None: m = m - ext(est_f, -1, t + 1)
        if jan is not None and not jan.is_empty(): m = m - ext(jan, -1, 1.2)
        # nervura (frente) x canaleta (verso) na parede externa: alinha as metades e veda a luz na emenda
        nerv = (elipse(ea, eb).offset(-0.65) - elipse(ea, eb).offset(-1.15)) - rect(-46, -120, 46, -60) - rect(-12, 80, 12, 120)
        can = (elipse(ea, eb).offset(-0.5) - elipse(ea, eb).offset(-1.3)) - rect(-46, -120, 46, -60) - rect(-12, 80, 12, 120)
        if jan is not None and not jan.is_empty():
            nerv = nerv - jan.offset(0.3); can = can - jan
        if frente: m = m + ext(nerv, -0.8, 0.01)
        else: m = m - ext(can, -1, 1.0)
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
pts = np.vstack([np.array(p) for p in (F2 ^ rect(-31.5, -130, 31.5, -60)).to_polygons()])
S_TOPO = float(pts[:, 1].max())
Y_PISO = S_TOPO + 1.2
Y_TOPO = Y_PISO + ALT_ASSENTO

def r_copo(z):
    return float(np.interp(z, COPO['z'], COPO['r_max']))

def assento(topo):
    """Cone que copia a base do copo (+ folga), do piso ate o topo do disco. Coords locais (u,v,w)."""
    piso = topo - ALT_ASSENTO
    ch = 0.6
    prof = [(r_copo(max(zz - CHAPA_COPO, 0)) + FOLGA_ASSENTO, piso + zz)
            for zz in np.arange(0, ALT_ASSENTO - ch + 0.001, 0.25)]
    rt = prof[-1][0]
    prof += [(rt + ch + 1, topo + 1), (0, topo + 1), (0, piso)]   # chanfro passa do topo: evita vertice coincidente
    cone = Manifold.revolve(CrossSection([prof]), 256)
    imas = [Manifold.cylinder(IMA_H + 0.7, IMA_D / 2 + 0.1, IMA_D / 2 + 0.1, 48).translate([u, v, piso - IMA_H - 0.2]) for (u, v) in IMAS_ASSENTO]
    return cone, imas

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
    """LED: gaveta aberta pela borda de TRAS (v>0 = verso do arco). A caixa entra deitada (tampa da pilha
    para baixo), com a lateral da chave virada para fora, rente a borda. Tunel do fio nas DUAS pontas,
    entao a caixa pode entrar virada para qualquer lado (a chave sempre fica para fora)."""
    cl, cw, chh = CAIXA_PILHA
    folga = 0.2; piso_g = 1.2; folga_ponta = 2.5      # espaco na ponta para o fio dobrar
    if led:
        y_b = Y_PISO - 1.0 - (chh + 2 * folga) - piso_g
    else:
        y_b = -102.0
    h = Y_TOPO - y_b
    d = disco_base(y_b, Y_TOPO)
    d = d - fenda_local(y_b)
    cone, imas_a = assento(h)
    d = d - cone
    for k in imas_a: d = d - k
    imas = [(0, -24), (0, 24)] if not led else [(0, -24), (28, 18), (-28, 18)]
    for (u, v) in imas: d = d - ima(u, v)
    extra = {}
    if led:
        L = cl + 2 * folga + 2 * folga_ponta
        r_canto = math.sqrt((R_BERCO - 2.0) ** 2 - (cl / 2) ** 2)    # borda (com chanfro de sombra) no canto da caixa
        v_tras = r_canto + 0.3                                        # lateral da chave rente a borda
        v_frente = v_tras - cw - 2 * folga
        gaveta = Manifold.cube([L, R_BERCO + 5 - v_frente, chh + 2 * folga]).translate([-L / 2, v_frente, piso_g])
        d = d - gaveta
        # ressalto de retencao no piso, perto da abertura (a caixa passa com um clique)
        d = d + Manifold.cube([cl * 0.6, 0.8, 0.35]).translate([-cl * 0.3, v_tras + 0.4, piso_g - 0.01])
        # tuneis do fio: da fenda ate as duas pontas da gaveta
        for sx in (-1, 1):
            u0 = sx * (L / 2 - folga_ponta / 2)
            tunel = Manifold.cube([4.0, v_frente - 2.0 + 2.5, 3.0]).translate([u0 - 2.0, 2.0, piso_g])
            d = d - tunel
            # da fenda (onde o fio sai da sola, x ~ -30) ate o tunel, pelo vao aberto da fenda
        canal = Manifold.cube([30.5 - L / 2 + 4, 4.0, 3.0]).translate([-30.5 - 1, 1.0, piso_g])
        d = d - canal
        extra.update(caixa_pilha=CAIXA_PILHA, gaveta='aberta por tras, chave para fora')
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
pino = Manifold.cylinder(2.0, 3.0, 3.0, 48) + Manifold.cylinder(2.0 + 8.0, D_PINO / 2, D_PINO / 2, 32)
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
h = ALT_ASSENTO + 1.2 + ((IMA_H + 0.6) if IMAS_ASSENTO else 0.4)
anel = Manifold.cylinder(h, 37.0, 37.0, 256)
cone, imas_a = assento(h)
anel = anel - cone
for k in imas_a: anel = anel - k
save(anel, 'TESTE_ASSENTO_COPO', dict(obs='copo 80.9x80.9x80; folga %.2f' % FOLGA_ASSENTO))
# segmento real do anel LED (lado esquerdo): estrelas-janela em cima (y>0), estrelas vazadas embaixo
caixa = Manifold.cube([30, 92, 20]).translate([-121, -46, -10])
for frente in (True, False):
    asm, _, _ = metade(True, frente, misto=True)
    ea, eb = P['ELIPSE_A'], P['ELIPSE_B']
    so_anel = Manifold.extrude(elipse(ea, eb).offset(0.5) - elipse(ea, eb).offset(-P['ANEL_LED'] - 0.5), 20).translate([0, 0, -10])
    seg = asm ^ caixa ^ so_anel          # so o anel (sem pedacos soltos das palmeiras)
    save(para_impressao(seg, True, frente), f'TESTE_LUZ_SEGMENTO_{"FRENTE" if frente else "VERSO"}',
         dict(obs='metade de cima: estrela-janela (pele 0.4) / metade de baixo: estrela vazada'))

# ---------------- verificacoes de montagem ----------------
zs = np.array(COPO['z']); rs = np.array([r if r else 0 for r in COPO['r_max']])
yb_copo = Y_PISO + CHAPA_COPO
pts = [(r, yb_copo + z) for z, r in zip(zs, rs)] + [(-r, yb_copo + z) for z, r in zip(zs[::-1], rs[::-1])]
sil = CrossSection([pts]).offset(1.0)
chk = {}
for led in (False, True):
    inter = (ARTE[led] ^ sil) - rect(-60, -130, 60, Y_PISO + ALT_ASSENTO)
    chk['colisao_copo_arco_' + ('LED' if led else 'SEM_LED') + '_mm2'] = round(inter.area(), 3)
chk['y_piso_copo'] = round(yb_copo, 2); chk['y_topo_copo'] = round(yb_copo + zs[-1], 2)
chk['y_topo_berco'] = round(Y_TOPO, 2); chk['topo_da_fenda'] = round(S_TOPO, 2)
# arco dentro da fenda: interferencia 3D
for led in (False, True):
    d, y_b = BERCO[led]
    d_asm = d.translate([0, 0, y_b]).rotate([-90, 0, 0])  # local -> montagem
    for frente in (True, False):
        v = (ASM[(led, frente)] ^ d_asm).volume()
        chk[f'interf_berco_{"LED" if led else "SEM_LED"}_{"F" if frente else "V"}_mm3'] = round(v, 3)
for led in (False, True):
    chk['interf_entre_metades_' + ('LED' if led else 'SEM_LED') + '_mm3'] = round((ASM[(led, True)] ^ ASM[(led, False)]).volume(), 3)
json.dump(dict(pecas=REL, verificacoes=chk), open(os.path.join(OUT, 'relatorio.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(chk, indent=1))
