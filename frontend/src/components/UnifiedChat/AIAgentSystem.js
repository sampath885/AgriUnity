// AIAgentSystem.js - Phase 3: Enhanced AI Agent Intelligence
class AIAgentSystem {
  constructor(dealGroup, user, workflowEngine, onMessageGenerated) {
    this.dealGroup = dealGroup;
    this.user = user;
    this.workflowEngine = workflowEngine;
    this.onMessageGenerated = onMessageGenerated;
    this.conversationContext = [];
    this.userPreferences = this.initializeUserPreferences();
    this.aiPersonality = this.initializeAIPersonality();
    this.knowledgeBase = this.initializeKnowledgeBase();
    this.responseTemplates = this.initializeResponseTemplates();
    
    this.initializeAI();
  }

  // Initialize AI personality based on user role
  initializeAIPersonality() {
    const basePersonality = {
      tone: 'helpful',
      detailLevel: 'medium',
      responseStyle: 'conversational',
      expertise: 'agricultural_business',
      language: 'en'
    };

    if (this.user.role === 'FARMER') {
      return {
        ...basePersonality,
        role: 'farmer_advisor',
        focus: 'profit_maximization',
        expertise: 'crop_management,market_analysis,logistics'
      };
    } else if (this.user.role === 'BUYER') {
      return {
        ...basePersonality,
        role: 'buyer_advisor',
        focus: 'quality_assurance',
        expertise: 'quality_standards,logistics,payment_processing'
      };
    }

    return basePersonality;
  }

  // Initialize user preferences
  initializeUserPreferences() {
    return {
      responseStyle: 'helpful',
      detailLevel: 'medium',
      notificationFrequency: 'high',
      language: 'en',
      preferredTopics: ['pricing', 'logistics', 'quality'],
      learningStyle: 'visual'
    };
  }

  // Initialize knowledge base
  initializeKnowledgeBase() {
    return {
      marketData: {
        wheat: { currentPrice: '₹52/kg', trend: 'stable', forecast: '₹50-55/kg' },
        rice: { currentPrice: '₹48/kg', trend: 'rising', forecast: '₹45-52/kg' },
        cotton: { currentPrice: '₹65/kg', trend: 'volatile', forecast: '₹60-70/kg' }
      },
      logistics: {
        hubs: ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata'],
        averageTransitTime: '2-3 days',
        costPerKm: '₹2.5/kg'
      },
      regulations: {
        qualityStandards: 'FSSAI compliant',
        exportRequirements: 'Phytosanitary certificate required',
        importDuties: 'Varies by destination'
      }
    };
  }

  // Initialize response templates
  initializeResponseTemplates() {
    return {
      greeting: [
        "Hello! I'm your AI agricultural advisor. How can I help you today? 🌾",
        "Welcome! I'm here to guide you through this deal. What would you like to know? 🤝",
        "Hi there! Ready to make the best deal? Let me know what you need! 💰"
      ],
      stageGuidance: {
        'NEGOTIATING': [
          "We're in the negotiation phase. Consider these factors for the best deal:",
          "During negotiations, focus on price, quality, and delivery terms.",
          "Remember: a good deal benefits both parties. Let's find the sweet spot!"
        ],
        'ACCEPTED': [
          "Great! Deal accepted. Now let's handle logistics and payments.",
          "Excellent! The hard part is done. Let's get your produce moving.",
          "Perfect! Now we ensure smooth delivery and payment processing."
        ],
        'IN_TRANSIT': [
          "Your produce is on the move! Let's track its journey.",
          "Shipment in progress! We'll keep you updated on delivery status.",
          "Transportation active! Estimated delivery: {delivery_date}."
        ],
        'DELIVERED': [
          "Delivery completed! Time to confirm receipt and process payment.",
          "Great news! Your produce has arrived. Let's finalize everything.",
          "Delivery successful! Now let's complete the payment process."
        ]
      },
      marketInsights: [
        "Current market analysis shows {trend} prices for {crop}.",
        "Based on recent data, {crop} prices are {trend}.",
        "Market indicators suggest {trend} for {crop} in the coming weeks."
      ],
      recommendations: [
        "I recommend {action} to {benefit}.",
        "Consider {action} for better {outcome}.",
        "My suggestion: {action} to optimize {aspect}."
      ]
    };
  }

  // Initialize AI system
  initializeAI() {
    this.generateWelcomeMessage();
    this.startProactiveMonitoring();
  }

  // Generate welcome message
  generateWelcomeMessage() {
    const welcomeMessage = this.createMessage({
      type: 'ai_greeting',
      content: this.getRandomTemplate('greeting'),
      priority: 'low',
      category: 'ai_guidance'
    });

    this.onMessageGenerated(welcomeMessage);
  }

  // Start proactive monitoring
  startProactiveMonitoring() {
    // Monitor workflow progress
    setInterval(() => {
      this.checkWorkflowProgress();
    }, 60000); // Check every minute

    // Monitor market conditions
    setInterval(() => {
      this.checkMarketConditions();
    }, 300000); // Check every 5 minutes

    // Monitor deadlines
    setInterval(() => {
      this.checkDeadlines();
    }, 30000); // Check every 30 seconds
  }

  // Check workflow progress and provide guidance
  checkWorkflowProgress() {
    const workflowStatus = this.workflowEngine.getWorkflowStatus();
    const currentStage = workflowStatus.currentStage;
    const pendingActions = workflowStatus.pendingActions;

    // Generate stage-specific guidance
    if (this.shouldProvideGuidance(currentStage)) {
      this.generateStageGuidance(currentStage);
    }

    // Handle pending actions
    if (pendingActions.length > 0) {
      this.handlePendingActions(pendingActions);
    }
  }

  // Check if guidance should be provided
  shouldProvideGuidance(stage) {
    const lastGuidance = this.conversationContext
      .filter(ctx => ctx.type === 'stage_guidance')
      .pop();

    if (!lastGuidance) return true;

    const timeSinceLastGuidance = Date.now() - new Date(lastGuidance.timestamp).getTime();
    const guidanceInterval = 10 * 60 * 1000; // 10 minutes

    return timeSinceLastGuidance > guidanceInterval;
  }

  // Generate stage-specific guidance
  generateStageGuidance(stage) {
    const templates = this.responseTemplates.stageGuidance[stage];
    if (!templates) return;

    const template = this.getRandomTemplate(templates);
    const content = this.processTemplate(template, { stage });

    const guidanceMessage = this.createMessage({
      type: 'ai_stage_guidance',
      content: content,
      priority: 'medium',
      category: 'ai_guidance',
      metadata: { stage, guidanceType: 'proactive' }
    });

    this.onMessageGenerated(guidanceMessage);
    this.addToContext('stage_guidance', { stage, content });
  }

  // Handle pending actions
  handlePendingActions(pendingActions) {
    pendingActions.forEach(action => {
      if (action.status === 'pending' && !action.aiNotified) {
        this.generateActionNotification(action);
        action.aiNotified = true;
      }
    });
  }

  // Generate action notification
  generateActionNotification(action) {
    let content = '';
    let priority = 'medium';

    switch (action.type) {
      case 'COUNTER_OFFER_SUGGESTION':
        content = `💡 **Counter Offer Suggestion**\n\n${action.message}\n\n**Current Offer:** ₹${action.data.currentOffer.price_per_kg}/kg\n**Suggested Price:** ₹${action.data.suggestedPrice}/kg\n\nThis could increase your profit by ${((action.data.suggestedPrice - action.data.currentOffer.price_per_kg) / action.data.currentOffer.price_per_kg * 100).toFixed(1)}%`;
        priority = 'high';
        break;
      
      case 'MARKET_INSIGHTS':
        content = `📊 **Market Analysis**\n\n${action.message}\n\n**Current Trend:** ${action.data.marketTrend}\n**Price Range:** ${action.data.priceRange}\n\nUse this information to make informed decisions about your deal.`;
        priority = 'medium';
        break;
      
      case 'HUB_ASSIGNED':
        content = `🚚 **Logistics Hub Assigned**\n\n${action.message}\n\n**Hub Location:** ${action.data.location}\n**Status:** Ready for collection\n\nPlease prepare your produce for pickup at the assigned hub.`;
        priority = 'high';
        break;
      
      case 'ESCROW_CONTRACT_READY':
        content = `💰 **Escrow Contract Ready**\n\n${action.message}\n\n**Contract ID:** ${action.data.contractId}\n**Amount:** ₹${action.data.amount}\n\nPlease review and confirm the escrow contract to proceed.`;
        priority = 'high';
        break;
      
      case 'DELIVERY_SCHEDULED':
        content = `📅 **Delivery Scheduled**\n\n${action.message}\n\n**Delivery Date:** ${new Date(action.data.deliveryDate).toLocaleDateString()}\n**Status:** Confirmed\n\nPlease ensure someone is available to receive the delivery.`;
        priority = 'high';
        break;
      
      case 'POLL_DEADLINE_APPROACHING':
        content = `⏰ **Poll Deadline Approaching**\n\n${action.message}\n\n**Time Remaining:** ${action.data.hoursLeft} hours\n**Action Required:** Please vote on the current offer\n\nYour vote is crucial for the group's decision!`;
        priority = 'high';
        break;
      
      default:
        content = `ℹ️ **Action Required**\n\n${action.message}\n\nPlease review and take necessary action to continue.`;
        priority = 'medium';
    }

    const notificationMessage = this.createMessage({
      type: 'ai_action_notification',
      content: content,
      priority: priority,
      category: 'ai_guidance',
      metadata: { actionType: action.type, actionData: action.data }
    });

    this.onMessageGenerated(notificationMessage);
  }

  // Check market conditions
  checkMarketConditions() {
    const crop = this.dealGroup.products?.[0]?.crop?.name?.toLowerCase();
    if (!crop || !this.knowledgeBase.marketData[crop]) return;

    const marketData = this.knowledgeBase.marketData[crop];
    const currentPrice = parseFloat(marketData.currentPrice.replace('₹', ''));
    const targetPrice = this.dealGroup.target_price_per_kg;

    if (targetPrice && Math.abs(currentPrice - targetPrice) / targetPrice > 0.15) {
      this.generateMarketAlert(crop, marketData, targetPrice);
    }
  }

  // Generate market alert
  generateMarketAlert(crop, marketData, targetPrice) {
    const currentPrice = parseFloat(marketData.currentPrice.replace('₹', ''));
    const priceDifference = ((currentPrice - targetPrice) / targetPrice * 100).toFixed(1);
    const trend = currentPrice > targetPrice ? 'above' : 'below';

    const content = `📈 **Market Alert**\n\n**Crop:** ${crop.charAt(0).toUpperCase() + crop.slice(1)}\n**Current Market Price:** ${marketData.currentPrice}\n**Your Target Price:** ₹${targetPrice}/kg\n**Difference:** ${priceDifference}% ${trend} target\n**Market Trend:** ${marketData.trend}\n\n**Recommendation:** ${this.getMarketRecommendation(currentPrice, targetPrice, marketData.trend)}`;

    const marketMessage = this.createMessage({
      type: 'ai_market_alert',
      content: content,
      priority: 'high',
      category: 'ai_guidance',
      metadata: { crop, marketData, targetPrice }
    });

    this.onMessageGenerated(marketMessage);
  }

  // Get market recommendation
  getMarketRecommendation(currentPrice, targetPrice, trend) {
    if (currentPrice > targetPrice * 1.1) {
      return "Consider increasing your target price to match current market conditions.";
    } else if (currentPrice < targetPrice * 0.9) {
      return "Current market prices are below your target. You may need to adjust expectations.";
    } else {
      return "Market prices are close to your target. This is a good time to negotiate.";
    }
  }

  // Check deadlines
  checkDeadlines() {
    const activePoll = this.dealGroup.active_poll;
    if (!activePoll) return;

    const now = new Date();
    const expiry = new Date(activePoll.expires_at);
    const timeLeft = expiry - now;
    const hoursLeft = timeLeft / (1000 * 60 * 60);

    if (hoursLeft <= 1 && hoursLeft > 0) {
      this.generateUrgentDeadlineAlert(hoursLeft);
    } else if (hoursLeft <= 0.5 && hoursLeft > 0) {
      this.generateCriticalDeadlineAlert(hoursLeft);
    }
  }

  // Generate urgent deadline alert
  generateUrgentDeadlineAlert(hoursLeft) {
    const content = `⚠️ **Urgent: Poll Deadline Approaching**\n\n**Time Remaining:** ${(hoursLeft * 60).toFixed(0)} minutes\n**Action Required:** Vote immediately\n\nThis is your final reminder to participate in the group decision!`;

    const urgentMessage = this.createMessage({
      type: 'ai_urgent_deadline',
      content: content,
      priority: 'high',
      category: 'ai_guidance',
      metadata: { deadlineType: 'urgent', timeLeft: hoursLeft }
    });

    this.onMessageGenerated(urgentMessage);
  }

  // Generate critical deadline alert
  generateCriticalDeadlineAlert(hoursLeft) {
    const content = `🚨 **Critical: Poll Expiring Soon**\n\n**Time Remaining:** ${(hoursLeft * 60).toFixed(0)} minutes\n**Status:** Last chance to vote\n\n**Immediate action required** to avoid missing this opportunity!`;

    const criticalMessage = this.createMessage({
      type: 'ai_critical_deadline',
      content: content,
      priority: 'high',
      category: 'ai_guidance',
      metadata: { deadlineType: 'critical', timeLeft: hoursLeft }
    });

    this.onMessageGenerated(criticalMessage);
  }

  // Process user message and generate response
  processUserMessage(userMessage) {
    // Add to conversation context
    this.addToContext('user_message', userMessage);

    // Analyze message intent
    const intent = this.analyzeIntent(userMessage.content);
    
    // Generate appropriate response
    const response = this.generateResponse(intent, userMessage);
    
    // Add to context
    this.addToContext('ai_response', response);
    
    return response;
  }

  // Analyze message intent
  analyzeIntent(content) {
    const lowerContent = content.toLowerCase();
    
    if (lowerContent.includes('price') || lowerContent.includes('cost')) {
      return 'price_inquiry';
    } else if (lowerContent.includes('market') || lowerContent.includes('trend')) {
      return 'market_inquiry';
    } else if (lowerContent.includes('logistics') || lowerContent.includes('delivery')) {
      return 'logistics_inquiry';
    } else if (lowerContent.includes('help') || lowerContent.includes('advice')) {
      return 'help_request';
    } else if (lowerContent.includes('status') || lowerContent.includes('progress')) {
      return 'status_inquiry';
    } else {
      return 'general_inquiry';
    }
  }

  // Generate response based on intent
  generateResponse(intent, userMessage) {
    let content = '';
    let priority = 'medium';

    switch (intent) {
      case 'price_inquiry':
        content = this.generatePriceResponse();
        priority = 'medium';
        break;
      
      case 'market_inquiry':
        content = this.generateMarketResponse();
        priority = 'medium';
        break;
      
      case 'logistics_inquiry':
        content = this.generateLogisticsResponse();
        priority = 'medium';
        break;
      
      case 'help_request':
        content = this.generateHelpResponse();
        priority = 'high';
        break;
      
      case 'status_inquiry':
        content = this.generateStatusResponse();
        priority = 'low';
        break;
      
      default:
        content = this.generateGeneralResponse();
        priority = 'low';
    }

    return this.createMessage({
      type: 'ai_response',
      content: content,
      priority: priority,
      category: 'ai_guidance',
      metadata: { intent, userMessageId: userMessage.id }
    });
  }

  // Generate price response
  generatePriceResponse() {
    const crop = this.dealGroup.products?.[0]?.crop?.name;
    const targetPrice = this.dealGroup.target_price_per_kg;
    const currentOffer = this.dealGroup.current_offer?.price_per_kg;

    let content = `💰 **Price Information**\n\n`;
    
    if (crop) {
      const marketData = this.knowledgeBase.marketData[crop.toLowerCase()];
      if (marketData) {
        content += `**Crop:** ${crop}\n**Current Market Price:** ${marketData.currentPrice}\n**Market Trend:** ${marketData.trend}\n**Forecast:** ${marketData.forecast}\n\n`;
      }
    }

    if (targetPrice) {
      content += `**Your Target Price:** ₹${targetPrice}/kg\n`;
    }

    if (currentOffer) {
      content += `**Current Offer:** ₹${currentOffer}/kg\n`;
    }

    content += `\n**Recommendation:** Focus on quality and delivery terms when negotiating price.`;

    return content;
  }

  // Generate market response
  generateMarketResponse() {
    const crop = this.dealGroup.products?.[0]?.crop?.name;
    
    let content = `📊 **Market Analysis**\n\n`;
    
    if (crop) {
      const marketData = this.knowledgeBase.marketData[crop.toLowerCase()];
      if (marketData) {
        content += `**Crop:** ${crop}\n**Current Price:** ${marketData.currentPrice}\n**Trend:** ${marketData.trend}\n**Forecast:** ${marketData.forecast}\n\n`;
      }
    }

    content += `**Market Insights:**\n• Monitor price trends regularly\n• Consider seasonal factors\n• Stay updated on government policies\n• Track export/import demand\n\n**Strategy:** Use market data to make informed pricing decisions.`;

    return content;
  }

  // Generate logistics response
  generateLogisticsResponse() {
    const assignedHub = this.dealGroup.assigned_hub;
    const logisticsStatus = this.dealGroup.logistics_status;
    
    let content = `🚚 **Logistics Information**\n\n`;
    
    if (assignedHub) {
      content += `**Assigned Hub:** ${assignedHub}\n`;
    }
    
    if (logisticsStatus) {
      content += `**Status:** ${logisticsStatus}\n`;
    }

    content += `\n**Available Hubs:** ${this.knowledgeBase.logistics.hubs.join(', ')}\n**Average Transit Time:** ${this.knowledgeBase.logistics.averageTransitTime}\n**Cost per km:** ${this.knowledgeBase.logistics.costPerKm}\n\n**Next Steps:** Coordinate with the logistics team for smooth operations.`;

    return content;
  }

  // Generate help response
  generateHelpResponse() {
    return `🤖 **How I Can Help You**\n\n**I'm your AI agricultural advisor, here to:**\n\n• 📊 Provide market insights and analysis\n• 💰 Help with pricing strategies\n• 🚚 Guide logistics and delivery\n• 📋 Track deal progress\n• ⚡ Suggest optimal actions\n• 🔔 Send timely notifications\n\n**Just ask me about:**\n• Current market prices\n• Deal status and progress\n• Logistics coordination\n• Payment processing\n• Quality standards\n\n**I'm here 24/7 to help you succeed!** 🌾`;
  }

  // Generate status response
  generateStatusResponse() {
    const workflowStatus = this.workflowEngine.getWorkflowStatus();
    const currentStage = workflowStatus.currentStage;
    const pendingActions = workflowStatus.pendingActions;
    
    let content = `📋 **Current Status**\n\n**Stage:** ${currentStage}\n**Progress:** ${this.getStageProgress(currentStage)}%\n\n`;
    
    if (pendingActions.length > 0) {
      content += `**Pending Actions:** ${pendingActions.length}\n`;
      pendingActions.slice(0, 3).forEach(action => {
        content += `• ${action.message}\n`;
      });
    } else {
      content += `**Status:** All caught up! No pending actions.`;
    }

    return content;
  }

  // Generate general response
  generateGeneralResponse() {
    return `💬 **General Guidance**\n\nI'm here to help you navigate this agricultural deal successfully. Feel free to ask me about:\n\n• Market conditions and pricing\n• Deal progress and next steps\n• Logistics and delivery\n• Payment and escrow\n• Quality standards\n• Any other concerns\n\nWhat would you like to know more about? 🤔`;
  }

  // Get stage progress percentage
  getStageProgress(stage) {
    const stageOrder = ['NEGOTIATING', 'ACCEPTED', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED'];
    const currentIndex = stageOrder.indexOf(stage);
    return currentIndex >= 0 ? ((currentIndex + 1) / stageOrder.length * 100).toFixed(0) : 0;
  }

  // Get random template
  getRandomTemplate(templates) {
    if (Array.isArray(templates)) {
      return templates[Math.floor(Math.random() * templates.length)];
    }
    return templates;
  }

  // Process template with variables
  processTemplate(template, variables) {
    let processed = template;
    Object.entries(variables).forEach(([key, value]) => {
      processed = processed.replace(new RegExp(`{${key}}`, 'g'), value);
    });
    return processed;
  }

  // Create message object
  createMessage(messageData) {
    return {
      id: Date.now() + Math.random(),
      content: messageData.content,
      sender: null,
      sender_name: 'AI Advisor 🤖',
      created_at: new Date().toISOString(),
      message_type: messageData.type,
      category: messageData.category,
      priority: messageData.priority,
      is_ai_agent: true,
      metadata: messageData.metadata || {}
    };
  }

  // Add to conversation context
  addToContext(type, data) {
    this.conversationContext.push({
      type,
      data,
      timestamp: new Date().toISOString()
    });

    // Keep only last 50 context items
    if (this.conversationContext.length > 50) {
      this.conversationContext = this.conversationContext.slice(-50);
    }
  }

  // Get AI system status
  getAIStatus() {
    return {
      personality: this.aiPersonality,
      userPreferences: this.userPreferences,
      conversationContext: this.conversationContext.length,
      lastActivity: this.conversationContext[this.conversationContext.length - 1]?.timestamp,
      active: true
    };
  }

  // Update user preferences
  updateUserPreferences(preferences) {
    this.userPreferences = { ...this.userPreferences, ...preferences };
  }

  // Cleanup
  destroy() {
    // Clear any intervals or timers
    this.conversationContext = [];
  }
}

export default AIAgentSystem;
