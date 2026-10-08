# Passagem para revisão: Arco Presépio v2

Documento para quem for revisar e dar o acabamento final, seja humano ou agente.
Leia inteiro antes de mudar qualquer coisa: várias decisões vieram de **testes físicos** do cliente e não devem ser desfeitas.

## 1. O produto

- Guirlanda/enfeite de Natal **autoral e premium**. É um arco elíptico (234 × 206 mm) com estábulo, palmeiras e cerca recortados, laço no topo, estrela dourada pendurada e um **copo luminoso** (vela LED) apoiado num **berço** embaixo.
- Funciona **de pé na bancada** (o berço é a base) e **pendurado como guirlanda** (pela argola dourada).
- Duas versões:
  - **SEM LED:** marfim, com filete gravado nas faces.
  - **LED:** **branco**. Um fio anjo de 2 m corre dentro do anel numa câmara, e a luz sai por estrelas vazadas e janelas na borda.
- O copo (vaso "Copo luminoso", 80,9 × 80,9 × 80 mm) é um **produto separado** do cliente. Ele tem licença do arquivo, mas o arquivo **não** está no repositório. Daqui só se usa o perfil medido (`src/copo_perfil.json`).
- **Impressora:** Bambu Lab **P1S sem AMS**. As peças douradas são impressas à parte, com troca de carretel.

## 2. Como regenerar tudo

```bash
pip install manifold3d trimesh numpy networkx scipy rtree
./gerar_tudo.sh          # gera stl/, stl/relatorio.json e 3mf/
```

- `src/arte2d.py`: arte 2D do arco, tirada do arco original (`origem/Objects/01_ARCO_FRENTE_12.model`). Inclui a câmara de luz e as constantes geométricas `P`.
- `src/gerar.py`: **todos os parâmetros ficam no topo**. Gera metades, berços, testes, argola, pino e plinto, e roda as verificações.
- `src/montar_3mf.py`: projetos do Bambu Studio com placas, perfil P1S e filamentos (1 = marfim ou branco, 2 = dourado).
- `origem/`: as partes do 3MF original do cliente que os scripts usam (arco, argola e as configurações do projeto).
- `stl/COMUM_*_original.stl`: laço, nó e estrela **originais, sem alteração** (não são regenerados).

**Coordenadas de montagem:**
- O arco fica no plano XY, com espessura em Z (−3 a +3) e frente = +Z.
- Centro da elipse externa: (0, −5,28); a = 117; b = 100,19.
- O berço é construído em coordenadas locais (u, v, w) = (x, −z, y − y_base), com v > 0 = parte de trás.

## 3. Decisões validadas por teste físico (não reverter)

| Item | Valor | Origem |
|---|---|---|
| Folga de pino/furo | **0,25 mm por lado** | Teste: furo +0,3 no diâmetro não entrou, +0,5 entrou |
| Cavilha | Filamento de 1,75 mm em furo de Ø2,25, 2 mm de profundidade por metade | Idem |
| Cor da versão LED | **Branco** | Teste em azul: a luz não passa |
| Fio anjo | 2 m em **3 passadas** pela câmara de 4,6 × 4,4 mm | Vídeo do cliente: coube e as metades fecharam |
| Assento do copo | Cone de **4,5 mm**, folga de 0,2, copia o perfil real do vaso | Cliente: "a base do copo ficou bom". A arte do vaso começa a ~4,8 mm, **não pode subir** |
| Escala do copo | **Uniforme 1,0572 do arquivo** (80,9 × 80,9 × 80) | O cliente corrigiu: Z é 80, não 90 |
| Caixinha de pilha | 28,55 × 18,50 × 12,35 mm, chave deslizante numa lateral comprida | Medido pelo cliente |
| Ímãs | 3,95 × 1,89 mm (bolso de Ø4,15 × 2,09) | Cliente |

## 4. Decisões de projeto e por quê

- **Duas metades coladas por versão:** o cliente quer detalhe e acabamento nas duas faces.
  - **SEM LED:** vitrine para cima (filete nítido).
  - **LED:** vitrine **na mesa**, com a câmara aberta para cima, sem suporte e com a pele sólida.
- **Chanfros em degraus de 0,2 mm** (= altura de camada). Não use degraus menores: geram vértices quase coincidentes e quebram a malha.
- **Friso em V na emenda:** chanfro de 0,4 na borda de colagem de cada metade esconde a linha de cola.
- **Encaixe das metades LED:** nervura (frente, 0,5 × 0,8) e canaleta (verso, 0,8 × 1,0) na parede externa de 1,8 mm. Alinha e veda a luz.
- **Estrelas** (`MODO_ESTRELA='furo'`): vazadas, 4 pontas, a cada 9 mm, nas duas faces. **Janelas na borda** a cada 18 mm. O cliente pediu luz "piscando e saindo para fora". A alternativa `'janela'` (pele de 0,4 só na estrela) fica disponível.
- **Berço = sela:** desce sobre a base achatada do anel e é colado.
  - A fenda é **varrida verticalmente** para não ter pontes. **Não remova a varredura**: sem ela o berço não monta num anel fechado.
- **Copo preso:**
  - Um aperto num cone de ~27° não segura (o atrito é menor que tan 27°).
  - Por isso: cone para centralizar + **3 pares de ímãs**, a 30°, 150° e 270° num raio de 16 mm.
  - No copo, os ímãs vão **colados por dentro, no piso** (o fundo tem só ~1,3 mm), escondidos sob a vela.
- **Gaveta do berço LED:** aberta pela **borda de trás**. A caixinha entra deitada, com a lateral da chave rente à borda. Há túnel de fio nas duas pontas (a caixinha pode entrar virada) e um ressalto de 0,35 mm de retenção. Não tem tampa.
- **Plinto:** opcional. O berço sozinho já é estável na bancada (tombamento estimado em ~28°).

## 5. Verificações automáticas (devem continuar em 0)

Em `stl/relatorio.json`:
- `colisao_copo_arco_*`
- `interf_berco_*`
- `interf_entre_metades_*`

Além disso:
- Toda peça precisa estar **fechada** depois de `trimesh.merge_vertices()`. O `montar_3mf.py` faz `assert`.
- **Armadilha conhecida:** STL não compartilha vértices. O escritor do 3MF **precisa** de `merge_vertices()`, senão o Bambu acusa "não-manifold" e "primeira camada vazia". Isso já aconteceu uma vez.
- **Armadilha conhecida:** `revolve` com pontos no eixo, ou vértices coincidentes com faces planas, gerou arestas ruins. Veja a solução no chanfro do `assento()`.

## 6. Pendências e riscos

1. **Força dos ímãs:** não foi testada se 3 pares de 4 × 2 mm através de ~1,3 mm seguram o copo num balanço forte de porta. O teste é o `TESTE_ASSENTO_COPO` com os ímãs.
2. **Gaveta do berço LED:** ainda não foi impressa. Conferir:
   - o teto (ponte de ~19 mm);
   - o clique do ressalto;
   - o acesso à chave (a borda é curva, então no meio a caixinha fica ~4 mm para dentro).
3. **Estrela vazada:** apagada, pode deixar o fio aparecer levemente pelo recorte. O cliente ainda não escolheu entre `furo` e `janela`; usei `furo`.
4. **Estábulo iluminado:** é uma ideia em aberto (~1 m a mais de fio). Exige engrossar pilares e telhado para ~6 mm e saber a **largura do LED** do fio, que o cliente ainda não mediu.
5. **Tempos:** os de `GUIA.md` são do PrusaSlicer × 1,07 (calibrado contra o Bambu no arco original). Confirmar no Bambu Studio.
6. **Projetos `.3mf`:** não foram abertos num Bambu Studio real por quem gerou, só validados por XML e geometria. Vale abrir e fatiar todas as placas.

## 7. Sugestões de acabamento (se quiser ir além)

- Abrir os 3 `.3mf` no Bambu Studio e fatiar. Corrigir qualquer aviso.
- Revisar estética e proporção das estrelas e janelas, com render ou foto.
- Gerar miniaturas (`Metadata/plate_N.png`) para os `.3mf` ficarem com prévia no Bambu.
- Separar parâmetros "de produção" e "de teste" no topo de `gerar.py`.
- **Não** mexer na arte do estábulo, nas palmeiras, no laço nem na estrela sem pedir ao cliente: a estética é dele.

## 8. Preferências do cliente

- Português, direto e prático. Explicações passo a passo para o Bambu Studio (ele está aprendendo).
- Estética sofisticada, limpa e autoral. Nada de excesso de dourado ou ornamento.
- Reduzir suporte, tempo e pós-processamento sem perder qualidade.
- Testes pequenos antes da peça grande.
- Ao concluir, sempre informar as configurações de fatiamento.
