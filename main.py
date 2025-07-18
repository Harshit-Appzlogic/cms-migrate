#!/usr/bin/env python3
"""
Main entry point for the CMS Migration System
"""
import sys
import os
from pathlib import Path
from rich.console import Console

from migration_system import MigrationSystem

console = Console()

def main():
    """Main entry point for CMS Migration System"""
    
    # Check if COHERE_API_KEY is set
    if not os.getenv("COHERE_API_KEY"):
        console.print("❌ COHERE_API_KEY not found", style="red")
        console.print("Please set your Cohere API key in the .env file", style="yellow")
        return 1
    
    # HTML directory
    html_dir = "scrap"
    
    if not Path(html_dir).exists():
        console.print(f"❌ HTML directory '{html_dir}' not found", style="red")
        return 1
    
    try:
        # Initialize and run migration system
        console.print("🚀 Starting CMS Migration System", style="bold green")
        migration_system = MigrationSystem()
        results = migration_system.migrate_content(html_dir)
        
        # Display results
        console.print(f"\n{results.summary()}", style="bold green")
        
        console.print("\n📁 Output files generated:")
        for output_type, file_path in results.output_files.items():
            console.print(f"  • {output_type}: {file_path}")
        
        return 0
        
    except Exception as e:
        console.print(f"❌ Migration failed: {e}", style="red")
        return 1

if __name__ == "__main__":
    sys.exit(main())