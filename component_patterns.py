import json
from typing import Dict, List, Any
from collections import defaultdict


class ComponentPatternDetector:
    
    def __init__(self):
        self.patterns = defaultdict(list)  # pattern_type -> [instances]
        self.component_signatures = {}     # signature -> pattern_info
    
    def detect_patterns(self, all_results: List[Dict]) -> Dict[str, Any]:
        """Analyze all classification results to find reusable patterns"""
        
        # Group by component type first
        by_type = defaultdict(list)
        for result in all_results:
            by_type[result['content_type']].append(result)
        
        reusable_patterns = {}
        
        for content_type, instances in by_type.items():
            if len(instances) >= 2:  # Must appear in multiple places to be reusable
                pattern = self._analyze_pattern(content_type, instances)
                if pattern['reusability_score'] >= 0.7:
                    reusable_patterns[content_type] = pattern
        
        return reusable_patterns
    
    def _analyze_pattern(self, content_type: str, instances: List[Dict]) -> Dict[str, Any]:
        
        # Extract field patterns
        all_fields = []
        field_variations = defaultdict(set)
        
        for instance in instances:
            fields = instance.get('fields', {})
            all_fields.append(set(fields.keys()))
            
            for field, value in fields.items():
                field_variations[field].add(type(value).__name__)
        
        # Find common fields (appear in 70%+ of instances)
        common_fields = set()
        threshold = len(instances) * 0.7
        
        for field in field_variations:
            count = sum(1 for field_set in all_fields if field in field_set)
            if count >= threshold:
                common_fields.add(field)
        
        # Determine component template
        template = self._create_component_template(content_type, instances, common_fields)
        
        # Calculate reusability score
        reusability_score = self._calculate_reusability(instances, common_fields)
        
        return {
            'content_type': content_type,
            'instances_count': len(instances),
            'common_fields': list(common_fields),
            'field_variations': {k: list(v) for k, v in field_variations.items()},
            'template': template,
            'reusability_score': reusability_score,
            'usage_contexts': [inst.get('source_file', 'unknown') for inst in instances]
        }
    
    def _create_component_template(self, content_type: str, instances: List[Dict], common_fields: set) -> Dict[str, Any]:
        
        template = {
            'component_name': self._generate_component_name(content_type, instances),
            'description': self._generate_description(content_type, instances),
            'fields': {},
            'variants': self._detect_variants(instances)
        }
        
        # Define field schema for common fields
        for field in common_fields:
            field_info = self._analyze_field_pattern(field, instances)
            template['fields'][field] = field_info
        
        return template
    
    def _generate_component_name(self, content_type: str, instances: List[Dict]) -> str:
        sample_fields = instances[0].get('fields', {})
        
        if 'links' in sample_fields and len(sample_fields.get('links', [])) > 5:
            return f"{content_type}_menu_component"
        elif 'price' in sample_fields or 'cost' in str(sample_fields).lower():
            return f"{content_type}_pricing_component"
        elif 'image' in sample_fields or 'photo' in str(sample_fields).lower():
            return f"{content_type}_media_component"
        else:
            return f"{content_type}_content_component"
    
    def _generate_description(self, content_type: str, instances: List[Dict]) -> str:
        """Generate component description based on usage patterns"""
        
        usage_files = set(inst.get('source_file', '') for inst in instances)
        common_fields = set()
        for inst in instances:
            common_fields.update(inst.get('fields', {}).keys())
        
        return f"Reusable {content_type} component used across {len(usage_files)} pages. Contains {', '.join(list(common_fields)[:3])} and appears in contexts like {list(usage_files)[:2]}."
    
    def _detect_variants(self, instances: List[Dict]) -> List[Dict[str, Any]]:
        """Detect component variants (different configurations)"""
        
        variants = []
        
        # Group by field structure similarity
        structure_groups = defaultdict(list)
        for instance in instances:
            # Create signature based on field names and types
            fields = instance.get('fields', {})
            signature = tuple(sorted([
                f"{k}:{type(v).__name__}:{len(str(v)) if isinstance(v, (str, list)) else 'other'}"
                for k, v in fields.items()
            ]))
            structure_groups[signature].append(instance)
        
        for signature, group in structure_groups.items():
            if len(group) >= 2:  # Variant must appear multiple times
                variant = {
                    'variant_name': f"variant_{len(variants) + 1}",
                    'instances': len(group),
                    'distinguishing_features': self._find_distinguishing_features(group),
                    'usage_context': [inst.get('source_file', '') for inst in group[:3]]
                }
                variants.append(variant)
        
        return variants
    
    def _find_distinguishing_features(self, instances: List[Dict]) -> List[str]:
        """Find what makes this variant unique"""
        
        features = []
        sample = instances[0].get('fields', {})
        
        # Check for distinguishing characteristics
        if 'links' in sample:
            avg_links = sum(len(inst.get('fields', {}).get('links', [])) for inst in instances) / len(instances)
            if avg_links > 10:
                features.append("large_navigation_menu")
            elif avg_links < 3:
                features.append("minimal_links")
        
        if any('price' in str(inst.get('fields', {})).lower() for inst in instances):
            features.append("includes_pricing")
        
        if any('image' in inst.get('fields', {}) for inst in instances):
            features.append("media_rich")
        
        return features or ["standard_variant"]
    
    def _analyze_field_pattern(self, field_name: str, instances: List[Dict]) -> Dict[str, Any]:
        """Analyze how a field is used across instances"""
        
        field_values = []
        for instance in instances:
            value = instance.get('fields', {}).get(field_name)
            if value:
                field_values.append(value)
        
        # Determine field characteristics
        field_info = {
            'field_name': field_name,
            'required': len(field_values) >= len(instances) * 0.8,  # 80%+ have this field
            'data_type': self._determine_data_type(field_values),
            'typical_length': self._get_typical_length(field_values),
            'is_variable': self._is_highly_variable(field_values)
        }
        
        # Add field-specific analysis
        if field_name in ['links', 'menu_items', 'navigation']:
            field_info['component_type'] = 'navigation'
            field_info['average_items'] = sum(len(v) if isinstance(v, list) else 1 for v in field_values) / len(field_values)
        elif field_name in ['title', 'heading', 'name']:
            field_info['component_type'] = 'heading'
            field_info['is_unique_content'] = self._is_highly_variable(field_values)
        elif field_name in ['description', 'content', 'body']:
            field_info['component_type'] = 'rich_text'
            field_info['is_content_heavy'] = any(len(str(v)) > 200 for v in field_values)
        
        return field_info
    
    def _determine_data_type(self, values: List[Any]) -> str:
        """Determine the most common data type"""
        types = [type(v).__name__ for v in values if v]
        return max(set(types), key=types.count) if types else 'str'
    
    def _get_typical_length(self, values: List[Any]) -> int:
        """Get typical content length"""
        lengths = [len(str(v)) for v in values if v]
        return sum(lengths) // len(lengths) if lengths else 0
    
    def _is_highly_variable(self, values: List[Any]) -> bool:
        """Check if field values vary significantly (indicating dynamic content)"""
        if len(values) < 2:
            return False
        
        unique_values = len(set(str(v) for v in values))
        return unique_values / len(values) > 0.7  # 70%+ unique values
    
    def _calculate_reusability(self, instances: List[Dict], common_fields: set) -> float:
        """Calculate how reusable this component pattern is"""
        
        score = 0.0
        
        # More instances = more reusable
        if len(instances) >= 5:
            score += 0.3
        elif len(instances) >= 3:
            score += 0.2
        elif len(instances) >= 2:
            score += 0.1
        
        # Common field structure = more reusable
        total_fields = sum(len(inst.get('fields', {})) for inst in instances) / len(instances)
        if total_fields > 0:
            common_ratio = len(common_fields) / total_fields
            score += common_ratio * 0.4
        
        # Used across different pages = more reusable
        unique_files = len(set(inst.get('source_file', '') for inst in instances))
        if unique_files >= 3:
            score += 0.3
        elif unique_files >= 2:
            score += 0.2
        
        return min(score, 1.0)