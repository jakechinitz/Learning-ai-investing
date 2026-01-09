#!/usr/bin/env python3
"""
Quick entry point for generating daily reports.
Run: python generate_report.py
"""

from src.report_generator import generate_daily_report

if __name__ == "__main__":
    report = generate_daily_report()
    print("\n✅ Report generated successfully!")
    print(f"View it in data/reports/")
