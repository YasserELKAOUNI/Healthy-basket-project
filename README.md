# Email Phishing Analysis Agent

An AI-powered email phishing detection system using AWS Bedrock Claude 4.5 and Elastic MCP Server. This agent analyzes emails for phishing indicators using advanced AI analysis combined with rule-based detection.

## Features

- **AI-Powered Analysis**: Uses AWS Bedrock Claude 4.5 for sophisticated phishing detection
- **Elastic Integration**: Connects to Elastic MCP Server for email storage and search
- **Rule-Based Detection**: Combines AI analysis with traditional phishing indicators
- **REST API**: FastAPI-based web service for easy integration
- **CLI Tool**: Command-line interface for batch processing
- **Similar Email Search**: Find related phishing attempts
- **Comprehensive Reporting**: Detailed analysis results with confidence scores

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Email Input   │───▶│  Phishing Agent  │───▶│  Analysis       │
│                 │    │                  │    │  Results        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Elastic MCP     │
                       │  Server          │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  AWS Bedrock     │
                       │  Claude 4.5      │
                       └──────────────────┘
```

## Prerequisites

- Python 3.8+
- AWS Account with Bedrock access
- Elastic Cloud account or Elasticsearch instance
- AWS CLI configured with appropriate permissions

## Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp config.env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # Elastic MCP Server Configuration
   ELASTIC_URL=https://searchsearch-a9ed61.kb.europe-west1.gcp.elastic.cloud
   ELASTIC_API_KEY=your_elastic_api_key_here
   
   # AWS Bedrock Configuration
   BEDROCK_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_aws_access_key_here
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
   AWS_DEFAULT_REGION=us-east-1
   ```

4. **Configure AWS credentials**:
   ```bash
   aws configure
   ```
   
   Or set environment variables:
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

## Usage

### 1. REST API Server

Start the FastAPI server:
```bash
python mcp_server.py
```

The API will be available at `http://localhost:8000`

**API Endpoints**:

- `GET /` - API information
- `GET /health` - Health check
- `POST /analyze` - Analyze an email for phishing
- `POST /search` - Search emails in database
- `POST /index` - Index an email
- `GET /stats` - Get analysis statistics
- `GET /docs` - Interactive API documentation

**Example API Usage**:

```bash
# Analyze an email
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "email": {
      "sender": "noreply@bank-security.com",
      "subject": "URGENT: Verify Your Account",
      "body": {"text": "Click here to verify: http://bit.ly/verify"},
      "recipient": "user@example.com"
    },
    "include_similar_search": true,
    "auto_index": true
  }'
```

### 2. Command Line Interface

**Create a sample email**:
```bash
python cli.py create-sample
```

**Analyze an email**:
```bash
python cli.py analyze sample_email.json
```

**Analyze and index**:
```bash
python cli.py analyze sample_email.json --index
```

**Search emails**:
```bash
python cli.py search "urgent verify account"
```

### 3. Direct Python Usage

```python
from email_phishing_analyzer import EmailPhishingAnalyzer

# Initialize analyzer
analyzer = EmailPhishingAnalyzer(
    elastic_url="https://searchsearch-a9ed61.kb.europe-west1.gcp.elastic.cloud",
    elastic_api_key="your_api_key",
    bedrock_region="us-east-1"
)

# Email data
email_data = {
    "sender": "noreply@bank-security.com",
    "subject": "URGENT: Verify Your Account",
    "body": {"text": "Click here to verify: http://bit.ly/verify"},
    "recipient": "user@example.com"
}

# Analyze email
result = analyzer.analyze_email(email_data)

print(f"Is Phishing: {result.is_phishing}")
print(f"Confidence: {result.confidence_score}")
print(f"Risk Factors: {result.risk_factors}")
```

## Email Data Format

The agent expects email data in the following JSON format:

```json
{
  "sender": "sender@example.com",
  "sender_name": "Sender Name",
  "subject": "Email Subject",
  "body": {
    "text": "Plain text content",
    "html": "<html>HTML content</html>"
  },
  "recipient": "recipient@example.com",
  "timestamp": "2024-01-15T10:30:00Z",
  "attachments": ["file1.pdf", "file2.doc"]
}
```

## Analysis Results

The analysis returns a comprehensive result object:

```python
@dataclass
class PhishingAnalysisResult:
    is_phishing: bool                    # Whether email is likely phishing
    confidence_score: float              # Confidence score (0.0-1.0)
    risk_factors: List[str]              # Identified risk factors
    suspicious_urls: List[str]           # Suspicious URLs found
    suspicious_domains: List[str]         # Suspicious domains
    suspicious_keywords: List[str]       # Suspicious keywords/phrases
    sender_analysis: Dict[str, Any]      # Sender reputation analysis
    content_analysis: Dict[str, Any]     # Content analysis details
    recommendations: List[str]           # Handling recommendations
```

## Phishing Detection Features

### AI Analysis (Claude 4.5)
- Content analysis for phishing patterns
- Sender reputation assessment
- URL and domain analysis
- Grammar and urgency detection
- Contextual understanding

### Rule-Based Detection
- Suspicious keyword detection
- URL shortener identification
- Domain reputation checking
- Pattern matching for common phishing tactics

### Elastic Integration
- Email storage and indexing
- Similar email search
- Historical analysis
- Pattern recognition across campaigns

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ELASTIC_URL` | Elastic MCP Server URL | Required |
| `ELASTIC_API_KEY` | Elastic API key | Optional |
| `BEDROCK_REGION` | AWS Bedrock region | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `LOG_LEVEL` | Logging level | `INFO` |

### Customization

You can customize the phishing detection by modifying:

- `phishing_keywords` list in `EmailPhishingAnalyzer`
- `suspicious_domains` list for URL shorteners
- Claude prompts for different analysis approaches
- Elasticsearch queries for search functionality

## Security Considerations

- Store API keys securely using environment variables
- Use HTTPS for all API communications
- Implement rate limiting for production use
- Regularly update dependencies
- Monitor API usage and costs

## Troubleshooting

### Common Issues

1. **AWS Bedrock Access Denied**:
   - Ensure your AWS account has Bedrock access
   - Check IAM permissions for Bedrock models
   - Verify region configuration

2. **Elastic Connection Failed**:
   - Check Elastic URL and API key
   - Verify network connectivity
   - Ensure Elasticsearch is running

3. **Analysis Timeout**:
   - Check Claude model availability
   - Verify request size limits
   - Monitor AWS service status

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python mcp_server.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review AWS Bedrock documentation
- Consult Elastic MCP Server documentation
- Open an issue in the repository

## Roadmap

- [ ] Real-time email monitoring
- [ ] Advanced ML models integration
- [ ] Dashboard and visualization
- [ ] Multi-language support
- [ ] Integration with email providers
- [ ] Automated response actions
