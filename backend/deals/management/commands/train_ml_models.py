from django.core.management.base import BaseCommand
from django.utils import timezone
from deals.models import MarketPrice
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import joblib
import pickle
import os
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error

class Command(BaseCommand):
    help = 'Train ML pricing models using existing MarketPrice data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-retrain',
            action='store_true',
            help='Force retraining even if models exist'
        )
        parser.add_argument(
            '--test-only',
            action='store_true',
            help='Only test existing models without training'
        )

    def handle(self, *args, **options):
        if options['test_only']:
            self._test_existing_models()
            return

        if options['force_retrain'] or not self._models_exist():
            self._train_models()
        else:
            self.stdout.write("✅ ML models already exist. Use --force-retrain to retrain.")
            self._test_existing_models()

    def _models_exist(self):
        """Check if ML model files exist"""
        required_files = [
            'advanced_pricing_model.pkl',
            'price_scaler.pkl',
            'price_encoders.pkl',
            'price_features.pkl'
        ]
        
        missing_files = [f for f in required_files if not os.path.exists(f)]
        
        if missing_files:
            self.stdout.write(f"❌ Missing ML model files: {missing_files}")
            return False
        
        self.stdout.write("✅ All ML model files found")
        return True

    def _train_models(self):
        """Train ML pricing models"""
        self.stdout.write("🚀 Training ML Pricing Models...")
        
        try:
            # Load data from MarketPrice model
            self.stdout.write("📊 Loading market data...")
            market_data = MarketPrice.objects.all()
            
            if not market_data.exists():
                self.stdout.write("❌ No market data found in MarketPrice model")
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(list(market_data.values(
                'crop_name', 'region', 'price', 'date', 'quality_grade'
            )))
            
            self.stdout.write(f"✅ Loaded {len(df)} market price records")
            self.stdout.write(f"📋 Data shape: {df.shape}")
            
            # Data preprocessing
            self.stdout.write("🔧 Preprocessing data...")
            df_processed = self._preprocess_data(df)
            
            if df_processed is None or len(df_processed) == 0:
                self.stdout.write("❌ No valid data after preprocessing")
                return
            
            # Feature engineering
            self.stdout.write("⚙️ Engineering features...")
            result = self._engineer_features(df_processed)
            
            if result is None or len(result) < 3:
                self.stdout.write("❌ Feature engineering failed")
                return
            
            X, y, feature_columns, le_crop, le_district = result
            
            # Train models
            self.stdout.write("🧠 Training ML models...")
            models = self._train_models_with_data(X, y)
            
            if not models:
                self.stdout.write("❌ Model training failed")
                return
            
            # Save models
            self.stdout.write("💾 Saving models...")
            self._save_models(models, feature_columns, le_crop, le_district)
            
            self.stdout.write("✅ ML models trained and saved successfully!")
            
            # Test the models
            self._test_trained_models(X, y, models)
            
        except Exception as e:
            self.stdout.write(f"❌ Error training models: {str(e)}")
            import traceback
            traceback.print_exc()

    def _preprocess_data(self, df):
        """Preprocess the market data"""
        try:
            # Remove rows with missing critical data
            df_clean = df.dropna(subset=['crop_name', 'region', 'price', 'date'])
            
            # Convert price to numeric
            df_clean['price'] = pd.to_numeric(df_clean['price'], errors='coerce')
            df_clean = df_clean.dropna(subset=['price'])
            
            # Convert date to datetime
            df_clean['date'] = pd.to_datetime(df_clean['date'])
            
            # Remove outliers (prices beyond 3 standard deviations)
            price_mean = df_clean['price'].mean()
            price_std = df_clean['price'].std()
            price_lower = price_mean - 3 * price_std
            price_upper = price_mean + 3 * price_std
            
            df_clean = df_clean[
                (df_clean['price'] >= price_lower) & 
                (df_clean['price'] <= price_upper)
            ]
            
            # Extract district from region
            df_clean['district'] = df_clean['region'].str.split(',').str[0].str.strip().str.lower()
            
            # Use ALL India data (not just Andhra Pradesh)
            # df_clean = df_clean[df_clean['region'].str.contains('Andhra Pradesh', case=False, na=False)]
            
            self.stdout.write(f"✅ Preprocessed data: {len(df_clean)} records")
            self.stdout.write(f"📊 Price range: ₹{df_clean['price'].min():.2f} - ₹{df_clean['price'].max():.2f}/quintal")
            self.stdout.write(f"🌾 Crops: {df_clean['crop_name'].nunique()}")
            self.stdout.write(f"🏘️ States: {df_clean['region'].str.split(',').str[1].str.strip().nunique()}")
            self.stdout.write(f"🏘️ Districts: {df_clean['district'].nunique()}")
            
            return df_clean
            
        except Exception as e:
            self.stdout.write(f"❌ Preprocessing error: {str(e)}")
            return None

    def _engineer_features(self, df):
        """Engineer features for ML"""
        try:
            # Time-based features
            df['month'] = df['date'].dt.month
            df['year'] = df['date'].dt.year
            df['day_of_week'] = df['date'].dt.dayofweek
            df['quarter'] = df['date'].dt.quarter
            df['is_month_start'] = df['date'].dt.is_month_start.astype(int)
            df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
            
            # Seasonal features
            df['is_kharif'] = df['month'].isin([6, 7, 8, 9]).astype(int)
            df['is_rabi'] = df['month'].isin([10, 11, 12, 1, 2, 3]).astype(int)
            
            # Regional features - Major markets across India
            major_markets = ['hyderabad', 'warangal', 'mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata', 'pune', 'ahmedabad', 'jaipur']
            df['is_major_market'] = df['district'].isin(major_markets).astype(int)
            
            # Quality features
            df['has_quality_grade'] = df['quality_grade'].notna().astype(int)
            
            # Encode categorical variables
            le_crop = LabelEncoder()
            le_district = LabelEncoder()
            
            df['crop_encoded'] = le_crop.fit_transform(df['crop_name'])
            df['district_encoded'] = le_district.fit_transform(df['district'])
            
            # Select features for ML
            feature_columns = [
                'crop_encoded', 'district_encoded', 'month', 'year', 'day_of_week',
                'quarter', 'is_month_start', 'is_month_end', 'is_kharif', 'is_rabi',
                'is_major_market', 'has_quality_grade'
            ]
            
            # Remove rows with NaN in features
            df_features = df.dropna(subset=feature_columns + ['price'])
            
            X = df_features[feature_columns]
            y = df_features['price']
            
            self.stdout.write(f"✅ Feature engineering complete: {len(X)} samples, {len(feature_columns)} features")
            
            return X, y, feature_columns, le_crop, le_district
            
        except Exception as e:
            self.stdout.write(f"❌ Feature engineering error: {str(e)}")
            return None

    def _train_models_with_data(self, X, y):
        """Train ML models"""
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Random Forest (Optimized for speed)
            self.stdout.write("🌲 Training Random Forest...")
            rf_model = RandomForestRegressor(
                n_estimators=100,  # Reduced from 200
                max_depth=10,      # Reduced from 15
                min_samples_split=20,  # Increased for speed
                min_samples_leaf=10,   # Increased for speed
                random_state=42,
                n_jobs=-1
            )
            rf_model.fit(X_train_scaled, y_train)
            
            # Train Gradient Boosting (Optimized for speed)
            self.stdout.write("📈 Training Gradient Boosting...")
            gb_model = GradientBoostingRegressor(
                n_estimators=150,  # Reduced from 300
                learning_rate=0.15, # Increased for faster convergence
                max_depth=6,       # Reduced from 8
                min_samples_split=25, # Increased for speed
                min_samples_leaf=12,  # Increased for speed
                random_state=42
            )
            gb_model.fit(X_train_scaled, y_train)
            
            # Evaluate models
            self.stdout.write("📊 Evaluating models...")
            rf_score = rf_model.score(X_test_scaled, y_test)
            gb_score = gb_model.score(X_test_scaled, y_test)
            
            self.stdout.write(f"Random Forest R²: {rf_score:.4f}")
            self.stdout.write(f"Gradient Boosting R²: {gb_score:.4f}")
            
            # Select best model
            if rf_score > gb_score:
                best_model = rf_model
                best_model_name = "Random Forest"
                best_score = rf_score
            else:
                best_model = gb_model
                best_model_name = "Gradient Boosting"
                best_score = gb_score
            
            self.stdout.write(f"🏆 Best Model: {best_model_name} (R²: {best_score:.4f})")
            
            return {
                'model': best_model,
                'scaler': scaler,
                'model_name': best_model_name,
                'score': best_score,
                'X_test': X_test_scaled,
                'y_test': y_test
            }
            
        except Exception as e:
            self.stdout.write(f"❌ Model training error: {str(e)}")
            return None

    def _save_models(self, models, feature_columns, le_crop, le_district):
        """Save trained models"""
        try:
            # Save the best model
            joblib.dump(models['model'], 'advanced_pricing_model.pkl')
            self.stdout.write("✅ Model saved: advanced_pricing_model.pkl")
            
            # Save the scaler
            joblib.dump(models['scaler'], 'price_scaler.pkl')
            self.stdout.write("✅ Scaler saved: price_scaler.pkl")
            
            # Save fitted encoders
            encoders = {
                'crop_encoder': le_crop,
                'district_encoder': le_district
            }
            
            with open('price_encoders.pkl', 'wb') as f:
                pickle.dump(encoders, f)
            self.stdout.write("✅ Encoders saved: price_encoders.pkl")
            
            # Save feature columns
            with open('price_features.pkl', 'wb') as f:
                pickle.dump(feature_columns, f)
            self.stdout.write("✅ Feature columns saved: price_features.pkl")
            
        except Exception as e:
            self.stdout.write(f"❌ Error saving models: {str(e)}")

    def _test_trained_models(self, X, y, models):
        """Test the trained models"""
        try:
            self.stdout.write("🧪 Testing trained models...")
            
            # Make predictions
            y_pred = models['model'].predict(models['X_test'])
            
            # Calculate metrics
            mae = mean_absolute_error(models['y_test'], y_pred)
            mse = mean_squared_error(models['y_test'], y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(models['y_test'], y_pred)
            
            self.stdout.write(f"📊 Model Performance:")
            self.stdout.write(f"   MAE: ₹{mae:.2f}/kg")
            self.stdout.write(f"   RMSE: ₹{rmse:.2f}/kg")
            self.stdout.write(f"   R² Score: {r2:.4f}")
            
            # Show sample predictions
            sample_indices = np.random.choice(len(y_pred), min(5, len(y_pred)), replace=False)
            self.stdout.write(f"\n📋 Sample Predictions:")
            for idx in sample_indices:
                actual = float(models['y_test'].iloc[idx] if hasattr(models['y_test'], 'iloc') else models['y_test'][idx])
                predicted = float(y_pred[idx])
                error = abs(actual - predicted)
                self.stdout.write(f"   Actual: ₹{actual:.2f}, Predicted: ₹{predicted:.2f}, Error: ₹{error:.2f}")
            
        except Exception as e:
            self.stdout.write(f"❌ Model testing error: {str(e)}")

    def _test_existing_models(self):
        """Test existing ML models"""
        self.stdout.write("🧪 Testing existing ML models...")
        
        try:
            # Load models
            model = joblib.load('advanced_pricing_model.pkl')
            scaler = joblib.load('price_scaler.pkl')
            
            with open('price_features.pkl', 'rb') as f:
                feature_columns = pickle.load(f)
            
            self.stdout.write("✅ Models loaded successfully")
            self.stdout.write(f"📊 Feature columns: {feature_columns}")
            
            # Test with sample data
            sample_features = np.random.random(len(feature_columns))
            sample_features_scaled = scaler.transform(sample_features.reshape(1, -1))
            
            prediction = model.predict(sample_features_scaled)[0]
            self.stdout.write(f"🎯 Sample prediction: ₹{float(prediction):.2f}/kg")
            
        except Exception as e:
            self.stdout.write(f"❌ Model testing failed: {str(e)}")
