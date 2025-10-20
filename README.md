# 🛒 Smart MCP Groceries Health Basket Analysis System

A modern, intelligent system for grocery recommendations and nutritional analysis using MCP tools and Claude AI. This system helps users make informed decisions about their grocery shopping based on health and nutritional insights.

## ✨ Features

- **🧠 LLM-Powered Intent Analysis**: Uses Claude 4.5 Sonnet to intelligently analyze queries and select optimal MCP tools
- **🤖 Advanced AI Analysis**: Generates comprehensive health and nutrition reports using Claude 4.5 Sonnet
- **📱 Modern Web Interface**: Beautiful, responsive UI with green health-themed design
- **🔧 Comprehensive MCP Integration**: Uses specialized catalog tools and platform core tools
- **📊 Multiple Output Modes**: Choose between AI analysis, raw results, or rule-based fallback
- **⚡ Rate Limit Handling**: Intelligent retry logic with exponential backoff and caching
- **🔄 Graceful Fallbacks**: Rule-based system when LLM is unavailable
- **🌍 Multilingual Support**: French language output for comprehensive analysis

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file based on `config.env.example`:
```env
ELASTIC_URL=https://searchsearch-a9ed61.kb.europe-west1.gcp.elastic.cloud/api/agent_builder/mcp
ELASTIC_API_KEY=your_api_key_here
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
BEDROCK_REGION=us-east-1
```

**Note**: The `.env` file is automatically ignored by git for security.

### 3. Start the Web UI
```bash
python start_web_ui.py
```

### 4. Open Your Browser
Navigate to: **http://localhost:8000**

## 🎯 Usage Examples

### Query Types Supported:

1. **Health Recommendations**
   - "Find healthy breakfast options"
   - "Recommend high-protein foods"
   - "Show me organic vegetables"

2. **Product Search**
   - "Find red wine"
   - "Search for gluten-free products"
   - "Find low-sodium items"
   - "Show me dairy alternatives"

3. **Nutrition Analysis**
   - "Find nutritious foods"
   - "Show me high-fiber options"
   - "Recommend vitamin-rich products"

4. **Promotions & Deals**
   - "Find current promotions"
   - "Show me discounted items"
   - "What's on sale?"

5. **Data Exploration**
   - "List all indices"
   - "Explore available data"
   - "What data is available?"

6. **Product Retrieval**
   - "Get product PROD_12345"
   - "Show me item ABC_XYZ"

## 🔧 CLI Usage

### Smart Grocery CLI (Service-based)
```bash
# Full AI analysis with Claude 4.5 (default)
python smart_grocery_service_cli.py "Find healthy breakfast options"
python smart_grocery_service_cli.py "Find red wine"
python smart_grocery_service_cli.py "Find current promotions"

# Raw results only (bypasses LLM for faster results)
python smart_grocery_service_cli.py "Find healthy breakfast options" --no-llm
```

### Available Commands
- **Product Search**: Find products using intelligent tool selection
- **Health Recommendations**: Get AI-powered nutritional advice in French
- **Nutrition Analysis**: Analyze nutritional content and health benefits
- **Promotions Search**: Find current deals and discounts
- **Data Exploration**: Discover available data sources and indices
- **Product Details**: Retrieve specific product information by ID

## 🌐 Web Interface Features

### Modern Health-Themed Design
- **Green Color Scheme**: Represents health, nature, and freshness
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Intuitive Interface**: Easy-to-use query input with examples
- **Real-time Status**: Live system status with health indicators

### Interactive Elements
- **Smart Query Input**: Natural language processing for grocery queries
- **Example Queries**: Click-to-use health-focused examples
- **AI Analysis Toggle**: Choose between AI insights or raw data
- **Loading Animations**: Visual feedback during processing

### Results Display
- **Intent Analysis**: Shows detected query intent and confidence
- **Comprehensive Health Analysis**: 7-section AI-generated nutrition reports
- **Raw Results**: Formatted MCP tool results for debugging
- **Error Handling**: Clear error messages and troubleshooting

## 🧠 AI Analysis Sections

When LLM analysis is enabled, Claude 4.5 Sonnet generates comprehensive analysis in French:

1. **Direct Answer**: Immediate response to your grocery/health question
2. **Nutritional Analysis**: Detailed analysis of nutritional value and health benefits
3. **Health Recommendations**: Specific health benefits and dietary considerations
4. **Shopping Guidance**: Best products for health goals and value analysis
5. **Meal Planning Insights**: How products fit into balanced diets
6. **Healthy Lifestyle Tips**: Additional dietary recommendations and lifestyle factors
7. **Healthy Score Index**: Uses nutritional scoring for product evaluation

## 🔍 MCP Tools Used

### Core Platform Tools
- **`platform_core_search`**: General search across Elasticsearch indices with flexible querying
- **`platform_core_get_document_by_id`**: Retrieve full content of Elasticsearch documents by ID
- **`platform_core_list_indices`**: List indices, aliases and datastreams from Elasticsearch cluster
- **`platform_core_get_index_mapping`**: Retrieve mappings for specified indices
- **`platform_core_index_explorer`**: Find relevant indices based on natural language queries

### Specialized Catalog Tools
- **`catalog_products_search`**: Search grocery products by text (specialized for grocery data)
- **`catalog_nutrition_search`**: Retrieve nutrition rows filtered by health_score
- **`catalog_promotions_search`**: Fetch SKUs with active promotions and promo payload

## 📊 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   Smart CLI     │    │   MCP Tools     │
│   (FastAPI)     │◄──►│   (Python)      │◄──►│   (Elastic)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HTML/CSS/JS   │    │   Intent        │    │   Data Storage  │
│   Interface     │    │   Analysis      │    │   & Search      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User          │    │   Claude AI     │    │   Product       │
│   Interaction   │    │   Analysis      │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🎨 UI Components

### Query Interface
- **Natural Language Input**: Ask questions about groceries and health
- **Smart Examples**: Pre-built queries for common health scenarios
- **Analysis Options**: Toggle between AI analysis and raw results
- **Status Indicators**: Real-time system health monitoring

### Results Display
- **Intent Recognition**: Shows how the system interpreted your query
- **Confidence Scoring**: Displays confidence level for tool selection
- **Health Analysis**: Comprehensive nutritional and dietary insights
- **Actionable Recommendations**: Practical advice for healthy shopping

## 🔒 Security & Privacy

- **Environment Variables**: Secure configuration management
- **API Key Authentication**: Proper MCP server authentication
- **Input Validation**: Sanitized user inputs
- **Error Handling**: Secure error messages without sensitive data

## 📱 Browser Compatibility

- **Chrome**: Full support with modern features
- **Firefox**: Complete functionality
- **Safari**: Full compatibility
- **Edge**: Full support
- **Mobile Browsers**: Responsive design for all devices

## 🚨 Troubleshooting

### Common Issues:

1. **"System Offline"**
   - Check if `.env` file is configured
   - Verify Elastic URL and API key
   - Ensure MCP server is accessible

2. **"LLM analysis failed" / "ThrottlingException"**
   - **Rate Limiting**: Claude is experiencing high demand
   - **Solution**: Use `--no-llm` flag for immediate results
   - **Retry Logic**: System automatically retries with exponential backoff
   - **Caching**: Repeated queries use cached results

3. **"Found 0 results"**
   - **Data Compatibility**: Catalog tools may not match current data structure
   - **Current Data**: System contains wine products from Belgian grocery store
   - **Fallback**: Try different query types or use `platform_core_search`

4. **"Analysis failed"**
   - Check MCP server connectivity
   - Verify Elastic indices exist (`products`, `nutrition`, `promotions`)
   - Check API key permissions

### Debug Modes:
- **Raw Results**: Use `--no-llm` flag to see MCP tool responses
- **Rule-based**: System automatically falls back to rule-based analysis
- **Caching**: Repeated queries are cached to avoid rate limits

## 🔄 Recent Updates & Improvements

### Latest Enhancements:
- **Claude 4.5 Sonnet**: Upgraded from Claude 3.5 to 4.5 for better analysis
- **LLM Intent Analysis**: Intelligent query analysis using Claude 4.5
- **Rate Limit Handling**: Retry logic with exponential backoff and caching
- **French Language Output**: Comprehensive analysis in French
- **Healthy Score Index**: Nutritional scoring integration
- **Comprehensive MCP Tools**: Added specialized catalog tools
- **Graceful Fallbacks**: Rule-based system when LLM unavailable

### System Evolution:
- **Original**: Email phishing analysis system
- **Repurposed**: Grocery health basket analysis
- **Enhanced**: LLM-powered intent analysis and advanced features
- **Optimized**: Rate limiting, caching, and multilingual support

## 🎉 Success!

You now have a fully functional groceries health basket analysis system! The system uses Claude 4.5 Sonnet for intelligent intent analysis and comprehensive health recommendations in French.

### Key Capabilities:
- **🧠 Smart Tool Selection**: LLM-powered analysis chooses optimal MCP tools
- **🤖 Advanced AI Analysis**: Claude 4.5 generates detailed nutritional insights
- **⚡ Robust Performance**: Rate limiting handling with graceful fallbacks
- **🌍 Multilingual**: French language output for comprehensive analysis
- **📊 Multiple Modes**: AI analysis, raw results, or rule-based fallback

**Happy healthy shopping! 🛒🥗🍷**

---

## 📝 Project Files

- **`smart_grocery_service_cli.py`**: Main CLI with LLM-powered intent analysis (legacy `smart_grocery_cli.py` deprecated)
- **`web_ui.py`**: FastAPI web interface
- **`start_web_ui.py`**: Web server launcher
- **`config.env.example`**: Environment configuration template
- **`.gitignore`**: Comprehensive git ignore rules
- **`requirements.txt`**: Python dependencies
- **`README.md`**: This documentation
