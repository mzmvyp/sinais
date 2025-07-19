"""
Signal Writer CORRIGIDO - Sem travamentos e com melhor gestão de conexão
"""
import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import logging
from decimal import Decimal, ROUND_HALF_UP

from config.settings import settings

@dataclass
class TradingSignal:
    """Estrutura de sinal compatível com sistema existente"""
    symbol: str
    signal_type: str        # BUY_LONG_analize, SELL_SHORT_analize
    entry_price: float
    confidence: float       # 0.0 a 1.0
    
    # Campos obrigatórios do sistema padrão
    targets: List[float] = None
    stop_loss: float = None
    confluence_score: int = 95  # Padrão 95
    status: str = "ACTIVE"
    indicators_used: List[str] = None
    targets_hit: List[bool] = None
    
    # Campos automáticos
    id: str = None
    timestamp: datetime = None
    
    # Campos opcionais de compatibilidade
    strategy: str = ""
    strength: float = 0.0
    target_timeframe: Optional[str] = None
    pattern_data: Optional[Dict] = None
    market_conditions: Optional[Dict] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # Gera ID no formato padrão: SYMBOL_TYPE_TIMESTAMP
        if self.id is None:
            timestamp_int = int(time.time() * 100)  # Timestamp em centésimos
            self.id = f"{self.symbol}_{self.signal_type}_{timestamp_int}"
        
        # Valida e ajusta signal_type para formato padrão
        self._normalize_signal_type()
        
        # Define targets padrão se não fornecido
        if self.targets is None:
            self.targets = self._calculate_default_targets()
        
        # Define stop_loss padrão se não fornecido
        if self.stop_loss is None:
            self.stop_loss = self._calculate_default_stop_loss()
        
        # Define indicators_used padrão
        if self.indicators_used is None:
            self.indicators_used = [f"technical_analize_{self.signal_type.lower()}"]
        
        # Define targets_hit padrão (todos false inicialmente)
        if self.targets_hit is None:
            self.targets_hit = [False] * len(self.targets)
        
        # Converte confidence (0-1) para confluence_score (0-100) se necessário
        if 0 <= self.confidence <= 1:
            # Mapeia confidence para confluence_score (95-100)
            self.confluence_score = int(95 + (self.confidence * 5))
    
    def _get_decimal_places(self, price: float) -> int:
        """Detecta o número de casas decimais do preço"""
        try:
            # Converte para string e conta decimais
            price_str = f"{price:.10f}".rstrip('0')
            if '.' in price_str:
                return len(price_str.split('.')[1])
            return 0
        except:
            return 2  # Padrão 2 casas decimais
    
    def _round_to_decimal_places(self, value: float, decimal_places: int) -> float:
        """Arredonda valor para o número específico de casas decimais"""
        try:
            if decimal_places <= 0:
                return round(value)
            
            # Usa Decimal para arredondamento preciso
            decimal_value = Decimal(str(value))
            rounded = decimal_value.quantize(
                Decimal('0.' + '0' * decimal_places), 
                rounding=ROUND_HALF_UP
            )
            return float(rounded)
        except:
            return round(value, decimal_places)
    
    def _normalize_signal_type(self):
        """Normaliza signal_type para formato padrão"""
        if self.signal_type in ['BUY', 'buy']:
            self.signal_type = 'BUY_LONG'
        elif self.signal_type in ['SELL', 'sell']:
            self.signal_type = 'SELL_SHORT'
        elif not self.signal_type.endswith('_analize'):
            # Se já está no formato correto mas sem sufixo
            if 'BUY' in self.signal_type.upper():
                self.signal_type = 'BUY_LONG'
            elif 'SELL' in self.signal_type.upper():
                self.signal_type = 'SELL_SHORT'
    
    def _calculate_default_targets(self):
        """Calcula targets padrão mantendo o mesmo número de decimais do entry_price"""
        # Detecta casas decimais do entry_price
        decimal_places = self._get_decimal_places(self.entry_price)
        
        if 'BUY' in self.signal_type:
            # Targets para BUY_LONG: 3 níveis crescentes
            raw_targets = [
                self.entry_price * 1.015,  # +1.5%
                self.entry_price * 1.025,  # +2.5%  
                self.entry_price * 1.04    # +4.0%
            ]
        else:
            # Targets para SELL_SHORT: 3 níveis decrescentes
            raw_targets = [
                self.entry_price * 0.985,  # -1.5%
                self.entry_price * 0.975,  # -2.5%
                self.entry_price * 0.96    # -4.0%
            ]
        
        # Arredonda todos os targets para o mesmo número de decimais
        formatted_targets = [
            self._round_to_decimal_places(target, decimal_places) 
            for target in raw_targets
        ]
        
        return formatted_targets
    
    def _calculate_default_stop_loss(self):
        """Calcula stop_loss padrão mantendo o mesmo número de decimais"""
        decimal_places = self._get_decimal_places(self.entry_price)
        
        if 'BUY' in self.signal_type:
            raw_stop = self.entry_price * 0.97  # -3% para BUY_LONG
        else:
            raw_stop = self.entry_price * 1.03  # +3% para SELL_SHORT
        
        return self._round_to_decimal_places(raw_stop, decimal_places)
    
    def to_database_format(self):
        """Converte para formato do banco de dados"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'entry_price': self.entry_price,
            'targets': json.dumps(self.targets),
            'stop_loss': self.stop_loss,
            'confidence': self.confidence,
            'confluence_score': self.confluence_score,
            'status': self.status,
            'created_at': self.timestamp.isoformat(),
            'entry_time': self.timestamp.isoformat(),
            'exit_time': None,
            'current_price': self.entry_price,  # Inicial = entry_price
            'pnl_percentage': 0.0,
            'pnl_absolute': 0.0,
            'duration_hours': 0.0,
            'targets_hit': json.dumps(self.targets_hit),
            'indicators_used': json.dumps(self.indicators_used),
            'volume_confirmed': 1 if self.confluence_score >= 100 else 0,
            'risk_reward_ratio': self._calculate_risk_reward(),
            'max_profit': 0.0,
            'max_drawdown': 0.0,
            'updated_at': self.timestamp.isoformat()
        }
    
    def _calculate_risk_reward(self):
        """Calcula risk/reward ratio"""
        if not self.targets:
            return 1.0
        
        target_distance = abs(self.targets[0] - self.entry_price)
        stop_distance = abs(self.stop_loss - self.entry_price)
        
        if stop_distance > 0:
            return target_distance / stop_distance
        return 1.0

class SignalWriter:
    """Writer CORRIGIDO para evitar travamentos"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.signals_db_path = settings.database.signals_db_path
        self.signals_table = "trading_signals_v2"
        
        # NOVO: Configurações de timeout
        self.connection_timeout = getattr(settings.database, 'connection_timeout', 30)
        self.query_timeout = getattr(settings.database, 'query_timeout', 10)
        
        # NOVO: Cache para verificação de sinais ativos
        self._active_signals_cache = {}
        self._cache_expiry = {}
        self._cache_timeout = 300  # 5 minutos
        
        self._ensure_table_exists()
        self.logger.info("SignalWriter inicializado com proteção contra travamentos")
        
    def _get_connection(self) -> sqlite3.Connection:
        """Cria conexão com banco de sinais COM TIMEOUT"""
        try:
            conn = sqlite3.connect(
                self.signals_db_path, 
                timeout=self.connection_timeout
            )
            
            # NOVO: Configurações para evitar locks
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=5000")
            conn.execute("PRAGMA temp_store=memory")
            conn.execute("PRAGMA busy_timeout=5000")  # 5 segundos
            
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao conectar com banco de sinais: {e}")
            raise
    
    def _ensure_table_exists(self):
        """Garante que a tabela existe com estrutura correta"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.signals_table}'")
                if cursor.fetchone():
                    self.logger.info(f"Tabela {self.signals_table} verificada")
                else:
                    self.logger.warning(f"Tabela {self.signals_table} não encontrada")
        except Exception as e:
            self.logger.error(f"Erro ao verificar tabela: {e}")
    
    def _is_cache_valid(self, symbol: str) -> bool:
        """Verifica se cache ainda é válido para o symbol"""
        now = time.time()
        return (symbol in self._cache_expiry and 
                self._cache_expiry[symbol] > now)
    
    def _update_cache(self, symbol: str, has_active: bool):
        """Atualiza cache de sinais ativos"""
        self._active_signals_cache[symbol] = has_active
        self._cache_expiry[symbol] = time.time() + self._cache_timeout
    
    def _has_active_signal_for_symbol(self, symbol: str) -> bool:
        """Verifica se symbol já tem sinal ativo - COM CACHE"""
        
        # NOVO: Verifica cache primeiro
        if self._is_cache_valid(symbol):
            return self._active_signals_cache.get(symbol, False)
        
        try:
            query = f"""
            SELECT COUNT(*) FROM {self.signals_table}
            WHERE symbol = ? AND status = 'ACTIVE'
            """
            
            start_time = time.time()
            
            with self._get_connection() as conn:
                cursor = conn.execute(query, (symbol,))
                count = cursor.fetchone()[0]
                has_active = count > 0
                
                # Atualiza cache
                self._update_cache(symbol, has_active)
                
                query_time = time.time() - start_time
                self.logger.debug(f"Verificação de sinal ativo para {symbol}: {has_active} ({query_time:.3f}s)")
                
                return has_active
                
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                self.logger.warning(f"🔒 Banco travado ao verificar {symbol} - assumindo sem sinal ativo")
                return False  # Em caso de lock, permite criar sinal
            raise
        except Exception as e:
            self.logger.error(f"Erro ao verificar sinais ativos para {symbol}: {e}")
            return False  # Em caso de erro, permite criar
    
    def write_signal(self, signal: TradingSignal) -> bool:
        """Escreve sinal no formato padrão - SEM TRAVAMENTOS"""
        
        start_time = time.time()
        
        # Verifica se já existe sinal ativo para este symbol
        if self._has_active_signal_for_symbol(signal.symbol):
            self.logger.info(f"Symbol {signal.symbol} já possui sinal ativo - pulando")
            return False
        
        insert_sql = f"""
        INSERT OR REPLACE INTO {self.signals_table} (
            id, symbol, signal_type, entry_price, targets, stop_loss,
            confidence, confluence_score, status, created_at, entry_time,
            exit_time, current_price, pnl_percentage, pnl_absolute,
            duration_hours, targets_hit, indicators_used, volume_confirmed,
            risk_reward_ratio, max_profit, max_drawdown, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            data = signal.to_database_format()
            
            values = (
                data['id'], data['symbol'], data['signal_type'], data['entry_price'],
                data['targets'], data['stop_loss'], data['confidence'], data['confluence_score'],
                data['status'], data['created_at'], data['entry_time'], data['exit_time'],
                data['current_price'], data['pnl_percentage'], data['pnl_absolute'],
                data['duration_hours'], data['targets_hit'], data['indicators_used'],
                data['volume_confirmed'], data['risk_reward_ratio'], data['max_profit'],
                data['max_drawdown'], data['updated_at']
            )
            
            with self._get_connection() as conn:
                conn.execute(insert_sql, values)
                conn.commit()
                
                # NOVO: Invalida cache após inserção
                self._update_cache(signal.symbol, True)
            
            write_time = time.time() - start_time
            
            self.logger.info(
                f"✅ Sinal gravado: {signal.symbol} {signal.signal_type} "
                f"(conf: {signal.confluence_score}, entry: {signal.entry_price}, "
                f"ID: {signal.id[:12]}) em {write_time:.3f}s"
            )
            return True
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                self.logger.error(f"🔒 Banco travado ao gravar sinal para {signal.symbol}")
                # Tenta uma vez mais após pequena pausa
                time.sleep(1)
                try:
                    with self._get_connection() as conn:
                        conn.execute(insert_sql, values)
                        conn.commit()
                        self._update_cache(signal.symbol, True)
                    self.logger.info(f"✅ Sinal gravado na segunda tentativa: {signal.symbol}")
                    return True
                except Exception:
                    self.logger.error(f"❌ Falha definitiva ao gravar sinal para {signal.symbol}")
                    return False
            else:
                self.logger.error(f"Erro de operação ao gravar sinal: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao gravar sinal: {e}")
            return False
    
    def write_multiple_signals(self, signals: List[TradingSignal]) -> int:
        """Escreve múltiplos sinais - SEQUENCIAL PARA EVITAR LOCKS"""
        success_count = 0
        
        for signal in signals:
            try:
                if self.write_signal(signal):
                    success_count += 1
                    
                # NOVO: Pequena pausa entre sinais para evitar contenção
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Erro ao gravar sinal {signal.symbol}: {e}")
                continue
        
        self.logger.info(f"📊 Gravados {success_count}/{len(signals)} sinais")
        return success_count
    
    def get_active_signals(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Busca sinais ativos - COM TIMEOUT"""
        query = f"SELECT * FROM {self.signals_table} WHERE status = 'ACTIVE'"
        
        params = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY created_at DESC LIMIT 100"  # NOVO: Limita resultados
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                columns = [description[0] for description in cursor.description]
                
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    
                    # Deserializa campos JSON
                    for field in ['targets', 'targets_hit', 'indicators_used']:
                        if row_dict.get(field):
                            try:
                                row_dict[field] = json.loads(row_dict[field])
                            except json.JSONDecodeError:
                                row_dict[field] = None
                    
                    results.append(row_dict)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar sinais ativos: {e}")
            return []
    
    def cleanup_old_signals(self, days_old: int = 7) -> int:
        """Remove sinais antigos - COM PROTEÇÃO"""
        delete_sql = f"""
        DELETE FROM {self.signals_table}
        WHERE created_at < datetime('now', '-{days_old} days')
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(delete_sql)
                removed_count = cursor.rowcount
                conn.commit()
                
                # NOVO: Limpa cache após limpeza
                self._active_signals_cache.clear()
                self._cache_expiry.clear()
            
            self.logger.info(f"🗑️  Removidos {removed_count} sinais antigos")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar sinais antigos: {e}")
            return 0
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas dos sinais - COM TIMEOUT"""
        try:
            with self._get_connection() as conn:
                # Estatísticas gerais com LIMIT
                general_stats = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total_signals,
                        COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_signals,
                        COUNT(DISTINCT symbol) as symbols_count,
                        AVG(confidence) as avg_confidence,
                        AVG(confluence_score) as avg_confluence
                    FROM {self.signals_table}
                    WHERE created_at >= datetime('now', '-30 days')  -- Só últimos 30 dias
                """).fetchone()
                
                # Contagem por tipo com LIMIT
                type_stats = conn.execute(f"""
                    SELECT signal_type, COUNT(*) as count
                    FROM {self.signals_table}
                    WHERE created_at >= datetime('now', '-30 days')
                    GROUP BY signal_type
                    LIMIT 20
                """).fetchall()
                
                return {
                    'total_signals': general_stats[0] or 0,
                    'active_signals': general_stats[1] or 0,
                    'symbols_count': general_stats[2] or 0,
                    'avg_confidence': round(general_stats[3] or 0, 3),
                    'avg_confluence': round(general_stats[4] or 0, 3),
                    'by_type': {row[0]: row[1] for row in type_stats}
                }
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar estatísticas: {e}")
            return {'error': str(e)}

# Função utilitária para diagnóstico
def diagnose_signal_writer():
    """Diagnóstica problemas do signal writer"""
    print("🔍 DIAGNÓSTICO DO SIGNAL WRITER")
    print("=" * 35)
    
    try:
        writer = SignalWriter()
        
        # Testa conexão
        print("🔗 TESTANDO CONEXÃO:")
        start_time = time.time()
        
        try:
            with writer._get_connection() as conn:
                result = conn.execute("SELECT 1").fetchone()
                conn_time = time.time() - start_time
                print(f"   ✅ Conexão OK ({conn_time:.3f}s)")
        except Exception as e:
            print(f"   ❌ Erro de conexão: {e}")
            return
        
        # Estatísticas
        print("\n📊 ESTATÍSTICAS:")
        stats = writer.get_signal_statistics()
        
        if 'error' not in stats:
            print(f"   Total de sinais: {stats['total_signals']}")
            print(f"   Sinais ativos: {stats['active_signals']}")
            print(f"   Symbols únicos: {stats['symbols_count']}")
            print(f"   Confidence média: {stats['avg_confidence']:.3f}")
        else:
            print(f"   ❌ Erro: {stats['error']}")
        
        # Testa cache
        print("\n💾 TESTANDO CACHE:")
        test_symbol = "BTCUSDT"
        
        # Primeira verificação
        start_time = time.time()
        has_active1 = writer._has_active_signal_for_symbol(test_symbol)
        time1 = time.time() - start_time
        
        # Segunda verificação (deve usar cache)
        start_time = time.time()
        has_active2 = writer._has_active_signal_for_symbol(test_symbol)
        time2 = time.time() - start_time
        
        print(f"   Primeira consulta: {time1:.3f}s")
        print(f"   Segunda consulta: {time2:.3f}s")
        print(f"   Cache funcionando: {'✅' if time2 < time1 * 0.5 else '❌'}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Erro no diagnóstico: {e}")
        return None