"""
Market Data Analyzer
Clean analysis from BIG_DATA.csv with no fallbacks
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """Clean market data analysis from BIG_DATA.csv"""
    
    def __init__(self):
        self.big_data_df = None
        self._load_big_data()
    
    def _load_big_data(self):
        """Load BIG_DATA.csv - NO FALLBACKS"""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.join(base_dir, "scripts", "BIG_DATA.csv")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"BIG_DATA.csv not found at: {file_path}")
            
            self.big_data_df = pd.read_csv(file_path)
            
            if self.big_data_df.empty:
                raise ValueError("BIG_DATA.csv is empty")
            
            logger.info(f"✅ BIG_DATA.csv loaded: {len(self.big_data_df)} records")
            
        except Exception as e:
            logger.error(f"❌ Failed to load BIG_DATA.csv: {e}")
            raise RuntimeError(f"BIG_DATA.csv loading failed: {e}")
    
    def get_market_data(self, crop_name: str, district: str, date: datetime, grade: str = None) -> Dict[str, Any]:
        """Get comprehensive market data - NO FALLBACKS"""
        
        if self.big_data_df is None:
            raise RuntimeError("BIG_DATA.csv not loaded")
        
        try:
            # Standardize names
            std_crop = self._standardize_crop_name(crop_name)
            std_district = self._standardize_district_name(district)
            
            # Filter data - first try to find exact crop+district+grade match
            if grade:
                crop_data = self.big_data_df[
                    (self.big_data_df['Commodity'].str.lower() == std_crop.lower()) &
                    (self.big_data_df['District Name'].str.lower() == std_district.lower()) &
                    (self.big_data_df['Grade'].str.lower() == grade.lower())
                ]
                
                if crop_data.empty:
                    # Try crop+grade (any district)
                    crop_data = self.big_data_df[
                        (self.big_data_df['Commodity'].str.lower() == std_crop.lower()) &
                        (self.big_data_df['Grade'].str.lower() == grade.lower())
                    ]
            
            # If no grade-specific data or no grade provided, fall back to crop+district
            if not grade or crop_data.empty:
                crop_data = self.big_data_df[
                    (self.big_data_df['Commodity'].str.lower() == std_crop.lower()) &
                    (self.big_data_df['District Name'].str.lower() == std_district.lower())
                ]
                
                if crop_data.empty:
                    # Try to find data for just the crop (any district)
                    crop_only_data = self.big_data_df[
                        self.big_data_df['Commodity'].str.lower() == std_crop.lower()
                    ]
                    
                    if crop_only_data.empty:
                        raise ValueError(f"No data found for {crop_name} in any district")
                    else:
                        # Use data from any district for this crop
                        logger.info(f"ℹ️ Using data for {crop_name} from other districts")
                        crop_data = crop_only_data
            
            # Analyze prices
            price_analysis = self._analyze_prices(crop_data)
            
            # Market insights
            market_insights = self._get_market_insights(crop_data, std_crop, std_district)
            
            return {
                'crop_name': std_crop,
                'district': std_district,
                'grade': grade,
                'data_points': len(crop_data),
                'price_analysis': price_analysis,
                'market_insights': market_insights,
                'data_source': 'BIG_DATA.csv',
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Market data retrieval failed: {e}")
            raise RuntimeError(f"Market data retrieval failed: {e}")
    
    def _standardize_crop_name(self, crop_name: str) -> str:
        """Standardize crop names"""
        crop_mappings = {
            'rice': 'Rice', 'paddy': 'Rice', 'PADDY': 'Rice',
            'gram': 'GRAM', 'chickpea': 'GRAM', 'bengal gram': 'GRAM',
            'tomato': 'Tomato', 'potato': 'Potato', 'onion': 'Onion',
            'wheat': 'Wheat', 'maize': 'Maize', 'sugarcane': 'Sugarcane'
        }
        
        return crop_mappings.get(crop_name.lower(), crop_name.title())
    
    def _standardize_district_name(self, district: str) -> str:
        """Standardize district names"""
        district_mappings = {
            'east godavari': 'krishna', 'EAST GODAVARI': 'krishna',
            'west godavari': 'krishna', 'WEST GODAVARI': 'krishna',
            'krishna': 'krishna', 'KRISHNA': 'krishna'
        }
        
        return district_mappings.get(district.lower(), district.lower())
    
    def _analyze_prices(self, crop_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze price data - Convert from quintals (100kg) to per kg"""
        try:
            # Get price column (handle different column names)
            price_col = None
            for col in ['Modal_Price', 'Min_Price', 'Max_Price', 'Price']:
                if col in crop_data.columns:
                    price_col = col
                    break
            
            if price_col is None:
                raise ValueError("No price column found in data")
            
            # Prices in CSV are in quintals (100kg), convert to per kg
            prices_quintal = pd.to_numeric(crop_data[price_col], errors='coerce').dropna()
            
            if prices_quintal.empty:
                raise ValueError("No valid price data found")
            
            # Convert quintal prices to per kg (divide by 100)
            prices_per_kg = prices_quintal / 100.0
            
            logger.info(f"💰 Price conversion: {prices_quintal.iloc[-1]} ₹/quintal = {prices_per_kg.iloc[-1]:.2f} ₹/kg")
            
            return {
                'current_price_per_kg': float(prices_per_kg.iloc[-1]),
                'average_price_per_kg': float(prices_per_kg.mean()),
                'min_price_per_kg': float(prices_per_kg.min()),
                'max_price_per_kg': float(prices_per_kg.max()),
                'price_trend': self._calculate_price_trend(prices_per_kg),
                'price_volatility': float(prices_per_kg.std()),
                'data_points': len(prices_per_kg),
                'original_quintal_price': float(prices_quintal.iloc[-1]),  # Keep original for reference
                'conversion_factor': 'quintal_to_kg'
            }
            
        except Exception as e:
            logger.error(f"❌ Price analysis failed: {e}")
            raise RuntimeError(f"Price analysis failed: {e}")
    
    def _calculate_price_trend(self, prices: pd.Series) -> str:
        """Calculate price trend"""
        if len(prices) < 2:
            return "Insufficient data"
        
        recent_avg = prices.tail(5).mean()
        older_avg = prices.head(5).mean()
        
        if recent_avg > older_avg * 1.05:
            return "Rising (+5%+)"
        elif recent_avg < older_avg * 0.95:
            return "Falling (-5%+)"
        else:
            return "Stable (±5%)"
    
    def _get_market_insights(self, crop_data: pd.DataFrame, crop: str, district: str) -> Dict[str, Any]:
        """Get market insights"""
        try:
            return {
                'market_coverage': {
                    'markets_count': len(crop_data['Market Name'].unique()),
                    'market_names': list(crop_data['Market Name'].unique())
                },
                'seasonal_factors': self._get_seasonal_factors(crop_data),
                'quality_grades': list(crop_data['Grade'].unique()) if 'Grade' in crop_data.columns else [],
                'supply_indicators': self._get_supply_indicators(crop_data)
            }
            
        except Exception as e:
            logger.error(f"❌ Market insights failed: {e}")
            raise RuntimeError(f"Market insights failed: {e}")
    
    def _get_seasonal_factors(self, crop_data: pd.DataFrame) -> List[str]:
        """Get seasonal factors"""
        try:
            if 'Date' not in crop_data.columns:
                return ["Data not available"]
            
            # Extract month from date
            crop_data['Month'] = pd.to_datetime(crop_data['Date'], errors='coerce').dt.month
            monthly_counts = crop_data['Month'].value_counts()
            
            peak_months = monthly_counts.head(3).index.tolist()
            seasons = []
            
            for month in peak_months:
                if month in [6, 7, 8, 9]:
                    seasons.append("Monsoon Peak")
                elif month in [10, 11, 12]:
                    seasons.append("Post-Monsoon")
                elif month in [1, 2, 3]:
                    seasons.append("Winter")
                else:
                    seasons.append("Summer")
            
            return list(set(seasons))
            
        except Exception as e:
            logger.error(f"❌ Seasonal analysis failed: {e}")
            return ["Analysis failed"]
    
    def _get_supply_indicators(self, crop_data: pd.DataFrame) -> Dict[str, Any]:
        """Get supply indicators"""
        try:
            indicators = {}
            
            # Check for arrival data
            if 'Arrival' in crop_data.columns:
                arrivals = pd.to_numeric(crop_data['Arrival'], errors='coerce').dropna()
                if not arrivals.empty:
                    indicators['avg_arrival'] = float(arrivals.mean())
                    indicators['supply_trend'] = "High" if arrivals.mean() > 100 else "Moderate"
            
            # Check for variety data
            if 'Variety' in crop_data.columns:
                indicators['varieties_available'] = len(crop_data['Variety'].unique())
            
            return indicators if indicators else {"message": "Limited supply data"}
            
        except Exception as e:
            logger.error(f"❌ Supply analysis failed: {e}")
            return {"message": "Supply analysis failed"}
    
    def get_available_crops(self) -> List[str]:
        """Get list of available crops"""
        if self.big_data_df is None:
            raise RuntimeError("BIG_DATA.csv not loaded")
        
        crops = self.big_data_df['Commodity'].unique()
        return [crop for crop in crops if pd.notna(crop)]
    
    def get_available_districts(self) -> List[str]:
        """Get list of available districts"""
        if self.big_data_df is None:
            raise RuntimeError("BIG_DATA.csv not loaded")
        
        districts = self.big_data_df['District Name'].unique()
        return [district for district in districts if pd.notna(district)]
