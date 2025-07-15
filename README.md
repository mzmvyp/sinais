# Trading Analyzer 🚀

Sistema modular de análise técnica para criptomoedas com detecção de padrões e geração automática de sinais.

## ✨ Características

- **RSI com Detecção de Divergências**: Identifica divergências bullish/bearish automaticamente
- **MACD com Cruzamentos**: Detecta cruzamentos da linha de sinal
- **Sistema Modular**: Facilmente extensível para novos indicadores
- **Análise Paralela**: Processa múltiplos symbols simultaneamente
- **Banco de Dados SQLite**: Armazenamento eficiente de sinais
- **Configuração Flexível**: Parâmetros ajustáveis por arquivo

## 📁 Estrutura do Projeto

```
trading_analyzer/
├── main.py                 # Ponto de entrada principal
├── config/
│   └── settings.py         # Configurações do sistema
├── core/
│   ├── analyzer.py         # Orquestrador principal
│   ├── data_reader.py      # Leitura de dados
│   └── signal_writer.py    # Escrita de sinais
├── indicators/
│   └── technical.py        # Indicadores técnicos (RSI, MACD)
├── requirements.txt        # Dependências
└── README.md              # Este arquivo
```

## 🚀 Instalação

### 1. Pré-requisitos

- Python 3.9+ (testado com 3.13.5)
- Windows 10/11

### 2. Instalar Dependências

```bash
# Criar ambiente virtual (recomendado)
python -m venv trading_env
trading_env\Scripts\activate

# Instalar dependências
pip install pandas numpy sqlalchemy schedule python-dotenv

# Instalar TA-Lib (escolha uma opção):

# Opção A: Pip direto (pode funcionar)
pip install TA-Lib

# Opção B: Se der erro, baixe do site do Christoph Gohlke
# 1. Vá em: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
# 2. Baixe o arquivo .whl para sua versão do Python
# 3. pip install arquivo_baixado.whl

# Opção C: Alternativa mais simples
pip install pandas-ta
```

### 3. Configurar Caminhos

Edite o arquivo `config/settings.py` e ajuste os caminhos dos bancos:

```python
@dataclass
class DatabaseConfig:
    stream_db_path: str = r"SEU_CAMINHO\crypto_stream.db"
    signals_db_path: str = r"SEU_CAMINHO\trading_analyzer_v2.db"
```

## 🎯 Uso

### Comandos Básicos

```bash
# Ver status do sistema
python main.py --status

# Analisar um symbol específico
python main.py --analyze BTCUSDT

# Analisar todos os symbols configurados
python main.py --analyze-all

# Análise contínua (executa em loop)
python main.py --continuous

# Análise contínua com intervalo personalizado (5 minutos)
python main.py --continuous --interval 300
```

### Comandos Avançados

```bash
# Analisar symbols específicos
python main.py --analyze-all --symbols BTCUSDT ETHUSDT BNBUSDT

# Usar timeframe diferente
python main.py --analyze BTCUSDT --timeframe 15m

# Saída em JSON
python main.py --analyze BTCUSDT --output json

# Modo silencioso (apenas erros)
python main.py --analyze-all --quiet

# Limpar sinais antigos (7 dias)
python main.py --cleanup 7
```

## ⚙️ Configuração

### Principais Configurações

```python
# config/settings.py

# Symbols para análise
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"]

# RSI
rsi_period = 14
rsi_overbought = 70
rsi_oversold = 30

# MACD
macd_fast = 12
macd_slow = 26
macd_signal = 9

# Sistema
analysis_interval = 300  # 5 minutos
confidence_threshold = 0.6
parallel_analysis = True
```

### Ajustar Lista de Symbols

```python
# Em config/settings.py, modifique:
symbols: List[str] = ["BTCUSDT", "ETHUSDT", "SEUS_SYMBOLS_AQUI"]
```

## 📊 Sinais Gerados

O sistema gera sinais baseados em:

### RSI
- **Sobrecompra/Sobrevenda**: RSI > 70 (SELL) ou RSI < 30 (BUY)
- **Divergência Bullish**: Preço faz vale mais baixo, RSI faz vale mais alto → BUY
- **Divergência Bearish**: Preço faz pico mais alto, RSI faz pico mais baixo → SELL

### MACD
- **Cruzamento Bullish**: MACD cruza acima da linha de sinal → BUY
- **Cruzamento Bearish**: MACD cruza abaixo da linha de sinal → SELL

## 🗄️ Estrutura dos Sinais

Os sinais são salvos na tabela `traiding_signals_v2` com:

```sql
- symbol (TEXT): Symbol da crypto
- signal_type (TEXT): 'BUY', 'SELL', 'NEUTRAL'
- strategy (TEXT): Nome da estratégia (ex: 'RSI_bullish_divergence')
- confidence (REAL): Confiança do sinal (0.0 a 1.0)
- strength (REAL): Força do sinal (0.0 a 1.0)
- entry_price (REAL): Preço de entrada sugerido
- timestamp (DATETIME): Momento do sinal
- indicators_used (TEXT): JSON com dados dos indicadores
```

## 🔧 Extensibilidade

### Adicionar Novo Indicador

1. **Criar nova classe em `indicators/technical.py`:**

```python
class NovoIndicadorAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze(self, market_data: MarketData) -> IndicatorResult:
        # Sua lógica aqui
        pass
```

2. **Integrar no `TechnicalAnalyzer`:**

```python
def __init__(self):
    self.novo_indicador = NovoIndicadorAnalyzer()

def analyze_all(self, market_data: MarketData):
    results['NovoIndicador'] = self.novo_indicador.analyze(market_data)
```

### Adicionar Padrões Gráficos

Crie `indicators/patterns.py` para detectar:
- Cup & Handle
- Head & Shoulders
- Double Top/Bottom
- Triangles, Flags, etc.

## 📝 Logs

O sistema gera logs em:
- **Console**: Informações em tempo real
- **Arquivo**: `trading_analyzer.log`

Níveis de log: DEBUG, INFO, WARNING, ERROR

## 🚨 Troubleshooting

### TA-Lib não instala
```bash
# Use pandas-ta como alternativa
pip install pandas-ta

# Em indicators/technical.py, substitua:
import talib
# por:
import pandas_ta as ta
```

### Banco não encontrado
- Verifique os caminhos em `config/settings.py`
- Certifique-se de que os arquivos `.db` existem

### Poucos dados
- O sistema precisa de pelo menos 100 pontos de dados
- Verifique se há dados suficientes no banco de stream

### Erro de permissão
- Execute como administrador
- Verifique permissões das pastas

## 🎯 Próximos Passos

- [ ] Adicionar Bollinger Bands
- [ ] Implementar padrões gráficos (Cup & Handle, Head & Shoulders)
- [ ] Adicionar análise de volume
- [ ] Criar estratégias de scalping
- [ ] Interface web para monitoramento
- [ ] Backtesting automatizado

## 📄 Licença

Este projeto é para uso pessoal e educacional.

---

**⚠️ Aviso**: Este sistema é para fins educacionais. Sempre faça sua própria análise antes de tomar decisões de investimento.