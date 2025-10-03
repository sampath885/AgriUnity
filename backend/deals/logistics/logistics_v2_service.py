"""
Logistics V2 Service - Road Network Optimization

Phase 3 implementation with:
- Distance Matrix API integration (Google/OSRM)
- Road network-based hub selection
- Fallback to V1 if API fails
- Background job for refined recommendations
"""

import os
import logging
import requests
import time
from typing import Optional, Dict, Any, List, Tuple
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache


from ..models import DealGroup, GroupMessage
from hubs.models import HubPartner
from locations.models import PinCode
from users.models import CustomUser

logger = logging.getLogger(__name__)


class DistanceMatrixProvider:
    """Abstract base class for distance matrix providers."""
    
    def get_travel_times(self, origins: List[Tuple[float, float]], 
                         destinations: List[Tuple[float, float]]) -> Optional[List[List[int]]]:
        """Get travel times between origins and destinations in minutes."""
        raise NotImplementedError


class OSRMDistanceMatrixProvider(DistanceMatrixProvider):
    """Open Source Routing Machine (OSRM) distance matrix provider."""
    
    def __init__(self, base_url: str = "https://router.project-osrm.org"):
        self.base_url = base_url
        self.timeout = getattr(settings, 'OSRM_TIMEOUT', 3)
        self.max_retries = getattr(settings, 'OSRM_MAX_RETRIES', 2)
    
    def get_travel_times(self, origins: List[Tuple[float, float]], 
                         destinations: List[Tuple[float, float]]) -> Optional[List[List[int]]]:
        """Get travel times using OSRM API."""
        try:
            # Format coordinates for OSRM
            coords = []
            for lat, lon in origins + destinations:
                coords.append(f"{lon},{lat}")
            
            coords_str = ";".join(coords)
            url = f"{self.base_url}/table/v1/driving/{coords_str}"
            
            params = {
                'sources': ';'.join(str(i) for i in range(len(origins))),
                'destinations': ';'.join(str(i + len(origins)) for i in range(len(destinations))),
                'annotations': 'duration'
            }
            
            for attempt in range(self.max_retries):
                try:
                    response = requests.get(url, params=params, timeout=self.timeout)
                    response.raise_for_status()
                    
                    data = response.json()
                    if 'durations' in data:
                        # Convert seconds to minutes
                        durations = data['durations']
                        return [[int(duration / 60) if duration else None for duration in row] for row in durations]
                    
                except requests.RequestException as e:
                    if attempt == self.max_retries - 1:
                        logger.error(f"OSRM API failed after {self.max_retries} attempts: {e}")
                        return None
                    time.sleep(0.5)  # Brief delay before retry
            
            return None
            
        except Exception as e:
            logger.error(f"Error in OSRM distance matrix: {e}")
            return None


class GoogleDistanceMatrixProvider(DistanceMatrixProvider):
    """Google Maps Distance Matrix API provider."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        self.base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        self.timeout = getattr(settings, 'GOOGLE_MAPS_TIMEOUT', 3)
        self.max_retries = getattr(settings, 'GOOGLE_MAPS_MAX_RETRIES', 2)
        
        if not self.api_key:
            logger.warning("Google Maps API key not configured")
    
    def get_travel_times(self, origins: List[Tuple[float, float]], 
                         destinations: List[Tuple[float, float]]) -> Optional[List[List[int]]]:
        """Get travel times using Google Maps API."""
        if not self.api_key:
            return None
            
        try:
            # Google API has limits on request size, so we need to batch
            max_origins = 10
            max_destinations = 10
            
            if len(origins) > max_origins or len(destinations) > max_destinations:
                logger.warning(f"Request too large for Google API: {len(origins)} origins, {len(destinations)} destinations")
                return None
            
            # Format coordinates for Google API
            origins_str = "|".join(f"{lat},{lon}" for lat, lon in origins)
            destinations_str = "|".join(f"{lat},{lon}" for lat, lon in destinations)
            
            params = {
                'origins': origins_str,
                'destinations': destinations_str,
                'mode': 'driving',
                'key': self.api_key
            }
            
            for attempt in range(self.max_retries):
                try:
                    response = requests.get(self.base_url, params=params, timeout=self.timeout)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data.get('status') == 'OK':
                        # Extract travel times
                        rows = data.get('rows', [])
                        travel_times = []
                        
                        for row in rows:
                            elements = row.get('elements', [])
                            row_times = []
                            for element in elements:
                                if element.get('status') == 'OK':
                                    # Duration is in seconds, convert to minutes
                                    duration = element.get('duration', {}).get('value', 0)
                                    row_times.append(int(duration / 60))
                                else:
                                    row_times.append(None)
                            travel_times.append(row_times)
                        
                        return travel_times
                    
                    elif data.get('status') == 'OVER_QUERY_LIMIT':
                        logger.warning("Google Maps API quota exceeded")
                        return None
                    else:
                        logger.error(f"Google Maps API error: {data.get('status')}")
                        return None
                        
                except requests.RequestException as e:
                    if attempt == self.max_retries - 1:
                        logger.error(f"Google Maps API failed after {self.max_retries} attempts: {e}")
                        return None
                    time.sleep(0.5)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Google Maps distance matrix: {e}")
            return None


class LogisticsV2Service:
    """Phase 3 Logistics V2 service with road network optimization."""
    
    def __init__(self):
        # Initialize providers with fallback order
        self.providers = []
        
        # Try Google Maps first (more accurate)
        google_provider = GoogleDistanceMatrixProvider()
        if google_provider.api_key:
            self.providers.append(google_provider)
        
        # OSRM as fallback (free, open source)
        self.providers.append(OSRMDistanceMatrixProvider())
        
        logger.info(f"Initialized Logistics V2 with {len(self.providers)} providers")
    
    def find_optimal_hub_v2(self, deal_group: DealGroup) -> Optional[HubPartner]:
        """
        Find optimal hub using road network optimization.
        Falls back to V1 if all providers fail.
        """
        try:
            logger.info(f"Computing V2 hub recommendation for deal group {deal_group.id}")
            
            # Get farmer coordinates
            farmer_coords = self._get_farmer_coordinates(deal_group)
            if not farmer_coords:
                logger.warning("No farmer coordinates available, falling back to V1")
                return self._fallback_to_v1(deal_group)
            
            # Get candidate hubs (K nearest by Haversine)
            candidate_hubs = self._get_candidate_hubs(farmer_coords, k=5)
            if not candidate_hubs:
                logger.warning("No candidate hubs available, falling back to V1")
                return self._fallback_to_v1(deal_group)
            
            # Try to get road network data
            travel_times = self._get_travel_times(farmer_coords, candidate_hubs)
            
            if travel_times:
                # Use road network optimization
                optimal_hub = self._select_hub_by_travel_time(farmer_coords, candidate_hubs, travel_times)
                if optimal_hub:
                    logger.info(f"V2 hub selected using road network: {optimal_hub.name}")
                    self._save_hub_recommendation(deal_group, optimal_hub, method='V2')
                    return optimal_hub
            
            # Fallback to V1
            logger.info("Road network optimization failed, falling back to V1")
            return self._fallback_to_v1(deal_group)
            
        except Exception as e:
            logger.error(f"Error in V2 hub selection: {e}")
            return self._fallback_to_v1(deal_group)
    
    def _get_farmer_coordinates(self, deal_group: DealGroup) -> List[Tuple[float, float]]:
        """Get farmer coordinates with pincode fallback."""
        coordinates = []
        
        farmers = CustomUser.objects.filter(
            listings__in=deal_group.products.all()
        ).distinct()
        
        for farmer in farmers:
            if farmer.latitude is not None and farmer.longitude is not None:
                coordinates.append((float(farmer.latitude), float(farmer.longitude)))
            elif farmer.pincode:
                try:
                    pincode_data = PinCode.objects.get(code=farmer.pincode)
                    coordinates.append((pincode_data.latitude, pincode_data.longitude))
                except PinCode.DoesNotExist:
                    continue
        
        return coordinates
    
    def _get_candidate_hubs(self, farmer_coords: List[Tuple[float, float]], k: int = 5) -> List[HubPartner]:
        """Get K nearest hubs by Haversine distance as candidates."""
        from .logistics_service import _haversine_km, _calculate_centroid
        
        centroid = _calculate_centroid(farmer_coords)
        if not centroid:
            return []
        
        centroid_lat, centroid_lon = centroid
        
        # Get all hubs and calculate distances
        hubs = HubPartner.objects.all()
        hub_distances = []
        
        for hub in hubs:
            distance = _haversine_km(centroid_lat, centroid_lon, hub.latitude, hub.longitude)
            hub_distances.append((hub, distance))
        
        # Sort by distance and return top K
        hub_distances.sort(key=lambda x: x[1])
        return [hub for hub, distance in hub_distances[:k]]
    
    def _get_travel_times(self, farmer_coords: List[Tuple[float, float]], 
                          candidate_hubs: List[HubPartner]) -> Optional[List[List[int]]]:
        """Get travel times using available providers."""
        hub_coords = [(hub.latitude, hub.longitude) for hub in candidate_hubs]
        
        for provider in self.providers:
            try:
                travel_times = provider.get_travel_times(farmer_coords, hub_coords)
                if travel_times:
                    logger.info(f"Successfully got travel times from {provider.__class__.__name__}")
                    return travel_times
            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} failed: {e}")
                continue
        
        return None
    
    def _select_hub_by_travel_time(self, farmer_coords: List[Tuple[float, float]], 
                                  candidate_hubs: List[HubPartner], 
                                  travel_times: List[List[int]]) -> Optional[HubPartner]:
        """Select hub with minimum total travel time."""
        if not travel_times or len(travel_times) != len(farmer_coords):
            return None
        
        hub_scores = []
        
        for i, hub in enumerate(candidate_hubs):
            total_time = 0
            valid_times = 0
            
            for j, farmer_coord in enumerate(farmer_coords):
                if j < len(travel_times) and i < len(travel_times[j]):
                    time_minutes = travel_times[j][i]
                    if time_minutes is not None:
                        total_time += time_minutes
                        valid_times += 1
            
            if valid_times > 0:
                # Average travel time per farmer
                avg_time = total_time / valid_times
                hub_scores.append((hub, avg_time, total_time))
        
        if not hub_scores:
            return None
        
        # Select hub with minimum average travel time
        hub_scores.sort(key=lambda x: x[1])
        return hub_scores[0][0]
    
    def _save_hub_recommendation(self, deal_group: DealGroup, hub: HubPartner, method: str = 'V2'):
        """Save hub recommendation to deal group."""
        with transaction.atomic():
            deal_group.recommended_collection_point = hub
            deal_group.save(update_fields=['recommended_collection_point'])
            
            # Cache the method used for this recommendation
            cache_key = f"hub_recommendation_method_{deal_group.id}"
            cache.set(cache_key, method, timeout=3600)  # 1 hour
    
    def _fallback_to_v1(self, deal_group: DealGroup) -> Optional[HubPartner]:
        """Fallback to V1 logistics service."""
        logger.info(f"Falling back to V1 for deal group {deal_group.id}")
        hub = find_optimal_hub_v1(deal_group)
        if hub:
            # Mark this as V1 recommendation
            cache_key = f"hub_recommendation_method_{deal_group.id}"
            cache.set(cache_key, 'V1', timeout=3600)
        return hub
    
    def get_recommendation_method(self, deal_group: DealGroup) -> str:
        """Get the method used for the current hub recommendation."""
        cache_key = f"hub_recommendation_method_{deal_group.id}"
        return cache.get(cache_key, 'V1')


# Global instance
logistics_v2_service = LogisticsV2Service()


# Convenience functions
def find_optimal_hub_v2(deal_group: DealGroup) -> Optional[HubPartner]:
    """Convenience function to find optimal hub using V2."""
    return logistics_v2_service.find_optimal_hub_v2(deal_group)


def get_recommendation_method(deal_group: DealGroup) -> str:
    """Convenience function to get recommendation method."""
    return logistics_v2_service.get_recommendation_method(deal_group)
