#!/usr/bin/env python3
"""
Quality Analyzer for AFROTC 695 Recruitment System
Combines code coverage and vulnerability analysis with visualization
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

def run_coverage_analysis() -> Dict[str, Any]:
    """Run code coverage analysis"""
    print("Running code coverage analysis...")
    
    try:
        # Create coverage directory
        coverage_dir = Path("coverage_reports")
        coverage_dir.mkdir(exist_ok=True)
        
        # Initialize coverage
        subprocess.run([sys.executable, "-m", "coverage", "erase"], check=True)
        
        # Run tests with coverage (simplified approach)
        test_files = [
            "tests/test_2fa_utils.py",
            "tests/test_user_model_2fa.py", 
            "tests/test_2fa_routes.py",
            "tests/test_database_migration.py"
        ]
        
        # Run each test file that exists
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"Running coverage for {test_file}...")
                try:
                    subprocess.run([
                        sys.executable, "-m", "coverage", "run", "--source=.", test_file
                    ], check=True, timeout=60)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    print(f"Warning: {test_file} failed or timed out")
        
        # Generate summary report
        result = subprocess.run([
            sys.executable, "-m", "coverage", "report", "--format=json"
        ], capture_output=True, text=True, check=True)
        
        # Parse the summary
        try:
            summary = json.loads(result.stdout)
            return summary
        except json.JSONDecodeError:
            print("Error parsing coverage summary")
            return None
            
    except Exception as e:
        print(f"Coverage analysis failed: {e}")
        return None

def run_vulnerability_scan() -> Dict[str, Any]:
    """Run vulnerability scan"""
    print("Running vulnerability scan...")
    
    try:
        # Import and run vulnerability scanner
        import vulnerability_scanner
        return vulnerability_scanner.generate_vulnerability_summary()
    except ImportError:
        print("Vulnerability scanner not available")
        return None
    except Exception as e:
        print(f"Vulnerability scan failed: {e}")
        return None

def generate_quality_summary() -> Dict[str, Any]:
    """Generate comprehensive quality summary combining coverage and security"""
    print("Generating comprehensive quality summary...")
    
    # Create reports directory
    reports_dir = Path("quality_reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Run analyses
    coverage_data = run_coverage_analysis()
    vulnerability_data = run_vulnerability_scan()
    
    # Calculate coverage metrics
    coverage_summary = {
        'total_lines': 0,
        'covered_lines': 0,
        'missing_lines': 0,
        'coverage_percentage': 0,
        'files_analyzed': 0
    }
    
    if coverage_data:
        try:
            totals = coverage_data.get('totals', {})
            coverage_summary['total_lines'] = totals.get('num_statements', 0)
            coverage_summary['covered_lines'] = totals.get('covered_lines', 0)
            coverage_summary['missing_lines'] = totals.get('missing_lines', 0)
            coverage_summary['coverage_percentage'] = totals.get('percent_covered', 0)
            coverage_summary['files_analyzed'] = len(coverage_data.get('files', {}))
        except Exception as e:
            print(f"Error processing coverage data: {e}")
    
    # Calculate security metrics
    security_summary = {
        'total_issues': 0,
        'high_severity': 0,
        'medium_severity': 0,
        'low_severity': 0,
        'risk_score': 0,
        'status': 'unknown'
    }
    
    if vulnerability_data:
        try:
            overall = vulnerability_data.get('overall_summary', {})
            security_summary['total_issues'] = overall.get('total_issues', 0)
            security_summary['high_severity'] = overall.get('high_severity', 0)
            security_summary['medium_severity'] = overall.get('medium_severity', 0)
            security_summary['low_severity'] = overall.get('low_severity', 0)
            security_summary['risk_score'] = overall.get('risk_score', 0)
            security_summary['status'] = overall.get('status', 'unknown')
        except Exception as e:
            print(f"Error processing vulnerability data: {e}")
    
    # Calculate overall quality score
    coverage_score = coverage_summary['coverage_percentage']
    security_score = max(0, 10 - security_summary['risk_score'])  # Invert risk score
    
    # Weighted quality score (70% coverage, 30% security)
    quality_score = (coverage_score * 0.7) + (security_score * 0.3)
    
    # Determine overall quality grade
    if quality_score >= 90:
        grade = 'A+'
        status = 'excellent'
    elif quality_score >= 80:
        grade = 'A'
        status = 'very_good'
    elif quality_score >= 70:
        grade = 'B'
        status = 'good'
    elif quality_score >= 60:
        grade = 'C'
        status = 'fair'
    elif quality_score >= 50:
        grade = 'D'
        status = 'poor'
    else:
        grade = 'F'
        status = 'critical'
    
    # Create comprehensive summary
    summary = {
        'generated_at': datetime.now().isoformat(),
        'coverage': coverage_summary,
        'security': security_summary,
        'quality_score': round(quality_score, 2),
        'grade': grade,
        'status': status,
        'recommendations': []
    }
    
    # Generate recommendations
    if coverage_summary['coverage_percentage'] < 70:
        summary['recommendations'].append({
            'type': 'coverage',
            'priority': 'high',
            'message': f'Code coverage is {coverage_summary["coverage_percentage"]:.1f}%. Aim for at least 70% coverage.'
        })
    
    if security_summary['total_issues'] > 0:
        summary['recommendations'].append({
            'type': 'security',
            'priority': 'high' if security_summary['high_severity'] > 0 else 'medium',
            'message': f'Found {security_summary["total_issues"]} security issues ({security_summary["high_severity"]} high severity).'
        })
    
    if coverage_summary['files_analyzed'] < 5:
        summary['recommendations'].append({
            'type': 'testing',
            'priority': 'medium',
            'message': f'Only {coverage_summary["files_analyzed"]} files analyzed. Consider adding more test files.'
        })
    
    # Save summary
    with open('quality_reports/summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary

def main():
    """Main quality analysis function"""
    print("AFROTC 695 Quality Analyzer")
    print("=" * 40)
    
    summary = generate_quality_summary()
    
    if summary:
        print("\nQuality Analysis Results:")
        print("-" * 30)
        print(f"Overall Quality Score: {summary['quality_score']}/100")
        print(f"Grade: {summary['grade']}")
        print(f"Status: {summary['status'].replace('_', ' ').title()}")
        
        print(f"\nCode Coverage:")
        print(f"  Coverage: {summary['coverage']['coverage_percentage']:.1f}%")
        print(f"  Files Analyzed: {summary['coverage']['files_analyzed']}")
        print(f"  Lines Covered: {summary['coverage']['covered_lines']}/{summary['coverage']['total_lines']}")
        
        print(f"\nSecurity Analysis:")
        print(f"  Total Issues: {summary['security']['total_issues']}")
        print(f"  High Severity: {summary['security']['high_severity']}")
        print(f"  Medium Severity: {summary['security']['medium_severity']}")
        print(f"  Low Severity: {summary['security']['low_severity']}")
        print(f"  Risk Score: {summary['security']['risk_score']}/10")
        print(f"  Status: {summary['security']['status'].title()}")
        
        if summary['recommendations']:
            print(f"\nRecommendations:")
            for rec in summary['recommendations']:
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                print(f"  {priority_icon} {rec['message']}")
        
        print(f"\nDetailed reports saved to: quality_reports/")
        print("Summary saved to: quality_reports/summary.json")
    else:
        print("Quality analysis failed!")

if __name__ == "__main__":
    main()






