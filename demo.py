#!/usr/bin/env python3
"""
Demo script to showcase the CMS Migration System capabilities
"""
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
import shutil

from migration_system import MigrationSystem
from database import db_manager

console = Console()

def run_demo():
    """Run demonstration with sample files"""
    
    # Check API key
    if not os.getenv("COHERE_API_KEY"):
        console.print("❌ COHERE_API_KEY not found", style="red")
        console.print("Please set your Cohere API key in the .env file", style="yellow")
        return 1
    
    # Create demo directory with sample files
    demo_dir = Path("demo_files")
    demo_dir.mkdir(exist_ok=True)
    
    # Copy sample files for demo
    sample_files = ["recipe_scrap.html", "tech_scrap.html", "publishers_scrap3.html"]
    scrap_dir = Path("scrap")
    
    console.print("🎬 Setting up Demo Files", style="bold blue")
    
    for file in sample_files:
        source = scrap_dir / file
        if source.exists():
            shutil.copy(source, demo_dir / file)
            console.print(f"  ✅ {file}")
    
    try:
        # Run migration
        console.print("\n🚀 Running CMS Migration Demo", style="bold green")
        
        migration_system = MigrationSystem()
        results = migration_system.migrate_content(str(demo_dir))
        
        # Show results
        console.print(f"\n{results.summary()}", style="bold green")
        
        # Show detailed analysis
        console.print("\n📊 Demo Results Analysis:", style="bold blue")
        
        if db_manager.connect():
            try:
                # Show schemas
                schemas = db_manager.get_component_schemas()
                
                schema_table = Table(title="Generated CMS Schemas")
                schema_table.add_column("Component Type", style="cyan")
                schema_table.add_column("Fields", justify="right")
                schema_table.add_column("CMS Ready", style="green")
                
                for schema in schemas:
                    comp_type = schema.get('uid', '').replace('_component', '')
                    field_count = len(schema.get('schema', []))
                    
                    schema_table.add_row(
                        comp_type.title(),
                        str(field_count),
                        "✅ Yes"
                    )
                
                console.print(schema_table)
                
                # Show extracted data
                extracted = db_manager.get_extracted_data()
                
                instance_table = Table(title="Extracted Component Instances")
                instance_table.add_column("Type", style="cyan")
                instance_table.add_column("Source Page", style="yellow")
                instance_table.add_column("Confidence", justify="right")
                
                for data in extracted:
                    instance_table.add_row(
                        data.get('component_type', 'N/A'),
                        data.get('source_file', 'N/A'),
                        f"{data.get('confidence', 0):.2f}"
                    )
                
                console.print(instance_table)
                
                # Show the concept
                console.print("\n🎯 Key Concept Demonstrated:", style="bold green")
                console.print("  • Multiple pages analyzed")
                console.print("  • Common patterns identified")
                console.print("  • Reusable schemas generated")
                console.print("  • Ready for CMS import")
                
            finally:
                db_manager.close()
        
        return 0
        
    except Exception as e:
        console.print(f"❌ Demo failed: {e}", style="red")
        return 1
    
    finally:
        # Clean up
        shutil.rmtree(demo_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(run_demo())