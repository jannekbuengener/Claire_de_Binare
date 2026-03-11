# B3: BSDE-basiertes Risiko-Reward-Modell in Claire de Binare

*Jannek Büngener & ChatGPT*

## 1\. Einführung in BSDE (Backward Stochastic Differential Equations)

Backward Stochastic Differential Equations (BSDE) sind Differentialgleichungen, deren Lösung durch eine Terminalbedingung definiert und dann rückwärts in der Zeit gelöst wird. In der Finanzmathematik findet dieses Framework breite Anwendung – von der Bewertung komplexer Derivate bis zu dynamischen Risikomaßen. Die BSDE-Formulierung kann dabei Unsicherheit und Nichtlinearitäten (etwa Sprünge oder stochastische Volatilität) einbeziehen. Technisch entspricht ein BSDE-System oft dem Hamilton–Jacobi–Bellman (HJB)-Ansatz eines stochastischen Kontrollproblems: Die Lösung einer BSDE liefert Werte- und Gradientenfunktionen, die Optimallösungen repräsentieren. So lassen sich z.B. dynamische Nutzen- oder Risiko-Präferenzen (via *g*\-Erwartungen) implementieren.

Ein BSDE besitzt neben der „vorwärts“ definierten Zustandsgleichung (z.B. Preis-SDE eines Underlyings) einen „rückwärts“ definierten Wertprozess Yt und einen Begleitprozess Zt, der den Gradienten liefert. Formal schreibt sich ein (einfaches) BSDE-System typischerweise als

{dXt=Xt,t dt+Xt,t dWt, −dYt=ft,Xt,Yt,Zt dt−Zt dWt,  YT=gXT. 

Dabei ist Yt z.B. der risikokorrigierte Wert (Expected Reward) des Handels ab Zeit t, gXT die terminale Reward-Funktion (z.B. Profit bei Handelsschluss) und f ein Treiber (Generator), der beispielsweise Risikoaversion oder Kosten modellieren kann. Wichtig ist, dass *Reflektierte BSDE* (RBSDE) eine Barriere einführen können, um Schranken wie Drawdown-Limits sicherzustellen. Das bedeutet: Die Lösung Yt kann so erzwungen werden, stets über einem Mindestvermögen zu bleiben, was ein mathematisches Pendant zu einem dynamischen Drawdown-Stopp darstellt. Insgesamt bieten BSDE damit einen flexiblen, theoretisch fundierten Rahmen, um Risiko-Reward-Optimierung als stochastisches Steuerungsproblem anzugehen.

## 2\. Anwendung auf Trade-Entscheidungen

Ein Handelssignal lässt sich als stochastisches Steuerungsproblem fassen: Wir betrachten die Portfolio- oder Trade-Wertentwicklung Xt (z.B. als SDE für den Kontostand) und definieren am Zeithorizont T eine Belohnung gXT, z.B. den kumulierten Profit. Die BSDE-Kompomenten Yt und Zt modellieren dabei die risikokorrigierte Erwartung des Rewards und dessen Sensitivität. Der BSDE-Treiber f könnte negative Terme enthalten, die z.B. Volatilität, Risklimit-Verstöße oder Liquiditätskosten bestrafen. Auf diese Weise wird jede mögliche Trade-Entscheidung mathematisch bewertet.

Beispielhafter BSDE-Aufbau: Setze als Terminalbedingung YT=PnL einer Trade-Strategie. Definiere ft,Xt,Yt,Zt so, dass hohe Volatilität (z.B. 2 von Preisbewegungen) oder Nähe zum Drawdown-Limit den Rückwärtswert Y sinken lassen. Ein hoher Y0 bedeutet gute Risiko-Ertrags-Erwartung. Die BSDE-Lösung liefert dann Y0 – einen Score für das eingehende Signal – sowie Zt (deren Interpretation als *Stopp-Loss-/Positionsregel* dienen kann).

Wichtig ist hier der Bezug zur stochastischen Kontrolle: BSDEs sind äquivalent zu HJB-Ansätzen. So enthalten offene Quellprojekte wie **deep-bsde-pytorch** u.a. eine *Hamilton-Jacobi-Bellman*\-Gleichung[\[4\]](https://github.com/zhoufy20/deep-bsde-pytorch#:~:text=%2A%20Allen,Example%20PDE%20with%20Oscillating%20Explicit), was zeigt, dass BSDE-Ansätze optimalen Trading-Entscheidungen nahekommen. Tatsächlich lässt sich ein BSDE-Training auch als eine Art Reinforcement-Learning interpretieren: Der Gradient Y der BSDE-Lösung fungiert als *Policy*, und das neuronale Netz lernt, die Abweichung zwischen dem prognostizierten und tatsächlichen End-Reward zu minimieren[\[5\]](https://github.com/zhoufy20/deep-bsde-pytorch#:~:text=Based%20on%20the%20backward%20stochastic,dimensional%20PDEs%20is%20obtained.%5B2). Damit berücksichtigt das Modell globale Optimierung (über den gesamten Zeithorizont) statt statischer Schwellen. Drawdown- oder andere Risikogrundlagen können über *reflektierte* oder beschränkte BSDE-Treiber integriert werden[\[3\]](https://www.nature.com/research-intelligence/nri-topic-summaries/backward-stochastic-differential-equations-and-applications-micro-171623#:~:text=Reflected%20BSDE%20,or%20below%20a%20predetermined%20obstacle).

## 3\. Technische Frameworks und Implementierungen

Für BSDE-Methoden stehen mehrere Open-Source-Bibliotheken zur Verfügung – meist als Erweiterungen von Deep-Learning-Frameworks:


In der Praxis würde man eines dieser Frameworks (oder ein eigenes Modell) trainieren und in den Risk-Manager integrieren. Die Wahl hängt ab von Sprache/Infrastructure (Claire setzt auf Python), Dimension des Problems und Trainingsaufwand.

## 4\. Integration in die Claire-Architektur

def on\_signal(signal):  
    if exceeds\_drawdown():  
        halt\_trading(); return Reject(reason="drawdown")  
    if total\_exposure() \>= MAX\_EXPOSURE\_PCT:  
        return Reject(reason="exposure")  
    size \= min(signal.size, MAX\_POSITION\_SIZE)  
    return Approve(size=size)

Anstelle (oder zusätzlich) der festen If/Else-Regeln könnte der BSDE-Model-Call eingefügt werden. Beispiel-Skizze:

def on\_signal(signal):  
    \# State sammeln: Marktpreise, Signal-Confidence, aktuelles Portfolio-Exposure  
    market\_data \= get\_current\_market\_data(symbol=signal.symbol)  
    state \= get\_portfolio\_snapshot()  \# z.B. aus Postgres/Redis\[11\]  
    \# BSDE-Modell ausführen  
    score \= bsde\_model.evaluate(signal, market\_data, state)  
    \# Entscheidung nach Score  
    if score \>= SCORE\_THRESHOLD:  
        return Approve(size=signal.size)  
    else:  
        return Reject(reason="bsde\_score")

*Inputs:* Der BSDE-Algorithmus benötigt als Eingangsdaten u.a. die aktuellen Marktpreise (aus Redis-Feeds der Signal Engine), die Konfidenz bzw. Stärke des Signals (vom Signal-Engine-Event), und den momentanen Portfolio-Status Exposure, offene Positionen – z.B. über den letzten Portfolio-Snapshot aus Postgres/Redis. Diese Daten stehen im Risk Manager bereits zur Verfügung oder könnten per Redis-Topics/Pipelines eingelesen werden.

*Output:* Der Risk Manager erwartet typischerweise **Approve/Reject** (gegebenenfalls mit angepasster Größe) für ein Signal. Der BSDE-Kern könnte sowohl ein binäres Urteil zurückliefern **oder** einen reellen *Risk-Reward-Score*. In letzterem Fall ließe man einen Schwellenwert entscheiden (wie oben). Wichtig ist nur, dass das Risk-Manager-Interface weiterhin ein klares „Freigegeben oder blockiert“ liefert (idealerweise ergänzt um Gründe/Statistiken für Audit-Logs).

*Einbindungspunkt:* Praktisch würde man den BSDE-Code als Modul (z.B. ein PyTorch-Modell) in den Risk-Manager importieren. Alternativ könnte man den BSDE-Kern auch als separaten Service auslagern (z.B. über gRPC/REST), falls getrennte Skalierung gewünscht ist. Im einfachsten Fall ergänzt man backoffice/services/risk\_manager/service.py um einen Methodenaufruf an das BSDE-Modell. Bereits vorhandene Metriken wie orders\_approved\_total und orders\_blocked\_total.md#L23-L25 würden dann automatisch weiterlaufen (mit ggf. neuem Grund „bsde\_score“).

*Beispielhafte Schnittstellen:* Der Risk-Manager kann das BSDE-Modell wie folgt nutzen: Bei jedem ankommenden signal\_event (inkl. Werten wie symbol, signal\_strength usw.) wird das Modell aufgerufen. Der Rückgabewert steuert das Prometheus-Metrik-Update (wie z.B. risk\_checks\_failed\_total) und entscheidet über order approval. Damit wäre die Entscheidungslogik von festen Limits auf optimierungsbasierte Score-Bewertung umgestellt.

## 5\. Trainingsstrategie / Datenbasis

Für das Training des BSDE-Modells werden umfangreiche Zeitreihen-Daten benötigt. Idealerweise nutzt man historische Marktdaten (Preise, Volumen, Volatilität) und vergangene Handelssignale mitsamt deren Ergebnis (Profit/Loss). Dafür kann Claire-typisch auf Postgres-Tabellen oder Redis-Streams zurückgegriffen werden, die historische Trades und Portfolio-Snapshots enthalten. Beispielsweise könnten vergangene Trades aus einer trades\-Tabelle (oder einem Redis-Stream) geladen und als Label (Profit) für Signale verwendet werden. Zudem sind Marktindikatoren wie historische Volatilitäten oder Spread-Werte nützlich. Wenn diese Werte bereits als Metriken vorliegen, lassen sie sich als Feature verwenden (z.B. durchschnittliche Volatilität aus Redis).

Da reale Daten begrenzt sein können, ist **Pretraining auf simulierten Szenarien** sinnvoll: Man erzeugt synthetische Preis-Pfade (z.B. Geometrische Brownian Motion oder simulierte Orderbuchdaten) und generiert darauf Handelssignale. Anschließend trainiert man das BSDE-Modell in Anlehnung an die Literatur: DeepBSDE-Frameworks bieten dafür „Generator“-Funktionen und Terminalbedingungen an[\[6\]](https://github.com/frankhan91/DeepBSDE#:~:text=Three%20examples%20in%20ref%20). Beispielsweise kann ein vorgegebener Referenz-Controller (z.B. Momentum-Strategie) die Aktionen bestimmen, deren Ergebnisse als Trainingsziel (Terminalbedingung) dienen. Die Modelle lernen dann, den erzeugten Reward möglichst gut vorherzusagen (ähnlich einem RL-Ansatz). Solche Monte-Carlo-Simulationen geben viele Pfade und Szenarien (ruhige Phasen, Sprünge, Volatilitätswechsel) vor, die das Modell robust machen.

Direkt nutzbare Redis-Daten könnten z.B. aus dem „adaptive intensity“-Modul stammen: Dort werden die letzten N Trades und Kennzahlen wie Winrate oder Drawdown berechnet[\[15\]](https://github.com/jannekbuengener/Claire_de_Binare/blob/f0d285fd8b6c26cb937bd269054a5a8ab5da0739/backoffice/docs/services/risk/RISK_LOGIC.md#L98-L101). Diese historischen Performance-Daten könnten Teil der Trainingsfeatures sein. Auch Echtzeit-Funktionsaufrufe (z.B. zur Abrufung von SIGMA\-Metriken) sind denkbar. Insgesamt sollten möglichst vielfältige Marktsituationen in den Trainingsdaten abgebildet werden, damit das Modell das Risiko-Reward-Verhältnis lernen kann.

## 6\. Evaluation und Benchmarking

Das BSDE-Modul muss gegen die bestehende Heuristik getestet werden. Dazu betreibt man das neue Risiko-Modul parallel zur alten Regel-Engine im **Shadow-Mode**: Jede generierte Serie-Trading-Simulation oder Backtest-Episode wird mit beiden Logiken (Fix-Regeln vs. BSDE-Schwellen) durchgespielt und verglichen. Wichtige Kennzahlen (Prometheus-Metriken oder Analytics-Auswertungen) sind dabei insbesondere **Gewinnquote (Winrate)**, **Sharpe-Ratio** (risikoadjustierter Return) und **maximaler Drawdown**. Ergänzend misst man *Profit-Faktor*, *durchschnittliche Haltezeit* und *Anzahl Trades*. Ein direktes Ziel ist, die Trade-Frequenz zu erhöhen, ohne dass Winrate oder Sharpe signifikant abnehmen.

Zur Überwachung könnten vorhandene Grafana-Dashboards angepasst werden: So wie derzeit bereits risk\_alert\_total oder adaptive Risk-Scores verfolgt werden, werden nun neue Metriken wie „bsde\_score\_total“, „bsde\_approved/bsde\_rejected“ oder finale PnL-Werte gemessen. Vergleichsmetriken (alt vs. neu) wie in Kapitel 4 des Backoffice-Dokuments (Order-Approved vs. Blocked) bleiben relevant. Im Endausbau könnte man außerdem spezifische Risiko-Kennzahlen (z.B. Expected Shortfall) online berechnen lassen.

Wichtig ist: Man sollte einen **klare Evaluations-Grundlage** etablieren – etwa indem man historische Paper-Trading-Daten nutzt und dort die Kennzahlen vergleicht. Selbst ein leicht höheres Risiko (Drawdown) kann tolerierbar sein, wenn dafür die Profitabilität deutlich steigt. Die Entscheidungsmatrix aus dem Risk-Logic (Tabelle „Konservativ vs Moderat vs Aggressiv“) kann hier als Richtwert dienen. Insgesamt erwartet man vom BSDE-Modul eine **optimierte Trade-Auswahl**, d.h. bessere risikoadjustierte Kennzahlen als mit fixen Grenzwerten.

## 7\. Implementierungs-Skizze (Pseudocode)

Das folgende Pseudocode-Szenario illustriert, wie das BSDE-Modul im Risk Manager eingebunden werden könnte:

\# Beispiel (Pseudocode) in risk\_manager/service.py

\# Initialisierung: Laden des trainierten BSDE-Modells  
bsde\_model \= load\_model("cdb\_bsde\_model.pt")

def on\_signal(signal: Signal) \-\> Decision:  
    \# 1\. Datenzugriff: aktuelle Marktinfo und Portfolio-State  
    market\_state \= redis\_stream.get\_latest("market\_data", symbol=signal.symbol)  
    portfolio \= get\_portfolio\_state()  \# evtl. aus Redis/DB synchronisiert\[11\]

    \# 2\. BSDE-basiertes Scoring  
    \# (modell intern: Neural Net, das Y0 \= erwarteteter Risiko-Reward berechnet)  
    score \= bsde\_model.predict({  
        "signal\_confidence": signal.confidence,  
        "price": market\_state.price,  
        "volatility": market\_state.v,   
        "position\_exposure": portfolio.exposure,  
        \# weitere Features nach Bedarf  
    })

    \# 3\. Entscheidung: Score vs. Schwelle  
    if score \>= APPROVAL\_THRESHOLD:  
        return Approve(size=compute\_size(signal, portfolio))  
    else:  
        return Reject(reason="bsde\_score")

Dieser vereinfachte Code zeigt das Prinzip: **Inputs** sind Signalstärke, aktuelle Preise/Volas (z.B. aus Redis-Topic), und Portfolio-Exposure (z.B. aus Postgres-Snapshot). **Das BSDE-Modell** (hier als bsde\_model) gibt einen Score zurück. **Output** ist ein Approve/Reject-Entscheid mit optionaler Positionsanpassung. In der realen Implementierung würde man natürlich Logging und Fallback-Regeln ergänzen.



