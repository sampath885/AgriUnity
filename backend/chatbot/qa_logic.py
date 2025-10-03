# backend/chatbot/qa_logic.py

import os
import sys
from django.conf import settings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def get_answer(query: str, user_role: str, user_id: int = None):
    """
    Get comprehensive agricultural advice using HYBRID approach: Local Data + Gemini AI Enhancement
    """
    try:
        # Get user context first
        user_context = {}
        local_data = {}
        
        if user_id:
            try:
                from users.models import CustomUser
                from products.models import ProductListing
                from locations.models import PinCode
                
                user = CustomUser.objects.get(id=user_id)
                user_context = {
                    'role': user.role,
                    'region': user.region,
                    'pincode': user.pincode,
                    'latitude': user.latitude,
                    'longitude': user.longitude,
                    'primary_crops': [crop.name for crop in user.primary_crops.all()],
                    'listings': []
                }
                
                if user.role == 'FARMER':
                    listings = ProductListing.objects.filter(farmer=user, status='AVAILABLE')
                    user_context['listings'] = [
                        {
                            'crop': listing.crop.name,
                            'quantity': listing.quantity_kg,
                            'grade': listing.grade,
                            'created_at': listing.created_at
                        }
                        for listing in listings
                    ]
                
                if user.pincode:
                    try:
                        pin_data = PinCode.objects.get(code=user.pincode)
                        user_context['district'] = pin_data.district
                        user_context['state'] = pin_data.state
                        user_context['full_region'] = f"{pin_data.district}, {pin_data.state}"
                    except PinCode.DoesNotExist:
                        pass
                        
            except Exception as e:
                print(f"Error getting user context: {e}")
        
        # Add user role to context
        user_context['role'] = user_role
        
        # STEP 1: Gather local data first
        print("🔍 Gathering local data...")
        local_data = gather_local_data(query, user_context)
        
        # STEP 2: Use Gemini AI with local data for enhanced response
        if GOOGLE_API_KEY:
            print("🤖 Using Gemini AI with local data for enhanced response...")
            enhanced_response = get_enhanced_gemini_response(query, user_role, user_context, local_data)
            
            if enhanced_response and enhanced_response != "AI response unavailable - using basic fallback":
                return f"🤖 **AgriGenie AI Response (Enhanced with Local Data):**\n\n{enhanced_response}"
        
        # Fallback to basic responses if Gemini fails
        return get_basic_fallback_response(query, user_role)
        
    except Exception as e:
        print(f"Error in QA Logic: {e}")
        return get_basic_fallback_response(query, user_role)

def gather_local_data(query: str, user_context: dict) -> dict:
    """
    Gather local data from various sources to enhance Gemini AI responses
    """
    local_data = {
        'market_prices': {},
        'user_profile': {},
        'regional_data': {},
        'crop_data': {},
        'available_data': []
    }
    
    try:
        # Add the deals app to the path
        sys.path.append(os.path.join(settings.BASE_DIR, 'deals'))
        
        # Import required modules
        from deals.ai_advisor import agri_genie
        from deals.models import MarketPrice
        from locations.models import PinCode
        
        # Get user profile data
        if user_context.get('full_region'):
            local_data['user_profile']['location'] = user_context['full_region']
        if user_context.get('primary_crops'):
            local_data['user_profile']['crops'] = user_context['primary_crops']
        if user_context.get('listings'):
            local_data['user_profile']['current_listings'] = user_context['listings']
        
        # STEP 1: Extract location from user's query if mentioned
        extracted_location = extract_location_from_query(query)
        if extracted_location:
            local_data['user_profile']['extracted_location'] = extracted_location
            local_data['available_data'].append(f"Location from query: {extracted_location}")
            
            # Try to get PINcode data for this location
            try:
                pin_data = PinCode.objects.filter(
                    district__icontains=extracted_location.get('district', ''),
                    state__icontains=extracted_location.get('state', '')
                ).first()
                
                if pin_data:
                    local_data['regional_data']['pin_data'] = {
                        'district': pin_data.district,
                        'state': pin_data.state,
                        'pincode': pin_data.code
                    }
                    local_data['available_data'].append(f"PINcode data found for {pin_data.district}, {pin_data.state}")
            except Exception as e:
                print(f"Error getting PINcode data: {e}")
        
        # STEP 2: Use user's saved location if available
        if user_context.get('full_region'):
            local_data['regional_data']['saved_location'] = user_context['full_region']
            local_data['available_data'].append(f"Saved location: {user_context['full_region']}")
        elif user_context.get('state'):
            local_data['regional_data']['saved_location'] = user_context['state']
            local_data['available_data'].append(f"Saved state: {user_context['state']}")
        elif user_context.get('district'):
            local_data['regional_data']['saved_location'] = user_context['district']
            local_data['available_data'].append(f"Saved district: {user_context['district']}")
        
        # Extract crop names from query for market data
        crop_keywords = ['paddy', 'rice', 'onion', 'potato', 'tomato', 'wheat', 'maize', 'cotton', 'sugarcane']
        query_crops = [crop for crop in crop_keywords if crop in query.lower()]
        
        # Get market price data for relevant crops
        if query_crops:
            # Try to get market data for any available location
            location_to_search = (
                extracted_location.get('district') or 
                extracted_location.get('state') or
                user_context.get('full_region') or
                user_context.get('state') or
                user_context.get('district')
            )
            
            if location_to_search:
                for crop in query_crops:
                    try:
                        # Get recent market prices
                        recent_prices = MarketPrice.objects.filter(
                            crop_name__icontains=crop,
                            region__icontains=location_to_search
                        ).order_by('-date')[:5]
                        
                        if recent_prices:
                            prices = [float(p.price) for p in recent_prices if p.price]
                            if prices:
                                local_data['market_prices'][crop] = {
                                    'recent_prices': prices,
                                    'average_price': sum(prices) / len(prices),
                                    'price_trend': 'rising' if prices[-1] > prices[0] else 'falling' if prices[-1] < prices[0] else 'stable',
                                    'data_points': len(prices)
                                }
                                local_data['available_data'].append(f"Market prices for {crop} in {location_to_search}")
                    except Exception as e:
                        print(f"Error getting market data for {crop}: {e}")
        
        # Get crop-specific data
        if query_crops:
            local_data['crop_data']['mentioned_crops'] = query_crops
            local_data['available_data'].append(f"Crop data for {', '.join(query_crops)}")
        
        # Add user location summary
        if local_data.get('regional_data'):
            location_summary = (
                local_data['regional_data'].get('pin_data', {}).get('district') or
                local_data['regional_data'].get('saved_location') or
                local_data['user_profile'].get('extracted_location', {}).get('district')
            )
            if location_summary:
                local_data['user_profile']['location_summary'] = location_summary
                local_data['available_data'].append(f"User location: {location_summary}")
        
        print(f"📊 Local data gathered: {local_data['available_data']}")
        
    except Exception as e:
        print(f"Error gathering local data: {e}")
    
    return local_data

def extract_location_from_query(query: str) -> dict:
    """
    Extract location information from user's query
    """
    query_lower = query.lower()
    
    # Common Indian states and districts
    states = [
        'andhra pradesh', 'maharashtra', 'karnataka', 'tamil nadu', 'punjab', 'haryana', 
        'uttar pradesh', 'bihar', 'west bengal', 'odisha', 'gujarat', 'rajasthan', 
        'madhya pradesh', 'telangana', 'kerala', 'assam', 'jharkhand', 'chhattisgarh'
    ]
    
    districts = [
        'east godavari', 'west godavari', 'krishna', 'guntur', 'prakasam', 'nellore',
        'chittoor', 'anantapur', 'kurnool', 'kadapa', 'visakhapatnam', 'vizianagaram',
        'srikakulam', 'mumbai', 'pune', 'nashik', 'nagpur', 'aurangabad', 'solapur',
        'kolhapur', 'sangli', 'satara', 'ratnagiri', 'sindhudurg', 'raigad', 'thane'
    ]
    
    extracted = {}
    
    # Check for state mentions
    for state in states:
        if state in query_lower:
            extracted['state'] = state.title()
            break
    
    # Check for district mentions
    for district in districts:
        if district in query_lower:
            extracted['district'] = district.title()
            break
    
    # Check for city mentions (common cities)
    cities = ['mumbai', 'pune', 'nashik', 'nagpur', 'hyderabad', 'bangalore', 'chennai', 'kolkata', 'delhi']
    for city in cities:
        if city in query_lower:
            extracted['city'] = city.title()
            break
    
    return extracted

def get_enhanced_gemini_response(query: str, user_role: str, user_context: dict, local_data: dict):
    """
    Get enhanced response from Gemini AI using local data as context
    """
    try:
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Build comprehensive context with local data
        context_info = ""
        
        # User profile context
        if user_context.get('full_region'):
            context_info += f"\n📍 User Location: {user_context['full_region']}"
        if user_context.get('primary_crops'):
            context_info += f"\n🌾 User's Crops: {', '.join(user_context['primary_crops'])}"
        if user_context.get('listings'):
            listings_str = ', '.join([f"{l['crop']} ({l['quantity']}kg)" for l in user_context['listings']])
            context_info += f"\n📦 Current Listings: {listings_str}"
        if user_context.get('role'):
            context_info += f"\n👤 User Role: {user_context['role']}"
        
        # Local market data context
        if local_data.get('market_prices'):
            context_info += "\n📊 **Local Market Data:**"
            for crop, data in local_data['market_prices'].items():
                context_info += f"\n• {crop.title()}: ₹{data['average_price']:.2f}/quintal ({data['price_trend']} trend, {data['data_points']} data points)"
        
        # Available data summary
        if local_data.get('available_data'):
            context_info += f"\n\n🔍 **Available Local Data:** {', '.join(local_data['available_data'])}"
        
        # Create enhanced prompt
        prompt = f"""
        You are AgriGenie, an expert AI agricultural advisor for Indian farmers. 
        
        **User Query:** "{query}"
        **User Role:** {user_role}
        
        **User Context:**{context_info}
        
        **CRITICAL INSTRUCTIONS - NEVER ASK FOR MORE INFORMATION:**
        - Use ALL available information provided above
        - If location is available, use it for regional advice
        - If market data is available, reference it specifically
        - Give comprehensive answers without asking for clarification
        - Assume the user wants complete information based on available data
        
        **Your Task:** Provide a comprehensive, data-driven answer that combines:
        1. **Local Data Analysis** - Use the provided market data and user context
        2. **Regional Knowledge** - Apply Indian agricultural knowledge for the user's region
        3. **Specific Recommendations** - Give actionable advice based on the query
        4. **Data Integration** - Reference the local market data when relevant
        
        **Response Format Requirements (IMPORTANT - Make it look professional like ChatGPT):**
        
        **Structure:**
        - Start with a friendly greeting and brief overview
        - Use clear, bold headlines with emojis for each section
        - Use bullet points (•) for lists and recommendations
        - Use numbered lists (1., 2., 3.) for step-by-step instructions
        - Use proper spacing between sections
        - End with actionable next steps
        
        **Formatting Examples:**
        ```
        🌾 **Crop Selection Guide**
        
        Based on your location in [Region], here are the best options:
        
        • **High-Yield Crops:** [specific crops with reasons]
        • **Drought-Resistant Options:** [specific crops with reasons]
        • **Cash Crops:** [specific crops with reasons]
        
        📊 **Market Analysis**
        
        Current market conditions show:
        • Price trends: [specific data]
        • Demand patterns: [specific data]
        
        1. **Immediate Actions**
        2. **Short-term Planning**
        3. **Long-term Strategy**
        ```
        
        **Response Requirements:**
        - Use the local market data to provide accurate price information
        - Reference the user's location for regional advice (if available)
        - Consider the user's current crops and listings
        - Give specific numbers, dates, and actionable steps
        - Use emojis and clear formatting
        - Keep it under 400 words but comprehensive
        - NEVER ask for more information - provide what you can based on available data
        - Make it easy to read with clear sections and bullet points
        
        **Format your response with clear sections, bullet points, and specific data references.**
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"Enhanced Gemini AI response failed: {e}")
        return "AI response unavailable - using basic fallback"

def get_local_ai_response(query: str, user_role: str, user_id: int = None):
    """
    Get response from local Phase 3 AI advisor with enhanced user context
    """
    try:
        # Add the deals app to the path
        sys.path.append(os.path.join(settings.BASE_DIR, 'deals'))
        sys.path.append(os.path.join(settings.BASE_DIR, 'users'))
        sys.path.append(os.path.join(settings.BASE_DIR, 'products'))
        
        # Import required modules
        from deals.ai_advisor import agri_genie
        from users.models import CustomUser
        from products.models import ProductListing, CropProfile
        from locations.models import PinCode
        
        # Get user context if user_id is provided
        user_context = {}
        if user_id:
            try:
                user = CustomUser.objects.get(id=user_id)
                user_context = {
                    'role': user.role,
                    'region': user.region,
                    'pincode': user.pincode,
                    'latitude': user.latitude,
                    'longitude': user.longitude,
                    'primary_crops': [crop.name for crop in user.primary_crops.all()],
                    'listings': []
                }
                
                # Get user's current product listings
                if user.role == 'FARMER':
                    listings = ProductListing.objects.filter(farmer=user, status='AVAILABLE')
                    user_context['listings'] = [
                        {
                            'crop': listing.crop.name,
                            'quantity': listing.quantity_kg,
                            'grade': listing.grade,
                            'created_at': listing.created_at
                        }
                        for listing in listings
                    ]
                
                # Get regional context from pincode
                if user.pincode:
                    try:
                        pin_data = PinCode.objects.get(code=user.pincode)
                        user_context['district'] = pin_data.district
                        user_context['state'] = pin_data.state
                        user_context['full_region'] = f"{pin_data.district}, {pin_data.state}"
                    except PinCode.DoesNotExist:
                        pass
                        
            except CustomUser.DoesNotExist:
                pass
        
        # Add user role to context
        user_context['role'] = user_role
        
        # Get comprehensive agricultural advice with enhanced context
        response = agri_genie.get_comprehensive_agricultural_advice(
            query=query,
            user_id=user_id,
            conversation_id=None,
            user_context=user_context
        )
        
        if response.get('status') == 'success':
            return format_local_response(response, user_context)
        else:
            return "No local data available"
            
    except Exception as e:
        print(f"Local AI response failed: {e}")
        # Return a specific error message that will trigger fallback
        return "Local AI advisor error - using fallback"

def format_local_response(response, user_context):
    """
    Format local AI response into farmer-friendly format
    """
    try:
        # Check if response has status
        if response.get('status') == 'error':
            return f"❌ **Error:** {response.get('error', 'Something went wrong')}"
        
        # Extract the main response content
        if 'crop_planning_advice' in response:
            advice = response['crop_planning_advice']
            if advice.get('status') == 'success':
                top_crop = advice.get('top_recommendations', [{}])[0] if advice.get('top_recommendations') else {}
                financial = advice.get('financial_plan', {})
                return f"🌾 **Crop Planning Advice:**\n\n" + \
                       f"**Best Crop:** {top_crop.get('crop', 'Rice')}\n" + \
                       f"**Season:** {advice.get('recommended_season', 'kharif')}\n" + \
                       f"**Expected Profit:** ₹{financial.get('expected_profit', 0):,.0f}/acre\n" + \
                       f"**Investment Needed:** ₹{financial.get('total_investment', 0):,.0f}/acre\n\n" + \
                       f"**What to do next:**\n" + "\n".join([f"• {action}" for action in advice.get('next_actions', [])])
        
        elif 'market_strategy' in response:
            strategy = response['market_strategy']
            if strategy.get('status') == 'success':
                timing = strategy.get('timing_strategy', {})
                pricing = strategy.get('pricing_strategy', {})
                return f"📊 **Market Strategy:**\n\n" + \
                       f"**When to sell:** {timing.get('recommendation', 'Within 1-2 weeks')}\n" + \
                       f"**Target price:** ₹{pricing.get('target_price', 0):.2f}/quintal\n" + \
                       f"**Strategy:** {strategy.get('negotiation_guidance', {}).get('strategy', 'Competitive pricing')}\n\n" + \
                       f"**Action plan:**\n" + "\n".join([f"• {action}" for action in strategy.get('action_plan', [])])
        
        elif 'financial_planning' in response:
            financial = response['financial_planning']
            if financial.get('status') == 'success':
                return f"💰 **Financial Planning:**\n\n{financial.get('message', 'Here is your financial guidance:')}\n\n" + \
                       f"**What I can help with:**\n" + "\n".join([f"• {cap}" for cap in financial.get('capabilities', [])]) + "\n\n" + \
                       f"**Your next steps:**\n" + "\n".join([f"• {step}" for step in financial.get('next_steps', [])])
        
        elif 'risk_assessment' in response:
            risk = response['risk_assessment']
            if risk.get('status') == 'success':
                risk_analysis = risk.get('risk_analysis', {})
                return f"⚠️ **Risk Assessment:**\n\n" + \
                       f"**Risk Level:** {risk_analysis.get('overall_risk_level', 'Medium')}\n" + \
                       f"**Main Risks:** {', '.join(risk_analysis.get('market_risks', {}).get('factors', ['Price volatility', 'Weather dependency']))}\n\n" + \
                       f"**How to protect yourself:**\n" + "\n".join([f"• {strategy}" for strategy in risk.get('mitigation_strategies', [])])
        
        elif 'group_strategy' in response:
            group = response['group_strategy']
            if group.get('status') == 'success':
                return f"👥 **Group Strategy:**\n\n{group.get('message', 'Here is your group strategy guidance:')}\n\n" + \
                       f"**What I can help with:**\n" + "\n".join([f"• {cap}" for cap in group.get('capabilities', [])]) + "\n\n" + \
                       f"**Your next steps:**\n" + "\n".join([f"• {step}" for step in group.get('next_steps', [])])
        
        # Handle general responses with intent
        elif 'nlu_understanding' in response:
            intent = response.get('nlu_understanding', {}).get('intent', {}).get('primary', 'general')
            
            if intent == 'crop_planning':
                return f"🌾 **Crop Planning:**\n\n{response.get('message', 'I can help you plan your crops for the next season.')}\n\n" + \
                       f"**What I can help with:**\n" + \
                       f"• Seasonal crop recommendations\n" + \
                       f"• Investment and ROI analysis\n" + \
                       f"• Risk assessment for different crops\n" + \
                       f"• Regional suitability analysis\n\n" + \
                       f"**Your next steps:**\n" + \
                       f"• Tell me your region and budget\n" + \
                       f"• Ask about specific crops you're interested in\n" + \
                       f"• Get seasonal planting advice"
            
            elif intent == 'market_strategy':
                return f"📊 **Market Strategy:**\n\n{response.get('message', 'I can help you with market timing and selling strategies.')}\n\n" + \
                       f"**What I can help with:**\n" + \
                       f"• Best time to sell your crops\n" + \
                       f"• Pricing strategies and negotiation\n" + \
                       f"• Market trend analysis\n" + \
                       f"• Risk mitigation strategies\n\n" + \
                       f"**Your next steps:**\n" + \
                       f"• Tell me what crop you want to sell\n" + \
                       f"• Get market timing recommendations\n" + \
                       f"• Learn negotiation strategies"
            
            elif intent == 'financial_planning':
                return f"💰 **Financial Planning:**\n\n{response.get('message', 'I can help you with financial planning for your farm.')}\n\n" + \
                       f"**What I can help with:**\n" + \
                       f"• Input cost analysis and optimization\n" + \
                       f"• ROI calculations for different crops\n" + \
                       f"• Financing option recommendations\n" + \
                       f"• Risk-adjusted return analysis\n" + \
                       f"• Budget planning and tracking\n\n" + \
                       f"**Your next steps:**\n" + \
                       f"• Tell me your crop and budget\n" + \
                       f"• Get detailed cost analysis\n" + \
                       f"• Learn about financing options"
            
            elif intent == 'risk_assessment':
                return f"⚠️ **Risk Assessment:**\n\n{response.get('message', 'I can help you assess and manage farming risks.')}\n\n" + \
                       f"**What I can help with:**\n" + \
                       f"• Weather and climate risks\n" + \
                       f"• Market price volatility\n" + \
                       f"• Crop disease and pest risks\n" + \
                       f"• Financial risk assessment\n" + \
                       f"• Risk mitigation strategies\n\n" + \
                       f"**Your next steps:**\n" + \
                       f"• Tell me your crop and region\n" + \
                       f"• Get specific risk analysis\n" + \
                       f"• Learn protection strategies"
            
            elif intent == 'group_strategy':
                return f"👥 **Group Strategy:**\n\n{response.get('message', 'I can help you with group strategies and collective bargaining.')}\n\n" + \
                       f"**What I can help with:**\n" + \
                       f"• Group performance analysis\n" + \
                       f"• Collective bargaining strategies\n" + \
                       f"• Risk sharing mechanisms\n" + \
                       f"• Group decision optimization\n" + \
                       f"• Market entry coordination\n\n" + \
                       f"**Your next steps:**\n" + \
                       f"• Tell me about your group\n" + \
                       f"• Get bargaining strategies\n" + \
                       f"• Learn coordination techniques"
            
            else:
                return f"🤖 **AgriGenie Response:**\n\n{response.get('message', 'I can help you with comprehensive agricultural advice.')}\n\n" + \
                       f"**What I can help with:**\n" + \
                       f"• 🌾 Crop planning and recommendations\n" + \
                       f"• 📊 Market strategies and timing\n" + \
                       f"• 💰 Financial planning and analysis\n" + \
                       f"• ⚠️ Risk assessment and mitigation\n" + \
                       f"• 👥 Group strategies and bargaining\n\n" + \
                       f"**Just ask me about:**\n" + \
                       f"• 'What should I plant next season in Maharashtra?'\n" + \
                       f"• 'When is the best time to sell potatoes?'\n" + \
                       f"• 'How much does it cost to grow rice?'\n" + \
                       f"• 'How can I protect against price drops?'"
        
        # Fallback for any other response structure
        else:
            return f"🤖 **AgriGenie Response:**\n\n{response.get('message', 'I can help you with agricultural advice. Please ask me about crops, market strategies, financial planning, or risk assessment.')}"
    
    except Exception as e:
        print(f"Formatting local response failed: {e}")
        return "No local data available"

def get_gemini_fallback_response(query: str, user_role: str, user_context: dict = None):
    """
    Get response from Gemini AI with enhanced context awareness and regional knowledge
    """
    try:
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Build context-aware prompt
        context_info = ""
        if user_context:
            if user_context.get('full_region'):
                context_info += f"\nUser Location: {user_context['full_region']}"
            if user_context.get('primary_crops'):
                context_info += f"\nUser's Crops: {', '.join(user_context['primary_crops'])}"
            if user_context.get('listings'):
                listings_str = ', '.join([f"{l['crop']} ({l['quantity']}kg)" for l in user_context['listings']])
                context_info += f"\nCurrent Listings: {listings_str}"
            if user_context.get('role'):
                context_info += f"\nUser Role: {user_context['role']}"
        
        # Create farmer-friendly prompt with regional knowledge
        prompt = f"""
        You are AgriGenie, an expert AI agricultural advisor for Indian farmers. 
        
        User Query: "{query}"
        User Role: {user_role}
        {context_info}
        
        Provide a direct, actionable answer in simple language (under 200 words) that includes:
        
        1. **Direct Answer**: Specific answer to their question
        2. **Regional Context**: If location is known, include regional advice
        3. **Actionable Steps**: 2-3 specific things they can do
        4. **Cost/Returns**: Approximate figures if relevant
        5. **Next Actions**: What they should do next
        
        **Important Guidelines:**
        - Use simple, farmer-friendly language
        - Include regional knowledge for Indian agriculture
        - Give specific numbers and dates when possible
        - Don't ask for more information - provide what you can
        - Use emojis to make it friendly
        - Focus on practical, actionable advice
        
        **Format your response with clear sections and bullet points.**
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"Gemini AI response failed: {e}")
        return "AI response unavailable - using basic fallback"

def get_basic_fallback_response(query: str, user_role: str):
    """
    Basic fallback response when all else fails
    """
    query_lower = query.lower()
    
    # Basic keyword-based responses
    if any(word in query_lower for word in ['plant', 'grow', 'crop', 'season']):
        return f"🌾 **Crop Advice:**\n\n" + \
               f"Based on your question about crops, here's what you should know:\n\n" + \
               f"**For Kharif season (June-October):**\n" + \
               f"• Rice, Maize, Cotton, Sugarcane, Pulses\n" + \
               f"• Best for regions with good monsoon\n\n" + \
               f"**For Rabi season (November-March):**\n" + \
               f"• Wheat, Barley, Mustard, Chickpea, Potato\n" + \
               f"• Good for winter crops\n\n" + \
               f"**Next steps:**\n" + \
               f"• Check your soil type and water availability\n" + \
               f"• Consider market prices for different crops\n" + \
               f"• Plan your budget (₹25,000-50,000 per acre)"
    
    elif any(word in query_lower for word in ['sell', 'market', 'price', 'profit']):
        return f"📊 **Market Strategy:**\n\n" + \
               f"Here's how to get better prices for your crops:\n\n" + \
               f"**Timing is key:**\n" + \
               f"• Sell during peak demand months\n" + \
               f"• Avoid selling during harvest glut\n\n" + \
               f"**Quality matters:**\n" + \
               f"• Grade your produce properly\n" + \
               f"• Clean and package well\n\n" + \
               f"**Next steps:**\n" + \
               f"• Check current market prices\n" + \
               f"• Contact multiple buyers\n" + \
               f"• Consider group selling for better prices"
    
    elif any(word in query_lower for word in ['cost', 'budget', 'money', 'investment']):
        return f"💰 **Financial Planning:**\n\n" + \
               f"Here's what you need to know about costs:\n\n" + \
               f"**Typical costs per acre:**\n" + \
               f"• Seeds: ₹2,000-5,000\n" + \
               f"• Fertilizers: ₹3,000-8,000\n" + \
               f"• Labor: ₹8,000-18,000\n" + \
               f"• Total: ₹25,000-50,000\n\n" + \
               f"**Expected returns:**\n" + \
               f"• Rice: 20-30% profit\n" + \
               f"• Vegetables: 30-50% profit\n" + \
               f"• Pulses: 25-40% profit\n\n" + \
               f"**Next steps:**\n" + \
               f"• Calculate your specific costs\n" + \
               f"• Check available loans\n" + \
               f"• Plan for unexpected expenses"
    
    elif any(word in query_lower for word in ['risk', 'danger', 'problem', 'protect']):
        return f"⚠️ **Risk Protection:**\n\n" + \
               f"Here's how to protect yourself:\n\n" + \
               f"**Main risks:**\n" + \
               f"• Weather damage (drought/floods)\n" + \
               f"• Price volatility\n" + \
               f"• Disease and pests\n\n" + \
               f"**Protection strategies:**\n" + \
               f"• Crop insurance (PMFBY scheme)\n" + \
               f"• Diversify your crops\n" + \
               f"• Save money for emergencies\n\n" + \
               f"**Next steps:**\n" + \
               f"• Check insurance options\n" + \
               f"• Build emergency fund\n" + \
               f"• Monitor weather forecasts"
    
    else:
        return f"🤖 **AgriGenie Response:**\n\n" + \
               f"I can help you with:\n\n" + \
               f"• 🌾 **Crop planning** - what to plant and when\n" + \
               f"• 📊 **Market strategy** - when to sell and how to get better prices\n" + \
               f"• 💰 **Financial planning** - costs, returns, and budgeting\n" + \
               f"• ⚠️ **Risk protection** - insurance and safety measures\n" + \
               f"• 👥 **Group strategies** - collective bargaining and cooperation\n\n" + \
               f"**Ask me anything specific about farming!** For example:\n" + \
               f"• 'What should I plant next season?'\n" + \
               f"• 'When is the best time to sell potatoes?'\n" + \
               f"• 'How much does it cost to grow rice?'\n" + \
               f"• 'How can I protect against price drops?'"

def is_generic_response(response: str) -> bool:
    """
    Check if a response is generic/template-based
    """
    generic_phrases = [
        "I can help you with",
        "What I can help with:",
        "Your next steps:",
        "Please ask me about",
        "I can help you with comprehensive agricultural advice"
    ]
    
    response_lower = response.lower()
    return any(phrase.lower() in response_lower for phrase in generic_phrases)