"""
Car data model for consistent representation across different sources
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Car:
    """Represents a car listing from any source"""
    
    # Basic car information
    brand: str
    model: str
    year: Optional[int] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    kilometers: Optional[int] = None
    
    # Technical specifications
    engine_type: Optional[str] = None
    engine_displacement: Optional[str] = None
    engine_power: Optional[str] = None
    gearbox_type: Optional[str] = None
    
    # Additional details
    color: Optional[str] = None
    
    # Location and contact
    location: Optional[str] = None
    dealer_name: Optional[str] = None
    
    # Metadata
    source_site: Optional[str] = None
    listing_url: Optional[str] = None
    image_urls: Optional[list] = None
    description: Optional[str] = None
    created_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Car object to a dictionary for JSON serialization"""
        return {
            'brand': self.brand,
            'model': self.model,
            'year': self.year,
            'price': self.price,
            'currency': self.currency,
            'kilometers': self.kilometers,
            'engine_type': self.engine_type,
            'engine_displacement': self.engine_displacement,
            'engine_power': self.engine_power,
            'gearbox_type': self.gearbox_type,
            'color': self.color,
            'location': self.location,
            'dealer_name': self.dealer_name,
            'source_site': self.source_site,
            'listing_url': self.listing_url,
            'image_urls': self.image_urls or [],
            'description': self.description,
            'created_date': self.created_date
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Car':
        """Create a Car object from a dictionary"""
        return cls(**data)
