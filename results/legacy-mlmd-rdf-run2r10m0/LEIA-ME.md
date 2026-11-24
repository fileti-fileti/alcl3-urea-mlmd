# MLMD do modelo MACE (run2, rodada 10, membro 0): RDFs para o teste rdf-aimd-v1

Dados e modelo inéditos: não compartilhe fora do projeto. 19/11/2026.

Nada aqui foi julgado: as RDFs foram calculadas e postas ao lado das suas, e o teste é seu
(o critério do seu LEIA-ME: 1º pico e coordenação no 1º mínimo, diferença > 2 × o erro
combinado).

## Conteúdo
- `modelo/alcl3_urea_run2_r10_m0.model`: o modelo MACE que dirigiu as 30 MLMD
  (sha256 `ff0e4578c01cd5ba8d6f08ba35eda9ad27e8d580f50f9085c37222485fd46e3a`).
- `plots/<sistema>.T<T>.png`: 20 figuras, uma por trajetória da sua referência: g(r) dos
  seus 10 pares, AIMD (azul) e MLMD (laranja, tracejado), com faixa de ±2 erros-padrão
  (5 blocos). O título diz se a trajetória ficou fora do treino.
- `rdf/<sistema>.T<T>.mlmd-run2r10m0.rdf.csv` e `.json`: a saída do seu `rdf.py` para as 30
  MLMD, inclusive as 10 que ainda não têm RDF da AIMD.

## O modelo
- MACE-MP-0 small (`2023-12-10-mace-128-L0_energy_epoch-249.model`) com ajuste fino de todos
  os pesos; r_max 6 Å; float64; 135 épocas (a partir da 99ª, peso maior na energia).
- Rótulos: single points CP2K com o seu input de referência (PBE-D3(BJ)/DZVP-MOLOPT-SR-GTH,
  1000 Ry, CP2K 2024.3), energia e forças. Ele reproduz esses single points, não a AIMD de
  350 Ry: nos 390 frames de AIMD rotulados, a energia de 1000 Ry ficou de +0,15 a
  +0,70 meV/átomo acima da de 350 Ry.
- Sem tensor de tensões no treino: use em NVT. NPT não foi treinado nem testado.
- Treino: 1 353 frames rotulados (10% separados para validação). 273 são frames de AIMD das
  27 trajetórias de treino (10 ou 11 por trajetória); 1 080 são frames de MLMD escolhidos em 10 rodadas de aprendizado ativo (metade pelo
  desacordo do comitê, metade por FPS), de MD de Langevin em NVT nas 9 condições
  (333/400/450 K × r10/r13/r15).
- É um comitê de 3 modelos (sementes diferentes); este é o membro 0, o que deu as forças da
  MLMD. Os outros 2 só mediram o desacordo.
- Erro em 60 frames AIMD das 3 trajetórias de teste (média do comitê): energia 0,55 meV/átomo,
  forças 31,7 meV/Å. O membro 0 sozinho tem o mesmo erro de força (31,7 meV/Å).

## Como a MLMD foi rodada (repete cada corrida AIMD, como pede o seu LEIA-ME)
ASE 3.29.0, mace-torch 0.3.16, torch 2.11.0, float64, uma GPU V100 por corrida.
- De cada corrida: o `init.xyz`, a caixa do `ABC` do `prod.inp` e a temperatura dos inputs.
  Os parâmetros foram lidos do `equil.inp` e do `prod.inp` de cada uma (as 30 são iguais).
- Velocidades iniciais de Maxwell-Boltzmann na temperatura, momento total zero; centro de
  massa fixo (3N − 3 graus de liberdade).
- Equilíbrio: 2 000 passos de 0,5 fs (1 ps), CSVR massivo (um termostato por grau de
  liberdade, como o `thermostat_mapping` do CP2K), constante de tempo 10 fs.
- Produção: 10 000 passos de 0,5 fs (5 ps), CSVR global (Bussi), constante de tempo 100 fs;
  um frame a cada 10 passos (5 fs): os 1 001 frames, passos 0–10 000.
- O membro 0 dá as forças; o desacordo do comitê foi registrado em cada frame. A corrida
  pararia se dois átomos ficassem a menos de 0,6 Å: nenhuma das 30 parou, todas têm os
  1 001 frames.
- Semente 1 (um gerador por corrida). Cerca de 0,2 h por corrida (15–17 passos/s).

## Como as RDFs foram calculadas
- O seu `rdf.py`, sem alterações e commitado no nosso repositório, nos 1 001 frames da
  produção, com `--box` = L da corrida e `--name <sistema>.T<T>.mlmd-run2r10m0`.
- Conferência antes das corridas: o `rdf.py` aplicado aos próprios frames da sua AIMD, como se
  fossem MLMD, reproduz o seu CSV exatamente.

## Treino × teste (o seu LEIA-ME pede trajetórias fora do treino)
- Fora do treino: T333 r10_mist, T400 r13_ionB e T450 r15_neut. Nenhum frame delas entrou no
  treino e nenhuma MD de exploração partiu delas. Frames de MLMD nas mesmas condições
  (temperatura e razão) entraram.
- As outras 27 tiveram frames no treino: as RDFs delas não são um teste independente.
- Têm RDF da AIMD e figura: 20, incluindo 2 das 3 de teste (T333 r10_mist, T400 r13_ionB).
  Sem RDF da AIMD ainda: T333 r13_ionB, r15_ionA, r15_ionB, r15_mist; T450 r10_fora,
  r10_neut, r10_reag, r13_neut, r15_neut (a 3ª de teste), r15_reag.
- Nada no modelo foi ajustado olhando estas RDFs.

## Usar o modelo na sua MLMD (ASE)
```bash
pip install mace-torch==0.3.16    # instala torch e ase
```
```python
from ase.io import read
from mace.calculators import MACECalculator

atoms = read("init.xyz")                       # símbolos e coordenadas em Å
atoms.set_cell([L, L, L]); atoms.pbc = True    # L em Å, do ABC do prod.inp
atoms.calc = MACECalculator(model_paths="alcl3_urea_run2_r10_m0.model",
                            device="cuda", default_dtype="float64")   # ou device="cpu"
```
- Unidades: eV, Å, eV/Å. Elementos: Al, C, Cl, H, N, O.
- Os xyz da AIMD não trazem a caixa: sem `set_cell` e `pbc` a energia sai como a de um
  aglomerado no vácuo, sem sentido.
- Conferido assim em dois frames de teste rotulados: os erros batem com a nossa avaliação.
- Velocidade de referência: 15–17 passos/s numa V100 para 400–450 átomos.

## Limites
- Um só modelo (o membro 0) e uma só MLMD por trajetória.
- As corridas a 400 e 450 K estão na densidade de 333 K, como as suas AIMD.
