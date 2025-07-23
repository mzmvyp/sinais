# stop_loss_analyzer.py - ANÁLISE DE QUALIDADE DOS STOPS

"""
Analisador de qualidade dos stop losses gerados pelo sistema inteligente
Relatórios detalhados sobre métodos, eficácia e distribuição de riscos
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict

from config.settings import settings

class StopLossQualityAnalyzer:
    """Analisador de qualidade dos stop losses inteligentes"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_path = settings.database.signals_db_path
        self.signals_table = settings.database.signals_table
        self.backup_table = settings.database.backup_table
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path, timeout=10)
    
    def get_stop_loss_quality_report(self, days: int = 7) -> Dict:
        """
        📊 Relatório completo da qualidade dos stop losses
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with self._get_connection() as conn:
                # Query principal dos sinais ativos
                active_query = f"""
                SELECT 
                    symbol, timeframe, detector_name, signal_type,
                    entry_price, stop_loss, confidence, created_at,
                    stop_loss_analysis
                FROM {self.signals_table}
                WHERE status = 'ACTIVE' AND datetime(created_at) >= ?
                """
                
                active_df = pd.read_sql_query(active_query, conn, params=(start_date.isoformat(),))
                
                # Query dos sinais no backup (inclui bloqueados)
                backup_query = f"""
                SELECT 
                    symbol, timeframe, detector_name, signal_type,
                    entry_price, stop_loss, confidence, created_at,
                    stop_loss_analysis, backup_reason
                FROM {self.backup_table}
                WHERE datetime(backup_timestamp) >= ?
                """
                
                backup_df = pd.read_sql_query(backup_query, conn, params=(start_date.isoformat(),))
            
            # Combina dados para análise completa
            all_signals = self._process_signal_data(active_df, backup_df)
            
            if not all_signals:
                return {
                    'period_days': days,
                    'total_signals_analyzed': 0,
                    'message': 'Nenhum sinal encontrado no período'
                }
            
            # Análises detalhadas
            method_analysis = self._analyze_by_method(all_signals)
            risk_analysis = self._analyze_risk_distribution(all_signals)
            timeframe_analysis = self._analyze_by_timeframe(all_signals)
            quality_metrics = self._calculate_quality_metrics(all_signals)
            recommendations = self._generate_recommendations(all_signals)
            
            return {
                'period_days': days,
                'analysis_timestamp': datetime.now().isoformat(),
                'total_signals_analyzed': len(all_signals),
                'method_analysis': method_analysis,
                'risk_analysis': risk_analysis,
                'timeframe_analysis': timeframe_analysis,
                'quality_metrics': quality_metrics,
                'recommendations': recommendations,
                'raw_data_sample': all_signals[:10]  # Primeiros 10 para debug
            }
            
        except Exception as e:
            self.logger.error(f"Erro no relatório de qualidade dos stops: {e}")
            return {'error': str(e)}
    
    def _process_signal_data(self, active_df: pd.DataFrame, backup_df: pd.DataFrame) -> List[Dict]:
        """Processa e combina dados dos sinais"""
        all_signals = []
        
        # Processa sinais ativos
        for _, row in active_df.iterrows():
            signal_data = self._extract_signal_data(row, 'active')
            if signal_data:
                all_signals.append(signal_data)
        
        # Processa sinais no backup
        for _, row in backup_df.iterrows():
            signal_data = self._extract_signal_data(row, 'backup')
            if signal_data:
                all_signals.append(signal_data)
        
        return all_signals
    
    def _extract_signal_data(self, row, source_type: str) -> Optional[Dict]:
        """Extrai dados estruturados de um sinal"""
        try:
            # Parse da análise de stop loss
            stop_analysis = {}
            if pd.notna(row.get('stop_loss_analysis')):
                try:
                    stop_analysis = json.loads(row['stop_loss_analysis'])
                except (json.JSONDecodeError, TypeError):
                    stop_analysis = {}
            
            # Calcula risco real
            entry_price = float(row['entry_price'])
            stop_price = float(row['stop_loss'])
            
            if row['signal_type'] == 'BUY_LONG':
                risk_pct = ((entry_price - stop_price) / entry_price) * 100
            else:  # SELL_SHORT
                risk_pct = ((stop_price - entry_price) / entry_price) * 100
            
            return {
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'detector_name': row['detector_name'],
                'signal_type': row['signal_type'],
                'entry_price': entry_price,
                'stop_loss': stop_price,
                'confidence': float(row['confidence']),
                'created_at': row['created_at'],
                'source_type': source_type,
                'backup_reason': row.get('backup_reason', None),
                'calculated_risk_pct': abs(risk_pct),
                # Dados da análise de stop loss
                'stop_method': stop_analysis.get('method_used', 'Unknown'),
                'stop_confidence': stop_analysis.get('confidence', 0),
                'reported_risk_pct': stop_analysis.get('risk_percentage', 0),
                'atr_value': stop_analysis.get('atr_value', 0),
                'nearest_sr': stop_analysis.get('nearest_support_resistance'),
                'analysis_details': stop_analysis.get('analysis_details', {})
            }
            
        except Exception as e:
            self.logger.warning(f"Erro ao processar sinal: {e}")
            return None
    
    def _analyze_by_method(self, signals: List[Dict]) -> Dict:
        """Análise por método de stop loss"""
        method_stats = defaultdict(lambda: {
            'count': 0,
            'avg_risk': 0,
            'avg_confidence': 0,
            'avg_stop_confidence': 0,
            'risk_distribution': defaultdict(int)
        })
        
        for signal in signals:
            method = signal['stop_method']
            stats = method_stats[method]
            
            stats['count'] += 1
            stats['avg_risk'] += signal['calculated_risk_pct']
            stats['avg_confidence'] += signal['confidence']
            stats['avg_stop_confidence'] += signal['stop_confidence']
            
            # Distribuição de risco por faixas
            risk = signal['calculated_risk_pct']
            if risk < 1.0:
                stats['risk_distribution']['<1%'] += 1
            elif risk < 2.0:
                stats['risk_distribution']['1-2%'] += 1
            elif risk < 3.0:
                stats['risk_distribution']['2-3%'] += 1
            elif risk < 4.0:
                stats['risk_distribution']['3-4%'] += 1
            else:
                stats['risk_distribution']['>4%'] += 1
        
        # Calcula médias
        for method, stats in method_stats.items():
            if stats['count'] > 0:
                stats['avg_risk'] = round(stats['avg_risk'] / stats['count'], 2)
                stats['avg_confidence'] = round(stats['avg_confidence'] / stats['count'], 3)
                stats['avg_stop_confidence'] = round(stats['avg_stop_confidence'] / stats['count'], 3)
                stats['risk_distribution'] = dict(stats['risk_distribution'])
        
        return dict(method_stats)
    
    def _analyze_risk_distribution(self, signals: List[Dict]) -> Dict:
        """Análise da distribuição de riscos"""
        risks = [s['calculated_risk_pct'] for s in signals]
        
        if not risks:
            return {}
        
        return {
            'total_signals': len(risks),
            'avg_risk': round(sum(risks) / len(risks), 2),
            'min_risk': round(min(risks), 2),
            'max_risk': round(max(risks), 2),
            'median_risk': round(sorted(risks)[len(risks)//2], 2),
            'risk_ranges': {
                'very_low_risk': len([r for r in risks if r < 1.0]),
                'low_risk': len([r for r in risks if 1.0 <= r < 2.0]),
                'medium_risk': len([r for r in risks if 2.0 <= r < 3.5]),
                'high_risk': len([r for r in risks if 3.5 <= r < 5.0]),
                'very_high_risk': len([r for r in risks if r >= 5.0])
            },
            'outliers': {
                'extremely_low': [s for s in signals if s['calculated_risk_pct'] < 0.5],
                'extremely_high': [s for s in signals if s['calculated_risk_pct'] > 6.0]
            }
        }
    
    def _analyze_by_timeframe(self, signals: List[Dict]) -> Dict:
        """Análise por timeframe"""
        tf_stats = defaultdict(lambda: {
            'count': 0,
            'avg_risk': 0,
            'methods_used': defaultdict(int),
            'avg_confidence': 0
        })
        
        for signal in signals:
            tf = signal['timeframe']
            stats = tf_stats[tf]
            
            stats['count'] += 1
            stats['avg_risk'] += signal['calculated_risk_pct']
            stats['avg_confidence'] += signal['confidence']
            stats['methods_used'][signal['stop_method']] += 1
        
        # Calcula médias e converte
        for tf, stats in tf_stats.items():
            if stats['count'] > 0:
                stats['avg_risk'] = round(stats['avg_risk'] / stats['count'], 2)
                stats['avg_confidence'] = round(stats['avg_confidence'] / stats['count'], 3)
                stats['methods_used'] = dict(stats['methods_used'])
        
        return dict(tf_stats)
    
    def _calculate_quality_metrics(self, signals: List[Dict]) -> Dict:
        """Calcula métricas de qualidade do sistema"""
        
        if not signals:
            return {}
        
        # Métricas básicas
        intelligent_methods = [s for s in signals if 'ATR' in s['stop_method'] or 'Support' in s['stop_method'] or 'Resistance' in s['stop_method'] or 'Swing' in s['stop_method'] or 'Structure' in s['stop_method']]
        fallback_methods = [s for s in signals if 'Fallback' in s['stop_method'] or 'Emergency' in s['stop_method']]
        
        # Confiança média por categoria
        high_confidence_stops = [s for s in signals if s['stop_confidence'] >= 0.8]
        medium_confidence_stops = [s for s in signals if 0.6 <= s['stop_confidence'] < 0.8]
        low_confidence_stops = [s for s in signals if s['stop_confidence'] < 0.6]
        
        # Consistência do risco
        reported_risks = [s['reported_risk_pct'] for s in signals if s['reported_risk_pct'] > 0]
        calculated_risks = [s['calculated_risk_pct'] for s in signals]
        
        risk_consistency = 0
        if reported_risks and len(reported_risks) == len(calculated_risks):
            differences = [abs(r - c) for r, c in zip(reported_risks, calculated_risks)]
            risk_consistency = round(1 - (sum(differences) / len(differences) / 5), 3)  # Normaliza para 0-1
        
        return {
            'intelligent_vs_fallback': {
                'intelligent_count': len(intelligent_methods),
                'fallback_count': len(fallback_methods),
                'intelligent_percentage': round(len(intelligent_methods) / len(signals) * 100, 1)
            },
            'confidence_distribution': {
                'high_confidence': len(high_confidence_stops),
                'medium_confidence': len(medium_confidence_stops),
                'low_confidence': len(low_confidence_stops)
            },
            'risk_consistency_score': risk_consistency,
            'method_diversity': len(set(s['stop_method'] for s in signals)),
            'avg_stop_confidence': round(sum(s['stop_confidence'] for s in signals) / len(signals), 3),
            'signals_with_sr_levels': len([s for s in signals if s['nearest_sr'] is not None])
        }
    
    def _generate_recommendations(self, signals: List[Dict]) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        if not signals:
            return ["Nenhum dado disponível para gerar recomendações"]
        
        # Análise de métodos fallback
        fallback_count = len([s for s in signals if 'Fallback' in s['stop_method']])
        fallback_pct = fallback_count / len(signals) * 100
        
        if fallback_pct > 30:
            recommendations.append(f"⚠️ {fallback_pct:.1f}% dos stops usam fallback - verificar disponibilidade de dados de mercado")
        elif fallback_pct > 15:
            recommendations.append(f"⚠️ {fallback_pct:.1f}% dos stops usam fallback - considerar melhorar dados históricos")
        
        # Análise de riscos extremos
        high_risks = [s for s in signals if s['calculated_risk_pct'] > 5.0]
        if high_risks:
            recommendations.append(f"🚨 {len(high_risks)} sinais com risco >5% - revisar parâmetros de validação")
        
        low_risks = [s for s in signals if s['calculated_risk_pct'] < 0.5]
        if low_risks:
            recommendations.append(f"📉 {len(low_risks)} sinais com risco <0.5% - considerar aumentar limites mínimos")
        
        # Análise de confiança dos stops
        avg_stop_conf = sum(s['stop_confidence'] for s in signals) / len(signals)
        if avg_stop_conf < 0.6:
            recommendations.append(f"📊 Confiança média dos stops baixa ({avg_stop_conf:.2f}) - melhorar algoritmos de detecção")
        
        # Análise de diversidade de métodos
        methods_count = len(set(s['stop_method'] for s in signals))
        if methods_count < 3:
            recommendations.append("🔧 Baixa diversidade de métodos - verificar funcionamento de todos os detectores")
        
        # Análise por timeframe
        tf_risks = defaultdict(list)
        for signal in signals:
            tf_risks[signal['timeframe']].append(signal['calculated_risk_pct'])
        
        for tf, risks in tf_risks.items():
            avg_risk = sum(risks) / len(risks)
            if avg_risk > 4.0:
                recommendations.append(f"⚠️ Timeframe {tf}: risco médio alto ({avg_risk:.1f}%)")
            elif avg_risk < 1.0:
                recommendations.append(f"📉 Timeframe {tf}: risco médio baixo ({avg_risk:.1f}%)")
        
        if not recommendations:
            recommendations.append("✅ Sistema de stop loss funcionando dentro dos parâmetros esperados")
        
        return recommendations

def print_stop_loss_quality_report(days: int = 7):
    """
    🖨️ Função utilitária para imprimir relatório formatado
    """
    analyzer = StopLossQualityAnalyzer()
    report = analyzer.get_stop_loss_quality_report(days)
    
    if 'error' in report:
        print(f"❌ Erro: {report['error']}")
        return
    
    print(f"\n📊 RELATÓRIO DE QUALIDADE DOS STOP LOSSES ({days} dias)")
    print("=" * 80)
    
    if report.get('total_signals_analyzed', 0) == 0:
        print("⚠️ Nenhum sinal encontrado no período")
        return
    
    print(f"Total de sinais analisados: {report['total_signals_analyzed']}")
    print(f"Período: {days} dias | Análise: {report['analysis_timestamp'][:19]}")
    
    # Métricas de qualidade
    quality = report.get('quality_metrics', {})
    if quality:
        print(f"\n🎯 MÉTRICAS DE QUALIDADE:")
        print(f"  • Stops inteligentes: {quality['intelligent_vs_fallback']['intelligent_percentage']:.1f}%")
        print(f"  • Confiança média dos stops: {quality['avg_stop_confidence']:.3f}")
        print(f"  • Diversidade de métodos: {quality['method_diversity']}")
        print(f"  • Consistência de risco: {quality['risk_consistency_score']:.3f}")
        print(f"  • Sinais com S/R: {quality['signals_with_sr_levels']}")
    
    # Análise de risco
    risk = report.get('risk_analysis', {})
    if risk:
        print(f"\n📈 DISTRIBUIÇÃO DE RISCOS:")
        print(f"  • Risco médio: {risk['avg_risk']:.2f}%")
        print(f"  • Faixa: {risk['min_risk']:.2f}% - {risk['max_risk']:.2f}%")
        print(f"  • Mediana: {risk['median_risk']:.2f}%")
        
        ranges = risk.get('risk_ranges', {})
        print(f"  • Muito baixo (<1%): {ranges.get('very_low_risk', 0)}")
        print(f"  • Baixo (1-2%): {ranges.get('low_risk', 0)}")
        print(f"  • Médio (2-3.5%): {ranges.get('medium_risk', 0)}")
        print(f"  • Alto (3.5-5%): {ranges.get('high_risk', 0)}")
        print(f"  • Muito alto (>5%): {ranges.get('very_high_risk', 0)}")
    
    # Análise por método
    methods = report.get('method_analysis', {})
    if methods:
        print(f"\n🔧 ANÁLISE POR MÉTODO:")
        for method, stats in methods.items():
            print(f"  • {method}:")
            print(f"    - Count: {stats['count']} | Risco médio: {stats['avg_risk']:.2f}%")
            print(f"    - Conf. Stop: {stats['avg_stop_confidence']:.3f} | Conf. Sinal: {stats['avg_confidence']:.3f}")
    
    # Recomendações
    recommendations = report.get('recommendations', [])
    if recommendations:
        print(f"\n💡 RECOMENDAÇÕES:")
        for rec in recommendations:
            print(f"  {rec}")

if __name__ == "__main__":
    import sys
    
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print_stop_loss_quality_report(days)