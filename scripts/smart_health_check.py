#!/usr/bin/env python3
"""
COPILOT SMART HEALTH MONITOR
Intelligent service health checking with automated diagnostics
"""

import requests
import json
import time
from datetime import datetime

def check_service_health():
    """Smart health check with diagnostics"""
    services = [
        {'name': 'Signal Engine', 'url': 'http://localhost:5001/health'},
        {'name': 'Risk Manager', 'url': 'http://localhost:5002/health'},
        {'name': 'Execution Service', 'url': 'http://localhost:5003/health'},
    ]
    
    print('🔍 COPILOT SMART HEALTH CHECK STARTING')
    print('=' * 50)
    
    results = []
    for service in services:
        try:
            start_time = time.time()
            response = requests.get(service['url'], timeout=5)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                print(f'✅ {service["name"]}: HEALTHY ({response_time:.1f}ms)')
                results.append({'service': service['name'], 'status': 'healthy', 'response_time': response_time})
            else:
                print(f'⚠️ {service["name"]}: DEGRADED (HTTP {response.status_code})')
                results.append({'service': service['name'], 'status': 'degraded', 'response_time': response_time})
                
        except requests.exceptions.RequestException as e:
            print(f'❌ {service["name"]}: DOWN ({str(e)})')
            results.append({'service': service['name'], 'status': 'down', 'error': str(e)})
    
    # Smart diagnostics
    healthy_services = [r for r in results if r.get('status') == 'healthy']
    print(f'\n📊 HEALTH SUMMARY: {len(healthy_services)}/{len(services)} services healthy')
    
    if len(healthy_services) == len(services):
        print('🎉 ALL SYSTEMS OPERATIONAL')
    elif len(healthy_services) > len(services) // 2:
        print('⚠️ PARTIAL SYSTEM DEGRADATION - INVESTIGATE')
    else:
        print('🚨 MAJOR SYSTEM OUTAGE - IMMEDIATE ATTENTION REQUIRED')
    
    return results

if __name__ == '__main__':
    check_service_health()