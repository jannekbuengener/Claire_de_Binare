#!/usr/bin/env python3
"""
COPILOT SMART DEVELOPMENT WORKFLOW ASSISTANT  
Intelligent development task automation and suggestions
"""

import os
import subprocess
import json
from pathlib import Path

def analyze_git_status():
    """Smart git status analysis with suggestions"""
    try:
        # Get git status
        status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        
        modified_files = [line[3:] for line in status.stdout.split('\n') if line.startswith(' M')]
        added_files = [line[3:] for line in status.stdout.split('\n') if line.startswith('A ')]
        
        print('📊 COPILOT SMART DEVELOPMENT ANALYSIS')
        print('=' * 50)
        
        if modified_files:
            print(f'📝 Modified files: {len(modified_files)}')
            for file in modified_files[:5]:  # Show first 5
                print(f'   • {file}')
        
        if added_files:
            print(f'✨ Added files: {len(added_files)}')
            for file in added_files[:5]:
                print(f'   • {file}')
                
        # Smart suggestions
        print('\n🧠 SMART SUGGESTIONS:')
        
        if any('test' in f for f in modified_files + added_files):
            print('   💡 Tests modified - Consider running: pytest tests/unit/')
            
        if any(f.endswith('.py') for f in modified_files + added_files):
            print('   💡 Python files changed - Consider running: ruff check services/')
            
        if any('docker' in f.lower() for f in modified_files + added_files):
            print('   💡 Docker config changed - Consider: docker-compose config')
            
        if any('.yml' in f or '.yaml' in f for f in modified_files + added_files):
            print('   💡 YAML files changed - Consider validating syntax')
            
        return True
        
    except Exception as e:
        print(f'❌ Git analysis failed: {e}')
        return False

def suggest_next_actions():
    """AI-powered next action suggestions"""
    print('\n🎯 NEXT ACTION SUGGESTIONS:')
    
    # Check for common development tasks
    if Path('requirements.txt').exists():
        print('   📦 Dependencies available - run: pip install -r requirements.txt')
    
    # Check if services are running
    print('   🔍 Run health check: python scripts/smart_health_check.py')
    
    # Check for pending tests
    print('   🧪 Run tests: python -m pytest tests/unit/')
    
    # Check for container status
    print('   🐳 Check containers: docker-compose ps')

if __name__ == '__main__':
    analyze_git_status()
    suggest_next_actions()