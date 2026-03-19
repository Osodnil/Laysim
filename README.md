## Warehouse Layout Generator (CD -> DXF)

Este projeto gera automaticamente múltiplos layouts para um CD (centro de distribuição) em uma grade (`grid`) discreta, calcula métricas/score e exporta os melhores cenários para `DXF` (para abrir no AutoCAD).

### Representação do layout (grid)

- Cada célula do grid é um tipo:
  - `EMPTY` (vazio)
  - `RACK` (armazenagem)
  - `CORRIDOR` (corredor / área navegável)
  - `DOCK` (doca de carregamento/descarregamento)

### “Protótipo” que inspirou a versão inicial

O protótipo descrito no enunciado já cobre o pipeline mínimo:

1. **Gerar N layouts diferentes** com regras simples aleatórias (docas, corredores e racks).
2. **Calcular score básico**:
   - distância (ex.: distância Manhattan até docas),
   - capacidade (quantidade de racks).
3. **Ranquear** e **exportar os top K em DXF**.

Essa abordagem é válida para reduzir custo e tempo, porque evita desenhar layouts do zero: você rapidamente cria e compara várias alternativas.

### Limitações conhecidas do protótipo (e o que este projeto faz)

O protótipo inicial:

- usa distância Manhattan (sem obstáculos reais),
- não modela fluxo/congestionamento,
- tem lógica de corredores/docas simples,
- ainda não garante conectividade operacional de forma robusta,
- exporta para DXF com geometria “celular” (mostrando cada célula).

Nas próximas etapas deste projeto, o objetivo é:

- parametrizar tudo (para experimentar cenários),
- melhorar geração (corredores horizontais, docas agrupadas e regras de conectividade),
- refinar score com componentes (distância via caminhos em corredores + capacidade + conectividade),
- adicionar CLI + CSV de resultados,
- preparar um formato de “cenário” para futuras simulações/otimização.

### Como rodar (quando o código estiver pronto)

No modo final, você deve executar um script principal (ex.: `generate_layouts.py`) passando parâmetros via CLI, por exemplo:

```powershell
python .\generate_layouts.py --width 50 --height 30 --n-layouts 30 --top-k 5 --output-dir .\out
```

Depois, abra os `*.dxf` gerados no AutoCAD.

