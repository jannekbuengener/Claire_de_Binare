#!/usr/bin/env python3
"""
Label-Migration Script
Mappt alte Labels auf neue Labels
"""

LABEL_MAPPING = {
    # Alte Label → Neue Label
    "type:testing": ["testing", "type:chore"],
    "infrastructure": ["scope:infra"],
    "security": ["type:security"],
    "monitoring": ["scope:monitoring"],
    "ci-cd": ["scope:ci"],
    "github-actions": ["scope:ci"],
    "scope:security": ["type:security"],
    
    # Milestone → Remove (use GitHub Milestones instead)
    "milestone:m1": [],
    "milestone:m2": [],
    "milestone:m3": [],
    "milestone:m4": [],
    "milestone:m5": [],
    "milestone:m6": [],
    "milestone:m7": [],
    "milestone:m8": [],
    "milestone:m9": [],
    
    # Epic → Remove (use GitHub Projects instead)
    "epic:ml-foundation": [],
    "epic:stabilization": [],
    "epic:paper-trading": [],
    "epic:live-trading": []
}

# Implementierung via GitHub CLI:
# gh issue list --label "old-label" --json number,labels
# gh issue edit <number> --remove-label "old-label" --add-label "new-label"
