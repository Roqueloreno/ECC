"""Monta projetos .3mf do Bambu Studio (uma placa por etapa) a partir dos STLs de stl/.
Usa o project_settings.config do 3MF original como base (P1S, PLA marfim + PLA dourado)
e aplica o perfil recomendado no GUIA.md.
Uso: python3 montar_3mf.py <pasta_extraida_do_3mf_original> <pasta_stl> <pasta_saida>"""
import sys, os, json, uuid, zipfile, io
import numpy as np, trimesh

ORIG, STL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
BED, PITCH = 256.0, 256.0 * 1.2      # Bambu dispoe as placas em grade de 3 colunas

PERFIL = {
    'layer_height': '0.2', 'initial_layer_print_height': '0.2',
    'wall_loops': '3', 'top_shell_layers': '4', 'top_shell_thickness': '0.8',
    'bottom_shell_layers': '5', 'bottom_shell_thickness': '0',
    'sparse_infill_density': '15%', 'sparse_infill_pattern': 'gyroid',
    'outer_wall_speed': '120', 'inner_wall_speed': '200', 'sparse_infill_speed': '300',
    'internal_solid_infill_speed': '200', 'top_surface_speed': '150',
    'top_surface_pattern': 'monotonicline', 'elefant_foot_compensation': '0.15',
    'enable_support': '0', 'ironing_type': 'no ironing',
    'print_settings_id': 'Presepio v2 P1S 0.20',
}

# (arquivo STL, nome no Bambu, filamento 1=marfim 2=dourado, x, y, rotacao_z)
PLACAS = {
    'SEM_LED': [
        ('01 TESTES - assento do copo + segmento de luz (imprima antes)', [
            ('TESTE_ASSENTO_COPO', 'TESTE_ASSENTO_COPO', 1, 70, 128, 0),
            ('TESTE_LUZ_SEGMENTO_FRENTE', 'TESTE_LUZ_FRENTE', 1, 160, 128, 0),
            ('TESTE_LUZ_SEGMENTO_VERSO', 'TESTE_LUZ_VERSO', 1, 205, 128, 0)]),
        ('02 ARCO FRENTE - marfim', [('SEM_LED_01_ARCO_FRENTE', 'ARCO_FRENTE', 1, 128, 128, 0)]),
        ('03 ARCO VERSO - marfim', [('SEM_LED_01_ARCO_VERSO', 'ARCO_VERSO', 1, 128, 128, 0)]),
        ('04 BERCO + LACOS + NOS + PINOS - marfim', [
            ('SEM_LED_02_BERCO_COPO', 'BERCO_COPO', 1, 60, 190, 0),
            ('COMUM_LACO_FRENTE_original', 'LACO_FRENTE', 1, 170, 200, 0),
            ('COMUM_LACO_VERSO_original', 'LACO_VERSO', 1, 170, 130, 0),
            ('COMUM_NO_LACO_original_imprimir_2x', 'NO_LACO_1', 1, 30, 60, 0),
            ('COMUM_NO_LACO_original_imprimir_2x', 'NO_LACO_2', 1, 52, 60, 0),
            ('COMUM_PINO_LACO', 'PINO_LACO_1', 1, 80, 60, 0),
            ('COMUM_PINO_LACO', 'PINO_LACO_2', 1, 92, 60, 0),
            ('COMUM_PINO_LACO', 'PINO_LACO_reserva', 1, 104, 60, 0)]),
        ('05 DOURADO - argola e estrela', [
            ('COMUM_ARGOLA_DOURADA_v2', 'ARGOLA_DOURADA', 2, 98, 128, 0),
            ('COMUM_ESTRELA_FRENTE_original', 'ESTRELA_FRENTE', 2, 130, 128, 0),
            ('COMUM_ESTRELA_VERSO_original', 'ESTRELA_VERSO', 2, 166, 128, 0)]),
        ('06 PLINTO BANCADA (opcional)', [('COMUM_PLINTO_BANCADA_opcional', 'PLINTO_opcional', 1, 128, 128, 0)]),
    ],
}
led = []
for nome, itens in PLACAS['SEM_LED']:
    novos = []
    for (f, n, fil, x, y, r) in itens:
        f = f.replace('SEM_LED_', 'LED_')
        novos.append((f, n, fil, x, y, r))
    if nome.startswith('04'):
        novos = [i for i in novos if i[1] != 'PINO_LACO_2'] + [('LED_04_TAMPA_PILHA', 'TAMPA_PILHA', 1, 75, 100, 0)]
        nome = '04 BERCO LED + TAMPA + LACOS + NOS + PINOS - marfim'
    led.append((nome, novos))
PLACAS['LED'] = led

def cabecalho():
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
            'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
            'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n')

def malha_xml(oid, m):
    v = m.vertices; f = m.faces
    s = io.StringIO()
    s.write(cabecalho())
    s.write(' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n')
    s.write(f'  <object id="{oid}" p:UUID="{uuid.uuid4()}" type="model">\n   <mesh>\n    <vertices>\n')
    for x, y, z in v:
        s.write(f'     <vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>\n')
    s.write('    </vertices>\n    <triangles>\n')
    for a, b, c in f:
        s.write(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n')
    s.write('    </triangles>\n   </mesh>\n  </object>\n </resources>\n <build/>\n</model>\n')
    return s.getvalue()

def montar(versao):
    placas = PLACAS[versao]
    z = zipfile.ZipFile(os.path.join(OUT, f'PRESEPIO_v2_{versao}.3mf'), 'w', zipfile.ZIP_DEFLATED)
    recursos, itens_build, rels, cfg_obj, cfg_placas = [], [], [], [], []
    oid = 1; idx_arquivo = 0; cache = {}; checagem = []
    for p, (nome_placa, itens) in enumerate(placas):
        col, lin = p % 3, p // 3
        ox, oy = col * PITCH, -lin * PITCH
        inst = []
        caixas = []
        for (f, n, fil, x, y, r) in itens:
            m = trimesh.load(os.path.join(STL, f + '.stl'), process=False)
            if r: m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(r), [0, 0, 1]))
            b = m.bounds; c = (b[0] + b[1]) / 2
            m.apply_translation(-c)                      # malha centrada (padrao Bambu)
            h = b[1][2] - b[0][2]
            caixas.append((n, x + m.bounds[0][0], y + m.bounds[0][1], x + m.bounds[1][0], y + m.bounds[1][1]))
            idx_arquivo += 1
            mesh_id, obj_id = oid, oid + 1; oid += 2
            caminho = f'3D/Objects/{n}_{idx_arquivo}.model'
            z.writestr(caminho, malha_xml(mesh_id, m))
            rels.append(caminho)
            recursos.append(f'  <object id="{obj_id}" p:UUID="{uuid.uuid4()}" type="model">\n   <components>\n'
                            f'    <component p:path="/{caminho}" objectid="{mesh_id}" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
                            '   </components>\n  </object>\n')
            itens_build.append(f'  <item objectid="{obj_id}" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 '
                               f'{ox + x:.4f} {oy + y:.4f} {h / 2:.4f}" printable="1"/>\n')
            cfg_obj.append(f'  <object id="{obj_id}">\n    <metadata key="name" value="{n}"/>\n'
                           f'    <metadata key="extruder" value="{fil}"/>\n'
                           f'    <part id="{mesh_id}" subtype="normal_part">\n      <metadata key="name" value="{n}"/>\n'
                           '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                           f'      <metadata key="extruder" value="{fil}"/>\n    </part>\n  </object>\n')
            inst.append(f'    <model_instance>\n      <metadata key="object_id" value="{obj_id}"/>\n'
                        f'      <metadata key="instance_id" value="0"/>\n      <metadata key="identify_id" value="{obj_id * 8}"/>\n    </model_instance>\n')
        # confere: dentro da mesa e sem sobreposicao (margem 3 mm)
        for (n, x0, y0, x1, y1) in caixas:
            if x0 < 1 or y0 < 1 or x1 > BED - 1 or y1 > BED - 1:
                checagem.append(f'{nome_placa}: {n} fora da mesa ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})')
        for i in range(len(caixas)):
            for j in range(i + 1, len(caixas)):
                a, b2 = caixas[i], caixas[j]
                if a[1] < b2[3] + 3 and b2[1] < a[3] + 3 and a[2] < b2[4] + 3 and b2[2] < a[4] + 3:
                    checagem.append(f'{nome_placa}: {a[0]} x {b2[0]} muito proximos')
        cfg_placas.append(f'  <plate>\n    <metadata key="plater_id" value="{p + 1}"/>\n'
                          f'    <metadata key="plater_name" value="{nome_placa}"/>\n    <metadata key="locked" value="false"/>\n'
                          + ''.join(inst) + '  </plate>\n')
    modelo = (cabecalho() + ' <metadata name="Application">BambuStudio-02.06.00.51</metadata>\n'
              ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
              f' <metadata name="Title">Arco Presepio v2 {versao}</metadata>\n <resources>\n'
              + ''.join(recursos) + f' </resources>\n <build p:UUID="{uuid.uuid4()}">\n' + ''.join(itens_build)
              + ' </build>\n</model>\n')
    z.writestr('3D/3dmodel.model', modelo)
    z.writestr('3D/_rels/3dmodel.model.rels',
               '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
               + ''.join(f' <Relationship Target="/{c}" Id="rel-{i + 1}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
                         for i, c in enumerate(rels)) + '</Relationships>')
    z.writestr('Metadata/model_settings.config', '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
               + ''.join(cfg_obj) + ''.join(cfg_placas) + '  <assemble>\n  </assemble>\n</config>\n')
    ps = json.load(open(os.path.join(ORIG, 'Metadata/project_settings.config')))
    for k, v in PERFIL.items():
        if k in ps or k in ('top_shell_thickness', 'bottom_shell_thickness'):
            ps[k] = v
    z.writestr('Metadata/project_settings.config', json.dumps(ps, indent=4, ensure_ascii=False))
    z.writestr('[Content_Types].xml', open(os.path.join(ORIG, '[Content_Types].xml')).read())
    z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
               ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>')
    z.close()
    return checagem

os.makedirs(OUT, exist_ok=True)
for v in ('SEM_LED', 'LED'):
    ch = montar(v)
    print(v, 'OK' if not ch else ch)
