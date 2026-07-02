#!/usr/bin/env python3
"""
Code Coverage Runner
Generates coverage reports for the AFROTC 695 Recruitment System
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
from datetime import datetime

def run_coverage_analysis():
    """Run coverage analysis on the test suite"""
    
    # Create coverage directory if it doesn't exist
    coverage_dir = Path("coverage_reports")
    coverage_dir.mkdir(exist_ok=True)
    
    # Initialize coverage
    subprocess.run([sys.executable, "-m", "coverage", "erase"], check=True)
    
    # Run tests with coverage
    test_files = [
        "tests/test_2fa_utils.py",
        "tests/test_user_model_2fa.py", 
        "tests/test_2fa_routes.py",
        "tests/test_database_migration.py"
    ]
    
    # Run each test file
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"Running coverage for {test_file}...")
            subprocess.run([
                sys.executable, "-m", "coverage", "run", "--source=.", test_file
            ], check=True)
    
    # Generate HTML report
    print("Generating HTML coverage report...")
    subprocess.run([
        sys.executable, "-m", "coverage", "html", 
        "--directory=coverage_reports/html",
        "--title=AFROTC 695 Code Coverage Report"
    ], check=True)
    
    # Generate JSON report for web interface
    print("Generating JSON coverage report...")
    subprocess.run([
        sys.executable, "-m", "coverage", "json", 
        "--output-file=coverage_reports/coverage.json"
    ], check=True)
    
    # Generate summary report
    print("Generating summary report...")
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

def generate_coverage_summary():
    """Generate a simplified coverage summary for the web interface"""
    
    try:
        with open("coverage_reports/coverage.json", "r") as f:
            coverage_data = json.load(f)
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_lines": 0,
            "covered_lines": 0,
            "missing_lines": 0,
            "coverage_percentage": 0,
            "files": []
        }
        
        for file_path, file_data in coverage_data["files"].items():
            # Skip test files and coverage files
            if "test_" in file_path or "coverage" in file_path:
                continue
                
            file_summary = {
                "file": file_path,
                "total_lines": len(file_data["executed_lines"]) + len(file_data["missing_lines"]),
                "covered_lines": len(file_data["executed_lines"]),
                "missing_lines": len(file_data["missing_lines"]),
                "coverage_percentage": 0
            }
            
            if file_summary["total_lines"] > 0:
                file_summary["coverage_percentage"] = round(
                    (file_summary["covered_lines"] / file_summary["total_lines"]) * 100, 2
                )
            
            summary["files"].append(file_summary)
            summary["total_lines"] += file_summary["total_lines"]
            summary["covered_lines"] += file_summary["covered_lines"]
            summary["missing_lines"] += file_summary["missing_lines"]
        
        if summary["total_lines"] > 0:
            summary["coverage_percentage"] = round(
                (summary["covered_lines"] / summary["total_lines"]) * 100, 2
            )
        
        # Sort files by coverage percentage (lowest first)
        summary["files"].sort(key=lambda x: x["coverage_percentage"])
        
        # Save summary
        with open("coverage_reports/summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        return summary
        
    except Exception as e:
        print(f"Error generating coverage summary: {e}")
        return None

if __name__ == "__main__":
    print("Running code coverage analysis...")
    summary = run_coverage_analysis()
    
    if summary:
        print("Coverage analysis completed successfully!")
        print(f"Total coverage: {summary.get('totals', {}).get('percent_covered', 0):.2f}%")
    else:
        print("Coverage analysis failed!")
    
    # Generate web-friendly summary
    web_summary = generate_coverage_summary()
    if web_summary:
        print(f"Web summary generated: {web_summary['coverage_percentage']}% overall coverage")
        print(f"Files analyzed: {len(web_summary['files'])}")






