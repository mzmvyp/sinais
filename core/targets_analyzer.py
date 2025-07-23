# targets_analyzer.py - ANÁLISE DE QUALIDADE DOS TARGETS TÉCNICOS

"""
Analisador de qualidade dos targets gerados pelo sistema inteligente
Relatórios detalhados sobre métodos, eficácia e distribuição de riscos/recompensas
Complementa o stop_loss_analyzer.py
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict

from config.settings import settings

class TargetsQualityAnalyzer:
    """Analisador de qualidade dos targets inteligentes"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_path = settings.database.signals_db_path
        self.signals_table = settings.database.signals_table
        self.backup_table = settings.database.backup_table
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path, timeout=10)
    
    def get_targets_quality_report(self, days: int = 7) -> Dict:
        """
        📊 Relatório completo da qualidade dos targets técnicos
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with self._get_connection() as conn:
                # Query principal dos sinais ativos
                active_query = f"""
                SELECT 
                    symbol, timeframe, detector_name, signal_type,
                    entry_price, targets, stop_loss, confidence, created_at,
                    targets_analysis, targets_hit, status
                FROM {self.signals_table}
                WHERE datetime(created_at) >= ?
                """
                
                active_df = pd.read_sql_query(active_query, conn, params=(start_date.isoformat(),))
                
                # Query dos sinais no backup
                backup_query = f"""
                SELECT 
                    symbol, timeframe, detector_name, signal_type,
                    entry_price, targets, stop_loss, confidence, created_at,
                    targets_analysis, backup_reason
                FROM {self.backup_table}
                WHERE datetime(backup_timestamp) >= ?
                """
                
                backup_df = pd.read_sql_query(backup_query, conn, params=(start_date.isoformat(),))
            
            # Combina dados para análise completa
            all_signals = self._process_targets_data(active_df, backup_df)
            
            if not all_signals:
                return {
                    'period_days': days,
                    'total_signals_analyzed': 0,
                    'message': 'Nenhum sinal encontrado no período'
                }
            
            # Análises detalhadas
            method_analysis = self._analyze_by_method(all_signals)
            risk_reward_analysis = self._analyze_risk_reward_distribution(all_signals)
            timeframe_analysis = self._analyze_by_timeframe(all_signals)
            performance_analysis = self._analyze_targets_performance(all_signals)
            quality_metrics = self._calculate_quality_metrics(all_signals)
            recommendations = self._generate_recommendations(all_signals)
            
            return {
                'period_days': days,
                'analysis_timestamp': datetime.now().isoformat(),
                'total_signals_analyzed': len(all_signals),
                'method_analysis': method_analysis,
                'risk_reward_analysis': risk_reward_analysis,
                'timeframe_analysis': timeframe_analysis,
                'performance_analysis': performance_analysis,
                'quality_metrics': quality_metrics,
                'recommendations': recommendations,
                'raw_data_sample': all_signals[:10]  # Primeiros 10 para debug
            }
            
        except Exception as e:
            self.logger.error(f"Erro no relatório de qualidade dos targets: {e}")
            return {'error': str(e)}
    
    def _process_targets_data(self, active_df: pd.DataFrame, backup_df: pd.DataFrame) -> List[Dict]:
        """Processa e combina dados dos targets"""
        all_signals = []
        
        # Processa sinais ativos
        for _, row in active_df.iterrows():
            signal_data = self._extract_targets_data(row, 'active')
            if signal_data:
                all_signals.append(signal_data)
        
        # Processa sinais no backup
        for _, row in backup_df.iterrows():
            signal_data = self._extract_targets_data(row, 'backup')
            if signal_data:
                all_signals.append(signal_data)
        
        return all_signals
    
    def _extract_targets_data(self, row, source_type: str) -> Optional[Dict]:
        """Extrai dados estruturados dos targets de um sinal"""
        try:
            # Parse da análise de targets
            targets_analysis = {}
            if pd.notna(row.get('targets_analysis')):
                try:
                    targets_analysis = json.loads(row['targets_analysis'])
                except (json.JSONDecodeError, TypeError):
                    targets_analysis = {}
            
            # Parse dos targets
            targets = []
            if pd.notna(row.get('targets')):
                try:
                    targets = json.loads(row['targets'])
                except (json.JSONDecodeError, TypeError):
                    targets = []
            
            # Parse dos targets atingidos (apenas para sinais ativos)
            targets_hit = []
            if source_type == 'active' and pd.notna(row.get('targets_hit')):
                try:
                    targets_hit = json.loads(row['targets_hit'])
                except (json.JSONDecodeError, TypeError):
                    targets_hit = [False] * len(targets)
            
            # Calcula métricas de risco/recompensa
            entry_price = float(row['entry_price'])
            stop_loss = float(row['stop_loss']) if pd.notna(row.get('stop_loss')) else entry_price * 0.98
            
            # Calcula risk/reward ratios
            risk = abs(entry_price - stop_loss)
            risk_reward_ratios = []
            
            for target in targets:
                if risk > 0:
                    rr_ratio = abs(target - entry_price) / risk
                    risk_reward_ratios.append(rr_ratio)
                else:
                    risk_reward_ratios.append(0)
            
            return {
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'detector_name': row['detector_name'],
                'signal_type': row['signal_type'],
                'entry_price': entry_price,
                'targets': targets,
                'stop_loss': stop_loss,
                'confidence': float(row['confidence']),
                'created_at': row['created_at'],
                'source_type': source_type,
                'backup_reason': row.get('backup_reason', None),
                'status': row.get('status', 'unknown'),
                'targets_hit': targets_hit,
                # Dados da análise de targets
                'targets_method': targets_analysis.get('method_used', 'Unknown'),
                'targets_confidence': targets_analysis.get('confidence', 0),
                'target_levels': targets_analysis.get('target_levels', []),
                'resistance_levels': targets_analysis.get('resistance_levels', []),
                'support_levels': targets_analysis.get('support_levels', []),
                'calculated_risk_reward_ratios': risk_reward_ratios,
                'reported_risk_reward_ratios': targets_analysis.get('risk_reward_ratios', []),
                'analysis_details': targets_analysis.get('analysis_details', {})
            }
            
        except Exception as e:
            self.logger.warning(f"Erro ao processar targets do sinal: {e}")
            return None
    
    def _analyze_by_method(self, signals: List[Dict]) -> Dict:
        """Análise por método de targets"""
        method_stats = defaultdict(lambda: {
            'count': 0,
            'avg_risk_reward': 0,
            'avg_confidence': 0,
            'avg_targets_confidence': 0,
            'risk_reward_distribution': defaultdict(int),
            'targets_hit_rate': {'target_1': 0, 'target_2': 0}
        })
        
        for signal in signals:
            method = signal['targets_method']
            stats = method_stats[method]
            
            stats['count'] += 1
            stats['avg_confidence'] += signal['confidence']
            stats['avg_targets_confidence'] += signal['targets_confidence']
            
            # Calcula média de risk/reward
            if signal['calculated_risk_reward_ratios']:
                avg_rr = sum(signal['calculated_risk_reward_ratios']) / len(signal['calculated_risk_reward_ratios'])
                stats['avg_risk_reward'] += avg_rr
                
                # Distribuição de risk/reward por faixas
                if avg_rr < 1.5:
                    stats['risk_reward_distribution']['<1.5'] += 1
                elif avg_rr < 2.5:
                    stats['risk_reward_distribution']['1.5-2.5'] += 1
                elif avg_rr < 3.5:
                    stats['risk_reward_distribution']['2.5-3.5'] += 1
                elif avg_rr < 5.0:
                    stats['risk_reward_distribution']['3.5-5.0'] += 1
                else:
                    stats['risk_reward_distribution']['>5.0'] += 1
            
            # Taxa de acerto dos targets (apenas para sinais ativos)
            if signal['source_type'] == 'active' and signal['targets_hit']:
                if len(signal['targets_hit']) > 0 and signal['targets_hit'][0]:
                    stats['targets_hit_rate']['target_1'] += 1
                if len(signal['targets_hit']) > 1 and signal['targets_hit'][1]:
                    stats['targets_hit_rate']['target_2'] += 1
        
        # Calcula médias finais
        for method, stats in method_stats.items():
            if stats['count'] > 0:
                stats['avg_risk_reward'] = round(stats['avg_risk_reward'] / stats['count'], 2)
                stats['avg_confidence'] = round(stats['avg_confidence'] / stats['count'], 3)
                stats['avg_targets_confidence'] = round(stats['avg_targets_confidence'] / stats['count'], 3)
                stats['risk_reward_distribution'] = dict(stats['risk_reward_distribution'])
                
                # Calcula taxa de acerto em percentual
                active_count = sum(1 for s in signals if s['targets_method'] == method and s['source_type'] == 'active')
                if active_count > 0:
                    stats['targets_hit_rate']['target_1'] = round(stats['targets_hit_rate']['target_1'] / active_count * 100, 1)
                    stats['targets_hit_rate']['target_2'] = round(stats['targets_hit_rate']['target_2'] / active_count * 100, 1)
        
        return dict(method_stats)
    
    def _analyze_risk_reward_distribution(self, signals: List[Dict]) -> Dict:
        """Análise da distribuição de risk/reward"""
        all_rr_ratios = []
        for signal in signals:
            if signal['calculated_risk_reward_ratios']:
                all_rr_ratios.extend(signal['calculated_risk_reward_ratios'])
        
        if not all_rr_ratios:
            return {}
        
        return {
            'total_targets': len(all_rr_ratios),
            'avg_risk_reward': round(sum(all_rr_ratios) / len(all_rr_ratios), 2),
            'min_risk_reward': round(min(all_rr_ratios), 2),
            'max_risk_reward': round(max(all_rr_ratios), 2),
            'median_risk_reward': round(sorted(all_rr_ratios)[len(all_rr_ratios)//2], 2),
            'risk_reward_ranges': {
                'very_low_rr': len([r for r in all_rr_ratios if r < 1.0]),
                'low_rr': len([r for r in all_rr_ratios if 1.0 <= r < 2.0]),
                'good_rr': len([r for r in all_rr_ratios if 2.0 <= r < 3.0]),
                'excellent_rr': len([r for r in all_rr_ratios if 3.0 <= r < 5.0]),
                'exceptional_rr': len([r for r in all_rr_ratios if r >= 5.0])
            },
            'outliers': {
                'extremely_low': [s for s in signals if any(rr < 0.5 for rr in s['calculated_risk_reward_ratios'])],
                'extremely_high': [s for s in signals if any(rr > 10.0 for rr in s['calculated_risk_reward_ratios'])]
            }
        }
    
    def _analyze_by_timeframe(self, signals: List[Dict]) -> Dict:
        """Análise por timeframe"""
        tf_stats = defaultdict(lambda: {
            'count': 0,
            'avg_risk_reward': 0,
            'methods_used': defaultdict(int),
            'avg_confidence': 0,
            'targets_hit_rate': {'target_1': 0, 'target_2': 0}
        })
        
        for signal in signals:
            tf = signal['timeframe']
            stats = tf_stats[tf]
            
            stats['count'] += 1
            stats['avg_confidence'] += signal['confidence']
            stats['methods_used'][signal['targets_method']] += 1
            
            if signal['calculated_risk_reward_ratios']:
                avg_rr = sum(signal['calculated_risk_reward_ratios']) / len(signal['calculated_risk_reward_ratios'])
                stats['avg_risk_reward'] += avg_rr
            
            # Taxa de acerto dos targets
            if signal['source_type'] == 'active' and signal['targets_hit']:
                if len(signal['targets_hit']) > 0 and signal['targets_hit'][0]:
                    stats['targets_hit_rate']['target_1'] += 1
                if len(signal['targets_hit']) > 1 and signal['targets_hit'][1]:
                    stats['targets_hit_rate']['target_2'] += 1
        
        # Calcula médias e converte
        for tf, stats in tf_stats.items():
            if stats['count'] > 0:
                stats['avg_risk_reward'] = round(stats['avg_risk_reward'] / stats['count'], 2)
                stats['avg_confidence'] = round(stats['avg_confidence'] / stats['count'], 3)
                stats['methods_used'] = dict(stats['methods_used'])
                
                # Taxa de acerto em percentual
                active_count = sum(1 for s in signals if s['timeframe'] == tf and s['source_type'] == 'active')
                if active_count > 0:
                    stats['targets_hit_rate']['target_1'] = round(stats['targets_hit_rate']['target_1'] / active_count * 100, 1)
                    stats['targets_hit_rate']['target_2'] = round(stats['targets_hit_rate']['target_2'] / active_count * 100, 1)
        
        return dict(tf_stats)
    
    def _analyze_targets_performance(self, signals: List[Dict]) -> Dict:
        """Análise de performance dos targets"""
        
        active_signals = [s for s in signals if s['source_type'] == 'active']
        
        if not active_signals:
            return {'message': 'Nenhum sinal ativo para análise de performance'}
        
        total_signals = len(active_signals)
        target_1_hits = sum(1 for s in active_signals if s['targets_hit'] and len(s['targets_hit']) > 0 and s['targets_hit'][0])
        target_2_hits = sum(1 for s in active_signals if s['targets_hit'] and len(s['targets_hit']) > 1 and s['targets_hit'][1])
        
        # Análise por método
        method_performance = defaultdict(lambda: {'total': 0, 'target_1_hits': 0, 'target_2_hits': 0})
        
        for signal in active_signals:
            method = signal['targets_method']
            method_performance[method]['total'] += 1
            
            if signal['targets_hit']:
                if len(signal['targets_hit']) > 0 and signal['targets_hit'][0]:
                    method_performance[method]['target_1_hits'] += 1
                if len(signal['targets_hit']) > 1 and signal['targets_hit'][1]:
                    method_performance[method]['target_2_hits'] += 1
        
        # Calcula taxas de sucesso por método
        for method, stats in method_performance.items():
            if stats['total'] > 0:
                stats['target_1_success_rate'] = round(stats['target_1_hits'] / stats['total'] * 100, 1)
                stats['target_2_success_rate'] = round(stats['target_2_hits'] / stats['total'] * 100, 1)
        
        return {
            'total_active_signals': total_signals,
            'overall_performance': {
                'target_1_hit_rate': round(target_1_hits / total_signals * 100, 1) if total_signals > 0 else 0,
                'target_2_hit_rate': round(target_2_hits / total_signals * 100, 1) if total_signals > 0 else 0,
                'total_target_1_hits': target_1_hits,
                'total_target_2_hits': target_2_hits
            },
            'performance_by_method': dict(method_performance),
            'best_performing_method': max(method_performance.items(), 
                                        key=lambda x: x[1]['target_1_success_rate'])[0] if method_performance else None
        }
    
    def _calculate_quality_metrics(self, signals: List[Dict]) -> Dict:
        """Calcula métricas de qualidade do sistema de targets"""
        
        if not signals:
            return {}
        
        # Métricas básicas
        intelligent_methods = [s for s in signals if 'Resistance_Levels' in s['targets_method'] or 'Support_Levels' in s['targets_method'] or 'Market_Structure' in s['targets_method'] or 'Fibonacci' in s['targets_method']]
        fallback_methods = [s for s in signals if 'Fallback' in s['targets_method'] or 'Emergency' in s['targets_method']]
        
        # Confiança média por categoria
        high_confidence_targets = [s for s in signals if s['targets_confidence'] >= 0.8]
        medium_confidence_targets = [s for s in signals if 0.6 <= s['targets_confidence'] < 0.8]
        low_confidence_targets = [s for s in signals if s['targets_confidence'] < 0.6]
        
        # Consistência do risk/reward
        reported_rr = []
        calculated_rr = []
        
        for signal in signals:
            if signal['reported_risk_reward_ratios'] and signal['calculated_risk_reward_ratios']:
                if len(signal['reported_risk_reward_ratios']) == len(signal['calculated_risk_reward_ratios']):
                    reported_rr.extend(signal['reported_risk_reward_ratios'])
                    calculated_rr.extend(signal['calculated_risk_reward_ratios'])
        
        rr_consistency = 0
        if reported_rr and len(reported_rr) == len(calculated_rr):
            differences = [abs(r - c) for r, c in zip(reported_rr, calculated_rr)]
            rr_consistency = round(1 - (sum(differences) / len(differences) / 5), 3)  # Normaliza para 0-1
        
        return {
            'intelligent_vs_fallback': {
                'intelligent_count': len(intelligent_methods),
                'fallback_count': len(fallback_methods),
                'intelligent_percentage': round(len(intelligent_methods) / len(signals) * 100, 1)
            },
            'confidence_distribution': {
                'high_confidence': len(high_confidence_targets),
                'medium_confidence': len(medium_confidence_targets),
                'low_confidence': len(low_confidence_targets)
            },
            'risk_reward_consistency_score': rr_consistency,
            'method_diversity': len(set(s['targets_method'] for s in signals)),
            'avg_targets_confidence': round(sum(s['targets_confidence'] for s in signals) / len(signals), 3),
            'signals_with_sr_levels': len([s for s in signals if s['resistance_levels'] or s['support_levels']])
        }
    
    def _generate_recommendations(self, signals: List[Dict]) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        if not signals:
            return ["Nenhum dado disponível para gerar recomendações"]
        
        # Análise de métodos fallback
        fallback_count = len([s for s in signals if 'Fallback' in s['targets_method']])
        fallback_pct = fallback_count / len(signals) * 100
        
        if fallback_pct > 30:
            recommendations.append(f"⚠️ {fallback_pct:.1f}% dos targets usam fallback - verificar disponibilidade de dados técnicos")
        elif fallback_pct > 15:
            recommendations.append(f"⚠️ {fallback_pct:.1f}% dos targets usam fallback - considerar melhorar detecção de S/R")
        
        # Análise de risk/reward extremos
        all_rr = []
        for signal in signals:
            if signal['calculated_risk_reward_ratios']:
                all_rr.extend(signal['calculated_risk_reward_ratios'])
        
        if all_rr:
            high_rr = [rr for rr in all_rr if rr > 8.0]
            low_rr = [rr for rr in all_rr if rr < 1.0]
            
            if high_rr:
                recommendations.append(f"🚨 {len(high_rr)} targets com RR >8.0 - revisar validação de distância máxima")
            
            if low_rr:
                recommendations.append(f"📉 {len(low_rr)} targets com RR <1.0 - considerar aumentar limites mínimos")
        
        # Análise de confiança dos targets
        avg_targets_conf = sum(s['targets_confidence'] for s in signals) / len(signals)
        if avg_targets_conf < 0.6:
            recommendations.append(f"📊 Confiança média dos targets baixa ({avg_targets_conf:.2f}) - melhorar algoritmos de detecção")
        
        # Análise de diversidade de métodos
        methods_count = len(set(s['targets_method'] for s in signals))
        if methods_count < 3:
            recommendations.append("🔧 Baixa diversidade de métodos - verificar funcionamento de todos os detectores")
        
        # Análise de performance
        active_signals = [s for s in signals if s['source_type'] == 'active']
        if active_signals:
            target_1_rate = sum(1 for s in active_signals if s['targets_hit'] and len(s['targets_hit']) > 0 and s['targets_hit'][0]) / len(active_signals) * 100
            target_2_rate = sum(1 for s in active_signals if s['targets_hit'] and len(s['targets_hit']) > 1 and s['targets_hit'][1]) / len(active_signals) * 100
            
            if target_1_rate < 30:
                recommendations.append(f"⚠️ Taxa de acerto Target 1 baixa ({target_1_rate:.1f}%) - revisar metodologia")
            elif target_1_rate > 70:
                recommendations.append(f"🎯 Excelente taxa de acerto Target 1 ({target_1_rate:.1f}%)")
            
            if target_2_rate < 15:
                recommendations.append(f"⚠️ Taxa de acerto Target 2 baixa ({target_2_rate:.1f}%) - considerar targets mais conservadores")
        
        if not recommendations:
            recommendations.append("✅ Sistema de targets funcionando dentro dos parâmetros esperados")
        
        return recommendations

def print_targets_quality_report(days: int = 7):
    """
    🖨️ Função utilitária para imprimir relatório formatado
    """
    analyzer = TargetsQualityAnalyzer()
    report = analyzer.get_targets_quality_report(days)
    
    if 'error' in report:
        print(f"❌ Erro: {report['error']}")
        return
    
    print(f"\n🎯 RELATÓRIO DE QUALIDADE DOS TARGETS ({days} dias)")
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
        print(f"  • Targets inteligentes: {quality['intelligent_vs_fallback']['intelligent_percentage']:.1f}%")
        print(f"  • Confiança média dos targets: {quality['avg_targets_confidence']:.3f}")
        print(f"  • Diversidade de métodos: {quality['method_diversity']}")
        print(f"  • Consistência de RR: {quality['risk_reward_consistency_score']:.3f}")
        print(f"  • Sinais com S/R: {quality['signals_with_sr_levels']}")
    
    # Análise de risk/reward
    rr_analysis = report.get('risk_reward_analysis', {})
    if rr_analysis:
        print(f"\n📈 DISTRIBUIÇÃO DE RISK/REWARD:")
        print(f"  • RR médio: {rr_analysis['avg_risk_reward']:.2f}")
        print(f"  • Faixa: {rr_analysis['min_risk_reward']:.2f} - {rr_analysis['max_risk_reward']:.2f}")
        print(f"  • Mediana: {rr_analysis['median_risk_reward']:.2f}")
        
        ranges = rr_analysis.get('risk_reward_ranges', {})
        print(f"  • Muito baixo (<1.0): {ranges.get('very_low_rr', 0)}")
        print(f"  • Baixo (1.0-2.0): {ranges.get('low_rr', 0)}")
        print(f"  • Bom (2.0-3.0): {ranges.get('good_rr', 0)}")
        print(f"  • Excelente (3.0-5.0): {ranges.get('excellent_rr', 0)}")
        print(f"  • Excepcional (>5.0): {ranges.get('exceptional_rr', 0)}")
    
    # Performance dos targets
    performance = report.get('performance_analysis', {})
    if performance and 'overall_performance' in performance:
        overall = performance['overall_performance']
        print(f"\n🎯 PERFORMANCE DOS TARGETS:")
        print(f"  • Taxa Target 1: {overall['target_1_hit_rate']:.1f}% ({overall['total_target_1_hits']} hits)")
        print(f"  • Taxa Target 2: {overall['target_2_hit_rate']:.1f}% ({overall['total_target_2_hits']} hits)")
        
        if performance.get('best_performing_method'):
            print(f"  • Melhor método: {performance['best_performing_method']}")
    
    # Análise por método
    methods = report.get('method_analysis', {})
    if methods:
        print(f"\n🔧 ANÁLISE POR MÉTODO:")
        for method, stats in methods.items():
            print(f"  • {method}:")
            print(f"    - Count: {stats['count']} | RR médio: {stats['avg_risk_reward']:.2f}")
            print(f"    - Conf. Targets: {stats['avg_targets_confidence']:.3f} | Conf. Sinal: {stats['avg_confidence']:.3f}")
            if 'targets_hit_rate' in stats:
                print(f"    - Hit Rate T1: {stats['targets_hit_rate']['target_1']:.1f}% | T2: {stats['targets_hit_rate']['target_2']:.1f}%")
    
    # Recomendações
    recommendations = report.get('recommendations', [])
    if recommendations:
        print(f"\n💡 RECOMENDAÇÕES:")
        for rec in recommendations:
            print(f"  {rec}")

if __name__ == "__main__":
    import sys
    
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print_targets_quality_report(days)