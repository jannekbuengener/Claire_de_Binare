#!/bin/bash
# label_all_prs.sh - Versieht alle Pull Requests mit passenden Labels
# Erstellt für: Claire de Binare Cleanroom
# Datum: 2025-11-22

set -e

REPO="jannekbuengener/Claire_de_Binare_Cleanroom"

echo "🏷️  Label-Bot für Claire de Binare Pull Requests"
echo "=================================================="
echo ""

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Schritt 1: Prüfe gh CLI
echo -e "${BLUE}Schritt 1: Prüfe GitHub CLI...${NC}"
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) nicht gefunden!"
    echo "Installation: brew install gh / sudo apt install gh"
    exit 1
fi

# Schritt 2: Prüfe Authentifizierung
echo -e "${BLUE}Schritt 2: Prüfe Authentifizierung...${NC}"
if ! gh auth status &> /dev/null; then
    echo "❌ Nicht authentifiziert!"
    echo "Bitte ausführen: gh auth login"
    exit 1
fi
echo "✅ Authentifiziert"
echo ""

# Schritt 3: Hole alle Pull Requests
echo -e "${BLUE}Schritt 3: Hole alle Pull Requests...${NC}"
PRS_JSON=$(gh api repos/$REPO/pulls?state=all --paginate)
PR_COUNT=$(echo "$PRS_JSON" | jq length)
echo "📊 Gefunden: $PR_COUNT Pull Requests"
echo ""

# Schritt 4: Hole verfügbare Labels
echo -e "${BLUE}Schritt 4: Prüfe verfügbare Labels...${NC}"
LABELS_JSON=$(gh api repos/$REPO/labels --paginate)
LABEL_COUNT=$(echo "$LABELS_JSON" | jq length)
echo "🏷️  Verfügbare Labels: $LABEL_COUNT"
echo ""

if [ "$LABEL_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Keine Labels gefunden! Erstelle Standard-Labels...${NC}"

    # Standard-Labels erstellen
    declare -A LABELS=(
        ["feat"]="Feature - Neue Funktionalität|0e8a16"
        ["fix"]="Bugfix - Fehlerbehebung|d73a4a"
        ["docs"]="Dokumentation|0075ca"
        ["test"]="Tests|yellow"
        ["refactor"]="Refactoring|fbca04"
        ["chore"]="Chore - Wartung|fef2c0"
        ["ci"]="CI/CD - Continuous Integration|blue"
        ["risk-engine"]="Risk Engine|ff6347"
        ["signal-engine"]="Signal Engine|4169e1"
        ["execution"]="Execution Service|32cd32"
        ["testing"]="Testing Infrastructure|ffa500"
        ["infrastructure"]="Infrastructure|8b4513"
        ["security"]="Security|b22222"
        ["performance"]="Performance|9370db"
    )

    for label in "${!LABELS[@]}"; do
        IFS='|' read -r desc color <<< "${LABELS[$label]}"
        echo "Creating label: $label"
        gh api repos/$REPO/labels --method POST \
            --field name="$label" \
            --field description="$desc" \
            --field color="$color" || true
    done

    echo "✅ Standard-Labels erstellt"
    echo ""
fi

# Schritt 5: Analysiere und label jeden PR
echo -e "${BLUE}Schritt 5: Analysiere Pull Requests und weise Labels zu...${NC}"
echo ""

# Zähler für Statistik
TOTAL_PRS=0
LABELED_PRS=0

# Iteriere über alle PRs
echo "$PRS_JSON" | jq -c '.[]' | while read -r pr; do
    PR_NUMBER=$(echo "$pr" | jq -r '.number')
    PR_TITLE=$(echo "$pr" | jq -r '.title')
    PR_BODY=$(echo "$pr" | jq -r '.body // ""')
    PR_STATE=$(echo "$pr" | jq -r '.state')
    PR_MERGED=$(echo "$pr" | jq -r '.merged_at != null')

    ((TOTAL_PRS++))

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}PR #$PR_NUMBER${NC}: $PR_TITLE"
    echo "Status: $PR_STATE | Merged: $PR_MERGED"
    echo ""

    # Array für zu vergebende Labels
    LABELS_TO_ADD=()

    # Analyse des Titels (case-insensitive)
    TITLE_LOWER=$(echo "$PR_TITLE" | tr '[:upper:]' '[:lower:]')

    # Typ-Labels (basierend auf Conventional Commits)
    if [[ "$TITLE_LOWER" =~ ^feat:|feature: ]]; then
        LABELS_TO_ADD+=("feat")
    fi
    if [[ "$TITLE_LOWER" =~ ^fix:|bugfix: ]]; then
        LABELS_TO_ADD+=("fix")
    fi
    if [[ "$TITLE_LOWER" =~ ^docs:|documentation: ]]; then
        LABELS_TO_ADD+=("docs")
    fi
    if [[ "$TITLE_LOWER" =~ ^test:|tests: ]]; then
        LABELS_TO_ADD+=("test")
    fi
    if [[ "$TITLE_LOWER" =~ ^refactor: ]]; then
        LABELS_TO_ADD+=("refactor")
    fi
    if [[ "$TITLE_LOWER" =~ ^chore: ]]; then
        LABELS_TO_ADD+=("chore")
    fi
    if [[ "$TITLE_LOWER" =~ ^ci:|^ci/cd: ]]; then
        LABELS_TO_ADD+=("ci")
    fi

    # Bereichs-Labels (basierend auf Keywords)
    if [[ "$TITLE_LOWER" =~ risk|risk-engine|risk_engine ]]; then
        LABELS_TO_ADD+=("risk-engine")
    fi
    if [[ "$TITLE_LOWER" =~ signal|signal-engine|signal_engine ]]; then
        LABELS_TO_ADD+=("signal-engine")
    fi
    if [[ "$TITLE_LOWER" =~ execution|exec ]]; then
        LABELS_TO_ADD+=("execution")
    fi
    if [[ "$TITLE_LOWER" =~ test|testing|pytest|coverage ]]; then
        LABELS_TO_ADD+=("testing")
    fi
    if [[ "$TITLE_LOWER" =~ infrastructure|docker|compose|deployment ]]; then
        LABELS_TO_ADD+=("infrastructure")
    fi
    if [[ "$TITLE_LOWER" =~ security|secrets|audit ]]; then
        LABELS_TO_ADD+=("security")
    fi
    if [[ "$TITLE_LOWER" =~ performance|optimization|speed ]]; then
        LABELS_TO_ADD+=("performance")
    fi

    # Spezial-Analyse für Dependabot
    if [[ "$TITLE_LOWER" =~ ^bump|dependabot|dependencies ]]; then
        LABELS_TO_ADD+=("dependencies")
        LABELS_TO_ADD+=("chore")
    fi

    # Wenn keine Labels gefunden, versuche aus Body zu extrahieren
    if [ ${#LABELS_TO_ADD[@]} -eq 0 ] && [ -n "$PR_BODY" ]; then
        BODY_LOWER=$(echo "$PR_BODY" | tr '[:upper:]' '[:lower:]')

        if [[ "$BODY_LOWER" =~ feature|feat ]]; then
            LABELS_TO_ADD+=("feat")
        fi
        if [[ "$BODY_LOWER" =~ fix|bug ]]; then
            LABELS_TO_ADD+=("fix")
        fi
        if [[ "$BODY_LOWER" =~ test ]]; then
            LABELS_TO_ADD+=("test")
        fi
    fi

    # Zeige gefundene Labels
    if [ ${#LABELS_TO_ADD[@]} -gt 0 ]; then
        echo "🏷️  Labels zu vergeben: ${LABELS_TO_ADD[*]}"

        # Füge Labels hinzu (wenn noch nicht vorhanden)
        for label in "${LABELS_TO_ADD[@]}"; do
            echo "  → Füge Label hinzu: $label"
            gh api repos/$REPO/issues/$PR_NUMBER/labels --method POST \
                --field "labels[]=$label" &> /dev/null || true
        done

        ((LABELED_PRS++))
        echo "✅ Labels hinzugefügt"
    else
        echo "⚠️  Keine passenden Labels gefunden - manuell prüfen"
    fi

    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ Fertig!${NC}"
echo ""
echo "📊 Statistik:"
echo "   Gesamt PRs:     $TOTAL_PRS"
echo "   Gelabelt:       $LABELED_PRS"
echo "   Nicht gelabelt: $((TOTAL_PRS - LABELED_PRS))"
echo ""
echo "Prüfe Ergebnisse mit:"
echo "  gh pr list --repo $REPO --state all --limit 50"
echo ""
