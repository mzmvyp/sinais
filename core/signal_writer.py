"""
Signal Writer - Escrita de sinais no banco de análise
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import logging

from config.settings import settings

@dataclass
class TradingSignal:
    """Estrutura para um sinal de trading"""
    symbol: str
    signal_type: str        # 'BUY', 'SELL', 'NEUTRAL'
    strategy: str           # Nome da estratégia
    confidence: float       # 0.0 a 1.0
    strength: float         # 0.0 a 1.0
    entry_price: float
    timestamp: datetime = None
    
    # Opcionais
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    target_timeframe: Optional[str] = None
    indicators_used: Optional[Dict] = None
    pattern_data: Optional[Dict] = None
    market_conditions: Optional[Dict] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # Valida tipos de sinal
        valid_signals = ['BUY', 'SELL', 'NEUTRAL']
        if self.signal_type not in valid_signals:
            raise ValueError(f"signal_type deve ser um de: {valid_signals}")
        
        # Valida confidence e strength
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence deve estar entre 0.0 e 1.0")
        
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError("strength deve estar entre 0.0 e 1.0")
    
    @property
    def is_strong_signal(self) -> bool:
        """Verifica se é um sinal forte"""
        return self.confidence >= settings.analysis.confidence_threshold and self.strength >= 0.7
    
    @property
    def signal_quality(self) -> str:
        """Retorna qualidade do sinal"""
        score = (self.confidence + self.strength) / 2
        
        if score >= 0.8:
            return "EXCELLENT"
        elif score >= 0.7:
            return "GOOD"
        elif score >= 0.6:
            return "FAIR"
        else:
            return "WEAK"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para serialização"""
        data = asdict(self)
        
        # Converte datetime para string
        if isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        
        # Converte dicts para JSON strings
        for field in ['indicators_used', 'pattern_data', 'market_conditions']:
            if data[field] is not None:
                data[field] = json.dumps(data[field])
        
        return data

class SignalWriter:
    """Classe para escrita de sinais no banco"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.signals_db_path = settings.database.signals_db_path
        self.signals_table = settings.database.signals_table
        self._ensure_table_exists()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Cria conexão com banco de sinais"""
        try:
            conn = sqlite3.connect(self.signals_db_path)
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao conectar com banco de sinais: {e}")
            raise
    
    def _ensure_table_exists(self):
        """Garante que a tabela de sinais existe"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            
            -- Informações do sinal
            signal_type TEXT NOT NULL,
            strategy TEXT NOT NULL,
            confidence REAL NOT NULL,
            strength REAL NOT NULL,
            
            -- Dados técnicos
            entry_price REAL,
            stop_loss REAL,
            take_profit REAL,
            target_timeframe TEXT,
            
            -- Metadados
            indicators_used TEXT,
            pattern_data TEXT,
            market_conditions TEXT,
            
            -- Campos de sistema
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            notes TEXT,
            
            -- Índice para evitar sinais duplicados
            UNIQUE(symbol, timestamp, strategy)
        )
        """.format(table=self.signals_table)
        
        try:
            with self._get_connection() as conn:
                conn.execute(create_table_sql)
                conn.commit()
                self.logger.info("Tabela de sinais verificada/criada")
        except Exception as e:
            self.logger.error(f"Erro ao criar tabela: {e}")
            raise
    
    def write_signal(self, signal: TradingSignal) -> bool:
        """
        Escreve um sinal no banco
        
        Args:
            signal: Sinal de trading
        
        Returns:
            True se sucesso, False caso contrário
        """
        insert_sql = """
        INSERT OR REPLACE INTO {table} (
            symbol, timestamp, signal_type, strategy, confidence, strength,
            entry_price, stop_loss, take_profit, target_timeframe,
            indicators_used, pattern_data, market_conditions, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """.format(table=self.signals_table)
        
        try:
            signal_dict = signal.to_dict()
            
            values = (
                signal_dict['symbol'],
                signal_dict['timestamp'],
                signal_dict['signal_type'],
                signal_dict['strategy'],
                signal_dict['confidence'],
                signal_dict['strength'],
                signal_dict['entry_price'],
                signal_dict['stop_loss'],
                signal_dict['take_profit'],
                signal_dict['target_timeframe'],
                signal_dict['indicators_used'],
                signal_dict['pattern_data'],
                signal_dict['market_conditions'],
                signal_dict['notes']
            )
            
            with self._get_connection() as conn:
                conn.execute(insert_sql, values)
                conn.commit()
            
            self.logger.info(
                f"Sinal gravado: {signal.symbol} {signal.signal_type} "
                f"{signal.strategy} (conf: {signal.confidence:.2f})"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao gravar sinal: {e}")
            return False
    
    def write_multiple_signals(self, signals: List[TradingSignal]) -> int:
        """
        Escreve múltiplos sinais
        
        Args:
            signals: Lista de sinais
        
        Returns:
            Número de sinais gravados com sucesso
        """
        success_count = 0
        
        for signal in signals:
            if self.write_signal(signal):
                success_count += 1
        
        self.logger.info(f"Gravados {success_count}/{len(signals)} sinais")
        return success_count
    
    def get_active_signals(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        Busca sinais ativos
        
        Args:
            symbol: Symbol específico (opcional)
        
        Returns:
            Lista de sinais ativos
        """
        query = f"""
        SELECT * FROM {self.signals_table}
        WHERE is_active = 1
        """
        
        params = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY timestamp DESC"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                columns = [description[0] for description in cursor.description]
                
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    
                    # Deserializa campos JSON
                    for field in ['indicators_used', 'pattern_data', 'market_conditions']:
                        if row_dict[field]:
                            try:
                                row_dict[field] = json.loads(row_dict[field])
                            except json.JSONDecodeError:
                                row_dict[field] = None
                    
                    results.append(row_dict)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar sinais ativos: {e}")
            return []
    
    def deactivate_signal(self, signal_id: int) -> bool:
        """
        Desativa um sinal
        
        Args:
            signal_id: ID do sinal
        
        Returns:
            True se sucesso
        """
        update_sql = f"""
        UPDATE {self.signals_table}
        SET is_active = 0
        WHERE id = ?
        """
        
        try:
            with self._get_connection() as conn:
                conn.execute(update_sql, (signal_id,))
                conn.commit()
            
            self.logger.info(f"Sinal {signal_id} desativado")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao desativar sinal {signal_id}: {e}")
            return False
    
    def cleanup_old_signals(self, days_old: int = 7) -> int:
        """
        Remove sinais antigos
        
        Args:
            days_old: Sinais mais antigos que X dias
        
        Returns:
            Número de sinais removidos
        """
        delete_sql = f"""
        DELETE FROM {self.signals_table}
        WHERE timestamp < datetime('now', '-{days_old} days')
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(delete_sql)
                removed_count = cursor.rowcount
                conn.commit()
            
            self.logger.info(f"Removidos {removed_count} sinais antigos")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar sinais antigos: {e}")
            return 0
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas dos sinais
        
        Returns:
            Dicionário com estatísticas
        """
        stats_sql = f"""
        SELECT 
            COUNT(*) as total_signals,
            COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_signals,
            COUNT(DISTINCT symbol) as symbols_count,
            COUNT(DISTINCT strategy) as strategies_count,
            AVG(confidence) as avg_confidence,
            AVG(strength) as avg_strength,
            signal_type,
            COUNT(*) as count_by_type
        FROM {self.signals_table}
        GROUP BY signal_type
        """
        
        try:
            with self._get_connection() as conn:
                # Estatísticas gerais
                general_stats = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total_signals,
                        COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_signals,
                        COUNT(DISTINCT symbol) as symbols_count,
                        COUNT(DISTINCT strategy) as strategies_count,
                        AVG(confidence) as avg_confidence,
                        AVG(strength) as avg_strength
                    FROM {self.signals_table}
                """).fetchone()
                
                # Contagem por tipo
                type_stats = conn.execute(f"""
                    SELECT signal_type, COUNT(*) as count
                    FROM {self.signals_table}
                    GROUP BY signal_type
                """).fetchall()
                
                return {
                    'total_signals': general_stats[0] or 0,
                    'active_signals': general_stats[1] or 0,
                    'symbols_count': general_stats[2] or 0,
                    'strategies_count': general_stats[3] or 0,
                    'avg_confidence': round(general_stats[4] or 0, 3),
                    'avg_strength': round(general_stats[5] or 0, 3),
                    'by_type': {row[0]: row[1] for row in type_stats}
                }
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar estatísticas: {e}")
            return {}