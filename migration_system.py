"""
The main migration system that ties everything together
"""
import os
from typing import Dict, List
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import Progress
from dotenv import load_dotenv

from models import ComponentResult, ComponentSchema, ExtractedContent, PageInfo, MigrationResults, get_content_types
from html_parser import find_content_sections, get_fallback_text
from ai_classifier import AIClassifier, SchemaGenerator
from schema_creator import create_schema, is_schema_good
from component_patterns import ComponentPatternDetector
from database import db_manager

load_dotenv()
console = Console()


class MigrationSystem:
    """The main system that handles the entire migration process"""
    
    def __init__(self, api_key: str = None):
        # Get API key from environment if not provided
        # self.api_key = api_key or os.getenv("COHERE_API_KEY")
        # self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("Need a Cohere API key to work with AI")
        
        # Set up our components
        self.ai_classifier = AIClassifier(self.api_key)
        self.schema_generator = SchemaGenerator(self.api_key)
        self.pattern_detector = ComponentPatternDetector()
        
        # Keep track of what we find
        self.page_info: List[PageInfo] = []
        self.content_results: Dict[str, List[ComponentResult]] = {}
        self.schemas: Dict[str, ComponentSchema] = {}
        self.extracted_content: List[ExtractedContent] = []
        self.reusable_patterns = {}  # Store reusable component patterns
    
    def migrate_content(self, html_folder: str) -> MigrationResults:
        """Run the complete migration process"""
        console.print("🚀 Starting content migration", style="bold green")
        start_time = datetime.now()
        
        # Connect to database
        if not db_manager.connect():
            raise RuntimeError("Couldn't connect to database")
        
        try:
            # Step 1: Analyze all the HTML files
            self._analyze_html_files(html_folder)
            
            # Step 2: Detect reusable component patterns
            self._detect_reusable_patterns()
            
            # Step 3: Create schemas for the content types we found
            self._create_content_schemas()
            
            # Step 4: Extract structured data using our schemas
            self._extract_structured_data(html_folder)
            
            # Step 5: Save everything and create output files
            output_files = self._save_results()
            
            # Calculate how long it took
            end_time = datetime.now()
            time_taken = (end_time - start_time).total_seconds()
            
            return MigrationResults(
                time_taken=time_taken,
                schemas_created=len(self.schemas),
                content_extracted=len(self.extracted_content),
                output_files=output_files
            )
            
        finally:
            db_manager.close()
    
    def _analyze_html_files(self, html_folder: str):
        """Look at all HTML files and figure out what types of content they have"""
        console.print("\n📊 Analyzing HTML files", style="bold blue")
        
        html_files = list(Path(html_folder).glob("*.html"))
        
        if not html_files:
            raise ValueError(f"No HTML files found in {html_folder}")
        
        with Progress() as progress:
            task = progress.add_task("Analyzing files...", total=len(html_files))
            
            for html_file in html_files:
                self._analyze_single_file(html_file)
                progress.update(task, advance=1)
    
    def _analyze_single_file(self, html_file: Path):
        """Analyze one HTML file"""
        try:
            # Find interesting content sections
            sections = find_content_sections(html_file)
            
            # Classify each section with AI
            file_results = []
            content_types_found = []
            
            for section in sections:
                result = self.ai_classifier.classify_content(section, html_file.name, html_file)
                
                if result.looks_good():
                    file_results.append(result)
                    content_types_found.append(result.content_type)
                    
                    # Group by content type
                    if result.content_type not in self.content_results:
                        self.content_results[result.content_type] = []
                    self.content_results[result.content_type].append(result)
            
            # Save info about this page
            page_info = PageInfo(
                filename=html_file.name,
                file_size=html_file.stat().st_size,
                content_types_found=list(set(content_types_found)),
                total_components=len(file_results),
                analyzed_at=datetime.now()
            )
            
            self.page_info.append(page_info)
            
            # Save to database
            db_manager.save_page_type(page_info.to_dict())
            
        except Exception as e:
            console.print(f"❌ Couldn't analyze {html_file.name}: {e}", style="red")
    
    def _detect_reusable_patterns(self):
        """Detect reusable component patterns across all analyzed content"""
        console.print("\n🔄 Detecting reusable component patterns", style="bold blue")
        
        # Convert content results to format expected by pattern detector
        all_results = []
        for content_type, results in self.content_results.items():
            for result in results:
                all_results.append({
                    'content_type': result.content_type,
                    'source_file': result.source_file,
                    'confidence': result.confidence,
                    'fields': result.fields
                })
        
        # Detect patterns
        self.reusable_patterns = self.pattern_detector.detect_patterns(all_results)
        
        # Display results
        reusable_count = len(self.reusable_patterns)
        total_types = len(self.content_results)
        
        console.print(f"📊 Found {reusable_count} reusable patterns out of {total_types} content types")
        
        for pattern_type, pattern_info in self.reusable_patterns.items():
            score = pattern_info['reusability_score']
            instances = pattern_info['instances_count']
            console.print(f"  🔧 {pattern_type}: {score:.2f} score, {instances} instances", style="cyan")
    
    def _create_content_schemas(self):
        """Create schemas for all the content types we found"""
        console.print("\n🔧 Creating content schemas", style="bold blue")
        
        # Show what types we found
        all_types = get_content_types()
        console.print(f"📋 Content types we know: {', '.join(all_types)}", style="cyan")
        
        for content_type, results in self.content_results.items():
            if not results:
                continue
            
            console.print(f"Creating schema for {content_type} ({len(results)} examples)")
            
            # Use AI to generate a schema based on our examples
            ai_schema = self.schema_generator.generate_schema(content_type, results)
            
            if ai_schema and 'fields' in ai_schema:
                # Create the schema object
                schema = create_schema(content_type, ai_schema['fields'])
                
                # Make sure it's valid
                if is_schema_good(schema):
                    self.schemas[content_type] = schema
                    
                    # Save to database
                    db_manager.save_component_schema(schema.to_cms_format())
                    
                    # Keep track of this type
                    type_info = {
                        "type": content_type,
                        "example_count": len(results),
                        "found_at": datetime.now().isoformat()
                    }
                    db_manager.save_component_type(type_info)
                else:
                    console.print(f"⚠️  Schema for {content_type} didn't pass validation", style="yellow")
    
    def _extract_structured_data(self, html_folder: str):
        """Go back through the files and extract structured data using our schemas"""
        console.print("\n📋 Extracting structured data", style="bold blue")
        
        html_files = list(Path(html_folder).glob("*.html"))
        
        with Progress() as progress:
            task = progress.add_task("Extracting data...", total=len(html_files))
            
            for html_file in html_files:
                self._extract_from_file(html_file)
                progress.update(task, advance=1)
    
    def _extract_from_file(self, html_file: Path):
        """Extract structured data from one file"""
        try:
            sections = find_content_sections(html_file)
            
            for section in sections:
                # Classify the section
                result = self.ai_classifier.classify_content(section, html_file.name, html_file)
                
                if result.looks_good() and result.content_type in self.schemas:
                    # Extract data for each field in the schema
                    schema = self.schemas[result.content_type]
                    extracted_data = {}
                    
                    for field in schema.fields:
                        # Try to get the value from AI results first
                        value = result.fields.get(field.name)
                        
                        # If not found, try simple fallback
                        if not value:
                            value = get_fallback_text(section, field.name)
                        
                        extracted_data[field.name] = value
                    
                    # Create the extracted content object
                    content = ExtractedContent(
                        content_type=result.content_type,
                        source_file=html_file.name,
                        confidence=result.confidence,
                        data=extracted_data,
                        extracted_at=datetime.now()
                    )
                    
                    self.extracted_content.append(content)
                    
                    # Save to database
                    db_manager.save_extracted_data(content.to_dict())
                    
        except Exception as e:
            console.print(f"❌ Couldn't extract from {html_file.name}: {e}", style="red")
    
    def _save_results(self) -> Dict[str, str]:
        """Save our results to files"""
        console.print("\n💾 Saving results", style="bold blue")
        
        # Create output directory
        output_dir = Path("migration_outputs")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_files = {}
        
        # Save schemas
        import json
        
        schemas_data = {
            content_type: schema.to_cms_format() 
            for content_type, schema in self.schemas.items()
        }
        
        schemas_file = output_dir / f"content_schemas_{timestamp}.json"
        with open(schemas_file, 'w') as f:
            json.dump(schemas_data, f, indent=2)
        output_files["schemas"] = str(schemas_file)
        console.print(f"✅ Saved {schemas_file.name}")
        
        # Save extracted data
        extracted_data = [content.to_dict() for content in self.extracted_content]
        
        data_file = output_dir / f"extracted_content_{timestamp}.json"
        with open(data_file, 'w') as f:
            json.dump(extracted_data, f, indent=2)
        output_files["extracted_data"] = str(data_file)
        console.print(f"✅ Saved {data_file.name}")
        
        # Generate CMS components from reusable patterns
        cms_components = self._generate_cms_components()
        
        # Save CMS components file
        components_file = output_dir / f"reusable_components_{timestamp}.json"
        with open(components_file, 'w') as f:
            json.dump(cms_components, f, indent=2)
        output_files["components"] = str(components_file)
        console.print(f"✅ Saved {components_file.name}")
        
        # Save migration report
        report = {
            "migration_date": datetime.now().isoformat(),
            "summary": {
                "schemas_created": len(self.schemas),
                "content_extracted": len(self.extracted_content),
                "content_types": list(self.schemas.keys()),
                "reusable_patterns": len(self.reusable_patterns),
                "reusability_score": self._calculate_overall_reusability()
            },
            "page_info": [info.to_dict() for info in self.page_info],
            "schemas": schemas_data,
            "reusable_patterns": self.reusable_patterns,
            "cms_components": cms_components
        }
        
        report_file = output_dir / f"migration_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        output_files["report"] = str(report_file)
        console.print(f"✅ Saved {report_file.name}")
        
        return output_files
    
    def _generate_cms_components(self) -> dict:
        """Generate CMS component definitions from reusable patterns"""
        cms_components = {}
        
        for pattern_type, pattern_info in self.reusable_patterns.items():
            component_name = pattern_info['template']['component_name']
            
            # Create CMS component schema
            cms_component = {
                "name": component_name,
                "display_name": pattern_type.replace('-', ' ').title(),
                "description": pattern_info['template']['description'],
                "category": self._determine_component_category(pattern_type),
                "reusable": True,
                "instances_count": pattern_info['instances_count'],
                "reusability_score": pattern_info['reusability_score'],
                "usage_contexts": pattern_info['usage_contexts'],
                "fields": []
            }
            
            # Add field definitions
            for field_name in pattern_info['common_fields']:
                field_info = pattern_info['template']['fields'].get(field_name, {})
                
                cms_field = {
                    "name": field_name,
                    "display_name": field_name.replace('_', ' ').title(),
                    "type": self._map_to_cms_field_type(field_info.get('data_type', 'str')),
                    "required": field_info.get('required', False),
                    "component_role": field_info.get('component_type', 'content')
                }
                
                # Add field-specific configuration
                if field_info.get('component_type') == 'navigation':
                    cms_field.update({
                        "type": "array",
                        "item_type": "link",
                        "typical_count": int(field_info.get('average_items', 5))
                    })
                elif field_info.get('component_type') == 'rich_text':
                    cms_field.update({
                        "type": "rich_text",
                        "multiline": True,
                        "content_heavy": field_info.get('is_content_heavy', False)
                    })
                elif field_info.get('component_type') == 'heading':
                    cms_field.update({
                        "type": "text",
                        "is_title_field": True,
                        "variable_content": field_info.get('is_unique_content', False)
                    })
                
                cms_component["fields"].append(cms_field)
            
            cms_components[component_name] = cms_component
        
        return cms_components
    
    def _determine_component_category(self, pattern_type: str) -> str:
        """Determine CMS component category"""
        if 'navigation' in pattern_type or 'menu' in pattern_type:
            return 'navigation'
        elif 'product' in pattern_type or 'showcase' in pattern_type:
            return 'commerce'
        elif 'recipe' in pattern_type or 'article' in pattern_type:
            return 'content'
        elif 'form' in pattern_type:
            return 'interactive'
        else:
            return 'general'
    
    def _map_to_cms_field_type(self, data_type: str) -> str:
        """Map Python data types to CMS field types"""
        mapping = {
            'str': 'text',
            'list': 'array',
            'int': 'number',
            'float': 'number',
            'bool': 'boolean',
            'dict': 'object'
        }
        return mapping.get(data_type, 'text')
    
    def _calculate_overall_reusability(self) -> float:
        """Calculate overall reusability score for the migration"""
        if not self.reusable_patterns:
            return 0.0
        
        total_score = sum(pattern['reusability_score'] for pattern in self.reusable_patterns.values())
        return round(total_score / len(self.reusable_patterns), 2)


def main():
    """Main entry point"""
    try:
        system = MigrationSystem()
        results = system.migrate_content("scrap")
        
        console.print(f"\n{results.summary()}", style="bold green")
        
        console.print("\n📁 Files created:")
        for file_type, file_path in results.output_files.items():
            console.print(f"  • {file_type}: {file_path}")
        
    except Exception as e:
        console.print(f"❌ Migration failed: {e}", style="red")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())