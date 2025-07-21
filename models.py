"""
Simple data models for the CMS migration system
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


# We start with basic types but discover more as we go
known_content_types = ["article", "navigation", "form", "unknown"]

def add_content_type(new_type):
    """Add a new content type if we haven't seen it before"""
    if new_type and new_type not in known_content_types:
        known_content_types.append(new_type)
        print(f"🆕 Found new content type: {new_type}")
        return True
    return False

def get_content_types():
    """Get all the content types we know about"""
    return sorted(known_content_types)

# What field types does our CMS support?
FIELD_TYPES = ["text", "file", "number", "boolean", "date"]


@dataclass
class ComponentResult:
    """What we found when analyzing a piece of content"""
    content_type: str
    confidence: float
    fields: Dict[str, Any]
    source_file: str
    html_content: str
    
    def looks_good(self, min_confidence: float = 0.3) -> bool:
        """Is this result confident enough to use?"""
        return self.confidence >= min_confidence


@dataclass
class SchemaField:
    """A field in our CMS schema"""
    name: str
    field_type: str
    display_name: str
    required: bool
    multiline: bool = False
    options: Optional[List[str]] = None
    
    def to_cms_format(self) -> Dict[str, Any]:
        """Convert to the format our CMS expects"""
        metadata = {}
        
        if self.multiline:
            metadata["multiline"] = True
            
        if self.field_type == "file":
            metadata["allow_upload"] = True
            
        if self.options:
            metadata["enum"] = [
                {"label": opt.title(), "value": opt.lower()}
                for opt in self.options
            ]
        
        return {
            "uid": self.name,
            "data_type": self.field_type,
            "display_name": self.display_name,
            "mandatory": self.required,
            "field_metadata": metadata
        }


@dataclass
class ComponentSchema:
    """A complete schema for a type of content"""
    content_type: str
    title: str
    fields: List[SchemaField]
    description: str
    
    def to_cms_format(self) -> Dict[str, Any]:
        """Convert to the exact format our CMS needs"""
        return {
            "title": self.title,
            "uid": f"{self.content_type}_component",
            "schema": [field.to_cms_format() for field in self.fields],
            "options": {
                "singleton": False,
                "is_page": False,
                "title": self.fields[0].name if self.fields else "title"
            },
            "description": self.description
        }


@dataclass
class ExtractedContent:
    """Content we extracted from a page"""
    content_type: str
    source_file: str
    confidence: float
    data: Dict[str, Any]
    extracted_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for saving"""
        return {
            "component_type": self.content_type,
            "source_file": self.source_file,
            "confidence": self.confidence,
            "field_data": self.data,
            "created_at": self.extracted_at.isoformat()
        }


@dataclass
class PageInfo:
    """Information about a page we analyzed"""
    filename: str
    file_size: int
    content_types_found: List[str]
    total_components: int
    analyzed_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for saving"""
        return {
            "page_name": self.filename,
            "file_size": self.file_size,
            "detected_components": self.content_types_found,
            "total_components": self.total_components,
            "analyzed_at": self.analyzed_at.isoformat()
        }


@dataclass
class MigrationResults:
    """Results of our migration process"""
    time_taken: float
    schemas_created: int
    content_extracted: int
    output_files: Dict[str, str]
    
    def summary(self) -> str:
        """Get a nice summary of what we accomplished"""
        return (
            f"Migration completed in {self.time_taken:.1f} seconds\n"
            f"• Created {self.schemas_created} content schemas\n"
            f"• Extracted {self.content_extracted} content pieces"
        )