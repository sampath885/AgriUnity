"""
Hub Optimizer - Enhanced Version with Google Maps Integration
Provides accurate distance calculations and real city names
"""

import logging
import math
from typing import Dict, Any, Optional, List
from django.db.models import Sum

logger = logging.getLogger(__name__)

class HubOptimizer:
    """Enhanced hub optimization with Google Maps integration"""
    
    def __init__(self):
        logger.info("✅ HubOptimizer initialized successfully")
        self.google_maps_service = None
        self._initialize_google_maps()
    
    def _initialize_google_maps(self):
        """Initialize Google Maps service if available"""
        try:
            from .google_maps_service import GoogleMapsService
            self.google_maps_service = GoogleMapsService()
            if self.google_maps_service.is_api_available():
                logger.info("✅ Google Maps API service initialized")
            else:
                logger.info("ℹ️ Google Maps API not available, using fallback calculations")
        except ImportError:
            logger.warning("⚠️ Google Maps service not available, using fallback calculations")
            self.google_maps_service = None
    
    def compute_and_recommend_hub(self, deal_group) -> Optional[Dict[str, Any]]:
        """Compute optimal collection hub using enhanced calculations"""
        
        try:
            logger.info(f"🔍 Computing hub for deal group: {deal_group.group_id}")
            
            # Get all farmers in the deal group
            farmers = []
            for product in deal_group.products.all():
                farmer = product.farmer
                if hasattr(farmer, 'latitude') and hasattr(farmer, 'longitude'):
                    if farmer.latitude and farmer.longitude:
                        farmers.append({
                            'id': farmer.id,
                            'name': farmer.name,
                            'latitude': float(farmer.latitude),
                            'longitude': float(farmer.longitude),
                            'quantity': product.quantity_kg
                        })
            
            if not farmers:
                logger.warning("⚠️ No farmers with valid coordinates found")
                return self._get_default_hub()
            
            logger.info(f"✅ Found {len(farmers)} farmers with valid coordinates")
            
            # Calculate optimal hub (centroid of all farmers)
            optimal_hub = self._calculate_centroid_hub(farmers)
            
            if optimal_hub:
                logger.info(f"✅ Optimal hub calculated: {optimal_hub['name']}")
                return optimal_hub
            else:
                logger.warning("⚠️ Failed to calculate optimal hub, using default")
                return self._get_default_hub()
            
        except Exception as e:
            logger.error(f"❌ Hub computation failed: {e}")
            return self._get_default_hub()
    
    def get_hub_details(self, deal_group) -> Dict[str, Any]:
        """Get comprehensive hub details with accurate distances"""
        
        try:
            optimal_hub = self.compute_and_recommend_hub(deal_group)
            
            if not optimal_hub:
                return self._get_error_hub_details()
            
            # Get accurate distance and transport cost estimates
            distance_info = self._get_accurate_distance_info(deal_group, optimal_hub)
            transport_cost = self._calculate_transport_cost(distance_info['total_distance_km'], deal_group.total_quantity_kg)
            
            return {
                'optimal_hub': optimal_hub.get('name', 'Optimal Collection Hub'),
                'hub_location': f"{optimal_hub.get('city', 'Central Location')}, {optimal_hub.get('state', 'Central Region')}",
                'total_distance_km': distance_info['total_distance_km'],
                'estimated_transport_cost': f"₹{transport_cost:.2f}",
                'hub_partner': optimal_hub.get('name', 'Central Hub'),
                'logistics_efficiency': self._calculate_efficiency_score(distance_info['total_distance_km']),
                'coordinates': {
                    'latitude': optimal_hub.get('latitude', 0.0),
                    'longitude': optimal_hub.get('longitude', 0.0)
                },
                'farmer_count': deal_group.products.count(),
                'total_quantity': deal_group.total_quantity_kg,
                'distance_api_used': distance_info.get('api_used', 'Haversine'),
                'travel_time_minutes': distance_info.get('total_duration_minutes', 0),
                'real_city_name': optimal_hub.get('city', 'Unknown'),
                'real_state_name': optimal_hub.get('state', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"❌ Hub details retrieval failed: {e}")
            return self._get_error_hub_details()
    
    def _get_accurate_distance_info(self, deal_group, hub_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get accurate distance information using Google Maps or fallback"""
        
        try:
            hub_coords = (hub_info.get('latitude', 0.0), hub_info.get('longitude', 0.0))
            
            if hub_coords[0] == 0.0 or hub_coords[1] == 0.0:
                return {'total_distance_km': 50.0, 'total_duration_minutes': 100, 'api_used': 'Default'}
            
            # Get all farmer coordinates
            farmer_coords = []
            for product in deal_group.products.all():
                farmer = product.farmer
                if hasattr(farmer, 'latitude') and hasattr(farmer, 'longitude'):
                    if farmer.latitude and farmer.longitude:
                        farmer_coords.append((float(farmer.latitude), float(farmer.longitude)))
            
            if not farmer_coords:
                return {'total_distance_km': 50.0, 'total_duration_minutes': 100, 'api_used': 'Default'}
            
            # Use Google Maps API if available, otherwise fallback
            if self.google_maps_service and self.google_maps_service.is_api_available():
                logger.info("🚀 Using Google Maps API for accurate distance calculation")
                
                # Get distance matrix from all farmers to hub
                distance_matrix = self.google_maps_service.get_distance_matrix(
                    origins=farmer_coords,
                    destinations=[hub_coords]
                )
                
                return {
                    'total_distance_km': distance_matrix['total_distance_km'],
                    'total_duration_minutes': distance_matrix['total_duration_minutes'],
                    'api_used': distance_matrix['api_used'],
                    'detailed_distances': distance_matrix.get('distances', [])
                }
            else:
                logger.info("ℹ️ Using Haversine formula for distance calculation")
                return self._calculate_fallback_distances(farmer_coords, hub_coords)
                
        except Exception as e:
            logger.error(f"❌ Distance calculation failed: {e}")
            return {'total_distance_km': 50.0, 'total_duration_minutes': 100, 'api_used': 'Error Fallback'}
    
    def _calculate_fallback_distances(self, farmer_coords: List, hub_coords: tuple) -> Dict[str, Any]:
        """Calculate distances using Haversine formula as fallback"""
        
        total_distance = 0
        for farmer_coord in farmer_coords:
            distance = self._haversine_distance(
                farmer_coord[0], farmer_coord[1],
                hub_coords[0], hub_coords[1]
            )
            total_distance += distance
        
        return {
            'total_distance_km': round(total_distance, 2),
            'total_duration_minutes': round(total_distance * 2, 1),  # Rough estimate: 2 min per km
            'api_used': 'Haversine Fallback'
        }
    
    def _calculate_centroid_hub(self, farmers: List[Dict]) -> Optional[Dict[str, Any]]:
        """Calculate centroid hub from all farmers with real city names"""
        try:
            if not farmers:
                return None
            
            # Calculate weighted centroid based on quantity
            total_quantity = sum(f['quantity'] for f in farmers)
            if total_quantity == 0:
                total_quantity = 1  # Prevent division by zero
            
            weighted_lat = sum(f['latitude'] * f['quantity'] for f in farmers) / total_quantity
            weighted_lon = sum(f['longitude'] * f['quantity'] for f in farmers) / total_quantity
            
            # Get real city name from coordinates
            city_info = self._get_real_city_info(weighted_lat, weighted_lon)
            
            # Find the farmer closest to the centroid
            closest_farmer = min(farmers, key=lambda f: self._haversine_distance(
                weighted_lat, weighted_lon, f['latitude'], f['longitude']
            ))
            
            return {
                'name': f"Central Hub near {city_info['city']}",
                'address': f"Optimal collection point in {city_info['city']}",
                'latitude': weighted_lat,
                'longitude': weighted_lon,
                'city': city_info['city'],
                'state': city_info['state'],
                'country': city_info['country'],
                'full_address': city_info['full_address'],
                'place_id': city_info.get('place_id'),
                'is_real_location': not city_info.get('fallback', False)
            }
            
        except Exception as e:
            logger.error(f"❌ Centroid calculation failed: {e}")
            return None
    
    def _get_real_city_info(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get real city information from coordinates"""
        
        if self.google_maps_service and self.google_maps_service.is_api_available():
            try:
                logger.info(f"🌍 Getting real city name for coordinates: {latitude}, {longitude}")
                city_info = self.google_maps_service.get_city_name_from_coordinates(latitude, longitude)
                logger.info(f"✅ Real city found: {city_info['city']}, {city_info['state']}")
                return city_info
            except Exception as e:
                logger.error(f"❌ Google Maps city lookup failed: {e}")
                return self._get_fallback_city_info(latitude, longitude)
        else:
            return self._get_fallback_city_info(latitude, longitude)
    
    def _get_fallback_city_info(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fallback city information when Google API is not available"""
        
        # Enhanced coordinate-based city detection for India
        if 17.0 <= latitude <= 18.0 and 78.0 <= longitude <= 79.0:
            city = "Hyderabad"
            state = "Telangana"
        elif 16.0 <= latitude <= 17.0 and 80.0 <= longitude <= 81.0:
            # More specific check for Guntur vs Vijayawada
            if latitude < 16.4:
                city = "Guntur"
                state = "Andhra Pradesh"
            else:
                city = "Vijayawada"
                state = "Andhra Pradesh"
        elif 19.0 <= latitude <= 20.0 and 72.0 <= longitude <= 73.0:
            city = "Mumbai"
            state = "Maharashtra"
        elif 28.0 <= latitude <= 29.0 and 76.0 <= longitude <= 77.0:
            city = "Delhi"
            state = "Delhi"
        elif 12.0 <= latitude <= 13.0 and 77.0 <= longitude <= 78.0:
            city = "Bangalore"
            state = "Karnataka"
        elif 13.0 <= latitude <= 14.0 and 80.0 <= longitude <= 81.0:
            city = "Chennai"
            state = "Tamil Nadu"
        elif 22.0 <= latitude <= 23.0 and 88.0 <= longitude <= 89.0:
            city = "Kolkata"
            state = "West Bengal"
        elif 16.0 <= latitude <= 17.0 and 80.0 <= longitude <= 81.0:
            # More specific check for Guntur vs Vijayawada
            if latitude < 16.4:
                city = "Guntur"
                state = "Andhra Pradesh"
            else:
                city = "Vijayawada"
                state = "Andhra Pradesh"
        else:
            city = "Central India"
            state = "Central Region"
        
            return {
            'city': city,
            'state': state,
            'country': 'India',
            'full_address': f"{city}, {state}, India",
            'place_id': None,
            'coordinates': {'latitude': latitude, 'longitude': longitude},
            'fallback': True
            }
    
    def _estimate_total_distance(self, deal_group, hub_info: Dict[str, Any]) -> float:
        """Estimate total distance from farmers to hub (legacy method)"""
        try:
            hub_lat = hub_info.get('latitude', 0.0)
            hub_lon = hub_info.get('longitude', 0.0)
            
            if hub_lat == 0.0 or hub_lon == 0.0:
                return 50.0  # Default distance
            
            total_distance = 0.0
            farmer_count = 0
            
            for product in deal_group.products.all():
                farmer = product.farmer
                farmer_lat = getattr(farmer, 'latitude', None)
                farmer_lon = getattr(farmer, 'longitude', None)
                
                if farmer_lat and farmer_lon:
                    distance = self._haversine_distance(hub_lat, hub_lon, farmer_lat, farmer_lon)
                    total_distance += distance
                    farmer_count += 1
            
            if farmer_count == 0:
                return 50.0  # Default distance
            
            return total_distance / farmer_count  # Average distance
            
        except Exception as e:
            logger.error(f"❌ Distance estimation failed: {e}")
            return 50.0  # Default distance
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        try:
            # Convert to radians
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            # Haversine formula
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Earth's radius in kilometers
            r = 6371
            
            return r * c
            
        except Exception as e:
            logger.error(f"❌ Haversine calculation failed: {e}")
            return 50.0  # Default distance
    
    def _calculate_transport_cost(self, distance_km: float, quantity_kg: float) -> float:
        """Calculate transport cost based on distance and quantity"""
        base_rate = 0.15  # ₹0.15 per km per kg
        fuel_surcharge = 1.1  # 10% fuel surcharge
        
        if distance_km > 100:
            distance_multiplier = 1.2  # 20% increase for long distance
        elif distance_km > 50:
            distance_multiplier = 1.1  # 10% increase for medium distance
        else:
            distance_multiplier = 1.0
        
        return distance_km * quantity_kg * base_rate * fuel_surcharge * distance_multiplier
    
    def _calculate_efficiency_score(self, distance_km: float) -> str:
        """Calculate logistics efficiency score"""
        if distance_km <= 25:
            return "Excellent - Very efficient"
        elif distance_km <= 50:
            return "Good - Efficient"
        elif distance_km <= 100:
            return "Moderate - Acceptable"
        else:
            return "Low - Needs optimization"
    
    def _get_default_hub(self) -> Dict[str, Any]:
        """Get default hub when calculation fails"""
        return {
            'name': 'Central Collection Hub',
            'address': 'Optimal central location',
            'latitude': 17.3850,  # Hyderabad coordinates (better default)
            'longitude': 78.4867,
            'city': 'Hyderabad',
            'state': 'Telangana',
            'country': 'India',
            'full_address': 'Hyderabad, Telangana, India',
            'place_id': None,
            'is_real_location': False
        }
    
    def _get_error_hub_details(self) -> Dict[str, Any]:
        """Get error hub details when calculation fails"""
        return {
            'optimal_hub': 'Error calculating',
            'hub_location': 'Error calculating',
            'total_distance_km': 0,
            'estimated_transport_cost': 'Error calculating',
            'hub_partner': 'Error calculating',
            'logistics_efficiency': 'Error calculating',
            'coordinates': {'latitude': 17.3850, 'longitude': 78.4867},  # Hyderabad as fallback
            'farmer_count': 0,
            'total_quantity': 0,
            'distance_api_used': 'Error',
            'travel_time_minutes': 0,
            'real_city_name': 'Hyderabad',
            'real_state_name': 'Telangana'
        }
