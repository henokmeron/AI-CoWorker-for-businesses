# Usage Examples

This guide shows practical examples of using the AI Assistant Coworker.

## Table of Contents
1. [Basic Workflow](#basic-workflow)
2. [API Examples](#api-examples)
3. [Business Use Cases](#business-use-cases)
4. [Advanced Usage](#advanced-usage)

---

## Basic Workflow

### Example 1: Care Agency Assistant

**Scenario:** A care agency wants to help staff quickly find information about policies, rates, and procedures.

#### Step 1: Create Business

```python
# Via UI: Business Settings → Create New Business
Name: "Sunshine Care Agency"
Description: "24/7 care services provider"
```

#### Step 2: Upload Documents

Documents to upload:
- `care_policies.pdf` - Staff policies and procedures
- `fee_schedule.xlsx` - Hourly rates and fees
- `client_onboarding.docx` - New client procedures
- `overtime_rules.txt` - Overtime calculation rules

```python
# Via UI: Documents → Upload Documents
# Drag and drop all 4 files → Upload All
```

#### Step 3: Ask Questions

Example queries:
- "What is the overtime rate for weekends?"
- "What are the steps for onboarding a new client?"
- "What is the hourly rate for level 2 care?"
- "What is the policy on staff sick leave?"

**Sample Response:**
```
Question: "What is the overtime rate for weekends?"

Answer: According to Source 1 (overtime_rules.txt), weekend overtime 
is paid at 1.5x the standard hourly rate. For example, if your base 
rate is £12/hour, weekend overtime would be £18/hour. This applies 
to all hours worked on Saturday and Sunday.

Sources:
- overtime_rules.txt (Relevance: 94%)
- fee_schedule.xlsx (Relevance: 78%)
```

---

## API Examples

### Using cURL

#### 1. Create Business

```bash
curl -X POST http://localhost:8000/api/v1/businesses \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Business",
    "description": "Business description"
  }'
```

#### 2. Upload Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "X-API-Key: your-api-key" \
  -F "business_id=my_business" \
  -F "file=@/path/to/document.pdf"
```

#### 3. Query Documents

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "my_business",
    "query": "What are the payment terms?",
    "max_sources": 5
  }'
```

### Using Python

```python
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key"
headers = {"X-API-Key": API_KEY}

# Create business
response = requests.post(
    f"{BASE_URL}/api/v1/businesses",
    headers=headers,
    json={
        "name": "Tech Startup Inc",
        "description": "Software development company"
    }
)
business_id = response.json()["id"]

# Upload document
with open("employee_handbook.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/api/v1/documents/upload",
        headers=headers,
        files={"file": f},
        data={"business_id": business_id}
    )

print(f"Document uploaded: {response.json()}")

# Ask question
response = requests.post(
    f"{BASE_URL}/api/v1/chat",
    headers=headers,
    json={
        "business_id": business_id,
        "query": "What is the vacation policy?",
        "max_sources": 3
    }
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"\nSources:")
for source in result['sources']:
    print(f"- {source['document_name']}")
```

### Using JavaScript

```javascript
const BASE_URL = "http://localhost:8000";
const API_KEY = "your-api-key";

// Query documents
async function askQuestion(businessId, query) {
  const response = await fetch(`${BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      business_id: businessId,
      query: query,
      max_sources: 5,
    }),
  });

  const result = await response.json();
  console.log("Answer:", result.answer);
  console.log("Sources:", result.sources);
  return result;
}

// Upload document
async function uploadDocument(businessId, file) {
  const formData = new FormData();
  formData.append("business_id", businessId);
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/api/v1/documents/upload`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
    },
    body: formData,
  });

  return await response.json();
}
```

---

## Business Use Cases

### Use Case 1: Consulting Firm

**Setup:**
- Upload client proposals, contracts, rate cards
- Upload internal policies, templates, best practices

**Sample Queries:**
- "What is our standard hourly rate for senior consultants?"
- "Show me the engagement terms in the ABC Corp contract"
- "What are the deliverables for Phase 2 of the XYZ project?"
- "What is our policy on client entertainment expenses?"

---

### Use Case 2: Retail Business

**Setup:**
- Upload product catalogs, pricing lists
- Upload return policies, warranty information
- Upload employee schedules, shift guidelines

**Sample Queries:**
- "What is the return policy for electronics?"
- "What are the specifications for Product SKU-12345?"
- "What is the employee discount rate?"
- "What are the holiday hours for December?"

---

### Use Case 3: Legal Firm

**Setup:**
- Upload case summaries, legal precedents
- Upload client contracts, agreements
- Upload billing guidelines, time tracking rules

**Sample Queries:**
- "What was the outcome of the Smith vs Jones case?"
- "What are the billing codes for contract review?"
- "What is the retainer agreement for Client ABC?"
- "What are the document retention requirements?"

---

### Use Case 4: Real Estate Agency

**Setup:**
- Upload property listings, floor plans
- Upload commission structures, fee schedules
- Upload contracts, legal disclosures

**Sample Queries:**
- "What properties do we have under $500k in downtown?"
- "What is the commission rate for commercial properties?"
- "What disclosures are required for water damage?"
- "What are the terms in the purchase agreement template?"

---

## Advanced Usage

### Custom File Handler

Add support for a custom file format:

```python
# backend/app/services/file_handlers/custom_handlers/excel_handler.py

from typing import Dict, Any, List
import pandas as pd
from ..base_handler import BaseFileHandler

class EnhancedExcelHandler(BaseFileHandler):
    """Enhanced Excel handler with table extraction."""
    
    def can_handle(self, file_path: str, file_type: str) -> bool:
        return file_type in ['xlsx', 'xls']
    
    def process(self, file_path: str) -> Dict[str, Any]:
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        
        text_parts = []
        tables = []
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Convert to text
            text_parts.append(f"Sheet: {sheet_name}\n")
            text_parts.append(df.to_string())
            
            # Extract table data
            tables.append({
                "sheet": sheet_name,
                "data": df.to_dict('records')
            })
        
        return {
            "text": "\n\n".join(text_parts),
            "metadata": {
                "sheets": excel_file.sheet_names,
                "table_count": len(tables)
            },
            "chunks": [],
            "tables": tables
        }
    
    def get_supported_types(self) -> List[str]:
        return ['xlsx', 'xls']
```

Register the handler:

```python
# backend/app/services/document_processor.py

from .file_handlers.custom_handlers.excel_handler import EnhancedExcelHandler

# In DocumentProcessor.__init__():
self.register_handler(EnhancedExcelHandler())
```

---

### Conversation Context

Maintain conversation history for better context:

```python
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key"
headers = {"X-API-Key": API_KEY}

conversation_history = []

def ask(business_id, query):
    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": query,
        "timestamp": "2024-01-01T12:00:00"
    })
    
    # Send request with history
    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        headers=headers,
        json={
            "business_id": business_id,
            "query": query,
            "conversation_history": conversation_history[-10:],  # Last 10 messages
            "max_sources": 5
        }
    )
    
    result = response.json()
    
    # Add assistant response to history
    conversation_history.append({
        "role": "assistant",
        "content": result["answer"],
        "timestamp": "2024-01-01T12:00:01"
    })
    
    return result

# Usage
ask("my_business", "What is the vacation policy?")
ask("my_business", "How many days do I get?")  # Uses context from previous question
ask("my_business", "Can I carry over unused days?")  # Continues conversation
```

---

### Batch Document Upload

Upload multiple documents programmatically:

```python
import os
import requests
from pathlib import Path

def upload_directory(business_id, directory_path):
    """Upload all supported files from a directory."""
    
    BASE_URL = "http://localhost:8000"
    API_KEY = "your-api-key"
    headers = {"X-API-Key": API_KEY}
    
    supported_extensions = [
        '.pdf', '.docx', '.xlsx', '.txt', '.md', 
        '.csv', '.json', '.html', '.pptx'
    ]
    
    results = []
    
    for file_path in Path(directory_path).rglob('*'):
        if file_path.suffix.lower() in supported_extensions:
            print(f"Uploading {file_path.name}...")
            
            with open(file_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/v1/documents/upload",
                    headers=headers,
                    files={"file": (file_path.name, f)},
                    data={"business_id": business_id}
                )
                
                if response.status_code == 200:
                    results.append({
                        "file": file_path.name,
                        "status": "success",
                        "data": response.json()
                    })
                else:
                    results.append({
                        "file": file_path.name,
                        "status": "error",
                        "error": response.text
                    })
    
    return results

# Usage
results = upload_directory("my_business", "./documents")
print(f"Uploaded {len([r for r in results if r['status'] == 'success'])} documents")
```

---

### Custom Prompt Templates

Customize the AI's response style:

```python
# backend/app/services/rag_service.py

# Modify system_prompt in _build_messages():

system_prompt = """You are a professional business assistant specializing in [YOUR INDUSTRY].

Your communication style:
- Formal and professional tone
- Use industry-specific terminology
- Provide actionable recommendations
- Always cite sources

When answering:
1. Start with a direct answer
2. Provide relevant details
3. Cite specific sources
4. Suggest related information if helpful

Remember: Only use information from provided sources."""
```

---

### Streaming Responses

For better UX with long responses:

```python
import requests
import json

def chat_stream(business_id, query):
    """Stream chat response for real-time updates."""
    
    BASE_URL = "http://localhost:8000"
    API_KEY = "your-api-key"
    
    response = requests.post(
        f"{BASE_URL}/api/v1/chat/stream",
        headers={"X-API-Key": API_KEY},
        json={
            "business_id": business_id,
            "query": query,
            "max_sources": 5
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            chunk = json.loads(line)
            
            if chunk["type"] == "answer":
                print(chunk["content"], end="", flush=True)
            elif chunk["type"] == "sources":
                print("\n\nSources:")
                for source in chunk["content"]:
                    print(f"- {source['document_name']}")

# Usage
chat_stream("my_business", "What are the payment terms?")
```

---

## Tips & Best Practices

### Document Organization

1. **Use Clear Filenames:**
   - ✅ `fee_schedule_2024.xlsx`
   - ❌ `untitled.xlsx`

2. **Group Related Documents:**
   - Upload all related documents for a topic at once
   - Use consistent naming conventions

3. **Update Regularly:**
   - Delete outdated documents
   - Re-upload updated versions

### Query Optimization

1. **Be Specific:**
   - ✅ "What is the weekend overtime rate for care assistants?"
   - ❌ "rates?"

2. **Use Complete Questions:**
   - ✅ "What are the steps to onboard a new client?"
   - ❌ "onboarding"

3. **Provide Context:**
   - ✅ "In the employee handbook, what is the vacation policy?"
   - ✅ "According to the fee schedule, what is the hourly rate?"

### Performance Tips

1. **Optimize Chunk Size:**
   - Smaller chunks (500-800 tokens): Better for precise facts
   - Larger chunks (1000-1500 tokens): Better for context

2. **Limit Sources:**
   - 3-5 sources: Faster, focused responses
   - 10+ sources: Slower, more comprehensive

3. **Use Appropriate Models:**
   - GPT-3.5: Faster, cheaper, good for simple queries
   - GPT-4: Slower, better for complex analysis

