Okay, let’s machen: erste „GitHub/GitLab-Session“ mit festem Boden unter den Füßen 😄

Ich mache zwei Dinge für dich:

1. **Einen sauber überarbeiteten Prompt** für Claude Code / „CLAUDE im CDB-Kontext“, den du direkt im Repo verwenden kannst.
2. **Kurz-Anleitung**, wie du den Prompt in Claude Code nutzt, damit ihr euch als Team langsam an Plan Mode & Co gewöhnt.

---

## 1️⃣ Optimierter Prompt für eure GitHub/GitLab-Session

Den folgenden Block kannst du 1:1 in Claude Code verwenden (im CDB-Repo, in **Plan Mode** / Analysemodus, also ohne Dateiänderungen). 

---

**Sprache:** Deutsch

**Rolle & Kontext:**
Du bist **CLAUDE im CDB-Projektkontext**.
Du arbeitest in einer bestehenden Codebasis, die von mehreren Agenten/Menschen genutzt wird.
Deine Aufgabe in DIESER Session:
Eine zu CDB passende **GitHub/GitLab-Organisation** entwerfen, die unsere echte Arbeitsweise, Artefakte und Roadmap widerspiegelt – nicht ein generisches Template.

**Arbeitsmodus / Grenzen:**

* Du befindest dich im **Plan-/Analysemodus** (nur Lesen & Nachdenken).
* **KEINE Dateiänderungen**, **KEINE Bash-Kommandos**, **KEINE API-Calls**.
* Du darfst Repo-Inhalte lesen (Dateien, Ordner, ggf. vorhandene Issues/CI-Dateien), aber nichts verändern.
* Liefere **Vorschläge**, keine endgültigen Entscheidungen. Alles soll leicht änderbar und iterierbar bleiben. 

---

### 0. Kontextaufbau (nur lesen)

Bevor du Vorschläge machst, verschaffe dir ein Bild vom realen Projektzustand.
Prüfe – falls vorhanden – insbesondere:

* `CLAUDE.md` und ggf. weitere `CLAUDE*.md`-Varianten
* `docs/` (z.B. Roadmap, Master-Agenden, Architektur- oder Governance-Dokumente)
* vorhandene `ROADMAP.md`, `MASTER.md`, `AGENDA.md` o.ä.
* `.github/` und `.gitlab/` Verzeichnisse (Workflows, Pipelines, Issue-Templates)
* bestehende Labels, Milestones und Projekt-Boards (sofern aus Dateien oder Doku ableitbar)
* Hinweise auf Agenten-/Rollenstruktur (z.B. `.claude/agents/`, Ordnerstruktur, Doku) 

Wenn dir dafür Informationen fehlen, formuliere klar **Annahmen** und markiere sie als solche.

---

### 1. Projekt-Verständnis (kurz)

Beschreibe in deinen eigenen Worten, auf Basis der gefundenen Artefakte:

1. **Was ist CDB aus deiner Sicht?**

   * Zweck / Vision in 2–4 Sätzen
2. **Wie wird hier grob gearbeitet?**

   * z.B. eher experimentell vs. streng geplant
   * Rolle von Agenten vs. Menschen
3. **Schwerpunkte / Domänen**, die du erkennst

   * z.B. Governance, Agenten/Orchestrierung, Infrastruktur, Markt/Produkt, Doku, etc.

---

### 2. GitHub/GitLab-Zielbild (High-Level)

Formuliere ein Zielbild für GitHub/GitLab als „**Project OS für CDB**“:

* Welche **Aufgaben** soll GitHub/GitLab für CDB konkret übernehmen?
  (z.B. Code-Hub, Issue-Backlog, Entscheidungs-Historie, Experiment-Tracker, Governance, CI/CD)
* Welche **Artefakte** müssen dort gut abbildbar sein?

  * Code & Services
  * Doku (inkl. Master-/Roadmap-Dokumente)
  * Governance-Regeln / Entscheidungs-Logs
  * Workflows (z.B. Sessions, Experimente, Agenten-Runs)
  * Issues / Tickets / Ideen / Experimente

Leite dieses Zielbild **aus dem realen Zustand** ab (Kontrast: „heute vs. Ziel“).

---

### 3. Label-System (projektangepasst)

Entwirf ein **Label-System**, das wirklich zu CDB passt – nicht generisch.

1. **Typ-Labels** (Was für ein Issue ist das?)

   * z.B. `type:feature`, `type:bug`, `type:refactor`,
     `type:research`, `type:governance`, `type:ops`, `type:experiment`
2. **Prioritäten**

   * z.B. `prio:P0` (kritisch), `prio:P1`, `prio:P2`, `prio:P3`
3. **Status-/Meta-Labels (optional)**

   * z.B. `status:blocked`, `status:needs-spec`, `status:needs-review`
4. **Agenten-/Rollen-Labels (optional)**

   * z.B. `agent:infra`, `agent:governance`, `agent:frontend`,
     oder Labels, die zu eurer tatsächlichen Agenten-/Rollenstruktur passen.

**WICHTIG:**

* Begründe bei jeder Label-Gruppe kurz, **warum** sie zu unserer Arbeitsweise und den gefundenen Artefakten passt.
* Wenn du erkennst, dass heute schon Labels existieren:

  * Schlage eine **Mapping-Tabelle** vor: `aktuelles Label → neues System`.

---

### 4. Meilensteine (Roadmap → GitHub/GitLab)

Leite aus der vorhandenen Roadmap / MASTER-Dokumenten sinnvolle **Meilensteine** ab:

Für jeden vorgeschlagenen Meilenstein bitte:

* **Name** (prägnant, nicht nur „P0-P8“)
* **Zielbild in 2–4 Sätzen**
* **Grobe Inhalte** (Stichworte oder Bullet-Points)
* Falls sinnvoll: Hinweis, welche Agenten/Rollen hauptsächlich beitragen

Beispiele für mögliche Schnittarten (nur als Inspiration, bitte an CDB anpassen):

* „CDB Core v1 – stabiler Kern & Basis-Governance“
* „Agenten-Orchestrierung v1 – Agents auf echter Infrastruktur“
* „Product Discovery – erste externe Nutzer*innen & Feedback-Zyklus“
* „CI/CD v1 – Basis-Automatisierung und Qualitäts-Gates“

---

### 5. Boards / Organisation

Schlage **1–3 Projekt-Boards** vor, die zu UNS passen, z.B.:

1. **Delivery-Board (Kanban)**

   * Fokus: operative Arbeit (Code, Bugs, kleine Features)
   * Spalten: z.B. `Backlog` → `Ready` → `In Progress` → `Review` → `Done`
   * Wer arbeitet dort typischerweise?

2. **Roadmap-/Strategie-Board**

   * Fokus: größere Epics / Initiativen / Meilensteine
   * Spalten: z.B. `Ideen`, `Geplant`, `In Umsetzung`, `Validierung`, `Abgeschlossen`

3. **Agenten-/Experiment-Board** (optional)

   * Fokus: Experimente, die von Agenten (oder 19-Agents-Setup) durchgeführt werden
   * Spalten: z.B. `Hypothese`, `Setup`, `Running`, `Auswertung`, `Archiv`

Für jedes Board:

* Spaltenliste
* Zweck in 2–3 Sätzen
* Typische Rollen/Agenten, die dort aktiv sind

---

### 6. CI / Automatisierung (GitHub Actions / GitLab CI)

Schlage auf Basis der gefundenen Dateien und unserer Arbeitsweise vor:

* Welche **minimale CI-Pipeline** CDB sofort stabiler machen würde
  (z.B. Linting, Tests, Build, ggf. Security/Static Analysis).
* Welche **weiteren Pipelines** später sinnvoll wären
  (z.B. Release-Builds, Doku-Checks, Governance-Checks, Agenten-Playground-Deploy).
* Wenn bereits CI existiert:

  * Kurze Ist-Analyse
  * Vorschläge für **Aufräumen / Vereinheitlichen / „Hardening“**.

---

### 7. Offene Fragen an das Team

Liste **3–7 konkrete Fragen**, die du an uns stellen würdest, bevor wir das Setup wirklich in GitHub/GitLab einführen, z.B.:

* Unklarheiten zur Agentenstruktur
* Entscheidungen zu „Monorepo vs. Multi-Repo“
* Rollenteilung (wer pflegt Labels, wer pflegt Roadmap, wer pflegt CI?)
* Wie stark Governance automatisiert werden soll

---

### Output-Format

Bitte liefere deinen Output in dieser Struktur:

1. **Projekt-Verständnis (kurz)**
2. **GitHub/GitLab-Zielbild (High-Level)**
3. **Vorschlag Label-System (mit Begründung)**
4. **Vorschlag Meilensteine (Name + Ziel + Inhalte)**
5. **Vorschlag Boards/Organisation**
6. **Vorschläge CI/Automatisierung**
7. **Fragen an das Team vor Umsetzung**

---

## 2️⃣ Wie ihr euch „langsam rantastet“ (Claude Code + GitHub/GitLab)

Vorschlag für eure **erste gemeinsame Session**:

1. **Projekt vorbereiten**

   * Im CDB-Repo sicherstellen, dass es eine `CLAUDE.md` gibt (ggf. mit `/init` erzeugen). 
   * Dort könnt ihr später eine eigene Sektion `## GitHub/GitLab-Organisation` anlegen, in die wir dieses Vorgehen als „Standardprozess“ einbauen.

2. **Claude Code in Plan Mode starten**

   * Im Projektordner im Terminal: `claude`
   * Mit `Shift+Tab` in den **Plan-/Analysemodus** wechseln (read-only, keine Änderungen).
   * Dann den oben optimierten Prompt einfügen.

3. **Gemeinsam auswerten**

   * Ergebnis gemeinsam anschauen (z.B. im Call / Workshop).
   * Labels, Meilensteine und Boards markieren als:

     * „sofort übernehmen“
     * „später testen“
     * „passt nicht zu uns“
   * CI-Vorschläge priorisieren (z.B. zuerst nur „Lint + Tests auf PR“).

Wenn du / ihr später weitergehen wollt (z.B. Agents, Subagents, Hooks, Best-of-N Varianten für Board-Design), können wir das sauber in einer nächsten Session aufbauen – immer mit **Plan Mode zuerst, dann vorsichtige Umsetzung**. 

---

**Vorschlag nächster Schritt mit mir:**
Schick mir einfach das erste Ergebnis, das Claude mit diesem Prompt produziert (oder die Teile, bei denen ihr unsicher seid), und wir iterieren gemeinsam daran weiter – besonders an Labels & CI-Hardening.
