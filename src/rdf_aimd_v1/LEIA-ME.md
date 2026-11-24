# RDFs de AIMD — AlCl3:ureia (rdf-aimd-v1)

Dados inéditos: não compartilhe fora do projeto.

## O que é
Funções de distribuição radial parciais g(r) e número de coordenação acumulado n(r) de
10 pares atômicos, calculados na produção (5 ps, 1001 frames, passos 0–10000) de 20
trajetórias AIMD (CP2K, PBE-D3(BJ)/DZVP-MOLOPT-SR-GTH). O equilíbrio (1 ps) fica de fora.
Elas são a referência para testar o modelo MACE: as RDFs da MLMD serão calculadas com o
mesmo script (`rdf.py`) e comparadas com estas.

Trajetórias incluídas: T333 r10_ion, r10_mist, r13_ionA, r13_mist; T400 todas as 15;
T450 r13_reag. As outras 10 (rodadas no SDumont) entram depois, com o mesmo script.

## Arquivos
Um CSV por trajetória: `<sistema>.T<T>.aimd.rdf.csv`, por exemplo
`r15_ionA.T400.aimd.rdf.csv`. As da MLMD terão o nome `<sistema>.T<T>.mlmd-<modelo>.rdf.csv`.

Colunas:
- `r_center_A`: centro do bin (Å); bins de 0,02 Å até 9,70 Å.
- `r_upper_A`: borda superior do bin (Å); é onde `cn_` é avaliado.
- Para cada par (Al-Cl, Al-O, Al-N, Al-Al, Cl-Cl, Cl-H, O-H, C-O, C-N, N-H):
  - `g_<par>`: g(r), adimensional, incluindo pares intra e intermoleculares;
  - `se_<par>`: erro padrão de g(r), de 5 blocos de ~1 ps;
  - `cn_<par>`: número médio de átomos do 2º elemento por átomo do 1º até `r_upper_A`.

O `.json` de cada CSV traz os parâmetros, o tamanho da caixa, o número de átomos, os frames
usados e o sha256 dos arquivos de trajetória de origem.

## Como calcular as RDFs da MLMD do mesmo jeito
```bash
python rdf.py xyz traj.xyz --box <L em Å> --name <sistema>.T<T>.mlmd-<modelo> -o <pasta>
```
O script precisa de numpy e tem que estar commitado, sem alterações, num repo git (o seu
serve): ele recusa rodar com mudanças não commitadas e grava o commit no `.json`. O xyz
precisa ter os símbolos dos elementos e as coordenadas em Å. Os parâmetros (pares, r
máximo, bin, blocos) são fixos no script: não os mude, senão a comparação deixa de valer.
`python rdf.py selftest` confere a instalação.

Para a comparação valer, a MLMD tem que repetir a corrida AIMD:
- mesmo `init.xyz`, mesma caixa e mesma temperatura;
- passo de 0,5 fs;
- CSVR massivo de 10 fs por 1 ps, depois CSVR global de 100 fs por 5 ps;
- frames a cada 5 fs, os 1001 da produção.

Além disso:
- A trajetória testada não pode ter entrado no treino (divisão por trajetória).
- Se você ajustar o modelo olhando estas RDFs, elas viram validação, e o teste precisa de
  outras trajetórias que ficaram de fora.

Como vai ser julgado: para cada par, compara-se a posição e a altura do 1º pico e a
coordenação no 1º mínimo. Uma diferença conta se for maior que 2 × o erro combinado
(AIMD e MLMD).

## Limites
- Cada trajetória guarda a especiação da semente inicial (6 ps não equilibram a
  especiação). As RDFs descrevem cada semente, não o líquido em equilíbrio; não tire média
  entre sementes.
- As trajetórias a 400 e 450 K estão na densidade de 333 K, ou seja, sob pressão elevada.
- Pares com poucos átomos (Al-Al, C-O, C-N, O-H) têm a cauda (r > 8 Å) mais ruidosa; use
  `se_` para o erro.
