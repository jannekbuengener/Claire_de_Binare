# WORKFLOW_Signal_Tuning 

## Ziel
Signal-Parameter-Tuning zur Erhöhung der Handelsfrequenz ohne Verschlechterung der Winrate oder Verletzung von Risikolimits.

## Rollen
- Hauptmodell  
- data-analyst  
- risk-architect  
- test-engineer  

## Phase A – Analyse
1. data-analyst analysiert IST-Konfiguration + Optimierungsmöglichkeiten.
2. risk-architect definiert Risiko- und Frequenzgrenzen.
3. test-engineer plant Backtest-Matrix.
4. Claude erstellt Analyse-Report.

## Phase B – Delivery (User-Freigabe)
1. Branch erstellen.
2. Parameter anpassen (gemäß Analyse-Report und Risiko-Grenzen).
3. Backtests durchführen.
4. Testresultate dokumentieren.
5. PR erstellen.

## Erfolgsindikatoren
- Frequenz ↑  
- Winrate ≥ 50 %  
- Kein Risk-Limit-Verstoß
