"""
Google Maps API Service for Accurate Distance and Location Data
Provides real-world distance calculations and city names
"""

import os
import logging
import requests
import time
from typing import Dict, Any, Optional, List, Tuple
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class GoogleMapsService:
    """Google Maps API service for logistics optimization"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        self.base_url = "https://maps.googleapis.com/maps/api"
        self.timeout = getattr(settings, 'GOOGLE_MAPS_TIMEOUT', 5)
        self.max_retries = getattr(settings, 'GOOGLE_MAPS_MAX_RETRIES', 3)
        
        if not self.api_key:
            logger.warning("⚠️ Google Maps API key not configured. Using fallback calculations.")
    
    def get_city_name_from_coordinates(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get real city name and address from coordinates using Reverse Geocoding"""
        
        if not self.api_key:
            return self._get_fallback_city_info(latitude, longitude)
        
        try:
            url = f"{self.base_url}/geocode/json"
            params = {
                'latlng': f"{latitude},{longitude}",
                'key': self.api_key,
                'language': 'en'
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                address_components = result['address_components']
                
                # Extract city, state, and country information
                city_info = self._extract_address_components(address_components)
                
                return {
                    'city': city_info.get('city', 'Unknown City'),
                    'state': city_info.get('state', 'Unknown State'),
                    'country': city_info.get('country', 'India'),
                    'full_address': result['formatted_address'],
                    'place_id': result['place_id'],
                    'coordinates': {'latitude': latitude, 'longitude': longitude}
                }
            else:
                logger.warning(f"⚠️ Google Geocoding failed: {data.get('status', 'Unknown')}")
                return self._get_fallback_city_info(latitude, longitude)
                
        except Exception as e:
            logger.error(f"❌ Google Geocoding error: {e}")
            return self._get_fallback_city_info(latitude, longitude)
    
    def get_distance_matrix(self, origins: List[Tuple[float, float]], 
                           destinations: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Get accurate distance and travel time using Distance Matrix API"""
        
        if not self.api_key:
            return self._get_fallback_distance_matrix(origins, destinations)
        
        try:
            # Format coordinates for API
            origins_str = '|'.join([f"{lat},{lng}" for lat, lng in origins])
            destinations_str = '|'.join([f"{lat},{lng}" for lat, lng in destinations])
            
            url = f"{self.base_url}/distancematrix/json"
            params = {
                'origins': origins_str,
                'destinations': destinations_str,
                'mode': 'driving',  # Road transport
                'units': 'metric',   # Kilometers
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK':
                return self._parse_distance_matrix_response(data, origins, destinations)
            else:
                logger.warning(f"⚠️ Google Distance Matrix failed: {data.get('status', 'Unknown')}")
                return self._get_fallback_distance_matrix(origins, destinations)
                
        except Exception as e:
            logger.error(f"❌ Google Distance Matrix error: {e}")
            return self._get_fallback_distance_matrix(origins, destinations)
    
    def get_optimal_route(self, waypoints: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Get optimal route between multiple waypoints"""
        
        if not self.api_key:
            return self._get_fallback_route(waypoints)
        
        try:
            # Format waypoints for Directions API
            waypoints_str = '|'.join([f"{lat},{lng}" for lat, lng in waypoints])
            
            url = f"{self.base_url}/directions/json"
            params = {
                'origin': waypoints_str.split('|')[0],
                'destination': waypoints_str.split('|')[-1],
                'waypoints': '|'.join(waypoints_str.split('|')[1:-1]) if len(waypoints) > 2 else '',
                'mode': 'driving',
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['routes']:
                route = data['routes'][0]
                return self._parse_route_response(route, waypoints)
            else:
                logger.warning(f"⚠️ Google Directions failed: {data.get('status', 'Unknown')}")
                return self._get_fallback_route(waypoints)
                
        except Exception as e:
            logger.error(f"❌ Google Directions error: {e}")
            return self._get_fallback_route(waypoints)
    
    def _extract_address_components(self, address_components: List[Dict]) -> Dict[str, str]:
        """Extract city, state, and country from address components"""
        
        city_info = {}
        
        for component in address_components:
            types = component['types']
            
            if 'locality' in types or 'administrative_area_level_2' in types:
                city_info['city'] = component['long_name']
            elif 'administrative_area_level_1' in types:
                city_info['state'] = component['long_name']
            elif 'country' in types:
                city_info['country'] = component['long_name']
        
        return city_info
    
    def _parse_distance_matrix_response(self, data: Dict, origins: List, destinations: List) -> Dict[str, Any]:
        """Parse Google Distance Matrix API response"""
        
        try:
            rows = data['rows']
            results = {
                'distances': [],
                'durations': [],
                'total_distance_km': 0,
                'total_duration_minutes': 0,
                'api_used': 'Google Maps'
            }
            
            for i, row in enumerate(rows):
                elements = row['elements']
                for j, element in enumerate(elements):
                    if element['status'] == 'OK':
                        distance = element['distance']['value'] / 1000  # Convert meters to km
                        duration = element['duration']['value'] / 60    # Convert seconds to minutes
                        
                        results['distances'].append({
                            'from': origins[i],
                            'to': destinations[j],
                            'distance_km': round(distance, 2),
                            'duration_minutes': round(duration, 1)
                        })
                        
                        results['total_distance_km'] += distance
                        results['total_duration_minutes'] += duration
            
            results['total_distance_km'] = round(results['total_distance_km'], 2)
            results['total_duration_minutes'] = round(results['total_duration_minutes'], 1)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error parsing distance matrix: {e}")
            return self._get_fallback_distance_matrix(origins, destinations)
    
    def _parse_route_response(self, route: Dict, waypoints: List) -> Dict[str, Any]:
        """Parse Google Directions API response"""
        
        try:
            legs = route['legs']
            total_distance = sum(leg['distance']['value'] for leg in legs) / 1000  # Convert to km
            total_duration = sum(leg['duration']['value'] for leg in legs) / 60    # Convert to minutes
            
            return {
                'total_distance_km': round(total_distance, 2),
                'total_duration_minutes': round(total_duration, 1),
                'waypoints': waypoints,
                'route_polyline': route.get('overview_polyline', {}).get('points', ''),
                'api_used': 'Google Maps'
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing route response: {e}")
            return self._get_fallback_route(waypoints)
    
    def _get_fallback_city_info(self, latitude, longitude):
        """Enhanced fallback city detection using coordinate ranges and pincode data"""
        try:
            # First try to find a nearby pincode for more accurate city names
            from locations.models import PinCode
            
            # Search for pincodes within a reasonable range (0.1 degrees ≈ 11 km)
            nearby_pincodes = PinCode.objects.filter(
                latitude__range=(latitude - 0.1, latitude + 0.1),
                longitude__range=(longitude - 0.1, longitude + 0.1)
            ).order_by('code')[:5]
            
            if nearby_pincodes.exists():
                # Use the closest pincode for city/state names
                closest_pincode = nearby_pincodes.first()
                return {
                    'city': closest_pincode.district,
                    'state': closest_pincode.state,
                    'country': 'India',
                    'full_address': f"{closest_pincode.district}, {closest_pincode.state}, India",
                    'place_id': None,
                    'coordinates': {'latitude': latitude, 'longitude': longitude},
                    'fallback': True,
                    'source': 'Pincode Database'
                }
            
            # If no pincode found, use coordinate-based detection
            # Enhanced coordinate ranges for major Indian cities
            if 16.0 <= latitude <= 17.0 and 80.0 <= longitude <= 81.0:
                return {
                    'city': 'Vijayawada',
                    'state': 'Andhra Pradesh',
                    'country': 'India',
                    'full_address': 'Vijayawada, Andhra Pradesh, India',
                    'place_id': None,
                    'coordinates': {'latitude': latitude, 'longitude': longitude},
                    'fallback': True,
                    'source': 'Coordinate Detection'
                }
            elif 16.0 <= latitude <= 17.0 and 81.0 <= longitude <= 82.0:
                return {
                    'city': 'Rajahmundry',
                    'state': 'Andhra Pradesh',
                    'country': 'India',
                    'full_address': 'Rajahmundry, Andhra Pradesh, India',
                    'place_id': None,
                    'coordinates': {'latitude': latitude, 'longitude': longitude},
                    'fallback': True,
                    'source': 'Coordinate Detection'
                }
            elif 17.0 <= latitude <= 18.0 and 78.0 <= longitude <= 79.0:
                return {
                    'city': 'Hyderabad',
                    'state': 'Telangana',
                    'country': 'India',
                    'full_address': 'Hyderabad, Telangana, India',
                    'place_id': None,
                    'coordinates': {'latitude': latitude, 'longitude': longitude},
                    'fallback': True,
                    'source': 'Coordinate Detection'
                }
            elif 19.0 <= latitude <= 20.0 and 72.0 <= longitude <= 73.0:
                return {
                    'city': 'Mumbai',
                    'state': 'Maharashtra',
                    'country': 'India',
                    'full_address': 'Mumbai, Maharashtra, India',
                    'place_id': None,
                    'coordinates': {'latitude': latitude, 'longitude': longitude},
                    'fallback': True,
                    'source': 'Coordinate Detection'
                }
            elif 28.0 <= latitude <= 29.0 and 76.0 <= longitude <= 77.0:
                return {
                    'city': 'Delhi',
                    'state': 'Delhi',
                    'country': 'India',
                    'full_address': 'Delhi, Delhi, India',
                    'place_id': None,
                    'coordinates': {'latitude': latitude, 'longitude': longitude},
                    'fallback': True,
                    'source': 'Coordinate Detection'
                }
            elif 13.0 <= latitude <= 14.0 and 80.0 <= longitude <= 81.0:
                return {
                    'city': 'Chennai',
                    'state': 'Tamil Nadu',
                    'country': 'India',
                    'full_address': 'Chennai, Tamil Nadu, India',
                    'place_id': None,
                    'coordinates': {'latitude': latitude, 'longitude': longitude},
                    'fallback': True,
                    'source': 'Coordinate Detection'
                }
            else:
                # Generic fallback for other coordinates
                return {
                    'city': 'Central Location',
                    'state': 'Central Region',
                    'country': 'India',
                    'full_address': 'Central Location, Central Region, India',
                    'place_id': None,
                    'coordinates': {'latitude': latitude, 'longitude': longitude},
                    'fallback': True,
                    'source': 'Generic Fallback'
                }
                
        except Exception as e:
            print(f"⚠️ Error in fallback city detection: {e}")
            # Ultimate fallback
            return {
                'city': 'Central Location',
                'state': 'Central Region',
                'country': 'India',
                'full_address': 'Central Location, Central Region, India',
                'place_id': None,
                'coordinates': {'latitude': latitude, 'longitude': longitude},
                'fallback': True,
                'source': 'Error Fallback'
            }
    
    def _get_fallback_distance_matrix(self, origins: List, destinations: List) -> Dict[str, Any]:
        """Fallback distance calculation using Haversine formula with realistic estimates"""
        
        from .hub_optimizer import HubOptimizer
        
        hub_optimizer = HubOptimizer()
        total_distance = 0
        distances = []
        durations = []
        
        for origin in origins:
            for destination in destinations:
                distance = hub_optimizer._haversine_distance(
                    origin[0], origin[1], destination[0], destination[1]
                )
                total_distance += distance
                
                # Store individual distances
                distances.append({
                    'from': origin,
                    'to': destination,
                    'distance_km': round(distance, 2),
                    'duration_minutes': round(distance * 2.5, 1)  # Realistic: 2.5 min per km for rural roads
                })
        
        # Calculate realistic travel time based on road conditions
        # Rural roads: 20-30 km/h average, urban: 15-25 km/h average
        avg_speed_kmh = 25  # Conservative estimate for mixed road conditions
        total_time = (total_distance / avg_speed_kmh) * 60  # Convert to minutes
        
        return {
            'distances': distances,
            'durations': durations,
            'total_distance_km': round(total_distance, 2),
            'total_duration_minutes': round(total_time, 1),
            'api_used': 'Haversine Fallback (Enhanced)',
            'speed_assumption': f'{avg_speed_kmh} km/h average',
            'road_conditions': 'Mixed rural/urban roads'
        }
    
    def _get_fallback_route(self, waypoints: List) -> Dict[str, Any]:
        """Fallback route calculation with realistic travel time estimates"""
        
        from .hub_optimizer import HubOptimizer
        
        hub_optimizer = HubOptimizer()
        total_distance = 0
        
        for i in range(len(waypoints) - 1):
            distance = hub_optimizer._haversine_distance(
                waypoints[i][0], waypoints[i+1][0],
                waypoints[i][1], waypoints[i+1][1]
            )
            total_distance += distance
        
        # Calculate realistic travel time based on road conditions
        # Rural roads: 20-30 km/h average, urban: 15-25 km/h average
        # Add 10% buffer for stops, traffic, and road conditions
        avg_speed_kmh = 25  # Conservative estimate for mixed road conditions
        total_time = (total_distance / avg_speed_kmh) * 60 * 1.1  # Convert to minutes with buffer
        
        return {
            'total_distance_km': round(total_distance, 2),
            'total_duration_minutes': round(total_time, 1),
            'waypoints': waypoints,
            'route_polyline': '',
            'api_used': 'Haversine Fallback (Enhanced)',
            'speed_assumption': f'{avg_speed_kmh} km/h average',
            'road_conditions': 'Mixed rural/urban roads',
            'buffer_factor': '10% added for stops and road conditions'
        }
    
    def is_api_available(self) -> bool:
        """Check if Google Maps API is available"""
        return self.api_key is not None
