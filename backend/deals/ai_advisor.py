# backend/deals/ai_advisor.py
"""
AI Agricultural Advisor - Phase 3 Implementation
Provides advanced AI capabilities, comprehensive advisory services, and automation
"""

import os
import joblib
import pickle
import os
from django.conf import settings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q, Avg, Count, Max, Min
from .models import MarketPrice, DealGroup, GroupMessage, NegotiationMessage
from products.models import ProductListing
from users.models import CustomUser
import json
import re
from collections import defaultdict, Counter
import logging
from chatbot.models import KnowledgeChunk
from django.db.models import Q
import json

# Setup logging for Phase 3
logger = logging.getLogger(__name__)

class MarketIntelligenceEngine:
    """Enhanced market intelligence using ML models and historical data"""
    
    def __init__(self):
        self.ml_model = None
        self.scaler = None
        self.encoders = None
        self.feature_columns = None
        self._load_ml_models()
    
    def _load_ml_models(self):
        """Load trained ML models"""
        try:
            base_dir = getattr(settings, 'BASE_DIR', os.getcwd())
            model_path = os.path.join(base_dir, 'advanced_pricing_model.pkl')
            scaler_path = os.path.join(base_dir, 'price_scaler.pkl')
            encoders_path = os.path.join(base_dir, 'price_encoders.pkl')
            features_path = os.path.join(base_dir, 'price_features.pkl')

            self.ml_model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)

            with open(encoders_path, 'rb') as f:
                encoders_data = pickle.load(f)
                self.encoders = encoders_data
            
            with open(features_path, 'rb') as f:
                self.feature_columns = pickle.load(f)
                
            print("✅ ML models loaded successfully")
        except Exception as e:
            print(f"⚠️ ML models not available: {e}")
            self.ml_model = None
    
    def predict_market_price(self, crop_name, region, date, quality_grade='FAQ'):
        """Predict market price using ML models"""
        if not self.ml_model:
            return self._get_fallback_price(crop_name, region, date)
        
        try:
            # Prepare features
            features = self._prepare_features(crop_name, region, date, quality_grade)
            if features is None:
                return self._get_fallback_price(crop_name, region, date)
            
            # Scale features
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            
            # Predict
            predicted_price = self.ml_model.predict(features_scaled)[0]
            
            return {
                'predicted_price_quintal': float(predicted_price),
                'predicted_price_kg': float(predicted_price) / 100,
                'confidence': 'ML Model',
                'model_type': 'Gradient Boosting (R²: 0.7310)'
            }
            
        except Exception as e:
            print(f"ML prediction failed: {e}")
            return self._get_fallback_price(crop_name, region, date)
    
    def _prepare_features(self, crop_name, region, date, quality_grade):
        """Prepare features for ML prediction"""
        try:
            # Extract district from region
            district = region.split(',')[0].strip().lower() if ',' in region else region.lower()
            
            # Encode categorical variables with fallback handling
            try:
                crop_encoded = self.encoders['crop_encoder'].transform([crop_name])[0]
            except ValueError:
                # Fallback: use a default crop encoding if crop not in training data
                print(f"⚠️ Crop '{crop_name}' not in training data, using fallback encoding")
                crop_encoded = 0  # Default encoding
            
            try:
                district_encoded = self.encoders['district_encoder'].transform([district])[0]
            except ValueError:
                # Fallback: use a default district encoding if region not in training data
                print(f"⚠️ District '{district}' not in training data, using fallback encoding")
                district_encoded = 0  # Default encoding
            
            # Time-based features
            date_obj = pd.to_datetime(date) if isinstance(date, str) else date
            month = date_obj.month
            year = date_obj.year
            day_of_week = date_obj.weekday()  # Use weekday() instead of dayofweek
            quarter = ((month - 1) // 3) + 1  # Calculate quarter manually
            is_month_start = int(date_obj.day == 1)  # Check if it's the first day of month
            # Calculate last day of month
            last_day = pd.Timestamp(date_obj.year, date_obj.month, 1) + pd.offsets.MonthEnd(1)
            is_month_end = int(date_obj.day == last_day.day)
            
            # Seasonal features
            is_kharif = int(month in [6, 7, 8, 9])
            is_rabi = int(month in [10, 11, 12, 1, 2, 3])
            
            # Regional features
            major_markets = ['hyderabad', 'warangal', 'mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata', 'pune', 'ahmedabad', 'jaipur']
            is_major_market = int(district in major_markets)
            
            # Quality features
            has_quality_grade = int(quality_grade and quality_grade != '')
            
            # Create feature array
            features = np.array([
                crop_encoded, district_encoded, month, year, day_of_week,
                quarter, is_month_start, is_month_end, is_kharif, is_rabi,
                is_major_market, has_quality_grade
            ])
            
            return features
            
        except Exception as e:
            print(f"Feature preparation failed: {e}")
            return None
    
    def _get_fallback_price(self, crop_name, region, date):
        """Fallback price analysis using database queries"""
        try:
            # Get recent prices for the crop and region
            recent_prices = MarketPrice.objects.filter(
                crop_name=crop_name,
                region__icontains=region.split(',')[0] if ',' in region else region
            ).order_by('-date')[:100]
            
            if not recent_prices.exists():
                return None
            
            prices = [float(price.price) for price in recent_prices]
            
            return {
                'predicted_price_quintal': np.mean(prices),
                'predicted_price_kg': np.mean(prices) / 100,
                'confidence': 'Historical Data',
                'model_type': 'Database Average'
            }
            
        except Exception as e:
            print(f"Fallback analysis failed: {e}")
            return None
    
    def analyze_market_trends(self, crop_name, region, timeframe_days=90):
        """Analyze market trends using historical data and ML predictions"""
        try:
            current_date = timezone.now().date()
            start_date = current_date - timedelta(days=timeframe_days)
            
            # Get price data
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT date, price, volume_kg
                    FROM deals_marketprice 
                    WHERE crop_name = %s AND region LIKE %s
                    AND date >= %s
                    ORDER BY date
                """, [crop_name, f"%{region.split(',')[0]}%", start_date])
                
                data = cursor.fetchall()
                
                if not data:
                    return {'error': 'No market data available'}
                
                # Process data
                dates = [row[0] for row in data]
                prices = [float(row[1]) for row in data]
                quantities = [float(row[2]) if row[2] else 0 for row in data]
                
                # Calculate trends
                price_trend = self._calculate_price_trend(prices)
                volume_trend = self._calculate_volume_trend(quantities)
                volatility = self._calculate_volatility(prices)
                
                # Seasonal analysis
                seasonal_pattern = self._analyze_seasonal_pattern(dates, prices)
                
                # Market sentiment
                sentiment = self._assess_market_sentiment(prices, quantities)
                
                return {
                    'crop_name': crop_name,
                    'region': region,
                    'analysis_period': f"{timeframe_days} days",
                    'price_trend': price_trend,
                    'volume_trend': volume_trend,
                    'volatility': volatility,
                    'seasonal_pattern': seasonal_pattern,
                    'market_sentiment': sentiment,
                    'data_points': len(data),
                    'last_updated': current_date
                }
                
        except Exception as e:
            print(f"Market trend analysis failed: {e}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _calculate_price_trend(self, prices):
        """Calculate price trend direction and strength"""
        if len(prices) < 2:
            return {'direction': 'Stable', 'strength': 0, 'change_percent': 0}
        
        # Linear regression for trend
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        
        # Calculate percentage change
        start_price = prices[0]
        end_price = prices[-1]
        change_percent = ((end_price - start_price) / start_price) * 100 if start_price > 0 else 0
        
        # Determine trend direction and strength
        if slope > 0.1:
            direction = 'Strongly Rising'
            strength = 'High'
        elif slope > 0:
            direction = 'Rising'
            strength = 'Medium'
        elif slope < -0.1:
            direction = 'Strongly Falling'
            strength = 'High'
        elif slope < 0:
            direction = 'Falling'
            strength = 'Medium'
        else:
            direction = 'Stable'
            strength = 'Low'
        
        return {
            'direction': direction,
            'strength': strength,
            'slope': round(slope, 4),
            'change_percent': round(change_percent, 2)
        }
    
    def _calculate_volume_trend(self, quantities):
        """Calculate volume trend direction and strength"""
        if len(quantities) < 2:
            return {'direction': 'Stable', 'strength': 0, 'change_percent': 0}
        
        # Linear regression for trend
        x = np.arange(len(quantities))
        slope = np.polyfit(x, quantities, 1)[0]
        
        # Calculate percentage change
        start_quantity = quantities[0]
        end_quantity = quantities[-1]
        change_percent = ((end_quantity - start_quantity) / start_quantity) * 100 if start_quantity > 0 else 0
        
        return {
            'direction': 'Rising' if slope > 0 else 'Falling' if slope < 0 else 'Stable',
            'strength': 'High' if abs(slope) > 0.1 else 'Medium' if abs(slope) > 0.01 else 'Low',
            'slope': round(slope, 4),
            'change_percent': round(change_percent, 2)
        }
    
    def _calculate_volatility(self, prices):
        """Calculate price volatility"""
        if len(prices) < 2:
            return {'volatility': 0, 'risk_level': 'Low'}
        
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * 100
        
        if volatility > 20:
            risk_level = 'Very High'
        elif volatility > 15:
            risk_level = 'High'
        elif volatility > 10:
            risk_level = 'Medium'
        elif volatility > 5:
            risk_level = 'Low'
        else:
            risk_level = 'Very Low'
        
        return {
            'volatility': round(volatility, 2),
            'risk_level': risk_level
        }
    
    def _analyze_seasonal_pattern(self, dates, prices):
        """Analyze seasonal price patterns"""
        if len(dates) < 30:  # Need at least a month of data
            return {}
        
        # Group prices by month
        monthly_prices = defaultdict(list)
        for date, price in zip(dates, prices):
            month = date.month
            monthly_prices[month].append(price)
        
        # Calculate average price per month
        monthly_avg = {month: np.mean(prices) for month, prices in monthly_prices.items()}
        
        if not monthly_avg:
            return {}
        
        # Find peak and trough months
        peak_month = max(monthly_avg, key=monthly_avg.get)
        trough_month = min(monthly_avg, key=monthly_avg.get)
        
        return {
            'peak_month': peak_month,
            'trough_month': trough_month,
            'peak_price': round(monthly_avg[peak_month], 2),
            'trough_price': round(monthly_avg[trough_month], 2),
            'seasonal_strength': round((monthly_avg[peak_month] - monthly_avg[trough_month]) / monthly_avg[trough_month] * 100, 2)
        }
    
    def _assess_market_sentiment(self, prices, quantities):
        """Assess overall market sentiment"""
        if len(prices) < 2:
            return 'Neutral'
        
        # Price momentum
        recent_prices = prices[-10:] if len(prices) >= 10 else prices
        price_momentum = np.mean(recent_prices) - np.mean(prices[:10]) if len(prices) >= 10 else 0
        
        # Volume trend
        recent_quantities = quantities[-10:] if len(quantities) >= 10 else quantities
        volume_trend = np.mean(recent_quantities) - np.mean(quantities[:10]) if len(quantities) >= 10 else 0
        
        # Determine sentiment
        if price_momentum > 0 and volume_trend > 0:
            sentiment = 'Very Bullish'
        elif price_momentum > 0:
            sentiment = 'Bullish'
        elif price_momentum < 0 and volume_trend < 0:
            sentiment = 'Very Bearish'
        elif price_momentum < 0:
            sentiment = 'Bearish'
        else:
            sentiment = 'Neutral'
        
        return sentiment

class CropAdvisor:
    """Provides crop-specific advice and recommendations"""
    
    def __init__(self, market_engine):
        self.market_engine = market_engine
    
    def get_crop_advice(self, crop_name, region, user_role='farmer'):
        """Get comprehensive crop advice"""
        current_date = timezone.now().date()
        
        # Get current market analysis
        current_analysis = self._analyze_current_market(crop_name, region, current_date)
        
        # Get seasonal recommendations
        seasonal_advice = self._get_seasonal_advice(crop_name, current_date)
        
        # Get regional insights
        regional_insights = self._get_regional_insights(crop_name, region)
        
        # Get selling recommendations
        selling_advice = self._get_selling_recommendations(crop_name, region, current_date)
        
        return {
            'crop_name': crop_name,
            'region': region,
            'current_date': current_date,
            'market_analysis': current_analysis,
            'seasonal_advice': seasonal_advice,
            'regional_insights': regional_insights,
            'selling_recommendations': selling_advice,
            'user_role': user_role
        }
    
    def get_crop_planning_advice(self, region, season=None, budget_constraint=None, risk_tolerance='medium'):
        """Get comprehensive crop planning advice"""
        try:
            # Determine optimal season if not specified
            if not season:
                season = self._get_optimal_season(region)
            
            # Get suitable crops for the season
            suitable_crops = self._get_suitable_crops(season, region)
            
            # Analyze each crop option
            crop_analysis = []
            for crop in suitable_crops:
                analysis = self._analyze_crop_option(crop, region, season, budget_constraint, risk_tolerance)
                crop_analysis.append(analysis)
            
            # Rank crops by profitability and risk
            ranked_crops = self._rank_crop_options(crop_analysis, risk_tolerance)
            
            # Generate financial projections
            financial_plan = self._generate_financial_plan(ranked_crops[0], region, season)
            
            return {
                'status': 'success',
                'recommended_season': season,
                'top_recommendations': ranked_crops[:3],
                'financial_plan': financial_plan,
                'risk_assessment': self._assess_planning_risks(region, season),
                'next_actions': self._get_planning_next_actions(ranked_crops[0]),
                'phase': 'Phase 3 - Crop Planning Advisor'
            }
            
        except Exception as e:
            logger.error(f"Crop planning advice failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 3 - Crop Planning Advisor'
            }
    
    def _get_optimal_season(self, region):
        """Get optimal growing season for a region"""
        region_lower = region.lower()
        
        if region_lower in ['andhra pradesh', 'maharashtra', 'karnataka']:
            return 'kharif'
        elif region_lower in ['punjab', 'haryana', 'uttar pradesh']:
            return 'rabi'
        else:
            return 'kharif'  # Default
    
    def _get_suitable_crops(self, season, region):
        """Get suitable crops for season and region"""
        season_crops = {
            'kharif': ['rice', 'maize', 'cotton', 'sugarcane', 'pulses', 'tomato', 'onion'],
            'rabi': ['wheat', 'barley', 'mustard', 'chickpea', 'potato', 'vegetables'],
            'zaid': ['vegetables', 'fruits', 'pulses', 'maize']
        }
        
        return season_crops.get(season, ['rice', 'wheat', 'vegetables'])
    
    def _analyze_crop_option(self, crop, region, season, budget_constraint, risk_tolerance):
        """Analyze a specific crop option"""
        # Get market analysis
        market_data = self.market_engine.analyze_market_trends(crop, region, 90)
        
        # Calculate expected ROI
        expected_roi = self._calculate_expected_roi(crop, region, season)
        
        # Assess risk level
        risk_level = self._assess_crop_risk(crop, region, season, risk_tolerance)
        
        return {
            'crop': crop,
            'region': region,
            'season': season,
            'expected_roi': expected_roi,
            'risk_level': risk_level,
            'market_outlook': market_data.get('market_sentiment', 'Neutral')
        }
    
    def _calculate_expected_roi(self, crop, region, season):
        """Calculate expected ROI for a crop"""
        # Simplified ROI calculation
        base_roi = {
            'rice': 25, 'wheat': 20, 'potato': 30, 'tomato': 35, 'onion': 28
        }
        
        # Adjust for region and season
        region_multiplier = 1.0
        if region.lower() in ['punjab', 'haryana']:
            region_multiplier = 1.2
        elif region.lower() in ['andhra pradesh', 'maharashtra']:
            region_multiplier = 1.1
        
        season_multiplier = 1.0
        if season == 'kharif':
            season_multiplier = 1.15
        
        return round(base_roi.get(crop.lower(), 20) * region_multiplier * season_multiplier, 1)
    
    def _assess_crop_risk(self, crop, region, season, risk_tolerance):
        """Assess risk level for a crop"""
        base_risk = {
            'rice': 'low', 'wheat': 'low', 'potato': 'medium', 'tomato': 'high', 'onion': 'medium'
        }
        
        risk_level = base_risk.get(crop.lower(), 'medium')
        
        # Adjust based on risk tolerance
        if risk_tolerance == 'low' and risk_level == 'high':
            risk_level = 'medium'
        elif risk_tolerance == 'high' and risk_level == 'low':
            risk_level = 'medium'
        
        return {'level': risk_level, 'factors': ['market_volatility', 'weather_dependency']}
    
    def _rank_crop_options(self, crop_analysis, risk_tolerance):
        """Rank crop options by profitability and risk"""
        # Sort by ROI (descending)
        ranked = sorted(crop_analysis, key=lambda x: x['expected_roi'], reverse=True)
        
        # Adjust ranking based on risk tolerance
        if risk_tolerance == 'low':
            # Prefer low-risk crops
            ranked = sorted(ranked, key=lambda x: (x['risk_level']['level'] == 'low', x['expected_roi']), reverse=True)
        elif risk_tolerance == 'high':
            # Prefer high-ROI crops regardless of risk
            pass  # Already sorted by ROI
        
        return ranked
    
    def _generate_financial_plan(self, top_crop, region, season):
        """Generate financial plan for the top crop"""
        # Simplified financial planning
        investment_per_acre = {
            'low': 25000, 'medium': 35000, 'high': 50000
        }
        
        risk_level = top_crop['risk_level']['level']
        investment = investment_per_acre[risk_level]
        
        expected_profit = investment * (top_crop['expected_roi'] / 100)
        break_even_yield = investment / 2000  # Assuming ₹2000/quintal average price
        
        return {
            'total_investment': investment,
            'expected_profit': expected_profit,
            'break_even_yield': break_even_yield,
            'roi_percentage': top_crop['expected_roi']
        }
    
    def _assess_planning_risks(self, region, season):
        """Assess overall planning risks"""
        return {
            'weather_risk': 'medium',
            'market_risk': 'low',
            'input_cost_risk': 'low',
            'mitigation_strategies': [
                'Diversify crop selection',
                'Monitor weather forecasts',
                'Lock in input prices early'
            ]
        }
    
    def _get_planning_next_actions(self, top_crop):
        """Get next actions for crop planning"""
        return [
            'Prepare soil and irrigation',
            'Source quality seeds and inputs',
            'Set up monitoring systems',
            'Plan harvesting and marketing',
            'Consider crop insurance'
        ]
    
    def _analyze_current_market(self, crop_name, region, date):
        """Analyze current market conditions"""
        # Get ML prediction
        ml_prediction = self.market_engine.predict_market_price(crop_name, region, date)
        
        # Get historical context
        historical_data = self._get_historical_context(crop_name, region, date)
        
        # Get price trends
        price_trends = self._analyze_price_trends(crop_name, region, date)
        
        return {
            'ml_prediction': ml_prediction,
            'historical_context': historical_data,
            'price_trends': price_trends,
            'market_sentiment': self._assess_market_sentiment(crop_name, region)
        }
    
    def _get_seasonal_advice(self, crop_name, date):
        """Get seasonal crop advice"""
        month = date.month
        
        seasonal_patterns = {
            'Potato': {
                'kharif': 'High demand in monsoon, prices peak',
                'rabi': 'Stable prices, good for storage',
                'best_selling_months': [6, 7, 8, 11, 12],
                'avoid_months': [3, 4, 5]
            },
            'Onion': {
                'kharif': 'Supply shortage, high prices',
                'rabi': 'Abundant supply, competitive prices',
                'best_selling_months': [7, 8, 9, 10],
                'avoid_months': [1, 2, 3]
            },
            'Tomato': {
                'kharif': 'High demand, premium prices',
                'rabi': 'Moderate demand, stable prices',
                'best_selling_months': [6, 7, 8, 9],
                'avoid_months': [11, 12, 1]
            },
            'Rice': {
                'kharif': 'Harvest season, good prices',
                'rabi': 'Stable supply, moderate prices',
                'best_selling_months': [9, 10, 11],
                'avoid_months': [4, 5, 6]
            },
            'Wheat': {
                'kharif': 'Low supply, high prices',
                'rabi': 'Harvest season, competitive prices',
                'best_selling_months': [3, 4, 5],
                'avoid_months': [8, 9, 10]
            }
        }
        
        crop_pattern = seasonal_patterns.get(crop_name, {})
        
        if month in crop_pattern.get('best_selling_months', []):
            timing_advice = "🟢 EXCELLENT timing to sell! Prices are at seasonal peak."
        elif month in crop_pattern.get('avoid_months', []):
            timing_advice = "🔴 AVOID selling now. Prices are typically low this month."
        else:
            timing_advice = "🟡 MODERATE timing. Consider waiting for better prices."
        
        return {
            'current_season': 'Kharif' if month in [6, 7, 8, 9] else 'Rabi',
            'seasonal_analysis': crop_pattern.get('kharif' if month in [6, 7, 8, 9] else 'rabi', ''),
            'timing_advice': timing_advice,
            'best_months': crop_pattern.get('best_selling_months', []),
            'avoid_months': crop_pattern.get('avoid_months', [])
        }
    
    def _get_regional_insights(self, crop_name, region):
        """Get region-specific insights"""
        try:
            # Get regional price statistics
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        AVG(price) as avg_price,
                        MIN(price) as min_price,
                        MAX(price) as max_price,
                        COUNT(*) as data_points
                    FROM deals_marketprice 
                    WHERE crop_name = %s AND region LIKE %s
                    AND date >= DATE('now', '-90 days')
                """, [crop_name, f"%{region.split(',')[0]}%"])
                
                result = cursor.fetchone()
                if result:
                    avg_price, min_price, max_price, data_points = result
                    
                    # Calculate price volatility
                    cursor.execute("""
                        SELECT price FROM deals_marketprice 
                        WHERE crop_name = %s AND region LIKE %s
                        AND date >= DATE('now', '-90 days')
                        ORDER BY date DESC
                    """, [crop_name, f"%{region.split(',')[0]}%"])
                    
                    prices = [float(row[0]) for row in cursor.fetchall()]
                    if len(prices) > 1:
                        volatility = np.std(prices) / np.mean(prices) * 100
                    else:
                        volatility = 0
                    
                    return {
                        'avg_price_quintal': float(avg_price) if avg_price else 0,
                        'avg_price_kg': float(avg_price) / 100 if avg_price else 0,
                        'price_range': f"₹{min_price:.2f} - ₹{max_price:.2f}/quintal" if min_price and max_price else "N/A",
                        'data_points': data_points,
                        'price_volatility_percent': round(volatility, 2),
                        'market_stability': 'Stable' if volatility < 15 else 'Moderate' if volatility < 30 else 'Volatile'
                    }
            
            return {'error': 'No regional data available'}
            
        except Exception as e:
            print(f"Regional analysis failed: {e}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _get_selling_recommendations(self, crop_name, region, date):
        """Get selling strategy recommendations"""
        # Get current market price
        current_price = self.market_engine.predict_market_price(crop_name, region, date)
        
        # Get historical average
        historical_avg = self._get_historical_average(crop_name, region)
        
        if not current_price or not historical_avg:
            return {'error': 'Insufficient data for recommendations'}
        
        current_price_quintal = current_price['predicted_price_quintal']
        historical_avg_quintal = historical_avg['avg_price_quintal']
        
        # Calculate price premium/deficit
        price_difference = current_price_quintal - historical_avg_quintal
        price_percentage = (price_difference / historical_avg_quintal) * 100 if historical_avg_quintal > 0 else 0
        
        # Generate recommendations
        if price_percentage > 20:
            recommendation = "🚀 SELL NOW! Prices are significantly above historical average."
            urgency = "High"
            strategy = "Immediate sale recommended"
        elif price_percentage > 10:
            recommendation = "✅ Good time to sell. Prices are above average."
            urgency = "Medium"
            strategy = "Consider selling within 1-2 weeks"
        elif price_percentage > -10:
            recommendation = "⏳ Hold if possible. Prices are near average."
            urgency = "Low"
            strategy = "Wait for better prices or sell small quantities"
        else:
            recommendation = "🔴 Avoid selling now. Prices are below average."
            urgency = "Very Low"
            strategy = "Store and wait for price recovery"
        
        return {
            'current_price_quintal': current_price_quintal,
            'historical_average_quintal': historical_avg_quintal,
            'price_difference': price_difference,
            'price_percentage': round(price_percentage, 2),
            'recommendation': recommendation,
            'urgency': urgency,
            'strategy': strategy,
            'confidence': current_price['confidence']
        }
    
    def _get_historical_context(self, crop_name, region, date):
        """Get historical market context"""
        try:
            # Get last 12 months of data
            start_date = date - timedelta(days=365)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        strftime('%%Y-%%m', date) as month,
                        AVG(price) as avg_price,
                        COUNT(*) as transactions
                    FROM deals_marketprice 
                    WHERE crop_name = %s AND region LIKE %s
                    AND date >= %s
                    GROUP BY strftime('%%Y-%%m', date)
                    ORDER BY month DESC
                """, [crop_name, f"%{region.split(',')[0]}%", start_date])
                
                monthly_data = cursor.fetchall()
                
                if monthly_data:
                    # Calculate year-over-year change
                    current_year_avg = np.mean([float(row[1]) for row in monthly_data[:6]])  # Last 6 months
                    previous_year_avg = np.mean([float(row[1]) for row in monthly_data[6:12]]) if len(monthly_data) >= 12 else 0
                    
                    yoy_change = ((current_year_avg - previous_year_avg) / previous_year_avg * 100) if previous_year_avg > 0 else 0
                    
                    return {
                        'monthly_trends': [
                            {
                                'month': row[0],
                                'avg_price_quintal': float(row[1]),
                                'avg_price_kg': float(row[1]) / 100,
                                'transactions': row[2]
                            } for row in monthly_data
                        ],
                        'current_year_avg': current_year_avg,
                        'previous_year_avg': previous_year_avg,
                        'year_over_year_change': round(yoy_change, 2),
                        'trend_direction': 'Upward' if yoy_change > 0 else 'Downward' if yoy_change < 0 else 'Stable'
                    }
                
                return {'error': 'No historical data available'}
                
        except Exception as e:
            print(f"Historical context failed: {e}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _analyze_price_trends(self, crop_name, region, date):
        """Analyze price trends and patterns"""
        try:
            # Get recent price movements
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        date,
                        price,
                        LAG(price) OVER (ORDER BY date) as prev_price
                    FROM deals_marketprice 
                    WHERE crop_name = %s AND region LIKE %s
                    AND date >= DATE('now', '-30 days')
                    ORDER BY date DESC
                    LIMIT 30
                """, [crop_name, f"%{region.split(',')[0]}%"])
                
                recent_prices = cursor.fetchall()
                
                if len(recent_prices) > 1:
                    # Calculate trend
                    prices = [float(row[1]) for row in recent_prices]
                    price_changes = []
                    
                    for i in range(1, len(recent_prices)):
                        if recent_prices[i][2]:  # prev_price exists
                            change = float(recent_prices[i][1]) - float(recent_prices[i][2])
                            price_changes.append(change)
                    
                    if price_changes:
                        avg_change = np.mean(price_changes)
                        trend_strength = abs(avg_change) / np.mean(prices) * 100 if np.mean(prices) > 0 else 0
                        
                        if avg_change > 0:
                            trend = "Rising"
                            trend_description = f"Prices increasing by ₹{abs(avg_change):.2f}/quintal on average"
                        else:
                            trend = "Falling"
                            trend_description = f"Prices decreasing by ₹{abs(avg_change):.2f}/quintal on average"
                        
                        return {
                            'trend': trend,
                            'trend_description': trend_description,
                            'trend_strength': round(trend_strength, 2),
                            'avg_daily_change': round(avg_change, 2),
                            'recent_volatility': round(np.std(price_changes), 2),
                            'data_points': len(recent_prices)
                        }
                
                return {'error': 'Insufficient data for trend analysis'}
                
        except Exception as e:
            print(f"Trend analysis failed: {e}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _assess_market_sentiment(self, crop_name, region):
        """Assess overall market sentiment"""
        try:
            # Get recent transaction volume and price stability
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as recent_transactions,
                        AVG(price) as recent_avg_price,
                        MAX(price) - MIN(price) as price_range
                    FROM deals_marketprice 
                    WHERE crop_name = %s AND region LIKE %s
                    AND date >= DATE('now', '-7 days')
                """, [crop_name, f"%{region.split(',')[0]}%"])
                
                result = cursor.fetchone()
                if result:
                    transactions, avg_price, price_range = result
                    
                    # Assess sentiment based on volume and stability
                    if transactions > 20:
                        volume_sentiment = "High activity - Strong market interest"
                    elif transactions > 10:
                        volume_sentiment = "Moderate activity - Stable market"
                    else:
                        volume_sentiment = "Low activity - Limited market interest"
                    
                    if avg_price and price_range:
                        avg_price_float = float(avg_price)
                        price_range_float = float(price_range)
                        stability_ratio = price_range_float / avg_price_float if avg_price_float > 0 else 0
                        
                        if stability_ratio < 0.1:
                            stability_sentiment = "Very stable prices"
                        elif stability_ratio < 0.2:
                            stability_sentiment = "Stable prices"
                        elif stability_ratio < 0.3:
                            stability_sentiment = "Moderate price volatility"
                        else:
                            stability_sentiment = "High price volatility"
                    else:
                        stability_sentiment = "Price stability unknown"
                    
                    return {
                        'volume_sentiment': volume_sentiment,
                        'stability_sentiment': stability_sentiment,
                        'recent_transactions': transactions,
                        'recent_avg_price_quintal': float(avg_price) if avg_price else 0,
                        'price_stability_ratio': round(stability_ratio, 3) if 'stability_ratio' in locals() else 0
                    }
                
                return {'error': 'No recent market data'}
                
        except Exception as e:
            print(f"Sentiment analysis failed: {e}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _get_historical_average(self, crop_name, region):
        """Get historical average price"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT AVG(price) as avg_price
                    FROM deals_marketprice 
                    WHERE crop_name = %s AND region LIKE %s
                    AND date >= DATE('now', '-365 days')
                """, [crop_name, f"%{region.split(',')[0]}%"])
                
                result = cursor.fetchone()
                if result and result[0]:
                    return {
                        'avg_price_quintal': float(result[0]),
                        'avg_price_kg': float(result[0]) / 100
                    }
                
                return None
                
        except Exception as e:
            print(f"Historical average failed: {e}")
            return None

class GroupIntelligence:
    """Analyzes group dynamics and provides collective insights"""
    
    def __init__(self):
        pass
    
    def analyze_group_performance(self, deal_group_id):
        """Analyze group performance and provide insights"""
        try:
            deal_group = DealGroup.objects.get(id=deal_group_id)
            
            # Get group messages
            group_messages = GroupMessage.objects.filter(deal_group=deal_group)
            
            # Get negotiation history
            negotiation_messages = NegotiationMessage.objects.filter(deal_group=deal_group)
            
            # Analyze group sentiment
            sentiment_analysis = self._analyze_group_sentiment(group_messages)
            
            # Analyze negotiation patterns
            negotiation_analysis = self._analyze_negotiation_patterns(negotiation_messages)
            
            # Get market context
            market_context = self._get_group_market_context(deal_group)
            
            return {
                'deal_group_id': deal_group_id,
                'group_status': deal_group.status,
                'total_quantity_kg': deal_group.total_quantity_kg,
                'sentiment_analysis': sentiment_analysis,
                'negotiation_analysis': negotiation_analysis,
                'market_context': market_context,
                'group_recommendations': self._generate_group_recommendations(
                    deal_group, sentiment_analysis, negotiation_analysis, market_context
                )
            }
            
        except DealGroup.DoesNotExist:
            return {'error': 'Deal group not found'}
        except Exception as e:
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _analyze_group_sentiment(self, group_messages):
        """Analyze sentiment in group messages"""
        if not group_messages.exists():
            return {'message': 'No group messages found'}
        
        # Simple sentiment analysis based on keywords
        positive_keywords = ['good', 'great', 'excellent', 'happy', 'agree', 'accept', 'profit', 'success']
        negative_keywords = ['bad', 'poor', 'worried', 'concerned', 'reject', 'loss', 'problem', 'issue']
        
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for message in group_messages:
            content_lower = message.content.lower()
            
            if any(keyword in content_lower for keyword in positive_keywords):
                positive_count += 1
            elif any(keyword in content_lower for keyword in negative_keywords):
                negative_count += 1
            else:
                neutral_count += 1
        
        total_messages = len(group_messages)
        
        if total_messages > 0:
            positive_percent = (positive_count / total_messages) * 100
            negative_percent = (negative_count / total_messages) * 100
            neutral_percent = (neutral_count / total_messages) * 100
            
            if positive_percent > 50:
                overall_sentiment = "Positive"
                sentiment_description = "Group members are generally optimistic"
            elif negative_percent > 50:
                overall_sentiment = "Negative"
                sentiment_description = "Group members have concerns"
            else:
                overall_sentiment = "Neutral"
                sentiment_description = "Group sentiment is balanced"
        else:
            overall_sentiment = "Unknown"
            sentiment_description = "No messages to analyze"
        
        return {
            'overall_sentiment': overall_sentiment,
            'sentiment_description': sentiment_description,
            'positive_messages': positive_count,
            'negative_messages': negative_count,
            'neutral_messages': neutral_count,
            'total_messages': total_messages,
            'positive_percent': round(positive_percent, 1) if total_messages > 0 else 0,
            'negative_percent': round(negative_percent, 1) if total_messages > 0 else 0,
            'neutral_percent': round(neutral_percent, 1) if total_messages > 0 else 0
        }
    
    def _analyze_negotiation_patterns(self, negotiation_messages):
        """Analyze negotiation patterns and strategies"""
        if not negotiation_messages.exists():
            return {'message': 'No negotiation messages found'}
        
        # Analyze message types
        offer_count = negotiation_messages.filter(message_type='offer').count()
        counter_offer_count = negotiation_messages.filter(message_type='counter-offer').count()
        text_count = negotiation_messages.filter(message_type='text').count()
        
        # Analyze timing patterns
        messages_by_time = negotiation_messages.order_by('created_at')
        if messages_by_time.count() > 1:
            first_message = messages_by_time.first()
            last_message = messages_by_time.last()
            negotiation_duration = (last_message.created_at - first_message.created_at).total_seconds() / 3600  # hours
            
            # Calculate response times
            response_times = []
            for i in range(1, len(messages_by_time)):
                time_diff = (messages_by_time[i].created_at - messages_by_time[i-1].created_at).total_seconds() / 60  # minutes
                response_times.append(time_diff)
            
            avg_response_time = np.mean(response_times) if response_times else 0
        else:
            negotiation_duration = 0
            avg_response_time = 0
        
        return {
            'total_negotiation_messages': len(negotiation_messages),
            'offer_count': offer_count,
            'counter_offer_count': counter_offer_count,
            'text_count': text_count,
            'negotiation_duration_hours': round(negotiation_duration, 2),
            'avg_response_time_minutes': round(avg_response_time, 2),
            'negotiation_intensity': 'High' if len(negotiation_messages) > 10 else 'Medium' if len(negotiation_messages) > 5 else 'Low'
        }
    
    def _get_group_market_context(self, deal_group):
        """Get market context for the group's crop and region"""
        try:
            # Get the primary crop from the group
            products = deal_group.products.all()
            if not products.exists():
                return {'error': 'No products in group'}
            
            # Use the first product's crop and region
            product = products.first()
            crop_name = product.crop.name
            region = product.farmer.region if hasattr(product.farmer, 'region') else 'Unknown'
            
            # Get recent market data
            recent_prices = MarketPrice.objects.filter(
                crop_name=crop_name,
                region__icontains=region
            ).order_by('-date')[:30]
            
            if recent_prices.exists():
                prices = [float(price.price) for price in recent_prices]
                current_avg = np.mean(prices)
                price_trend = 'Stable'
                
                if len(prices) > 1:
                    if prices[0] > prices[-1] * 1.1:
                        price_trend = 'Rising'
                    elif prices[0] < prices[-1] * 0.9:
                        price_trend = 'Falling'
                
                return {
                    'crop_name': crop_name,
                    'region': region,
                    'current_avg_price_quintal': round(current_avg, 2),
                    'current_avg_price_kg': round(current_avg / 100, 2),
                    'price_trend': price_trend,
                    'recent_data_points': len(prices),
                    'price_volatility': round(np.std(prices) / np.mean(prices) * 100, 2) if np.mean(prices) > 0 else 0
                }
            
            return {'error': 'No market data available'}
            
        except Exception as e:
            return {'error': f'Market context failed: {str(e)}'}
    
    def _generate_group_recommendations(self, deal_group, sentiment, negotiation, market):
        """Generate recommendations for the group"""
        recommendations = []
        
        # Sentiment-based recommendations
        if sentiment.get('overall_sentiment') == 'Negative':
            recommendations.append({
                'type': 'Sentiment',
                'priority': 'High',
                'message': 'Group sentiment is negative. Consider addressing concerns through open discussion.',
                'action': 'Schedule a group discussion to address concerns'
            })
        
        # Negotiation-based recommendations
        if negotiation.get('negotiation_intensity') == 'High':
            recommendations.append({
                'type': 'Negotiation',
                'priority': 'Medium',
                'message': 'High negotiation activity suggests strong buyer interest. Consider group strategy.',
                'action': 'Coordinate group response to maximize leverage'
            })
        
        # Market-based recommendations
        if market.get('price_trend') == 'Rising':
            recommendations.append({
                'type': 'Market',
                'priority': 'High',
                'message': 'Market prices are rising. Consider holding for better prices.',
                'action': 'Delay sale if possible to capture higher prices'
            })
        elif market.get('price_trend') == 'Falling':
            recommendations.append({
                'type': 'Market',
                'priority': 'High',
                'message': 'Market prices are falling. Consider selling quickly.',
                'action': 'Accelerate sale to avoid further price drops'
            })
        
        # Group strategy recommendations
        if deal_group.status == 'NEGOTIATING':
            recommendations.append({
                'type': 'Strategy',
                'priority': 'Medium',
                'message': 'Group is in negotiation phase. Maintain unity for better bargaining power.',
                'action': 'Coordinate group decisions and maintain solidarity'
            })
        
        return recommendations

class MarketAnalysisEngine:
    """Enhanced market analysis engine for Phase 2"""
    
    def __init__(self, market_engine):
        self.market_engine = market_engine
    
    def analyze_market_trends(self, crop_name, region, timeframe_days=90):
        """Analyze comprehensive market trends"""
        try:
            current_date = timezone.now().date()
            start_date = current_date - timedelta(days=timeframe_days)
            
            # Get price data
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT date, price, volume_kg
                    FROM deals_marketprice 
                    WHERE crop_name = %s AND region LIKE %s
                    AND date >= %s
                    ORDER BY date
                """, [crop_name, f"%{region.split(',')[0]}%", start_date])
                
                data = cursor.fetchall()
                
                if not data:
                    return {'error': 'No market data available'}
                
                # Process data
                dates = [row[0] for row in data]
                prices = [float(row[1]) for row in data]
                quantities = [float(row[2]) if row[2] else 0 for row in data]
                
                # Calculate trends
                price_trend = self._calculate_price_trend(prices)
                volume_trend = self._calculate_volume_trend(quantities)
                volatility = self._calculate_volatility(prices)
                
                # Seasonal analysis
                seasonal_pattern = self._analyze_seasonal_pattern(dates, prices)
                
                # Market sentiment
                sentiment = self._assess_market_sentiment(prices, quantities)
                
                return {
                    'crop_name': crop_name,
                    'region': region,
                    'analysis_period': f"{timeframe_days} days",
                    'price_trend': price_trend,
                    'volume_trend': volume_trend,
                    'volatility': volatility,
                    'seasonal_pattern': seasonal_pattern,
                    'market_sentiment': sentiment,
                    'data_points': len(data),
                    'last_updated': current_date
                }
                
        except Exception as e:
            print(f"Market trend analysis failed: {e}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _calculate_price_trend(self, prices):
        """Calculate price trend direction and strength"""
        if len(prices) < 2:
            return {'direction': 'Stable', 'strength': 0, 'change_percent': 0}
        
        # Linear regression for trend
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        
        # Calculate percentage change
        start_price = prices[0]
        end_price = prices[-1]
        change_percent = ((end_price - start_price) / start_price) * 100 if start_price > 0 else 0
        
        # Determine trend direction and strength
        if slope > 0.1:
            direction = 'Strongly Rising'
            strength = 'High'
        elif slope > 0:
            direction = 'Rising'
            strength = 'Medium'
        elif slope < -0.1:
            direction = 'Strongly Falling'
            strength = 'High'
        elif slope < 0:
            direction = 'Falling'
            strength = 'Medium'
        else:
            direction = 'Stable'
            strength = 'Low'
        
        return {
            'direction': direction,
            'strength': strength,
            'slope': round(slope, 4),
            'change_percent': round(change_percent, 2)
        }
    
    def _calculate_volume_trend(self, quantities):
        """Calculate volume trend"""
        if len(quantities) < 2:
            return {'direction': 'Stable', 'change_percent': 0}
        
        start_vol = quantities[0]
        end_vol = quantities[-1]
        change_percent = ((end_vol - start_vol) / start_vol) * 100 if start_vol > 0 else 0
        
        if change_percent > 20:
            direction = 'Strongly Increasing'
        elif change_percent > 10:
            direction = 'Increasing'
        elif change_percent < -20:
            direction = 'Strongly Decreasing'
        elif change_percent < -10:
            direction = 'Decreasing'
        else:
            direction = 'Stable'
        
        return {
            'direction': direction,
            'change_percent': round(change_percent, 2)
        }
    
    def _calculate_volatility(self, prices):
        """Calculate price volatility"""
        if len(prices) < 2:
            return {'level': 'Unknown', 'percentage': 0}
        
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * 100
        
        if volatility < 5:
            level = 'Very Low'
        elif volatility < 10:
            level = 'Low'
        elif volatility < 20:
            level = 'Moderate'
        elif volatility < 30:
            level = 'High'
        else:
            level = 'Very High'
        
        return {
            'level': level,
            'percentage': round(volatility, 2)
        }
    
    def _analyze_seasonal_pattern(self, dates, prices):
        """Analyze seasonal price patterns"""
        if len(dates) < 30:
            return {'pattern': 'Insufficient data', 'confidence': 'Low'}
        
        # Group by month
        monthly_prices = {}
        for date, price in zip(dates, prices):
            month = date.month if hasattr(date, 'month') else pd.to_datetime(date).month
            if month not in monthly_prices:
                monthly_prices[month] = []
            monthly_prices[month].append(price)
        
        # Calculate monthly averages
        monthly_avg = {month: np.mean(prices) for month, prices in monthly_prices.items()}
        
        # Find peak and trough months
        if monthly_avg:
            peak_month = max(monthly_avg, key=monthly_avg.get)
            trough_month = min(monthly_avg, key=monthly_avg.get)
            
            return {
                'pattern': 'Seasonal variation detected',
                'confidence': 'Medium',
                'peak_month': peak_month,
                'trough_month': trough_month,
                'peak_price': round(monthly_avg[peak_month], 2),
                'trough_price': round(monthly_avg[trough_month], 2)
            }
        
        return {'pattern': 'No clear pattern', 'confidence': 'Low'}
    
    def _assess_market_sentiment(self, prices, quantities):
        """Assess overall market sentiment"""
        if not prices or not quantities:
            return {'sentiment': 'Unknown', 'confidence': 'Low'}
        
        # Price momentum
        recent_prices = prices[-7:] if len(prices) >= 7 else prices
        price_momentum = 'Positive' if recent_prices[-1] > recent_prices[0] else 'Negative'
        
        # Volume analysis
        recent_volumes = quantities[-7:] if len(quantities) >= 7 else quantities
        avg_volume = np.mean(recent_volumes) if recent_volumes else 0
        
        # Sentiment scoring
        score = 0
        if price_momentum == 'Positive':
            score += 2
        if avg_volume > np.mean(quantities) if quantities else 0:
            score += 1
        
        if score >= 2:
            sentiment = 'Bullish'
        elif score >= 1:
            sentiment = 'Neutral'
        else:
            sentiment = 'Bearish'
        
        return {
            'sentiment': sentiment,
            'confidence': 'Medium',
            'price_momentum': price_momentum,
            'volume_trend': 'Above average' if (quantities and avg_volume > np.mean(quantities)) else 'Below average'
        }

class DecisionSupportSystem:
    """Intelligent decision support system for Phase 2"""
    
    def __init__(self, market_engine, market_analyzer):
        self.market_engine = market_engine
        self.market_analyzer = market_analyzer
    
    def get_selling_recommendation(self, crop_name, region, user_context=None):
        """Get comprehensive selling recommendation"""
        try:
            current_date = timezone.now().date()
            
            # Get market analysis
            market_trends = self.market_analyzer.analyze_market_trends(crop_name, region)
            current_price = self.market_engine.predict_market_price(crop_name, region, current_date)
            
            if 'error' in market_trends or not current_price:
                return {'error': 'Insufficient data for recommendation'}
            
            # Analyze selling timing
            timing_analysis = self._analyze_selling_timing(market_trends, current_date)
            
            # Analyze market conditions
            market_conditions = self._analyze_market_conditions(market_trends)
            
            # Generate recommendation
            recommendation = self._generate_selling_recommendation(
                market_trends, current_price, timing_analysis, market_conditions
            )
            
            # Risk assessment
            risk_assessment = self._assess_selling_risk(market_trends, current_price)
            
            return {
                'crop_name': crop_name,
                'region': region,
                'current_date': current_date,
                'recommendation': recommendation,
                'timing_analysis': timing_analysis,
                'market_conditions': market_conditions,
                'risk_assessment': risk_assessment,
                'confidence': self._calculate_recommendation_confidence(market_trends),
                'next_actions': self._suggest_next_actions(recommendation, risk_assessment)
            }
            
        except Exception as e:
            print(f"Decision support failed: {e}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _analyze_selling_timing(self, market_trends, current_date):
        """Analyze optimal selling timing"""
        month = current_date.month
        
        # Seasonal timing
        seasonal_timing = self._get_seasonal_timing(month, market_trends)
        
        # Trend-based timing
        trend_timing = self._get_trend_based_timing(market_trends)
        
        # Market sentiment timing
        sentiment_timing = self._get_sentiment_based_timing(market_trends)
        
        # Combine timing factors
        overall_timing = self._combine_timing_factors(seasonal_timing, trend_timing, sentiment_timing)
        
        return {
            'seasonal_timing': seasonal_timing,
            'trend_timing': trend_timing,
            'sentiment_timing': sentiment_timing,
            'overall_timing': overall_timing
        }
    
    def _get_seasonal_timing(self, month, market_trends):
        """Get seasonal timing recommendation"""
        seasonal_pattern = market_trends.get('seasonal_pattern', {})
        
        if 'peak_month' in seasonal_pattern and 'trough_month' in seasonal_pattern:
            peak_month = seasonal_pattern['peak_month']
            trough_month = seasonal_pattern['trough_month']
            
            if month == peak_month:
                return {
                    'recommendation': 'SELL NOW - Peak seasonal prices',
                    'urgency': 'High',
                    'reasoning': 'Currently at seasonal price peak'
                }
            elif month == trough_month:
                return {
                    'recommendation': 'HOLD - Seasonal price trough',
                    'urgency': 'Very Low',
                    'reasoning': 'Prices at seasonal low point'
                }
            elif abs(month - peak_month) <= 1:
                return {
                    'recommendation': 'SELL SOON - Approaching peak',
                    'urgency': 'Medium',
                    'reasoning': 'Close to seasonal price peak'
                }
        
        return {
            'recommendation': 'MODERATE - Standard seasonal timing',
            'urgency': 'Low',
            'reasoning': 'No strong seasonal signals'
        }
    
    def _get_trend_based_timing(self, market_trends):
        """Get trend-based timing recommendation"""
        price_trend = market_trends.get('price_trend', {})
        direction = price_trend.get('direction', 'Unknown')
        strength = price_trend.get('strength', 'Unknown')
        
        if 'Rising' in direction and strength == 'High':
            return {
                'recommendation': 'HOLD - Strong upward trend',
                'urgency': 'Very Low',
                'reasoning': 'Prices rising strongly, wait for peak'
            }
        elif 'Falling' in direction and strength == 'High':
            return {
                'recommendation': 'SELL QUICKLY - Strong downward trend',
                'urgency': 'Very High',
                'reasoning': 'Prices falling rapidly, minimize losses'
            }
        elif 'Stable' in direction:
            return {
                'recommendation': 'FLEXIBLE - Stable prices',
                'urgency': 'Low',
                'reasoning': 'Prices stable, timing less critical'
            }
        
        return {
            'recommendation': 'MODERATE - Mixed trend signals',
            'urgency': 'Medium',
            'reasoning': 'Unclear trend direction'
        }
    
    def _get_sentiment_based_timing(self, market_trends):
        """Get sentiment-based timing recommendation"""
        sentiment = market_trends.get('market_sentiment', {})
        market_sentiment = sentiment.get('sentiment', 'Unknown')
        
        if market_sentiment == 'Bullish':
            return {
                'recommendation': 'HOLD - Bullish market sentiment',
                'urgency': 'Low',
                'reasoning': 'Market optimism suggests higher prices ahead'
            }
        elif market_sentiment == 'Bearish':
            return {
                'recommendation': 'SELL - Bearish market sentiment',
                'urgency': 'High',
                'reasoning': 'Market pessimism suggests lower prices ahead'
            }
        
        return {
            'recommendation': 'NEUTRAL - Balanced sentiment',
            'urgency': 'Medium',
            'reasoning': 'No strong sentiment signals'
        }
    
    def _combine_timing_factors(self, seasonal, trend, sentiment):
        """Combine multiple timing factors into overall recommendation"""
        # Scoring system
        scores = {
            'SELL NOW': 3,
            'SELL QUICKLY': 2,
            'SELL SOON': 1,
            'SELL': 1,
            'FLEXIBLE': 0,
            'MODERATE': 0,
            'NEUTRAL': 0,
            'HOLD': -1,
            'HOLD - Peak seasonal prices': -2
        }
        
        total_score = 0
        total_score += scores.get(seasonal.get('recommendation', ''), 0)
        total_score += scores.get(trend.get('recommendation', ''), 0)
        total_score += scores.get(sentiment.get('recommendation', ''), 0)
        
        # Determine overall recommendation
        if total_score >= 3:
            return {
                'recommendation': 'SELL IMMEDIATELY',
                'urgency': 'Very High',
                'reasoning': 'Multiple factors strongly favor selling'
            }
        elif total_score >= 1:
            return {
                'recommendation': 'SELL SOON',
                'urgency': 'High',
                'reasoning': 'Multiple factors favor selling'
            }
        elif total_score <= -3:
            return {
                'recommendation': 'HOLD STRONGLY',
                'urgency': 'Very Low',
                'reasoning': 'Multiple factors strongly favor holding'
            }
        elif total_score <= -1:
            return {
                'recommendation': 'HOLD',
                'urgency': 'Low',
                'reasoning': 'Multiple factors favor holding'
            }
        else:
            return {
                'recommendation': 'MONITOR CLOSELY',
                'urgency': 'Medium',
                'reasoning': 'Mixed signals, monitor market changes'
            }
    
    def _analyze_market_conditions(self, market_trends):
        """Analyze overall market conditions"""
        volatility = market_trends.get('volatility', {})
        volume_trend = market_trends.get('volume_trend', {})
        
        return {
            'volatility_level': volatility.get('level', 'Unknown'),
            'volume_trend': volume_trend.get('direction', 'Unknown'),
            'market_health': self._assess_market_health(market_trends),
            'opportunity_level': self._assess_opportunity_level(market_trends)
        }
    
    def _assess_market_health(self, market_trends):
        """Assess overall market health"""
        price_trend = market_trends.get('price_trend', {})
        volatility = market_trends.get('volatility', {})
        
        # Health scoring
        health_score = 0
        
        if 'Rising' in price_trend.get('direction', ''):
            health_score += 2
        elif 'Stable' in price_trend.get('direction', ''):
            health_score += 1
        
        if volatility.get('level') in ['Very Low', 'Low']:
            health_score += 1
        elif volatility.get('level') == 'Very High':
            health_score -= 1
        
        if health_score >= 3:
            return 'Excellent'
        elif health_score >= 1:
            return 'Good'
        elif health_score >= 0:
            return 'Fair'
        else:
            return 'Poor'
    
    def _assess_opportunity_level(self, market_trends):
        """Assess market opportunity level"""
        price_trend = market_trends.get('price_trend', {})
        sentiment = market_trends.get('market_sentiment', {})
        
        if 'Rising' in price_trend.get('direction', '') and sentiment.get('sentiment') == 'Bullish':
            return 'High - Rising prices with positive sentiment'
        elif 'Falling' in price_trend.get('direction', '') and sentiment.get('sentiment') == 'Bearish':
            return 'Low - Falling prices with negative sentiment'
        elif 'Stable' in price_trend.get('direction', ''):
            return 'Medium - Stable market conditions'
        else:
            return 'Variable - Mixed market signals'
    
    def _generate_selling_recommendation(self, market_trends, current_price, timing, conditions):
        """Generate final selling recommendation"""
        overall_timing = timing.get('overall_timing', {})
        recommendation = overall_timing.get('recommendation', 'Unknown')
        
        # Price context
        price_context = f"Current ML prediction: ₹{current_price.get('predicted_price_kg', 0):.2f}/kg"
        
        # Market context
        market_context = f"Market health: {conditions.get('market_health', 'Unknown')}"
        
        # Timing context
        timing_context = f"Timing: {overall_timing.get('reasoning', 'No timing data')}"
        
        # Risk context
        risk_level = "Low" if conditions.get('market_health') in ['Excellent', 'Good'] else "Medium" if conditions.get('market_health') == 'Fair' else "High"
        
        return {
            'action': recommendation,
            'price_context': price_context,
            'market_context': market_context,
            'timing_context': timing_context,
            'risk_level': risk_level,
            'confidence': 'High' if market_trends.get('data_points', 0) > 50 else 'Medium' if market_trends.get('data_points', 0) > 20 else 'Low'
        }
    
    def _assess_selling_risk(self, market_trends, current_price):
        """Assess risks associated with selling decision"""
        volatility = market_trends.get('volatility', {})
        price_trend = market_trends.get('price_trend', {})
        
        risk_factors = []
        risk_level = 'Low'
        
        # Volatility risk
        if volatility.get('level') in ['High', 'Very High']:
            risk_factors.append('High price volatility')
            risk_level = 'High'
        
        # Trend risk
        if 'Falling' in price_trend.get('direction', ''):
            risk_factors.append('Downward price trend')
            risk_level = 'Medium' if risk_level == 'Low' else 'High'
        
        # Data quality risk
        if market_trends.get('data_points', 0) < 20:
            risk_factors.append('Limited historical data')
            risk_level = 'Medium' if risk_level == 'Low' else 'High'
        
        return {
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'mitigation_strategies': self._suggest_risk_mitigation(risk_factors)
        }
    
    def _suggest_risk_mitigation(self, risk_factors):
        """Suggest strategies to mitigate identified risks"""
        strategies = []
        
        for risk in risk_factors:
            if 'volatility' in risk.lower():
                strategies.append('Consider selling in smaller batches to average prices')
            elif 'trend' in risk.lower():
                strategies.append('Monitor market closely and be ready to act quickly')
            elif 'data' in risk.lower():
                strategies.append('Use conservative estimates and monitor actual market conditions')
        
        return strategies if strategies else ['No specific mitigation needed']
    
    def _calculate_recommendation_confidence(self, market_trends):
        """Calculate confidence level of recommendation"""
        data_points = market_trends.get('data_points', 0)
        seasonal_confidence = market_trends.get('seasonal_pattern', {}).get('confidence', 'Low')
        
        if data_points > 100 and seasonal_confidence == 'High':
            return 'Very High'
        elif data_points > 50 and seasonal_confidence in ['High', 'Medium']:
            return 'High'
        elif data_points > 20:
            return 'Medium'
        else:
            return 'Low'
    
    def _suggest_next_actions(self, recommendation, risk_assessment):
        """Suggest next actions based on recommendation and risk"""
        actions = []
        
        if 'SELL' in recommendation.get('action', ''):
            actions.append('Prepare crop for immediate sale')
            actions.append('Contact potential buyers')
            if risk_assessment.get('risk_level') == 'High':
                actions.append('Consider insurance or forward contracts')
        elif 'HOLD' in recommendation.get('action', ''):
            actions.append('Monitor market conditions daily')
            actions.append('Prepare storage facilities if needed')
            actions.append('Set price alerts for target levels')
        else:
            actions.append('Continue monitoring market')
            actions.append('Prepare for flexible timing')
        
        return actions

class NaturalLanguageUnderstanding:
    """Phase 3: Advanced Natural Language Understanding for complex farmer queries"""
    
    def __init__(self):
        self.intent_patterns = self._initialize_intent_patterns()
        self.entity_extractors = self._initialize_entity_extractors()
        self.context_manager = ContextManager()
        self.conversation_history = defaultdict(list)
        
    def _initialize_intent_patterns(self):
        """Initialize intent recognition patterns"""
        return {
            'crop_planning': [
                r'\b(plant|grow|cultivate|sow|harvest)\b',
                r'\b(next season|upcoming|future|planning)\b',
                r'\b(what should|could you suggest|recommend)\b.*\b(plant|grow)\b',
                r'\b(best crop|optimal|profitable)\b.*\b(season|time)\b',
                r'\b(season|time)\b.*\b(plant|grow|cultivate)\b',
                r'\b(region|area|place)\b.*\b(plant|grow|cultivate)\b'
            ],
            'market_strategy': [
                r'\b(sell|market|price|timing|when)\b',
                r'\b(best time|optimal|strategy|approach)\b',
                r'\b(negotiate|bargain|deal|terms)\b',
                r'\b(market risk|opportunity|trend)\b',
                r'\b(when.*sell|sell.*when|timing.*sell)\b',
                r'\b(price.*strategy|strategy.*price)\b'
            ],
            'financial_planning': [
                r'\b(cost|investment|profit|revenue|budget)\b',
                r'\b(loan|credit|finance|funding)\b',
                r'\b(break even|ROI|return|profitability)\b',
                r'\b(expense|input|fertilizer|pesticide)\b',
                r'\b(\d+)\s*(budget|cost|investment|rupees?|rs|₹)\b',
                r'\b(budget|cost|investment)\s*(\d+)\b',
                r'\b(how much|cost.*grow|grow.*cost)\b'
            ],
            'risk_assessment': [
                r'\b(risk|danger|threat|problem|issue)\b',
                r'\b(weather|climate|disease|pest)\b',
                r'\b(insurance|protection|safety|mitigation)\b',
                r'\b(what if|scenario|possibility)\b',
                r'\b(risks.*grow|grow.*risks|dangers.*grow)\b',
                r'\b(season.*risk|risk.*season)\b',
                r'\b(protect|protection|safety)\b'
            ],
            'group_strategy': [
                r'\b(group|team|collective|together)\b',
                r'\b(negotiation|bargaining|collaboration)\b',
                r'\b(group decision|consensus|voting)\b',
                r'\b(team performance|group analysis)\b',
                r'\b(collective|bargaining|group.*sell)\b',
                r'\b(team.*strategy|strategy.*team)\b'
            ]
        }
    
    def _initialize_entity_extractors(self):
        """Initialize entity extraction patterns"""
        return {
            'crop': [
                r'\b(potato|onion|tomato|rice|wheat|maize|corn|sugarcane|cotton|pulses|paddy|dal|chana|moong|urad|arhar|masoor)\b',
                r'\b(vegetables|fruits|grains|cereals|oilseeds|spices|herbs)\b',
                r'\b(brinjal|cauliflower|cabbage|carrot|beetroot|radish|turnip|peas|beans|okra|bitter gourd|pumpkin)\b',
                r'\b(mango|banana|orange|apple|grapes|watermelon|muskmelon|papaya|guava|pomegranate)\b'
            ],
            'region': [
                r'\b(andhra pradesh|maharashtra|karnataka|tamil nadu|punjab|haryana|uttar pradesh|bihar|west bengal|odisha|gujarat|rajasthan|madhya pradesh)\b',
                r'\b(district|taluk|village|city|state|zone|area)\b'
            ],
            'time': [
                r'\b(today|tomorrow|next week|next month|next season|harvest time|planting time|sowing time)\b',
                r'\b(monsoon|summer|winter|spring|autumn|kharif|rabi|zaid)\b',
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
                r'\b(this season|current season|upcoming season|last season)\b'
            ],
            'quantity': [
                r'\b(\d+)\s*(kg|quintal|ton|acre|hectare|bigha|guntha)\b',
                r'\b(small|medium|large|high|low)\s*(quantity|amount|volume|area|land)\b'
            ],
            'budget': [
                r'\b(\d+)\s*(rupees?|rs|₹|inr|thousand|lakh|crore)\b',
                r'\b(budget|cost|investment|expense|money|capital)\s*(\d+)\b',
                r'\b(\d+)\s*(budget|cost|investment|expense|money|capital)\b'
            ],
            'risk_level': [
                r'\b(high|medium|low)\s*risk\b',
                r'\b(risky|safe|dangerous|secure)\b'
            ]
        }
    
    def understand_query(self, query, user_id=None, conversation_id=None):
        """Understand natural language query and extract intent and entities"""
        try:
            query_lower = query.lower().strip()
            
            # Extract intent
            intent = self._extract_intent(query_lower)
            
            # Extract entities
            entities = self._extract_entities(query_lower)
            
            # Get conversation context
            context = self.context_manager.get_context(user_id, conversation_id)
            
            # Update conversation history
            if user_id and conversation_id:
                self.conversation_history[f"{user_id}_{conversation_id}"].append({
                    'query': query,
                    'intent': intent,
                    'entities': entities,
                    'timestamp': timezone.now()
                })
            
            return {
                'status': 'success',
                'intent': intent,
                'entities': entities,
                'context': context,
                'confidence': self._calculate_confidence(intent, entities),
                'phase': 'Phase 3 - Advanced NLU'
            }
            
        except Exception as e:
            logger.error(f"NLU understanding failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 3 - Advanced NLU'
            }
    
    def _extract_intent(self, query):
        """Extract primary intent from query"""
        intent_scores = defaultdict(int)
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    intent_scores[intent] += 1
        
        if intent_scores:
            primary_intent = max(intent_scores, key=intent_scores.get)
            return {
                'primary': primary_intent,
                'confidence': min(intent_scores[primary_intent] / 2, 1.0),
                'alternatives': [k for k, v in intent_scores.items() if v > 0 and k != primary_intent]
            }
        
        return {
            'primary': 'general_query',
            'confidence': 0.5,
            'alternatives': []
        }
    
    def _extract_entities(self, query):
        """Extract entities from query"""
        entities = {}
        
        for entity_type, patterns in self.entity_extractors.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, query, re.IGNORECASE)
                matches.extend(found)
            
            if matches:
                entities[entity_type] = list(set(matches))
        
        return entities
    
    def _calculate_confidence(self, intent, entities):
        """Calculate confidence score for understanding"""
        intent_conf = intent.get('confidence', 0.5)
        entity_score = min(len(entities) / 3, 1.0) if entities else 0.5
        
        # Weighted average: intent (70%) + entities (30%)
        confidence = (intent_conf * 0.7) + (entity_score * 0.3)
        
        if confidence > 0.8:
            return 'High'
        elif confidence > 0.6:
            return 'Medium'
        else:
            return 'Low'
    
    def get_conversation_context(self, user_id, conversation_id):
        """Get conversation context for multi-turn conversations"""
        key = f"{user_id}_{conversation_id}"
        if key in self.conversation_history:
            recent_messages = self.conversation_history[key][-5:]  # Last 5 messages
            return {
                'recent_intents': [msg['intent']['primary'] for msg in recent_messages],
                'recent_entities': [msg['entities'] for msg in recent_messages],
                'conversation_length': len(self.conversation_history[key]),
                'last_query_time': recent_messages[-1]['timestamp'] if recent_messages else None
            }
        return {}

class ContextManager:
    """Manages conversation and user context for Phase 3"""
    
    def __init__(self):
        self.user_contexts = defaultdict(dict)
        self.conversation_contexts = defaultdict(dict)
    
    def get_context(self, user_id, conversation_id):
        """Get combined user and conversation context"""
        user_context = self.user_contexts.get(user_id, {})
        conv_context = self.conversation_contexts.get(conversation_id, {})
        
        return {
            'user_profile': user_context.get('profile', {}),
            'recent_queries': user_context.get('recent_queries', []),
            'preferences': user_context.get('preferences', {}),
            'conversation_state': conv_context.get('state', 'initial'),
            'referenced_entities': conv_context.get('referenced_entities', {})
        }
    
    def update_context(self, user_id, conversation_id, updates):
        """Update context with new information"""
        if user_id:
            self.user_contexts[user_id].update(updates.get('user', {}))
        
        if conversation_id:
            self.conversation_contexts[conversation_id].update(updates.get('conversation', {}))

class LearningAdaptation:
    """Phase 3: Learning and adaptation system for continuous improvement"""
    
    def __init__(self):
        self.learning_data = defaultdict(list)
        self.success_metrics = defaultdict(dict)
        self.adaptation_rules = self._initialize_adaptation_rules()
        self.performance_tracker = PerformanceTracker()
        
    def _initialize_adaptation_rules(self):
        """Initialize rules for system adaptation"""
        return {
            'price_prediction': {
                'accuracy_threshold': 0.8,
                'improvement_actions': ['retrain_model', 'adjust_features', 'update_weights'],
                'fallback_strategy': 'historical_average'
            },
            'timing_recommendations': {
                'success_threshold': 0.7,
                'improvement_actions': ['refine_seasonal_patterns', 'update_market_conditions', 'adjust_urgency_levels'],
                'fallback_strategy': 'conservative_timing'
            },
            'risk_assessment': {
                'accuracy_threshold': 0.75,
                'improvement_actions': ['update_risk_factors', 'refine_thresholds', 'add_new_indicators'],
                'fallback_strategy': 'high_risk_assumption'
            }
        }
    
    def learn_from_outcome(self, prediction_id, actual_outcome, user_feedback=None):
        """Learn from prediction outcomes and user feedback"""
        try:
            # Store learning data
            learning_entry = {
                'prediction_id': prediction_id,
                'actual_outcome': actual_outcome,
                'user_feedback': user_feedback,
                'timestamp': timezone.now(),
                'success_score': self._calculate_success_score(actual_outcome, user_feedback)
            }
            
            self.learning_data[prediction_id] = learning_entry
            
            # Update success metrics
            self._update_success_metrics(prediction_id, learning_entry)
            
            # Check if adaptation is needed
            adaptation_needed = self._check_adaptation_needs(prediction_id)
            
            return {
                'status': 'success',
                'learning_applied': True,
                'success_score': learning_entry['success_score'],
                'adaptation_needed': adaptation_needed,
                'phase': 'Phase 3 - Learning & Adaptation'
            }
            
        except Exception as e:
            logger.error(f"Learning from outcome failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 3 - Learning & Adaptation'
            }
    
    def _calculate_success_score(self, actual_outcome, user_feedback):
        """Calculate success score based on outcome and feedback"""
        base_score = 0.5
        
        # Adjust based on actual outcome
        if actual_outcome.get('price_accuracy', 0) > 0.9:
            base_score += 0.3
        elif actual_outcome.get('price_accuracy', 0) > 0.7:
            base_score += 0.1
        else:
            base_score -= 0.2
        
        # Adjust based on user feedback
        if user_feedback:
            if user_feedback.get('satisfaction', 0) > 0.8:
                base_score += 0.2
            elif user_feedback.get('satisfaction', 0) < 0.4:
                base_score -= 0.2
        
        return max(0.0, min(1.0, base_score))
    
    def _update_success_metrics(self, prediction_id, learning_entry):
        """Update success metrics for different prediction types"""
        prediction_type = prediction_id.split('_')[0] if '_' in prediction_id else 'general'
        
        if prediction_type not in self.success_metrics:
            self.success_metrics[prediction_type] = {
                'total_predictions': 0,
                'successful_predictions': 0,
                'average_success_score': 0.0,
                'recent_performance': []
            }
        
        metrics = self.success_metrics[prediction_type]
        metrics['total_predictions'] += 1
        
        if learning_entry['success_score'] > 0.7:
            metrics['successful_predictions'] += 1
        
        # Update average success score
        current_avg = metrics['average_success_score']
        total = metrics['total_predictions']
        new_avg = ((current_avg * (total - 1)) + learning_entry['success_score']) / total
        metrics['average_success_score'] = new_avg
        
        # Update recent performance (last 10)
        metrics['recent_performance'].append(learning_entry['success_score'])
        if len(metrics['recent_performance']) > 10:
            metrics['recent_performance'].pop(0)
    
    def _check_adaptation_needs(self, prediction_id):
        """Check if system adaptation is needed"""
        prediction_type = prediction_id.split('_')[0] if '_' in prediction_id else 'general'
        
        if prediction_type in self.success_metrics:
            metrics = self.success_metrics[prediction_type]
            recent_avg = np.mean(metrics['recent_performance']) if metrics['recent_performance'] else 0.5
            
            # Check against adaptation rules
            if prediction_type in self.adaptation_rules:
                rule = self.adaptation_rules[prediction_type]
                threshold = rule['accuracy_threshold']
                
                if recent_avg < threshold:
                    return {
                        'needed': True,
                        'type': prediction_type,
                        'current_performance': recent_avg,
                        'threshold': threshold,
                        'suggested_actions': rule['improvement_actions']
                    }
        
        return {'needed': False}
    
    def _analyze_recent_trend(self, recent_performance):
        """Analyze recent performance trend"""
        if not recent_performance or len(recent_performance) < 2:
            return 'Insufficient data'
        
        if len(recent_performance) < 5:
            return 'Limited data'
        
        # Calculate trend
        recent_avg = np.mean(recent_performance[-5:])  # Last 5
        earlier_avg = np.mean(recent_performance[:-5]) if len(recent_performance) >= 10 else np.mean(recent_performance[:5])
        
        if recent_avg > earlier_avg + 0.1:
            return 'Improving'
        elif recent_avg < earlier_avg - 0.1:
            return 'Declining'
        else:
            return 'Stable'
    
    def get_learning_insights(self, prediction_type=None):
        """Get insights from learning data"""
        try:
            if prediction_type:
                metrics = self.success_metrics.get(prediction_type, {})
                return {
                    'status': 'success',
                    'prediction_type': prediction_type,
                    'total_predictions': metrics.get('total_predictions', 0),
                    'success_rate': (metrics.get('successful_predictions', 0) / max(metrics.get('total_predictions', 1), 1)) * 100,
                    'average_success_score': metrics.get('average_success_score', 0.0),
                    'recent_trend': self._analyze_recent_trend(metrics.get('recent_performance', [])),
                    'adaptation_needed': self._check_adaptation_needs(f"{prediction_type}_test"),
                    'phase': 'Phase 3 - Learning & Adaptation'
                }
            else:
                # Overall insights
                overall_metrics = {}
                for ptype, metrics in self.success_metrics.items():
                    overall_metrics[ptype] = {
                        'success_rate': (metrics.get('successful_predictions', 0) / max(metrics.get('total_predictions', 1), 1)) * 100,
                        'average_score': metrics.get('average_success_score', 0.0)
                    }
                
                return {
                    'status': 'success',
                    'overall_performance': overall_metrics,
                    'total_prediction_types': len(self.success_metrics),
                    'learning_data_points': len(self.learning_data),
                    'phase': 'Phase 3 - Learning & Adaptation'
                }
                
        except Exception as e:
            logger.error(f"Getting learning insights failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 3 - Learning & Adaptation'
            }
    
    def _analyze_recent_trend(self, recent_performance):
        """Analyze recent performance trend"""
        if len(recent_performance) < 2:
            return 'Insufficient data'
        
        if len(recent_performance) >= 2:
            recent_avg = np.mean(recent_performance[-3:])  # Last 3
            previous_avg = np.mean(recent_performance[:-3]) if len(recent_performance) > 3 else recent_performance[0]
            
            if recent_avg > previous_avg + 0.1:
                return 'Improving'
            elif recent_avg < previous_avg - 0.1:
                return 'Declining'
            else:
                return 'Stable'

class PerformanceTracker:
    """Tracks system performance metrics for Phase 3"""
    
    def __init__(self):
        self.performance_metrics = defaultdict(list)
        self.benchmarks = self._initialize_benchmarks()
    
    def _initialize_benchmarks(self):
        """Initialize performance benchmarks"""
        return {
            'response_time': {'excellent': 0.5, 'good': 1.0, 'acceptable': 2.0},
            'accuracy': {'excellent': 0.9, 'good': 0.8, 'acceptable': 0.7},
            'user_satisfaction': {'excellent': 0.9, 'good': 0.8, 'acceptable': 0.7}
        }
    
    def track_performance(self, metric_type, value, context=None):
        """Track a performance metric"""
        entry = {
            'value': value,
            'timestamp': timezone.now(),
            'context': context or {},
            'benchmark': self._get_benchmark_rating(metric_type, value)
        }
        
        self.performance_metrics[metric_type].append(entry)
        
        # Keep only last 100 entries per metric
        if len(self.performance_metrics[metric_type]) > 100:
            self.performance_metrics[metric_type].pop(0)
    
    def _get_benchmark_rating(self, metric_type, value):
        """Get benchmark rating for a metric value"""
        if metric_type in self.benchmarks:
            benchmarks = self.benchmarks[metric_type]
            
            if metric_type == 'response_time':  # Lower is better
                if value <= benchmarks['excellent']:
                    return 'excellent'
                elif value <= benchmarks['good']:
                    return 'good'
                elif value <= benchmarks['acceptable']:
                    return 'acceptable'
                else:
                    return 'poor'
            else:  # Higher is better
                if value >= benchmarks['excellent']:
                    return 'excellent'
                elif value >= benchmarks['good']:
                    return 'good'
                elif value >= benchmarks['acceptable']:
                    return 'acceptable'
                else:
                    return 'poor'
        
        return 'unknown'

class AgriGenieAdvisor:
    """Main AI advisor that orchestrates all intelligence services - Phase 3 Complete"""
    
    def __init__(self):
        # Phase 1 & 2 components
        self.market_engine = MarketIntelligenceEngine()
        self.crop_advisor = CropAdvisor(self.market_engine)
        self.group_intelligence = GroupIntelligence()
        self.market_analyzer = MarketAnalysisEngine(self.market_engine)
        self.decision_support = DecisionSupportSystem(self.market_engine, self.market_analyzer)
        
        # Phase 3: Advanced AI Capabilities
        self.nlu_engine = NaturalLanguageUnderstanding()
        self.learning_system = LearningAdaptation()
        
        # Phase 3: Comprehensive Advisory Services
        self.crop_planning_advisor = self.crop_advisor
        self.market_strategy_advisor = MarketStrategyAdvisor(self.market_analyzer, self.decision_support)
        
        # Phase 3: Integration & Automation
        self.notification_system = SmartNotificationSystem()
        self.automation_system = AutomatedActionSystem(self.market_engine, self.decision_support)
        
        # Phase 3: Knowledge Base Integration
        self.knowledge_base_enabled = True
        
        print("🚀 Phase 3 AI Agricultural Advisor with Knowledge Base integration initialized successfully!")
    
    def understand_and_respond(self, query, user_id=None, conversation_id=None, user_context=None):
        """Phase 3: Advanced natural language understanding and response generation"""
        try:
            # Start performance tracking
            start_time = timezone.now()
            
            # Understand the query using NLU
            understanding = self.nlu_engine.understand_query(query, user_id, conversation_id)
            
            if understanding['status'] == 'error':
                return understanding
            
            # Get intent and entities
            intent = understanding['intent']['primary']
            entities = understanding['entities']
            confidence = understanding['confidence']
            
            # Check if this is an MSP query
            if 'msp' in query.lower() or 'minimum support price' in query.lower():
                response = self._handle_msp_query(query, entities, user_context)
            elif intent == 'crop_planning':
                response = self._handle_crop_planning_query(query, entities, user_context)
            elif intent == 'market_strategy':
                response = self._handle_market_strategy_query(query, entities, user_context)
            elif intent == 'financial_planning':
                response = self._handle_financial_planning_query(query, entities, user_context)
            elif intent == 'risk_assessment':
                response = self._handle_risk_assessment_query(query, entities, user_context)
            elif intent == 'group_strategy':
                response = self._handle_group_strategy_query(query, entities, user_context)
            else:
                response = self._handle_general_query(query, entities, user_context)
            
            # Add understanding metadata
            response['nlu_understanding'] = understanding
            response['confidence'] = confidence
            
            # Track performance
            end_time = timezone.now()
            response_time = (end_time - start_time).total_seconds()
            self.learning_system.performance_tracker.track_performance('response_time', response_time, {
                'intent': intent,
                'confidence': confidence,
                'query_length': len(query)
            })
            
            # Check for automation triggers
            if entities.get('crop') and entities.get('region'):
                crop_name = entities['crop'][0]
                region = entities['region'][0]
                
                # Get market data for automation checks
                market_data = self.market_engine.analyze_market_trends(crop_name, region, 90)
                
                # Check notifications
                notifications = self.notification_system.check_notification_triggers(crop_name, region, market_data)
                if notifications:
                    response['smart_notifications'] = notifications
                
                # Check automation triggers
                automation_actions = self.automation_system.check_automation_triggers(crop_name, region, market_data, user_context)
                if automation_actions:
                    response['automation_suggestions'] = automation_actions
            
            return response
            
        except Exception as e:
            logger.error(f"Understanding and response generation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 3 - Advanced NLU & Response'
            }
    
    def _handle_crop_planning_query(self, query, entities, user_context):
        """Handle crop planning queries"""
        region = entities.get('region', ['Andhra Pradesh'])[0]
        season = entities.get('time', [None])[0]
        risk_tolerance = user_context.get('risk_tolerance', 'medium') if user_context else 'medium'
        
        advice = self.crop_planning_advisor.get_crop_planning_advice(
            region, season, None, risk_tolerance
        )
        
        return {
            'status': 'success',
            'query': query,
            'response_type': 'crop_planning_advice',
            'intent': 'crop_planning',
            'advice': advice,
            'summary': f"Comprehensive crop planning advice for {region}",
            'key_recommendations': [
                f"Recommended season: {advice.get('recommended_season', 'Unknown')}",
                f"Top crop: {advice.get('top_recommendations', [{}])[0].get('crop', 'Unknown') if advice.get('top_recommendations') else 'Unknown'}",
                f"Expected ROI: {advice.get('financial_plan', {}).get('roi_percentage', 0):.1f}%"
            ],
            'next_actions': advice.get('next_actions', []),
            'phase': 'Phase 3 - Crop Planning Advisor'
        }
    
    def _handle_market_strategy_query(self, query, entities, user_context):
        """Handle market strategy queries"""
        crop_name = entities.get('crop', ['Potato'])[0]
        region = entities.get('region', ['Andhra Pradesh'])[0]
        quantity = entities.get('quantity', ['1000'])[0] if entities.get('quantity') else '1000'
        
        strategy = self.market_strategy_advisor.get_comprehensive_market_strategy(
            crop_name, region, quantity, user_context
        )
        
        return {
            'status': 'success',
            'query': query,
            'response_type': 'market_strategy',
            'intent': 'market_strategy',
            'strategy': strategy,
            'summary': f"Comprehensive market strategy for {crop_name} in {region}",
            'key_insights': [
                f"Market type: {strategy.get('market_type', 'Unknown')}",
                f"Timing: {strategy.get('timing_strategy', {}).get('recommendation', 'Unknown')}",
                f"Target price: ₹{strategy.get('pricing_strategy', {}).get('target_price', 0):.2f}/quintal"
            ],
            'action_plan': strategy.get('action_plan', []),
            'phase': 'Phase 3 - Market Strategy Advisor'
        }
    
    def _handle_financial_planning_query(self, query, entities, user_context):
        """Handle financial planning queries"""
        # This would integrate with financial planning systems
        return {
            'status': 'success',
            'query': query,
            'response_type': 'financial_planning',
            'intent': 'financial_planning',
            'message': "I can help you with financial planning for your agricultural operations. This includes cost analysis, ROI calculations, and financing recommendations.",
            'capabilities': [
                'Input cost analysis and optimization',
                'ROI calculations for different crops',
                'Financing option recommendations',
                'Risk-adjusted return analysis',
                'Budget planning and tracking'
            ],
            'next_steps': [
                'Specify the crop and region for detailed analysis',
                'Provide your budget constraints and risk tolerance',
                'Ask about specific financial aspects (costs, returns, financing)'
            ],
            'phase': 'Phase 3 - Financial Planning'
        }
    
    def _handle_risk_assessment_query(self, query, entities, user_context):
        """Handle risk assessment queries"""
        crop_name = entities.get('crop', ['Potato'])[0]
        region = entities.get('region', ['Andhra Pradesh'])[0]
        
        # Get comprehensive risk assessment
        market_analysis = self.market_engine.analyze_market_trends(crop_name, region, 180)
        decision_recommendation = self.decision_support.get_selling_recommendation(crop_name, region, user_context)
        
        return {
            'status': 'success',
            'query': query,
            'response_type': 'risk_assessment',
            'intent': 'risk_assessment',
            'risk_analysis': {
                'market_risks': market_analysis.get('volatility', {}),
                'timing_risks': decision_recommendation.get('risk_assessment', {}),
                'overall_risk_level': self._calculate_overall_risk(market_analysis, decision_recommendation)
            },
            'summary': f"Comprehensive risk assessment for {crop_name} in {region}",
            'mitigation_strategies': [
                'Diversify crop portfolio',
                'Implement crop insurance',
                'Monitor market conditions closely',
                'Consider alternative markets',
                'Build emergency funds'
            ],
            'phase': 'Phase 3 - Risk Assessment'
        }
    
    def _handle_group_strategy_query(self, query, entities, user_context):
        """Handle group strategy queries"""
        # This would integrate with group intelligence systems
        return {
            'status': 'success',
            'query': query,
            'response_type': 'group_strategy',
            'intent': 'group_strategy',
            'message': "I can help you with group strategies for collective bargaining, risk sharing, and market optimization.",
            'capabilities': [
                'Group performance analysis',
                'Collective bargaining strategies',
                'Risk sharing mechanisms',
                'Group decision optimization',
                'Market entry coordination'
            ],
            'next_steps': [
                'Provide your group ID or context',
                'Specify the type of group strategy needed',
                'Ask about specific group challenges or opportunities'
            ],
            'phase': 'Phase 3 - Group Strategy'
        }
    
    def _handle_general_query(self, query, entities, user_context):
        """Handle general queries"""
        return {
            'status': 'success',
            'query': query,
            'response_type': 'general_query',
            'intent': 'general_query',
            'message': f"I'm AgriGenie, your advanced AI agricultural advisor. I can help with comprehensive crop planning, market strategies, financial analysis, risk assessment, and group coordination.",
            'capabilities': [
                'Advanced Natural Language Understanding',
                'Comprehensive Crop Planning & Financial Analysis',
                'Intelligent Market Strategy & Negotiation Support',
                'Risk Assessment & Mitigation Strategies',
                'Group Intelligence & Collective Decision Making',
                'Smart Notifications & Automated Actions'
            ],
            'examples': [
                'What should I plant next season in Maharashtra?',
                'When is the best time to sell potatoes with optimal pricing?',
                'How can I optimize my crop portfolio for better returns?',
                'What are the risks for growing tomatoes this season?',
                'How can my group negotiate better prices collectively?'
            ],
            'phase': 'Phase 3 - Advanced AI Advisor'
        }
    
    def _calculate_overall_risk(self, market_analysis, decision_recommendation):
        """Calculate overall risk level"""
        risk_factors = []
        
        # Market volatility risk
        volatility = market_analysis.get('volatility', {}).get('level', 'Unknown')
        if volatility in ['High', 'Very High']:
            risk_factors.append('High market volatility')
        
        # Price trend risk
        price_trend = market_analysis.get('price_trend', {}).get('direction', 'Unknown')
        if price_trend in ['Strongly Falling', 'Falling']:
            risk_factors.append('Declining price trend')
        
        # Decision support risk
        decision_risk = decision_recommendation.get('recommendation', {}).get('risk_level', 'Unknown')
        if decision_risk == 'High':
            risk_factors.append('High decision risk')
        
        # Determine overall risk level
        if len(risk_factors) >= 2:
            return 'High'
        elif len(risk_factors) == 1:
            return 'Medium'
        else:
            return 'Low'
    
    # Phase 2 methods (maintained for backward compatibility)
    def get_enhanced_market_analysis(self, crop_name, region, timeframe_days=90):
        """Phase 2: Get enhanced market analysis with trends and sentiment"""
        try:
            analysis = self.market_analyzer.analyze_market_trends(crop_name, region, timeframe_days)
            return {
                'status': 'success',
                'analysis': analysis,
                'generated_at': timezone.now(),
                'phase': 'Phase 2 - Enhanced Market Intelligence'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 2 - Enhanced Market Intelligence'
            }
    
    def get_intelligent_selling_recommendation(self, crop_name, region, user_context=None):
        """Phase 2: Get intelligent selling recommendation with risk assessment"""
        try:
            recommendation = self.decision_support.get_selling_recommendation(crop_name, region, user_context)
            return {
                'status': 'success',
                'recommendation': recommendation,
                'generated_at': timezone.now(),
                'phase': 'Phase 2 - Intelligent Decision Support'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 2 - Intelligent Decision Support'
            }
    
    def get_market_intelligence_summary(self, crop_name, region):
        """Phase 2: Get comprehensive market intelligence summary"""
        try:
            # Get all types of analysis
            basic_advice = self.crop_advisor.get_crop_advice(crop_name, region)
            market_trends = self.market_analyzer.analyze_market_trends(crop_name, region)
            selling_recommendation = self.decision_support.get_selling_recommendation(crop_name, region)
            
            return {
                'status': 'success',
                'summary': {
                    'basic_advice': basic_advice,
                    'market_trends': market_trends,
                    'selling_recommendation': selling_recommendation
                },
                'generated_at': timezone.now(),
                'phase': 'Phase 2 - Comprehensive Intelligence'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 2 - Comprehensive Intelligence'
            }
    
    # Phase 3: New comprehensive methods
    def get_comprehensive_agricultural_advice(self, query, user_id=None, conversation_id=None, user_context=None):
        """Phase 3: Get comprehensive agricultural advice using advanced AI"""
        return self.understand_and_respond(query, user_id, conversation_id, user_context)
    
    def get_crop_planning_advice(self, region, season=None, budget_constraint=None, risk_tolerance='medium'):
        """Phase 3: Get comprehensive crop planning advice"""
        return self.crop_planning_advisor.get_crop_planning_advice(region, season, budget_constraint, risk_tolerance)
    
    def get_market_strategy_advice(self, crop_name, region, quantity, user_context=None):
        """Phase 3: Get comprehensive market strategy advice"""
        return self.market_strategy_advisor.get_comprehensive_market_strategy(crop_name, region, quantity, user_context)
    
    def get_smart_notifications(self, crop_name, region):
        """Phase 3: Get smart notifications for market conditions"""
        try:
            market_data = self.market_engine.analyze_market_trends(crop_name, region, 90)
            notifications = self.notification_system.check_notification_triggers(crop_name, region, market_data)
            
            return {
                'status': 'success',
                'notifications': notifications,
                'generated_at': timezone.now(),
                'phase': 'Phase 3 - Smart Notifications'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 3 - Smart Notifications'
            }
    
    def get_automation_suggestions(self, crop_name, region, user_context=None):
        """Phase 3: Get automation suggestions for market conditions"""
        try:
            market_data = self.market_engine.analyze_market_trends(crop_name, region, 90)
            automation_actions = self.automation_system.check_automation_triggers(crop_name, region, market_data, user_context)
            
            return {
                'status': 'success',
                'automation_actions': automation_actions,
                'generated_at': timezone.now(),
                'phase': 'Phase 3 - Automated Actions'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 3 - Automated Actions'
            }
    
    def get_learning_insights(self, prediction_type=None):
        """Phase 3: Get learning and adaptation insights"""
        return self.learning_system.get_learning_insights(prediction_type)
    
    def learn_from_outcome(self, prediction_id, actual_outcome, user_feedback=None):
        """Phase 3: Learn from prediction outcomes and user feedback"""
        return self.learning_system.learn_from_outcome(prediction_id, actual_outcome, user_feedback)
    
    def get_phase3_capabilities_summary(self):
        """Phase 3: Get comprehensive capabilities summary"""
        return {
            'status': 'success',
            'phase': 'Phase 3 - Advanced AI & Integration',
            'capabilities': {
                'advanced_ai': {
                    'natural_language_understanding': 'Complex farmer queries in natural language',
                    'learning_adaptation': 'Continuous improvement from outcomes and feedback',
                    'context_awareness': 'Multi-turn conversations with memory'
                },
                'comprehensive_advisory': {
                    'crop_planning': 'Seasonal planning with financial analysis and risk assessment',
                    'market_strategy': 'Advanced market timing and negotiation strategies',
                    'financial_planning': 'Cost analysis, ROI calculations, and financing options'
                },
                'integration_automation': {
                    'smart_notifications': 'Intelligent alerts for market opportunities and risks',
                    'automated_actions': 'Proactive responses to market conditions',
                    'performance_tracking': 'Continuous monitoring and optimization'
                }
            },
            'data_integration': 'Successfully integrated with 7 lakh rows of market data',
            'ml_models': 'Advanced analytics with continuous learning',
            'user_experience': 'Natural language interface with proactive intelligence',
            'generated_at': timezone.now()
        }
    
    def get_knowledge_base_status(self):
        """Get status of knowledge base integration"""
        try:
            total_chunks = KnowledgeChunk.objects.count()
            recent_chunks = KnowledgeChunk.objects.order_by('-id')[:5]
            
            # Check for MSP-related content
            msp_chunks = KnowledgeChunk.objects.filter(
                Q(content__icontains='MSP') | 
                Q(content__icontains='Minimum Support Price')
            ).count()
            
            return {
                'status': 'success',
                'knowledge_base_enabled': self.knowledge_base_enabled,
                'total_chunks': total_chunks,
                'msp_related_chunks': msp_chunks,
                'recent_sources': [chunk.source for chunk in recent_chunks],
                'phase': 'Phase 3 - Knowledge Base Integration'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'knowledge_base_enabled': self.knowledge_base_enabled,
                'phase': 'Phase 3 - Knowledge Base Integration'
            }
    
    def search_knowledge_base(self, query, limit=5):
        """Search knowledge base for relevant information"""
        try:
            # Simple text-based search for now
            # In production, you'd use vector similarity search
            chunks = KnowledgeChunk.objects.filter(
                Q(content__icontains=query) |
                Q(source__icontains=query)
            )[:limit]
            
            results = []
            for chunk in chunks:
                results.append({
                    'content': chunk.content,
                    'source': chunk.source,
                    'relevance_score': self._calculate_relevance(chunk.content, query)
                })
            
            # Sort by relevance
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results
            
        except Exception as e:
            print(f"Knowledge base search failed: {e}")
            return []
    
    def _calculate_relevance(self, content, query):
        """Calculate simple relevance score"""
        query_words = query.lower().split()
        content_lower = content.lower()
        
        score = 0
        for word in query_words:
            if word in content_lower:
                score += 1
        
        return score / len(query_words) if query_words else 0
    
    def get_msp_information(self, crop_name=None, season=None):
        """Get MSP information from knowledge base"""
        try:
            # Search for MSP-related information
            query = "MSP"  # Keep it simple - just search for MSP
            # Don't modify query - it breaks the search
            # if crop_name:
            #     query += f" {crop_name}"
            # if season:
            #     query += f" {season}"
            
            chunks = self.search_knowledge_base(query, limit=10)
            
            if not chunks:
                return None
            
            # Extract MSP data from chunks
            msp_data = []
            for chunk in chunks:
                if 'MSP' in chunk['content'] or 'Minimum Support Price' in chunk['content']:
                    msp_data.append({
                        'content': chunk['content'],
                        'source': chunk['source'],
                        'relevance': chunk['relevance_score']
                    })
            
            return msp_data
            
        except Exception as e:
            print(f"MSP information retrieval failed: {e}")
            return None
    
    def _extract_msp_values(self, msp_data, crop_name):
        """Extract specific MSP values from knowledge chunks"""
        extracted = {}
        
        for data in msp_data:
            content = data['content']
            
            # Look for MSP patterns in the content
            if 'MSP' in content and '2025-26' in content:
                # Extract crop-specific MSP values
                if crop_name and crop_name.lower() in content.lower():
                    # Use regex to extract price values
                    import re
                    price_match = re.search(r'₹?(\d+(?:,\d+)*)', content)
                    if price_match:
                        extracted['msp_price'] = price_match.group(1)
                        extracted['source'] = data['source']
                        extracted['content_snippet'] = content[:200] + "..."
        
        return extracted
    
    def _handle_msp_query(self, query, entities, user_context):
        """Handle MSP-specific queries"""
        crop_name = entities.get('crop', [None])[0]
        season = entities.get('time', ['Rabi'])[0]
        
        # Get MSP information from knowledge base
        msp_data = self.get_msp_information(crop_name, season)
        
        if msp_data:
            # Extract specific MSP values
            msp_values = self._extract_msp_values(msp_data, crop_name)
            
            return {
                'status': 'success',
                'query': query,
                'response_type': 'msp_information',
                'intent': 'msp_query',
                'msp_data': msp_data,
                'extracted_values': msp_values,
                'summary': f"MSP information for {season} crops from knowledge base",
                'source': 'Government MSP Document (Knowledge Base)',
                'phase': 'Phase 3 - MSP Advisor with Knowledge Base'
            }
        else:
            return {
                'status': 'success',
                'query': query,
                'response_type': 'msp_information',
                'intent': 'msp_query',
                'message': "MSP information not found in knowledge base. Please check if the document has been properly processed.",
                'phase': 'Phase 3 - MSP Advisor'
            }

class CropPlanningAdvisor:
    """Phase 3: Comprehensive crop planning advisor with financial analysis"""
    
    def __init__(self, market_engine):
        self.market_engine = market_engine
        self.crop_cycles = self._initialize_crop_cycles()
        self.input_costs = self._initialize_input_costs()
        self.weather_patterns = self._initialize_weather_patterns()
    
    def _initialize_crop_cycles(self):
        """Initialize crop growing cycles and seasons"""
        return {
            'kharif': {
                'months': [6, 7, 8, 9, 10],  # June to October
                'crops': ['rice', 'maize', 'cotton', 'sugarcane', 'pulses'],
                'characteristics': 'Monsoon dependent, high water requirement'
            },
            'rabi': {
                'months': [11, 12, 1, 2, 3],  # November to March
                'crops': ['wheat', 'barley', 'mustard', 'chickpea', 'potato'],
                'characteristics': 'Winter crops, moderate water requirement'
            },
            'zaid': {
                'months': [3, 4, 5],  # March to May
                'crops': ['vegetables', 'fruits', 'pulses'],
                'characteristics': 'Short duration, high value crops'
            }
        }
    
    def _initialize_input_costs(self):
        """Initialize typical input costs per acre"""
        return {
            'seeds': {'low': 2000, 'medium': 3500, 'high': 5000},
            'fertilizers': {'low': 3000, 'medium': 5000, 'high': 8000},
            'pesticides': {'low': 1500, 'medium': 2500, 'high': 4000},
            'irrigation': {'low': 1000, 'medium': 2000, 'high': 3500},
            'labor': {'low': 8000, 'medium': 12000, 'high': 18000},
            'machinery': {'low': 3000, 'medium': 5000, 'high': 8000}
        }
    
    def _initialize_weather_patterns(self):
        """Initialize weather patterns for different regions"""
        return {
            'andhra pradesh': {
                'monsoon': 'June-September',
                'rainfall': 'Heavy (800-1200mm)',
                'temperature': 'Hot (25-35°C)',
                'best_season': 'kharif'
            },
            'maharashtra': {
                'monsoon': 'June-September',
                'rainfall': 'Moderate (600-1000mm)',
                'temperature': 'Moderate (20-30°C)',
                'best_season': 'kharif'
            },
            'punjab': {
                'monsoon': 'July-September',
                'rainfall': 'Low (400-600mm)',
                'temperature': 'Extreme (5-40°C)',
                'best_season': 'rabi'
            }
        }
    
    def get_crop_planning_advice(self, region, season=None, budget_constraint=None, risk_tolerance='medium'):
        """Get comprehensive crop planning advice"""
        try:
            # Determine optimal season if not specified
            if not season:
                season = self._get_optimal_season(region)
            
            # Get suitable crops for the season
            suitable_crops = self._get_suitable_crops(season, region)
            
            # Analyze each crop option
            crop_analysis = []
            for crop in suitable_crops:
                analysis = self._analyze_crop_option(crop, region, season, budget_constraint, risk_tolerance)
                crop_analysis.append(analysis)
            
            # Rank crops by profitability and risk
            ranked_crops = self._rank_crop_options(crop_analysis, risk_tolerance)
            
            # Generate financial projections
            financial_plan = self._generate_financial_plan(ranked_crops[0], region, season)
            
            return {
                'status': 'success',
                'recommended_season': season,
                'top_recommendations': ranked_crops[:3],
                'financial_plan': financial_plan,
                'risk_assessment': self._assess_planning_risks(region, season),
                'next_actions': self._get_planning_next_actions(ranked_crops[0]),
                'phase': 'Phase 3 - Crop Planning Advisor'
            }
            
        except Exception as e:
            logger.error(f"Crop planning advice failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 3 - Crop Planning Advisor'
            }
    
    def _get_optimal_season(self, region):
        """Determine optimal growing season for a region"""
        region_lower = region.lower()
        
        if region_lower in self.weather_patterns:
            weather = self.weather_patterns[region_lower]
            if 'kharif' in weather.get('best_season', ''):
                return 'kharif'
            elif 'rabi' in weather.get('best_season', ''):
                return 'rabi'
            else:
                return 'zaid'
        
        # Default based on current month
        current_month = timezone.now().month
        if current_month in [6, 7, 8, 9, 10]:
            return 'kharif'
        elif current_month in [11, 12, 1, 2, 3]:
            return 'rabi'
        else:
            return 'zaid'
    
    def _get_suitable_crops(self, season, region):
        """Get suitable crops for the season and region"""
        if season in self.crop_cycles:
            base_crops = self.crop_cycles[season]['crops']
            
            # Filter based on regional suitability
            suitable_crops = []
            for crop in base_crops:
                if self._is_crop_suitable_for_region(crop, region):
                    suitable_crops.append(crop)
            
            return suitable_crops if suitable_crops else base_crops
        
        return ['rice', 'wheat', 'vegetables']  # Default fallback
    
    def _is_crop_suitable_for_region(self, crop, region):
        """Check if crop is suitable for the region"""
        # This would typically integrate with external APIs for detailed suitability
        # For now, using basic regional logic
        region_lower = region.lower()
        
        if 'rice' in crop and 'punjab' in region_lower:
            return False  # Rice not ideal for Punjab
        elif 'cotton' in crop and 'punjab' in region_lower:
            return True   # Cotton good for Punjab
        
        return True  # Default to suitable
    
    def _analyze_crop_option(self, crop, region, season, budget_constraint, risk_tolerance):
        """Analyze a specific crop option"""
        # Get market analysis
        market_analysis = self.market_engine.market_analyzer.analyze_market_trends(crop, region, 365)
        
        # Calculate input costs
        input_costs = self._calculate_input_costs(crop, risk_tolerance)
        
        # Estimate yield and revenue
        yield_estimate = self._estimate_yield(crop, region, season)
        price_estimate = market_analysis.get('price_trend', {}).get('current_price', 0)
        revenue_estimate = yield_estimate * price_estimate
        
        # Calculate profitability
        total_cost = sum(input_costs.values())
        profit_estimate = revenue_estimate - total_cost
        roi = (profit_estimate / total_cost) * 100 if total_cost > 0 else 0
        
        return {
            'crop': crop,
            'season': season,
            'input_costs': input_costs,
            'total_cost': total_cost,
            'yield_estimate': yield_estimate,
            'revenue_estimate': revenue_estimate,
            'profit_estimate': profit_estimate,
            'roi': roi,
            'market_trend': market_analysis.get('price_trend', {}).get('direction', 'Unknown'),
            'risk_level': self._assess_crop_risk(crop, region, season)
        }
    
    def _calculate_input_costs(self, crop, risk_tolerance):
        """Calculate input costs based on risk tolerance"""
        costs = {}
        for input_type, cost_ranges in self.input_costs.items():
            if risk_tolerance == 'low':
                costs[input_type] = cost_ranges['low']
            elif risk_tolerance == 'high':
                costs[input_type] = cost_ranges['high']
            else:  # medium
                costs[input_type] = cost_ranges['medium']
        
        return costs
    
    def _estimate_yield(self, crop, region, season):
        """Estimate crop yield per acre"""
        # This would integrate with historical data and ML models
        # For now, using basic estimates
        base_yields = {
            'rice': 25,      # quintals per acre
            'wheat': 20,
            'maize': 30,
            'cotton': 8,
            'sugarcane': 400,
            'potato': 150,
            'vegetables': 15
        }
        
        base_yield = base_yields.get(crop.lower(), 20)
        
        # Adjust for region and season
        if 'punjab' in region.lower():
            base_yield *= 1.2  # Punjab has good agricultural conditions
        elif 'maharashtra' in region.lower():
            base_yield *= 0.9  # Moderate conditions
        
        if season == 'kharif':
            base_yield *= 1.1  # Monsoon benefits
        elif season == 'rabi':
            base_yield *= 0.95  # Winter constraints
        
        return round(base_yield, 1)
    
    def _assess_crop_risk(self, crop, region, season):
        """Assess risk level for a crop in a region and season"""
        risk_factors = []
        risk_score = 0
        
        # Weather risk
        if season == 'kharif' and 'punjab' in region.lower():
            risk_factors.append('Low rainfall in Punjab during kharif')
            risk_score += 2
        
        # Market risk
        if crop in ['cotton', 'sugarcane']:
            risk_factors.append('Price volatility in commercial crops')
            risk_score += 1
        
        # Disease risk
        if crop in ['potato', 'tomato']:
            risk_factors.append('High disease susceptibility')
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 3:
            risk_level = 'High'
        elif risk_score >= 1:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        return {
            'level': risk_level,
            'score': risk_score,
            'factors': risk_factors
        }
    
    def _rank_crop_options(self, crop_analysis, risk_tolerance):
        """Rank crop options by profitability and risk"""
        # Scoring system: ROI (60%) + Risk (40%)
        for analysis in crop_analysis:
            roi_score = min(analysis['roi'] / 50, 1.0)  # Normalize ROI to 0-1
            
            risk_score = 1.0
            if analysis['risk_level']['level'] == 'Low':
                risk_score = 1.0
            elif analysis['risk_level']['level'] == 'Medium':
                risk_score = 0.7
            else:  # High
                risk_score = 0.4
            
            # Adjust risk score based on user tolerance
            if risk_tolerance == 'low':
                risk_score *= 0.8
            elif risk_tolerance == 'high':
                risk_score *= 1.2
            
            # Calculate composite score
            composite_score = (roi_score * 0.6) + (risk_score * 0.4)
            analysis['composite_score'] = composite_score
        
        # Sort by composite score
        return sorted(crop_analysis, key=lambda x: x['composite_score'], reverse=True)
    
    def _generate_financial_plan(self, top_crop, region, season):
        """Generate detailed financial plan for the top crop"""
        return {
            'crop': top_crop['crop'],
            'investment_breakdown': top_crop['input_costs'],
            'total_investment': top_crop['total_cost'],
            'expected_revenue': top_crop['revenue_estimate'],
            'expected_profit': top_crop['profit_estimate'],
            'roi_percentage': top_crop['roi'],
            'break_even_yield': top_crop['total_cost'] / (top_crop['revenue_estimate'] / top_crop['yield_estimate']),
            'financing_options': self._suggest_financing_options(top_crop['total_cost']),
            'risk_mitigation': self._suggest_risk_mitigation(top_crop['risk_level'])
        }
    
    def _suggest_financing_options(self, total_cost):
        """Suggest financing options for the investment"""
        if total_cost <= 15000:
            return ['Self-financing', 'Kisan Credit Card', 'Microfinance']
        elif total_cost <= 50000:
            return ['Kisan Credit Card', 'Agricultural Loan', 'Cooperative Credit']
        else:
            return ['Agricultural Loan', 'Commercial Bank Loan', 'Government Schemes']
    
    def _suggest_risk_mitigation(self, risk_assessment):
        """Suggest risk mitigation strategies"""
        strategies = []
        
        if risk_assessment['level'] == 'High':
            strategies.extend([
                'Crop insurance coverage',
                'Diversified planting',
                'Contract farming agreements',
                'Weather monitoring systems'
            ])
        elif risk_assessment['level'] == 'Medium':
            strategies.extend([
                'Partial crop insurance',
                'Market price monitoring',
                'Disease prevention protocols'
            ])
        else:  # Low
            strategies.extend([
                'Basic monitoring',
                'Regular health checks'
            ])
        
        return strategies
    
    def _assess_planning_risks(self, region, season):
        """Assess overall planning risks"""
        risks = []
        
        # Weather risks
        if season == 'kharif':
            risks.append('Monsoon variability and timing')
        elif season == 'rabi':
            risks.append('Winter frost and cold waves')
        
        # Market risks
        risks.append('Price volatility in agricultural commodities')
        risks.append('Supply chain disruptions')
        
        # Policy risks
        risks.append('Changes in government policies and subsidies')
        
        return {
            'risk_factors': risks,
            'mitigation_strategies': [
                'Stay informed about weather forecasts',
                'Monitor market trends regularly',
                'Diversify crop portfolio',
                'Maintain emergency funds'
            ]
        }
    
    def _get_planning_next_actions(self, top_crop):
        """Get next actions for crop planning"""
        return [
            'Secure financing for input costs',
            'Prepare land and irrigation systems',
            'Source quality seeds and inputs',
            'Set up monitoring and tracking systems',
            'Plan harvesting and post-harvest logistics',
            'Identify potential buyers and markets'
        ]

class MarketStrategyAdvisor:
    """Phase 3: Advanced market strategy advisor with negotiation support"""
    
    def __init__(self, market_analyzer, decision_support):
        self.market_analyzer = market_analyzer
        self.decision_support = decision_support
        self.negotiation_strategies = self._initialize_negotiation_strategies()
        self.market_timing_models = self._initialize_timing_models()
    
    def _initialize_negotiation_strategies(self):
        """Initialize negotiation strategies for different scenarios"""
        return {
            'buyer_market': {
                'strategy': 'Aggressive pricing with quality focus',
                'tactics': ['Highlight quality advantages', 'Offer volume discounts', 'Flexible payment terms'],
                'price_range': '5-15% above market average'
            },
            'seller_market': {
                'strategy': 'Premium pricing with limited supply',
                'tactics': ['Emphasize scarcity', 'Quality differentiation', 'Strict payment terms'],
                'price_range': '10-25% above market average'
            },
            'balanced_market': {
                'strategy': 'Competitive pricing with value addition',
                'tactics': ['Market-based pricing', 'Service differentiation', 'Relationship building'],
                'price_range': 'Market average ±5%'
            }
        }
    
    def _initialize_timing_models(self):
        """Initialize market timing models"""
        return {
            'seasonal_timing': {
                'weight': 0.4,
                'factors': ['harvest_peak', 'demand_cycle', 'storage_costs']
            },
            'trend_timing': {
                'weight': 0.3,
                'factors': ['price_momentum', 'volume_trends', 'market_sentiment']
            },
            'event_timing': {
                'weight': 0.2,
                'factors': ['government_announcements', 'weather_events', 'export_opportunities']
            },
            'risk_timing': {
                'weight': 0.1,
                'factors': ['volatility_periods', 'uncertainty_events', 'market_stress']
            }
        }
    
    def get_comprehensive_market_strategy(self, crop_name, region, quantity, user_context=None):
        """Get comprehensive market strategy including timing and negotiation"""
        try:
            # Get market analysis
            market_analysis = self.market_analyzer.analyze_market_trends(crop_name, region, 180)
            
            # Determine market type
            market_type = self._determine_market_type(market_analysis)
            
            # Get optimal timing
            timing_analysis = self._get_optimal_timing(crop_name, region, market_analysis)
            
            # Generate pricing strategy
            pricing_strategy = self._generate_pricing_strategy(crop_name, region, market_type, timing_analysis)
            
            # Get negotiation guidance
            negotiation_guidance = self._get_negotiation_guidance(market_type, user_context)
            
            # Assess risks and opportunities
            risk_opportunity = self._assess_risk_opportunity(market_analysis, timing_analysis)
            
            return {
                'status': 'success',
                'market_type': market_type,
                'timing_strategy': timing_analysis,
                'pricing_strategy': pricing_strategy,
                'negotiation_guidance': negotiation_guidance,
                'risk_opportunity': risk_opportunity,
                'action_plan': self._generate_action_plan(timing_analysis, pricing_strategy),
                'phase': 'Phase 3 - Market Strategy Advisor'
            }
            
        except Exception as e:
            logger.error(f"Market strategy generation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 3 - Market Strategy Advisor'
            }
    
    def _determine_market_type(self, market_analysis):
        """Determine if it's a buyer's or seller's market"""
        # Handle case where market_analysis is a string (error message)
        if isinstance(market_analysis, str):
            logger.warning(f"Market analysis is string instead of dict: {market_analysis}")
            return 'balanced_market'  # Default to balanced market
        
        # Ensure market_analysis is a dictionary
        if not isinstance(market_analysis, dict):
            logger.warning(f"Market analysis is not a dict: {type(market_analysis)}")
            return 'balanced_market'  # Default to balanced market
        
        price_trend = market_analysis.get('price_trend', {})
        volume_trend = market_analysis.get('volume_trend', {})
        sentiment = market_analysis.get('market_sentiment', {})
        
        # Analyze market conditions
        price_direction = price_trend.get('direction', 'Stable')
        volume_direction = volume_trend.get('direction', 'Stable')
        market_sentiment = sentiment.get('sentiment', 'Neutral')
        
        # Determine market type
        if (price_direction in ['Strongly Rising', 'Rising'] and 
            volume_direction in ['Strongly Increasing', 'Increasing']):
            return 'seller_market'
        elif (price_direction in ['Strongly Falling', 'Falling'] and 
              volume_direction in ['Strongly Decreasing', 'Decreasing']):
            return 'buyer_market'
        else:
            return 'balanced_market'
    
    def _get_optimal_timing(self, crop_name, region, market_analysis):
        """Get optimal timing for market entry"""
        # Handle case where market_analysis is a string (error message)
        if isinstance(market_analysis, str):
            logger.warning(f"Market analysis is string in _get_optimal_timing: {market_analysis}")
            # Return default timing analysis
            return {
                'overall_score': 0.5,
                'factor_scores': {'seasonal_timing': 0.5, 'trend_timing': 0.5, 'event_timing': 0.5, 'risk_timing': 0.5},
                'recommendation': 'Wait for better conditions',
                'urgency': 'Low',
                'optimal_window': 'Next 2-4 weeks'
            }
        
        # Ensure market_analysis is a dictionary
        if not isinstance(market_analysis, dict):
            logger.warning(f"Market analysis is not a dict in _get_optimal_timing: {type(market_analysis)}")
            # Return default timing analysis
            return {
                'overall_score': 0.5,
                'factor_scores': {'seasonal_timing': 0.5, 'trend_timing': 0.5, 'event_timing': 0.5, 'risk_timing': 0.5},
                'recommendation': 'Wait for better conditions',
                'urgency': 'Low',
                'optimal_window': 'Next 2-4 weeks'
            }
        
        timing_scores = {}
        
        # Calculate timing scores for different factors
        for timing_type, model in self.market_timing_models.items():
            score = self._calculate_timing_score(timing_type, crop_name, region, market_analysis)
            timing_scores[timing_type] = score * model['weight']
        
        # Overall timing score
        overall_score = sum(timing_scores.values())
        
        # Determine timing recommendation
        if overall_score > 0.7:
            timing_recommendation = 'Immediate action recommended'
            urgency = 'High'
        elif overall_score > 0.5:
            timing_recommendation = 'Action within 1-2 weeks'
            urgency = 'Medium'
        else:
            timing_recommendation = 'Wait for better conditions'
            urgency = 'Low'
        
        return {
            'overall_score': overall_score,
            'factor_scores': timing_scores,
            'recommendation': timing_recommendation,
            'urgency': urgency,
            'optimal_window': self._calculate_optimal_window(overall_score, crop_name, region)
        }
    
    def _calculate_timing_score(self, timing_type, crop_name, region, market_analysis):
        """Calculate timing score for a specific factor"""
        if timing_type == 'seasonal_timing':
            return self._calculate_seasonal_timing_score(crop_name, region)
        elif timing_type == 'trend_timing':
            return self._calculate_trend_timing_score(market_analysis)
        elif timing_type == 'event_timing':
            return self._calculate_event_timing_score(crop_name, region)
        elif timing_type == 'risk_timing':
            return self._calculate_risk_timing_score(market_analysis)
        
        return 0.5  # Default neutral score
    
    def _calculate_seasonal_timing_score(self, crop_name, region):
        """Calculate seasonal timing score"""
        current_month = timezone.now().month
        
        # Seasonal patterns for different crops
        seasonal_patterns = {
            'potato': {'peak_months': [12, 1, 2], 'trough_months': [6, 7, 8]},
            'onion': {'peak_months': [8, 9, 10], 'trough_months': [3, 4, 5]},
            'tomato': {'peak_months': [6, 7, 8], 'trough_months': [12, 1, 2]},
            'rice': {'peak_months': [9, 10, 11], 'trough_months': [3, 4, 5]},
            'wheat': {'peak_months': [3, 4, 5], 'trough_months': [9, 10, 11]}
        }
        
        crop_pattern = seasonal_patterns.get(crop_name.lower(), {})
        peak_months = crop_pattern.get('peak_months', [])
        trough_months = crop_pattern.get('trough_months', [])
        
        if current_month in peak_months:
            return 0.9  # Excellent timing
        elif current_month in trough_months:
            return 0.2  # Poor timing
        else:
            return 0.6  # Moderate timing
    
    def _calculate_trend_timing_score(self, market_analysis):
        """Calculate trend timing score"""
        price_trend = market_analysis.get('price_trend', {})
        sentiment = market_analysis.get('market_sentiment', {})
        
        # Positive trends get higher scores
        if price_trend.get('direction') in ['Strongly Rising', 'Rising']:
            base_score = 0.8
        elif price_trend.get('direction') in ['Strongly Falling', 'Falling']:
            base_score = 0.3
        else:
            base_score = 0.6
        
        # Adjust for sentiment
        if sentiment.get('sentiment') == 'Bullish':
            base_score += 0.1
        elif sentiment.get('sentiment') == 'Bearish':
            base_score -= 0.1
        
        return max(0.0, min(1.0, base_score))
    
    def _calculate_event_timing_score(self, crop_name, region):
        """Calculate event timing score"""
        # This would integrate with external APIs for real-time events
        # For now, using basic scoring
        current_month = timezone.now().month
        
        # Government announcement periods
        if current_month in [2, 3]:  # Budget season
            return 0.7
        elif current_month in [6, 7]:  # Monsoon onset
            return 0.8
        else:
            return 0.5
    
    def _calculate_risk_timing_score(self, market_analysis):
        """Calculate risk timing score"""
        volatility = market_analysis.get('volatility', {})
        volatility_level = volatility.get('level', 'Unknown')
        
        # Lower volatility is better for timing
        if volatility_level == 'Very Low':
            return 0.9
        elif volatility_level == 'Low':
            return 0.8
        elif volatility_level == 'Moderate':
            return 0.6
        elif volatility_level == 'High':
            return 0.4
        elif volatility_level == 'Very High':
            return 0.2
        else:
            return 0.5
    
    def _calculate_optimal_window(self, timing_score, crop_name, region):
        """Calculate optimal timing window"""
        if timing_score > 0.8:
            return 'Next 3-7 days'
        elif timing_score > 0.6:
            return 'Next 1-2 weeks'
        elif timing_score > 0.4:
            return 'Next 2-4 weeks'
        else:
            return 'Wait for better conditions'
    
    def _generate_pricing_strategy(self, crop_name, region, market_type, timing_analysis):
        """Generate pricing strategy based on market conditions"""
        # Get current market prices
        current_price = self._get_current_market_price(crop_name, region)
        
        # Get strategy for market type
        strategy = self.negotiation_strategies.get(market_type, {})
        
        # Calculate target price range
        if market_type == 'seller_market':
            target_price = current_price * 1.15  # 15% above market
            min_price = current_price * 1.10
            max_price = current_price * 1.25
        elif market_type == 'buyer_market':
            target_price = current_price * 1.05  # 5% above market
            min_price = current_price * 0.95
            max_price = current_price * 1.15
        else:  # balanced
            target_price = current_price * 1.02  # 2% above market
            min_price = current_price * 0.98
            max_price = current_price * 1.08
        
        return {
            'current_market_price': current_price,
            'target_price': round(target_price, 2),
            'price_range': {
                'minimum': round(min_price, 2),
                'maximum': round(max_price, 2)
            },
            'strategy': strategy.get('strategy', 'Competitive pricing'),
            'tactics': strategy.get('tactics', []),
            'price_range_description': strategy.get('price_range', 'Market-based pricing')
        }
    
    def _get_current_market_price(self, crop_name, region):
        """Get current market price for the crop"""
        try:
            # Query recent market prices
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT AVG(price) as avg_price
                    FROM deals_marketprice 
                    WHERE crop_name = %s AND region LIKE %s
                    AND date >= %s
                    ORDER BY date DESC
                    LIMIT 10
                """, [crop_name, f"%{region.split(',')[0]}%", timezone.now().date() - timedelta(days=30)])
                
                result = cursor.fetchone()
                if result and result[0]:
                    return float(result[0])
        except Exception as e:
            logger.error(f"Failed to get current market price: {e}")
        
        # Fallback to default prices
        default_prices = {
            'potato': 25.0,
            'onion': 15.0,
            'tomato': 40.0,
            'rice': 35.0,
            'wheat': 25.0
        }
        
        return default_prices.get(crop_name.lower(), 30.0)
    
    def _get_negotiation_guidance(self, market_type, user_context):
        """Get negotiation guidance based on market type"""
        strategy = self.negotiation_strategies.get(market_type, {})
        
        guidance = {
            'market_type': market_type,
            'strategy': strategy.get('strategy', 'Adaptive pricing'),
            'key_tactics': strategy.get('tactics', []),
            'price_positioning': strategy.get('price_range', 'Market-based'),
            'negotiation_style': self._get_negotiation_style(market_type),
            'concession_strategy': self._get_concession_strategy(market_type),
            'deal_breakers': self._get_deal_breakers(market_type)
        }
        
        return guidance
    
    def _get_negotiation_style(self, market_type):
        """Get recommended negotiation style"""
        if market_type == 'seller_market':
            return 'Firm and confident - emphasize quality and scarcity'
        elif market_type == 'buyer_market':
            return 'Flexible and accommodating - focus on value addition'
        else:
            return 'Balanced and collaborative - build long-term relationships'
    
    def _get_concession_strategy(self, market_type):
        """Get concession strategy"""
        if market_type == 'seller_market':
            return 'Minimal concessions, focus on quality and service'
        elif market_type == 'buyer_market':
            return 'Strategic concessions to secure volume and relationships'
        else:
            return 'Balanced concessions based on mutual value'
    
    def _get_deal_breakers(self, market_type):
        """Get deal breaker conditions"""
        if market_type == 'seller_market':
            return ['Prices below cost of production', 'Unreasonable payment terms', 'Quality compromises']
        elif market_type == 'buyer_market':
            return ['Excessive price demands', 'Poor quality standards', 'Unreliable supply']
        else:
            return ['Unfair pricing', 'Poor quality', 'Unreliable terms']
    
    def _assess_risk_opportunity(self, market_analysis, timing_analysis):
        """Assess risks and opportunities"""
        risks = []
        opportunities = []
        
        # Market risks
        if market_analysis.get('volatility', {}).get('level') in ['High', 'Very High']:
            risks.append('High price volatility - consider hedging strategies')
        
        if market_analysis.get('price_trend', {}).get('direction') in ['Strongly Falling', 'Falling']:
            risks.append('Declining price trend - consider storage or alternative markets')
        
        # Timing risks
        if timing_analysis.get('urgency') == 'High':
            risks.append('Urgent action required - limited time for optimal decisions')
        
        # Opportunities
        if market_analysis.get('price_trend', {}).get('direction') in ['Strongly Rising', 'Rising']:
            opportunities.append('Rising price trend - favorable selling conditions')
        
        if timing_analysis.get('overall_score') > 0.7:
            opportunities.append('Excellent timing for market entry')
        
        return {
            'risks': risks,
            'opportunities': opportunities,
            'risk_level': 'High' if len(risks) > 2 else 'Medium' if len(risks) > 0 else 'Low',
            'opportunity_level': 'High' if len(opportunities) > 2 else 'Medium' if len(opportunities) > 0 else 'Low'
        }
    
    def _generate_action_plan(self, timing_analysis, pricing_strategy):
        """Generate actionable plan"""
        actions = []
        
        # Immediate actions based on timing
        if timing_analysis.get('urgency') == 'High':
            actions.extend([
                'Prepare product for immediate market entry',
                'Contact potential buyers within 24 hours',
                'Set up logistics and transportation'
            ])
        elif timing_analysis.get('urgency') == 'Medium':
            actions.extend([
                'Prepare product for market entry within 1-2 weeks',
                'Research and contact potential buyers',
                'Plan logistics and transportation'
            ])
        else:
            actions.extend([
                'Monitor market conditions for better timing',
                'Prepare product quality and documentation',
                'Build relationships with potential buyers'
            ])
        
        # Pricing actions
        actions.extend([
            f"Set target price at ₹{pricing_strategy['target_price']}/quintal",
            f"Negotiate within price range: ₹{pricing_strategy['price_range']['minimum']} - ₹{pricing_strategy['price_range']['maximum']}/quintal",
            'Prepare quality certificates and documentation',
            'Plan for quality-based price differentiation'
        ])
        
        return actions

class SmartNotificationSystem:
    """Phase 3: Smart notification system with intelligent alerts and recommendations"""
    
    def __init__(self):
        self.notification_rules = self._initialize_notification_rules()
        self.user_preferences = defaultdict(dict)
        self.notification_history = defaultdict(list)
        self.alert_thresholds = self._initialize_alert_thresholds()
    
    def _initialize_notification_rules(self):
        """Initialize rules for different types of notifications"""
        return {
            'market_opportunity': {
                'triggers': ['price_spike', 'demand_surge', 'supply_shortage'],
                'priority': 'high',
                'channels': ['push', 'email', 'sms'],
                'frequency': 'immediate'
            },
            'risk_alert': {
                'triggers': ['price_drop', 'weather_warning', 'disease_outbreak'],
                'priority': 'critical',
                'channels': ['push', 'sms', 'email'],
                'frequency': 'immediate'
            },
            'timing_recommendation': {
                'triggers': ['optimal_selling_time', 'planting_window', 'harvest_time'],
                'priority': 'medium',
                'channels': ['push', 'email'],
                'frequency': 'daily'
            },
            'market_update': {
                'triggers': ['price_change', 'volume_change', 'trend_change'],
                'priority': 'low',
                'channels': ['email', 'in_app'],
                'frequency': 'weekly'
            }
        }
    
    def _initialize_alert_thresholds(self):
        """Initialize thresholds for different types of alerts"""
        return {
            'price_change': {
                'minor': 5.0,      # 5% change
                'moderate': 15.0,   # 15% change
                'major': 25.0       # 25% change
            },
            'volume_change': {
                'minor': 10.0,      # 10% change
                'moderate': 25.0,   # 25% change
                'major': 50.0       # 50% change
            },
            'volatility': {
                'low': 10.0,        # 10% volatility
                'medium': 20.0,     # 20% volatility
                'high': 30.0        # 30% volatility
            }
        }
    
    def check_notification_triggers(self, crop_name, region, market_data):
        """Check if any notification triggers are activated"""
        notifications = []
        
        # Check price change triggers
        price_change = self._calculate_price_change(market_data)
        if abs(price_change) >= self.alert_thresholds['price_change']['moderate']:
            notification = self._create_price_notification(crop_name, region, price_change, market_data)
            notifications.append(notification)
        
        # Check volume change triggers
        volume_change = self._calculate_volume_change(market_data)
        if abs(volume_change) >= self.alert_thresholds['volume_change']['moderate']:
            notification = self._create_volume_notification(crop_name, region, volume_change, market_data)
            notifications.append(notification)
        
        # Check volatility triggers
        volatility = market_data.get('volatility', {}).get('percentage', 0)
        if volatility >= self.alert_thresholds['volatility']['high']:
            notification = self._create_volatility_notification(crop_name, region, volatility, market_data)
            notifications.append(notification)
        
        # Check timing triggers
        timing_notification = self._check_timing_triggers(crop_name, region, market_data)
        if timing_notification:
            notifications.append(timing_notification)
        
        return notifications
    
    def _calculate_price_change(self, market_data):
        """Calculate recent price change percentage"""
        price_trend = market_data.get('price_trend', {})
        return price_trend.get('change_percent', 0)
    
    def _calculate_volume_change(self, market_data):
        """Calculate recent volume change percentage"""
        volume_trend = market_data.get('volume_trend', {})
        return volume_trend.get('change_percent', 0)
    
    def _create_price_notification(self, crop_name, region, price_change, market_data):
        """Create price change notification"""
        if price_change > 0:
            notification_type = 'market_opportunity'
            title = f"🚀 Price Surge Alert: {crop_name}"
            message = f"Great news! {crop_name} prices in {region} have increased by {abs(price_change):.1f}%"
            priority = 'high'
        else:
            notification_type = 'risk_alert'
            title = f"⚠️ Price Drop Alert: {crop_name}"
            message = f"Alert: {crop_name} prices in {region} have decreased by {abs(price_change):.1f}%"
            priority = 'critical'
        
        return {
            'type': notification_type,
            'title': title,
            'message': message,
            'priority': priority,
            'crop_name': crop_name,
            'region': region,
            'data': {
                'price_change': price_change,
                'current_price': market_data.get('price_trend', {}).get('current_price', 0),
                'timestamp': timezone.now()
            },
            'actions': self._get_notification_actions(notification_type, crop_name, region)
        }
    
    def _create_volume_notification(self, crop_name, region, volume_change, market_data):
        """Create volume change notification"""
        if volume_change > 0:
            notification_type = 'market_opportunity'
            title = f"📈 Volume Surge Alert: {crop_name}"
            message = f"High demand alert! {crop_name} trading volume in {region} increased by {abs(volume_change):.1f}%"
            priority = 'medium'
        else:
            notification_type = 'market_update'
            title = f"📉 Volume Drop Alert: {crop_name}"
            message = f"Market update: {crop_name} trading volume in {region} decreased by {abs(volume_change):.1f}%"
            priority = 'low'
        
        return {
            'type': notification_type,
            'title': title,
            'message': message,
            'priority': priority,
            'crop_name': crop_name,
            'region': region,
            'data': {
                'volume_change': volume_change,
                'timestamp': timezone.now()
            },
            'actions': self._get_notification_actions(notification_type, crop_name, region)
        }
    
    def _create_volatility_notification(self, crop_name, region, volatility, market_data):
        """Create volatility notification"""
        notification_type = 'risk_alert'
        title = f"⚡ High Volatility Alert: {crop_name}"
        message = f"Warning: {crop_name} prices in {region} showing {volatility:.1f}% volatility - high risk period"
        priority = 'critical'
        
        return {
            'type': notification_type,
            'title': title,
            'message': message,
            'priority': priority,
            'crop_name': crop_name,
            'region': region,
            'data': {
                'volatility': volatility,
                'timestamp': timezone.now()
            },
            'actions': self._get_notification_actions(notification_type, crop_name, region)
        }
    
    def _check_timing_triggers(self, crop_name, region, market_data):
        """Check if timing-based notifications should be sent"""
        current_month = timezone.now().month
        
        # Check for optimal selling time
        if self._is_optimal_selling_time(crop_name, current_month):
            return {
                'type': 'timing_recommendation',
                'title': f"⏰ Optimal Selling Time: {crop_name}",
                'message': f"Perfect timing! This is the optimal period to sell {crop_name} in {region}",
                'priority': 'medium',
                'crop_name': crop_name,
                'region': region,
                'data': {
                    'timing_type': 'optimal_selling',
                    'current_month': current_month,
                    'timestamp': timezone.now()
                },
                'actions': self._get_notification_actions('timing_recommendation', crop_name, region)
            }
        
        return None
    
    def _is_optimal_selling_time(self, crop_name, current_month):
        """Check if current month is optimal for selling the crop"""
        optimal_months = {
            'potato': [12, 1, 2],      # Winter months
            'onion': [8, 9, 10],       # Post-monsoon
            'tomato': [6, 7, 8],       # Summer months
            'rice': [9, 10, 11],       # Post-harvest
            'wheat': [3, 4, 5]         # Spring months
        }
        
        crop_optimal = optimal_months.get(crop_name.lower(), [])
        return current_month in crop_optimal
    
    def _get_notification_actions(self, notification_type, crop_name, region):
        """Get suggested actions for the notification"""
        action_maps = {
            'market_opportunity': [
                'View detailed market analysis',
                'Get selling recommendations',
                'Check optimal timing',
                'Contact buyers'
            ],
            'risk_alert': [
                'View risk assessment',
                'Get mitigation strategies',
                'Check alternative markets',
                'Review storage options'
            ],
            'timing_recommendation': [
                'View timing analysis',
                'Get market strategy',
                'Plan logistics',
                'Set price targets'
            ],
            'market_update': [
                'View market trends',
                'Check price forecasts',
                'Review selling strategy',
                'Monitor conditions'
            ]
        }
        
        return action_maps.get(notification_type, ['View details'])
    
    def send_notification(self, notification, user_id, channel='push'):
        """Send notification to user through specified channel"""
        try:
            # Store notification in history
            self.notification_history[user_id].append({
                'notification': notification,
                'channel': channel,
                'sent_at': timezone.now(),
                'status': 'sent'
            })
            
            # Limit history to last 100 notifications
            if len(self.notification_history[user_id]) > 100:
                self.notification_history[user_id].pop(0)
            
            # Here you would integrate with actual notification services
            # For now, just return success status
            return {
                'status': 'success',
                'notification_id': f"notif_{user_id}_{int(timezone.now().timestamp())}",
                'channel': channel,
                'sent_at': timezone.now(),
                'phase': 'Phase 3 - Smart Notifications'
            }
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'phase': 'Phase 3 - Smart Notifications'
            }
    
    def get_user_notifications(self, user_id, notification_type=None, limit=20):
        """Get user's notification history"""
        if user_id not in self.notification_history:
            return []
        
        notifications = self.notification_history[user_id]
        
        if notification_type:
            notifications = [n for n in notifications if n['notification']['type'] == notification_type]
        
        # Sort by most recent first
        notifications.sort(key=lambda x: x['sent_at'], reverse=True)
        
        return notifications[:limit]
    
    def set_user_preferences(self, user_id, preferences):
        """Set user notification preferences"""
        self.user_preferences[user_id].update(preferences)
        return {
            'status': 'success',
            'message': 'Notification preferences updated',
            'preferences': self.user_preferences[user_id]
        }

class AutomatedActionSystem:
    """Phase 3: Automated action system for intelligent responses to market conditions"""
    
    def __init__(self, market_engine, decision_support):
        self.market_engine = market_engine
        self.decision_support = decision_support
        self.automation_rules = self._initialize_automation_rules()
        self.action_history = defaultdict(list)
        self.auto_actions_enabled = defaultdict(lambda: True)
    
    def _initialize_automation_rules(self):
        """Initialize rules for automated actions"""
        return {
            'price_spike_automation': {
                'trigger_condition': 'price_increase > 20%',
                'actions': ['create_deal_group', 'notify_group_members', 'suggest_price_adjustment'],
                'conditions': ['sufficient_volume', 'group_consensus'],
                'priority': 'high'
            },
            'market_opportunity_automation': {
                'trigger_condition': 'optimal_timing_score > 0.8',
                'actions': ['suggest_group_formation', 'recommend_quantity', 'set_price_targets'],
                'conditions': ['market_conditions_favorable', 'farmer_availability'],
                'priority': 'medium'
            },
            'risk_mitigation_automation': {
                'trigger_condition': 'risk_level = high',
                'actions': ['suggest_insurance', 'recommend_diversification', 'alert_group'],
                'conditions': ['risk_above_threshold', 'mitigation_options_available'],
                'priority': 'critical'
            },
            'logistics_optimization_automation': {
                'trigger_condition': 'delivery_window < 7_days',
                'actions': ['suggest_logistics_partners', 'optimize_routes', 'coordinate_transport'],
                'conditions': ['logistics_required', 'partners_available'],
                'priority': 'medium'
            }
        }
    
    def check_automation_triggers(self, crop_name, region, market_data, user_context=None):
        """Check if any automation triggers are activated"""
        triggered_actions = []
        
        # Check price spike automation
        price_action = self._check_price_spike_automation(crop_name, region, market_data)
        if price_action:
            triggered_actions.append(price_action)
        
        # Check market opportunity automation
        opportunity_action = self._check_market_opportunity_automation(crop_name, region, market_data)
        if opportunity_action:
            triggered_actions.append(opportunity_action)
        
        # Check risk mitigation automation
        risk_action = self._check_risk_mitigation_automation(crop_name, region, market_data)
        if risk_action:
            triggered_actions.append(risk_action)
        
        # Check logistics automation
        logistics_action = self._check_logistics_automation(crop_name, region, market_data, user_context)
        if logistics_action:
            triggered_actions.append(logistics_action)
        
        return triggered_actions
    
    def _check_price_spike_automation(self, crop_name, region, market_data):
        """Check if price spike automation should be triggered"""
        price_change = market_data.get('price_trend', {}).get('change_percent', 0)
        
        if price_change > 20:  # 20% increase
            return {
                'automation_type': 'price_spike_automation',
                'triggered': True,
                'reason': f"Price increased by {price_change:.1f}%",
                'suggested_actions': [
                    'Create deal group for collective bargaining',
                    'Notify group members about price opportunity',
                    'Suggest price adjustment strategy',
                    'Coordinate group selling approach'
                ],
                'priority': 'high',
                'estimated_impact': 'High - Significant price advantage'
            }
        
        return None
    
    def _check_market_opportunity_automation(self, crop_name, region, market_data):
        """Check if market opportunity automation should be triggered"""
        # This would integrate with timing analysis
        # For now, using basic market conditions
        price_trend = market_data.get('price_trend', {}).get('direction', 'Unknown')
        sentiment = market_data.get('market_sentiment', {}).get('sentiment', 'Neutral')
        
        if price_trend in ['Strongly Rising', 'Rising'] and sentiment == 'Bullish':
            return {
                'automation_type': 'market_opportunity_automation',
                'triggered': True,
                'reason': f"Favorable market conditions: {price_trend} trend with {sentiment} sentiment",
                'suggested_actions': [
                    'Suggest group formation for better bargaining',
                    'Recommend optimal selling quantities',
                    'Set competitive price targets',
                    'Coordinate market entry timing'
                ],
                'priority': 'medium',
                'estimated_impact': 'Medium - Improved market positioning'
            }
        
        return None
    
    def _check_risk_mitigation_automation(self, crop_name, region, market_data):
        """Check if risk mitigation automation should be triggered"""
        volatility = market_data.get('volatility', {}).get('level', 'Unknown')
        price_trend = market_data.get('price_trend', {}).get('direction', 'Unknown')
        
        if (volatility in ['High', 'Very High'] or 
            price_trend in ['Strongly Falling', 'Falling']):
            return {
                'automation_type': 'risk_mitigation_automation',
                'triggered': True,
                'reason': f"High risk detected: {volatility} volatility, {price_trend} trend",
                'suggested_actions': [
                    'Suggest crop insurance options',
                    'Recommend portfolio diversification',
                    'Alert group about risk factors',
                    'Suggest alternative markets'
                ],
                'priority': 'critical',
                'estimated_impact': 'Critical - Risk mitigation required'
            }
        
        return None
    
    def _check_logistics_automation(self, crop_name, region, market_data, user_context):
        """Check if logistics automation should be triggered"""
        # This would integrate with actual logistics data
        # For now, using basic checks
        if user_context and user_context.get('delivery_required'):
            return {
                'automation_type': 'logistics_optimization_automation',
                'triggered': True,
                'reason': 'Delivery logistics required for crop sale',
                'suggested_actions': [
                    'Suggest logistics partners in the region',
                    'Optimize delivery routes',
                    'Coordinate transportation schedules',
                    'Calculate logistics costs'
                ],
                'priority': 'medium',
                'estimated_impact': 'Medium - Logistics optimization'
            }
        
        return None
    
    def execute_automated_action(self, action, user_id, context=None):
        """Execute an automated action"""
        try:
            action_result = {
                'action_type': action['automation_type'],
                'triggered_at': timezone.now(),
                'status': 'executing',
                'user_id': user_id,
                'context': context or {}
            }
            
            # Execute the action based on type
            if action['automation_type'] == 'price_spike_automation':
                result = self._execute_price_spike_action(action, user_id, context)
            elif action['automation_type'] == 'market_opportunity_automation':
                result = self._execute_market_opportunity_action(action, user_id, context)
            elif action['automation_type'] == 'risk_mitigation_automation':
                result = self._execute_risk_mitigation_action(action, user_id, context)
            elif action['automation_type'] == 'logistics_optimization_automation':
                result = self._execute_logistics_action(action, user_id, context)
            else:
                result = {'status': 'unknown_action_type'}
            
            # Update action result
            action_result.update(result)
            action_result['status'] = 'completed'
            
            # Store in history
            self.action_history[user_id].append(action_result)
            
            return action_result
            
        except Exception as e:
            logger.error(f"Automated action execution failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'action_type': action.get('automation_type', 'unknown'),
                'phase': 'Phase 3 - Automated Actions'
            }
    
    def _execute_price_spike_action(self, action, user_id, context):
        """Execute price spike automation action"""
        # This would create actual deal groups and notifications
        # For now, returning simulation results
        return {
            'executed_actions': [
                'Deal group creation initiated',
                'Group notifications sent',
                'Price strategy recommendations provided',
                'Coordination plan generated'
            ],
            'estimated_benefit': '15-25% price improvement through collective bargaining',
            'next_steps': [
                'Review group member responses',
                'Finalize price strategy',
                'Coordinate selling timeline',
                'Monitor market conditions'
            ]
        }
    
    def _execute_market_opportunity_action(self, action, user_id, context):
        """Execute market opportunity automation action"""
        return {
            'executed_actions': [
                'Group formation recommendations sent',
                'Quantity optimization calculated',
                'Price targets set',
                'Market entry timing coordinated'
            ],
            'estimated_benefit': '10-20% improved market positioning',
            'next_steps': [
                'Confirm group participation',
                'Set up logistics coordination',
                'Monitor market entry timing',
                'Track performance metrics'
            ]
        }
    
    def _execute_risk_mitigation_action(self, action, user_id, context):
        """Execute risk mitigation automation action"""
        return {
            'executed_actions': [
                'Risk assessment completed',
                'Insurance recommendations provided',
                'Diversification strategies suggested',
                'Group risk alerts sent'
            ],
            'estimated_benefit': 'Risk reduction by 30-50%',
            'next_steps': [
                'Review insurance options',
                'Plan diversification strategy',
                'Implement risk monitoring',
                'Update group risk protocols'
            ]
        }
    
    def _execute_logistics_action(self, action, user_id, context):
        """Execute logistics automation action"""
        return {
            'executed_actions': [
                'Logistics partners identified',
                'Route optimization completed',
                'Transportation schedules coordinated',
                'Cost calculations provided'
            ],
            'estimated_benefit': '15-25% logistics cost reduction',
            'next_steps': [
                'Confirm logistics partnerships',
                'Finalize delivery schedules',
                'Coordinate with buyers',
                'Monitor delivery performance'
            ]
        }
    
    def get_automation_history(self, user_id, action_type=None, limit=20):
        """Get user's automation action history"""
        if user_id not in self.action_history:
            return []
        
        actions = self.action_history[user_id]
        
        if action_type:
            actions = [a for a in actions if a['action_type'] == action_type]
        
        # Sort by most recent first
        actions.sort(key=lambda x: x['triggered_at'], reverse=True)
        
        return actions[:limit]
    
    def toggle_automation(self, user_id, enabled=True):
        """Enable or disable automated actions for a user"""
        self.auto_actions_enabled[user_id] = enabled
        
        return {
            'status': 'success',
            'message': f"Automated actions {'enabled' if enabled else 'disabled'} for user {user_id}",
            'automation_enabled': enabled
        }
    
    def search_knowledge_base(self, query, limit=5):
        """Search knowledge base for relevant information"""
        try:
            # Simple text-based search for now
            # In production, you'd use vector similarity search
            chunks = KnowledgeChunk.objects.filter(
                Q(content__icontains=query) |
                Q(source__icontains=query)
            )[:limit]
            
            results = []
            for chunk in chunks:
                results.append({
                    'content': chunk.content,
                    'source': chunk.source,
                    'relevance_score': self._calculate_relevance(chunk.content, query)
                })
            
            # Sort by relevance
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results
            
        except Exception as e:
            print(f"Knowledge base search failed: {e}")
            return []
    
    def _calculate_relevance(self, content, query):
        """Calculate simple relevance score"""
        query_words = query.lower().split()
        content_lower = content.lower()
        
        score = 0
        for word in query_words:
            if word in content_lower:
                score += 1
        
        return score / len(query_words) if query_words else 0
    
    def get_msp_information(self, crop_name=None, season=None):
        """Get MSP information from knowledge base"""
        try:
            # Search for MSP-related information
            query = "MSP"  # Keep it simple - just search for MSP
            # Don't modify query - it breaks the search
            # if crop_name:
            #     query += f" {crop_name}"
            # if season:
            #     query += f" {season}"
            
            chunks = self.search_knowledge_base(query, limit=10)
            
            if not chunks:
                return None
            
            # Extract MSP data from chunks
            msp_data = []
            for chunk in chunks:
                if 'MSP' in chunk['content'] or 'Minimum Support Price' in chunk['content']:
                    msp_data.append({
                        'content': chunk['content'],
                        'source': chunk['source'],
                        'relevance': chunk['relevance_score']
                    })
            
            return msp_data
            
        except Exception as e:
            print(f"MSP information retrieval failed: {e}")
            return None
    
    def _extract_msp_values(self, msp_data, crop_name):
        """Extract specific MSP values from knowledge chunks"""
        extracted = {}
        
        for data in msp_data:
            content = data['content']
            
            # Look for MSP patterns in the content
            if 'MSP' in content and '2025-26' in content:
                # Extract crop-specific MSP values
                if crop_name and crop_name.lower() in content.lower():
                    # Use regex to extract price values
                    import re
                    price_match = re.search(r'₹?(\d+(?:,\d+)*)', content)
                    if price_match:
                        extracted['msp_price'] = price_match.group(1)
                        extracted['source'] = data['source']
                        extracted['content_snippet'] = content[:200] + "..."
        
        return extracted
    
    def _handle_msp_query(self, query, entities, user_context):
        """Handle MSP-specific queries"""
        crop_name = entities.get('crop', [None])[0]
        season = entities.get('time', ['Rabi'])[0]
        
        # Get MSP information from knowledge base
        msp_data = self.get_msp_information(crop_name, season)
        
        if msp_data:
            # Extract specific MSP values
            msp_values = self._extract_msp_values(msp_data, crop_name)
            
            return {
                'status': 'success',
                'query': query,
                'response_type': 'msp_information',
                'intent': 'msp_query',
                'msp_data': msp_data,
                'extracted_values': msp_values,
                'summary': f"MSP information for {season} crops from knowledge base",
                'source': 'Government MSP Document (Knowledge Base)',
                'phase': 'Phase 3 - MSP Advisor with Knowledge Base'
            }
        else:
            return {
                'status': 'success',
                'query': query,
                'response_type': 'msp_information',
                'intent': 'msp_query',
                'message': "MSP information not found in knowledge base. Please check if the document has been properly processed.",
                'phase': 'Phase 3 - MSP Advisor'
            }

# Global instance for easy access
agri_genie = AgriGenieAdvisor()
