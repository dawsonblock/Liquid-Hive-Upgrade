# Integration Examples

This guide provides practical examples of integrating with the Liquid-Hive-Upgrade system across different use cases and programming languages.

## Table of Contents

- [Basic Chat Integration](#basic-chat-integration)
- [Advanced Streaming Chat](#advanced-streaming-chat)
- [Vision & Multimodal](#vision--multimodal)
- [Arena & Model Evaluation](#arena--model-evaluation)
- [Swarm Intelligence](#swarm-intelligence)
- [Enterprise Integration](#enterprise-integration)
- [Web Applications](#web-applications)
- [Mobile Applications](#mobile-applications)
- [Microservices Architecture](#microservices-architecture)

## Basic Chat Integration

### Python Flask Application

```python
from flask import Flask, request, jsonify, render_template
import asyncio
from liquid_hive import LiquidHiveClient

app = Flask(__name__)

# Initialize Liquid-Hive client
client = LiquidHiveClient(
    base_url="https://api.liquid-hive.dev",
    api_key="your-api-key"
)

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get response from Liquid-Hive
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(client.chat(message))
        
        return jsonify({
            'response': response['message'],
            'model': response['model_used'],
            'cost': response.get('cost', 0)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

**HTML Template (templates/chat.html):**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Liquid-Hive Chat</title>
    <style>
        .chat-container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .messages { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
        .input-container { display: flex; gap: 10px; }
        .message-input { flex: 1; padding: 10px; }
        .send-button { padding: 10px 20px; }
        .message { margin-bottom: 10px; }
        .user-message { text-align: right; color: #007bff; }
        .ai-message { text-align: left; color: #28a745; }
    </style>
</head>
<body>
    <div class="chat-container">
        <h1>Liquid-Hive Chat</h1>
        <div id="messages" class="messages"></div>
        <div class="input-container">
            <input type="text" id="messageInput" class="message-input" placeholder="Type your message...">
            <button onclick="sendMessage()" class="send-button">Send</button>
        </div>
    </div>

    <script>
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessage('You: ' + message, 'user-message');
            input.value = '';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    addMessage('AI: ' + data.response, 'ai-message');
                    addMessage(`Model: ${data.model} | Cost: $${data.cost.toFixed(4)}`, 'info-message');
                } else {
                    addMessage('Error: ' + data.error, 'error-message');
                }
            } catch (error) {
                addMessage('Error: ' + error.message, 'error-message');
            }
        }
        
        function addMessage(text, className) {
            const messages = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + className;
            messageDiv.textContent = text;
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        }
        
        // Send message on Enter key
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>
```

### Node.js Express Application

```javascript
const express = require('express');
const { LiquidHiveClient } = require('@liquid-hive/client');
const path = require('path');

const app = express();
const port = 3000;

// Initialize Liquid-Hive client
const client = new LiquidHiveClient({
  baseUrl: 'https://api.liquid-hive.dev',
  apiKey: process.env.LIQUID_HIVE_API_KEY
});

app.use(express.json());
app.use(express.static('public'));

// Serve the chat interface
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Chat endpoint
app.post('/api/chat', async (req, res) => {
  try {
    const { message } = req.body;
    
    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }
    
    // Get response from Liquid-Hive
    const response = await client.chat(message);
    
    res.json({
      response: response.message,
      model: response.model_used,
      cost: response.cost || 0
    });
    
  } catch (error) {
    console.error('Chat error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Health check
app.get('/health', async (req, res) => {
  try {
    const health = await client.health();
    res.json(health);
  } catch (error) {
    res.status(503).json({ error: 'Service unavailable' });
  }
});

app.listen(port, () => {
  console.log(`Chat app listening at http://localhost:${port}`);
});
```

## Advanced Streaming Chat

### WebSocket Streaming Implementation

```python
import asyncio
import websockets
import json
from liquid_hive import LiquidHiveClient

class StreamingChatServer:
    def __init__(self):
        self.client = LiquidHiveClient(
            base_url="https://api.liquid-hive.dev",
            api_key="your-api-key"
        )
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections."""
        print(f"Client connected: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                data = json.loads(message)
                
                if data.get('type') == 'chat':
                    await self.handle_chat_stream(websocket, data['message'])
                elif data.get('type') == 'health':
                    health = await self.client.health()
                    await websocket.send(json.dumps({
                        'type': 'health',
                        'data': health
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {websocket.remote_address}")
        except Exception as e:
            print(f"Error handling client: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'error': str(e)
            }))
    
    async def handle_chat_stream(self, websocket, message):
        """Handle streaming chat responses."""
        try:
            # Send typing indicator
            await websocket.send(json.dumps({
                'type': 'typing',
                'status': True
            }))
            
            # Get streaming response (if supported by client)
            # For now, we'll simulate streaming by sending the response in chunks
            response = await self.client.chat(message)
            
            # Simulate streaming by sending words one by one
            words = response['message'].split()
            for i, word in enumerate(words):
                await websocket.send(json.dumps({
                    'type': 'token',
                    'content': word + ' ',
                    'index': i
                }))
                await asyncio.sleep(0.1)  # Simulate delay
            
            # Send completion message
            await websocket.send(json.dumps({
                'type': 'complete',
                'model': response['model_used'],
                'cost': response.get('cost', 0),
                'tokens': response.get('tokens_used', {})
            }))
            
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'error': str(e)
            }))
    
    def start_server(self, host='localhost', port=8765):
        """Start the WebSocket server."""
        start_server = websockets.serve(self.handle_client, host, port)
        print(f"Streaming chat server started on ws://{host}:{port}")
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    server = StreamingChatServer()
    server.start_server()
```

**Client-side JavaScript:**
```javascript
class StreamingChatClient {
    constructor(wsUrl) {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.isConnected = false;
    }
    
    connect() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = () => {
                this.isConnected = true;
                console.log('Connected to streaming chat');
                resolve();
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };
            
            this.ws.onclose = () => {
                this.isConnected = false;
                console.log('Disconnected from streaming chat');
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };
        });
    }
    
    sendMessage(message) {
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'chat',
                message: message
            }));
        }
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'typing':
                this.onTyping(data.status);
                break;
            case 'token':
                this.onToken(data.content, data.index);
                break;
            case 'complete':
                this.onComplete(data);
                break;
            case 'error':
                this.onError(data.error);
                break;
            case 'health':
                this.onHealth(data.data);
                break;
        }
    }
    
    onTyping(isTyping) {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.style.display = isTyping ? 'block' : 'none';
        }
    }
    
    onToken(content, index) {
        const responseElement = document.getElementById('current-response');
        if (responseElement) {
            responseElement.textContent += content;
        }
    }
    
    onComplete(data) {
        console.log('Response complete:', data);
        const statsElement = document.getElementById('response-stats');
        if (statsElement) {
            statsElement.textContent = `Model: ${data.model} | Cost: $${data.cost.toFixed(4)}`;
        }
    }
    
    onError(error) {
        console.error('Chat error:', error);
        alert('Error: ' + error);
    }
    
    onHealth(health) {
        console.log('System health:', health);
    }
}

// Usage
const client = new StreamingChatClient('ws://localhost:8765');
client.connect().then(() => {
    console.log('Ready to chat!');
});
```

## Vision & Multimodal

### Image Analysis Application

```python
import streamlit as st
from liquid_hive import LiquidHiveClient
import asyncio
from PIL import Image
import io

# Initialize client
client = LiquidHiveClient(
    base_url="https://api.liquid-hive.dev",
    api_key=st.secrets["LIQUID_HIVE_API_KEY"]
)

st.title("🔍 AI Vision Analysis")
st.write("Upload an image and ask questions about it!")

# File uploader
uploaded_file = st.file_uploader(
    "Choose an image...", 
    type=['jpg', 'jpeg', 'png', 'gif']
)

if uploaded_file is not None:
    # Display the image
    image = Image.open(uploaded_file)
    st.image(image, caption='Uploaded Image', use_column_width=True)
    
    # Text input for questions
    question = st.text_input(
        "What would you like to know about this image?",
        placeholder="Describe what you see in this image"
    )
    
    # Grounding option
    grounding_required = st.checkbox(
        "Enable object detection/grounding",
        help="This will identify and locate objects in the image"
    )
    
    if st.button("Analyze Image") and question:
        with st.spinner("Analyzing image..."):
            try:
                # Prepare form data
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                
                # Create form data
                form_data = {
                    'image': ('image.png', img_bytes, 'image/png'),
                    'prompt': (None, question)
                }
                
                # Make API call (using requests directly for multipart)
                import requests
                import httpx
                
                async def analyze_image():
                    async with httpx.AsyncClient() as http_client:
                        response = await http_client.post(
                            f"{client.base_url}/api/vision",
                            params={"grounding_required": grounding_required},
                            files={
                                'image': ('image.png', img_bytes.getvalue(), 'image/png')
                            },
                            data={'prompt': question},
                            headers={"x-api-key": client.api_key}
                        )
                        return response.json()
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(analyze_image())
                
                # Display results
                st.subheader("🤖 AI Analysis")
                st.write(result.get('description', 'No description available'))
                
                # Display detected objects if grounding was enabled
                if grounding_required and 'objects_detected' in result:
                    st.subheader("🎯 Detected Objects")
                    for obj in result['objects_detected']:
                        st.write(f"**{obj['label']}** - Confidence: {obj['confidence']:.2%}")
                
                # Display metadata
                with st.expander("📊 Analysis Details"):
                    st.json({
                        'model_used': result.get('model_used'),
                        'processing_time': result.get('processing_time'),
                        'cost': result.get('cost')
                    })
                    
            except Exception as e:
                st.error(f"Error analyzing image: {str(e)}")

# Sidebar with examples
st.sidebar.header("💡 Example Questions")
st.sidebar.write("""
- What objects do you see in this image?
- Describe the scene in detail
- What colors are prominent?
- Are there any people in the image?
- What is the mood or atmosphere?
- Can you identify any text in the image?
""")
```

### React Vision Component

```jsx
import React, { useState, useRef } from 'react';
import { LiquidHiveClient } from '@liquid-hive/client';

const VisionAnalyzer = () => {
  const [image, setImage] = useState(null);
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [grounding, setGrounding] = useState(false);
  const fileInputRef = useRef(null);
  
  const client = new LiquidHiveClient({
    baseUrl: process.env.REACT_APP_LIQUID_HIVE_BASE_URL,
    apiKey: process.env.REACT_APP_LIQUID_HIVE_API_KEY
  });
  
  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setImage(file);
      setResult(null);
    }
  };
  
  const analyzeImage = async () => {
    if (!image || !question) return;
    
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('image', image);
      formData.append('prompt', question);
      
      // Direct API call since SDK doesn't support vision yet
      const response = await fetch(`${client.baseUrl}/api/vision?grounding_required=${grounding}`, {
        method: 'POST',
        headers: {
          'x-api-key': client.apiKey
        },
        body: formData
      });
      
      const data = await response.json();
      setResult(data);
      
    } catch (error) {
      console.error('Vision analysis error:', error);
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="vision-analyzer">
      <h2>🔍 AI Vision Analysis</h2>
      
      <div className="upload-section">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleImageUpload}
          accept="image/*"
          style={{ display: 'none' }}
        />
        <button onClick={() => fileInputRef.current?.click()}>
          Upload Image
        </button>
        
        {image && (
          <div className="image-preview">
            <img 
              src={URL.createObjectURL(image)} 
              alt="Upload preview" 
              style={{ maxWidth: '400px', maxHeight: '300px' }}
            />
          </div>
        )}
      </div>
      
      <div className="question-section">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What would you like to know about this image?"
          rows={3}
          style={{ width: '100%', marginBottom: '10px' }}
        />
        
        <label>
          <input
            type="checkbox"
            checked={grounding}
            onChange={(e) => setGrounding(e.target.checked)}
          />
          Enable object detection
        </label>
      </div>
      
      <button 
        onClick={analyzeImage} 
        disabled={!image || !question || loading}
        style={{ marginTop: '10px' }}
      >
        {loading ? 'Analyzing...' : 'Analyze Image'}
      </button>
      
      {result && (
        <div className="results-section" style={{ marginTop: '20px' }}>
          {result.error ? (
            <div className="error">Error: {result.error}</div>
          ) : (
            <>
              <h3>Analysis Result</h3>
              <p>{result.description}</p>
              
              {result.objects_detected && result.objects_detected.length > 0 && (
                <div className="detected-objects">
                  <h4>Detected Objects</h4>
                  <ul>
                    {result.objects_detected.map((obj, index) => (
                      <li key={index}>
                        <strong>{obj.label}</strong> - {(obj.confidence * 100).toFixed(1)}%
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div className="metadata" style={{ fontSize: '0.9em', color: '#666', marginTop: '10px' }}>
                Model: {result.model_used} | 
                Processing time: {result.processing_time}s | 
                Cost: ${result.cost?.toFixed(4)}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default VisionAnalyzer;
```

## Arena & Model Evaluation

### Automated Model Comparison

```python
import asyncio
from liquid_hive import LiquidHiveClient
from dataclasses import dataclass
from typing import List, Dict, Any
import json
import time

@dataclass
class EvaluationTask:
    input_text: str
    reference_output: str
    task_type: str
    difficulty: str
    metadata: Dict[str, Any]

class ModelEvaluator:
    def __init__(self, api_key: str, base_url: str = "https://api.liquid-hive.dev"):
        self.client = LiquidHiveClient(base_url=base_url, api_key=api_key)
        self.results = []
    
    async def create_evaluation_suite(self, tasks: List[EvaluationTask]) -> List[str]:
        """Submit multiple tasks for evaluation."""
        task_ids = []
        
        for task in tasks:
            try:
                response = await self.client.arena_submit(
                    task_input=task.input_text,
                    reference=task.reference_output,
                    metadata={
                        "task_type": task.task_type,
                        "difficulty": task.difficulty,
                        **task.metadata
                    }
                )
                task_ids.append(response['task_id'])
                print(f"Submitted task: {response['task_id']}")
                
            except Exception as e:
                print(f"Failed to submit task: {e}")
        
        return task_ids
    
    async def wait_for_completion(self, task_ids: List[str], timeout: int = 300) -> Dict[str, Any]:
        """Wait for all tasks to complete and collect results."""
        start_time = time.time()
        completed_tasks = {}
        
        while len(completed_tasks) < len(task_ids) and (time.time() - start_time) < timeout:
            for task_id in task_ids:
                if task_id not in completed_tasks:
                    try:
                        # Check task status (this would need to be implemented in the SDK)
                        # For now, we'll simulate with a delay
                        await asyncio.sleep(1)
                        
                        # In a real implementation, you'd check the task status
                        # result = await self.client.get_task_status(task_id)
                        # if result['status'] == 'completed':
                        #     completed_tasks[task_id] = result
                        
                    except Exception as e:
                        print(f"Error checking task {task_id}: {e}")
            
            await asyncio.sleep(5)  # Check every 5 seconds
        
        return completed_tasks
    
    async def run_comparative_evaluation(
        self, 
        tasks: List[EvaluationTask],
        models_to_compare: List[str]
    ) -> Dict[str, Any]:
        """Run a comprehensive comparative evaluation."""
        
        # Submit all tasks
        task_ids = await self.create_evaluation_suite(tasks)
        
        # Wait for completion
        completed_tasks = await self.wait_for_completion(task_ids)
        
        # Collect model comparisons
        comparisons = []
        for i, model_a in enumerate(models_to_compare):
            for model_b in models_to_compare[i+1:]:
                for task_id in task_ids:
                    if task_id in completed_tasks:
                        # Get outputs for both models from the completed task
                        task_result = completed_tasks[task_id]
                        
                        # This would need to be implemented based on the actual API
                        output_a = task_result.get(f'output_{model_a}')
                        output_b = task_result.get(f'output_{model_b}')
                        
                        if output_a and output_b:
                            # Determine winner (this could be automated or manual)
                            winner = self.determine_winner(output_a, output_b, task_id)
                            
                            comparison = await self.client.arena_compare(
                                task_id=task_id,
                                model_a=model_a,
                                model_b=model_b,
                                output_a=output_a,
                                output_b=output_b,
                                winner=winner
                            )
                            comparisons.append(comparison)
        
        # Get final leaderboard
        leaderboard = await self.client.arena_leaderboard()
        
        return {
            "total_tasks": len(task_ids),
            "completed_tasks": len(completed_tasks),
            "comparisons": len(comparisons),
            "leaderboard": leaderboard
        }
    
    def determine_winner(self, output_a: str, output_b: str, task_id: str) -> str:
        """Determine the winner between two outputs (placeholder implementation)."""
        # This is a simplified example - in practice, you might use:
        # - Human evaluation
        # - Automated scoring against reference
        # - LLM-as-a-judge evaluation
        
        # For this example, we'll just compare lengths (not a good metric!)
        if len(output_a) > len(output_b):
            return "model_a"
        else:
            return "model_b"

# Usage example
async def main():
    evaluator = ModelEvaluator("your-api-key")
    
    # Define evaluation tasks
    tasks = [
        EvaluationTask(
            input_text="Write a Python function to calculate fibonacci numbers",
            reference_output="def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
            task_type="code_generation",
            difficulty="medium",
            metadata={"language": "python"}
        ),
        EvaluationTask(
            input_text="Explain the concept of machine learning in simple terms",
            reference_output="Machine learning is a method of data analysis that automates analytical model building...",
            task_type="explanation",
            difficulty="easy",
            metadata={"domain": "AI/ML"}
        ),
        # Add more tasks...
    ]
    
    # Run evaluation
    results = await evaluator.run_comparative_evaluation(
        tasks=tasks,
        models_to_compare=["gpt-4o", "claude-3-sonnet", "deepseek-coder"]
    )
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

## Swarm Intelligence

### Distributed Task Processing

```python
import asyncio
from liquid_hive import LiquidHiveClient
from typing import List, Dict, Any, Optional
import json
import time

class SwarmTaskManager:
    def __init__(self, api_key: str, base_url: str = "https://api.liquid-hive.dev"):
        self.client = LiquidHiveClient(base_url=base_url, api_key=api_key)
        self.active_tasks = {}
    
    async def delegate_analysis_task(
        self, 
        documents: List[str],
        analysis_type: str = "comprehensive"
    ) -> List[str]:
        """Delegate document analysis to the swarm."""
        task_ids = []
        
        for i, document in enumerate(documents):
            task_payload = {
                "document": document,
                "analysis_type": analysis_type,
                "document_id": f"doc_{i}",
                "timestamp": time.time()
            }
            
            try:
                # This would use the swarm delegation API
                response = await self.client.delegate_swarm_task(
                    task_type="document_analysis",
                    payload=task_payload,
                    priority=2,
                    timeout_seconds=300,
                    required_capabilities=["nlp", "text_analysis"]
                )
                
                task_ids.append(response['task_id'])
                self.active_tasks[response['task_id']] = {
                    "document_id": f"doc_{i}",
                    "status": "pending",
                    "submitted_at": time.time()
                }
                
            except Exception as e:
                print(f"Failed to delegate task for document {i}: {e}")
        
        return task_ids
    
    async def monitor_tasks(self, task_ids: List[str]) -> Dict[str, Any]:
        """Monitor task progress and collect results."""
        results = {}
        
        while len(results) < len(task_ids):
            for task_id in task_ids:
                if task_id not in results:
                    try:
                        # Check task status
                        status = await self.client.get_swarm_task_status(task_id)
                        
                        if status['status'] == 'completed':
                            results[task_id] = status['result']
                            print(f"Task {task_id} completed")
                        elif status['status'] == 'failed':
                            results[task_id] = {'error': 'Task failed'}
                            print(f"Task {task_id} failed")
                        
                    except Exception as e:
                        print(f"Error checking task {task_id}: {e}")
            
            if len(results) < len(task_ids):
                await asyncio.sleep(5)  # Check every 5 seconds
        
        return results
    
    async def aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from multiple swarm tasks."""
        successful_results = {
            task_id: result for task_id, result in results.items()
            if 'error' not in result
        }
        
        if not successful_results:
            return {"error": "No successful results to aggregate"}
        
        # Aggregate common metrics
        aggregated = {
            "total_documents": len(results),
            "successful_analyses": len(successful_results),
            "failed_analyses": len(results) - len(successful_results),
            "summary": {
                "sentiment_distribution": {},
                "common_topics": [],
                "key_insights": []
            }
        }
        
        # Process individual results
        all_sentiments = []
        all_topics = []
        all_insights = []
        
        for result in successful_results.values():
            if 'sentiment' in result:
                all_sentiments.append(result['sentiment'])
            if 'topics' in result:
                all_topics.extend(result['topics'])
            if 'insights' in result:
                all_insights.extend(result['insights'])
        
        # Calculate sentiment distribution
        if all_sentiments:
            sentiment_counts = {}
            for sentiment in all_sentiments:
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            aggregated["summary"]["sentiment_distribution"] = sentiment_counts
        
        # Find common topics
        if all_topics:
            topic_counts = {}
            for topic in all_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            # Sort by frequency and take top 10
            common_topics = sorted(
                topic_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            aggregated["summary"]["common_topics"] = common_topics
        
        # Collect key insights
        aggregated["summary"]["key_insights"] = all_insights[:20]  # Top 20 insights
        
        return aggregated

# Usage example for distributed document analysis
async def analyze_document_corpus():
    swarm_manager = SwarmTaskManager("your-api-key")
    
    # Sample documents (in practice, these might be loaded from files or databases)
    documents = [
        "This is the first document about artificial intelligence and machine learning...",
        "The second document discusses the impact of technology on society...",
        "Document three covers environmental sustainability and green technology...",
        # Add more documents...
    ]
    
    print(f"Delegating analysis of {len(documents)} documents to the swarm...")
    
    # Delegate tasks
    task_ids = await swarm_manager.delegate_analysis_task(
        documents=documents,
        analysis_type="sentiment_and_topics"
    )
    
    print(f"Submitted {len(task_ids)} tasks. Monitoring progress...")
    
    # Monitor and collect results
    results = await swarm_manager.monitor_tasks(task_ids)
    
    print("All tasks completed. Aggregating results...")
    
    # Aggregate results
    aggregated = await swarm_manager.aggregate_results(results)
    
    print(json.dumps(aggregated, indent=2))
    
    return aggregated

# Real-time swarm monitoring
async def monitor_swarm_health():
    client = LiquidHiveClient(api_key="your-api-key")
    
    while True:
        try:
            status = await client.get_swarm_status()
            
            print(f"Swarm Status:")
            print(f"  Active Nodes: {status['active_nodes']}")
            print(f"  Pending Tasks: {status['pending_tasks']}")
            print(f"  Node Utilization: {status['node_utilization']:.2%}")
            print(f"  Completed Tasks Today: {status.get('completed_tasks_today', 0)}")
            print("-" * 40)
            
            # Alert if utilization is too high
            if status['node_utilization'] > 0.9:
                print("⚠️  WARNING: High node utilization detected!")
            
            # Alert if too many pending tasks
            if status['pending_tasks'] > 100:
                print("⚠️  WARNING: High task queue detected!")
            
        except Exception as e:
            print(f"Error monitoring swarm: {e}")
        
        await asyncio.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    # Run document analysis
    asyncio.run(analyze_document_corpus())
    
    # Or run health monitoring
    # asyncio.run(monitor_swarm_health())
```

## Enterprise Integration

### Microservices Architecture

```python
# service_a.py - Document Processing Service
from fastapi import FastAPI, HTTPException
from liquid_hive import LiquidHiveClient
import asyncio
from typing import List

app = FastAPI(title="Document Processing Service")

client = LiquidHiveClient(
    base_url="https://api.liquid-hive.dev",
    api_key="your-api-key"
)

@app.post("/process-documents")
async def process_documents(documents: List[str]):
    """Process multiple documents using Liquid-Hive swarm."""
    try:
        tasks = []
        for doc in documents:
            task_id = await client.delegate_swarm_task(
                task_type="document_processing",
                payload={"content": doc, "operations": ["summarize", "extract_entities"]},
                priority=1
            )
            tasks.append(task_id)
        
        return {"task_ids": tasks, "status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a processing task."""
    try:
        result = await client.get_swarm_task_status(task_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

```python
# service_b.py - Customer Support Service
from fastapi import FastAPI, HTTPException
from liquid_hive import LiquidHiveClient
import asyncio

app = FastAPI(title="Customer Support Service")

client = LiquidHiveClient(
    base_url="https://api.liquid-hive.dev",
    api_key="your-api-key"
)

@app.post("/support-chat")
async def support_chat(message: str, customer_id: str):
    """Handle customer support chat with AI assistance."""
    try:
        # Enhance the message with customer context
        enhanced_prompt = f"""
        Customer ID: {customer_id}
        Customer Message: {message}
        
        Please provide a helpful and professional response for customer support.
        """
        
        response = await client.chat(enhanced_prompt)
        
        return {
            "response": response['message'],
            "model": response['model_used'],
            "customer_id": customer_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-sentiment")
async def analyze_sentiment(text: str):
    """Analyze sentiment of customer feedback."""
    try:
        response = await client.chat(f"Analyze the sentiment of this text: {text}")
        return {"sentiment_analysis": response['message']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

```python
# gateway.py - API Gateway
from fastapi import FastAPI, HTTPException
import httpx
import asyncio

app = FastAPI(title="Enterprise API Gateway")

# Service endpoints
DOCUMENT_SERVICE = "http://document-service:8000"
SUPPORT_SERVICE = "http://support-service:8000"

@app.post("/api/documents/process")
async def process_documents_endpoint(documents: list):
    """Proxy to document processing service."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DOCUMENT_SERVICE}/process-documents",
            json=documents
        )
        return response.json()

@app.post("/api/support/chat")
async def support_chat_endpoint(message: str, customer_id: str):
    """Proxy to customer support service."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPPORT_SERVICE}/support-chat",
            json={"message": message, "customer_id": customer_id}
        )
        return response.json()

# Health check aggregation
@app.get("/health")
async def health_check():
    """Aggregate health check from all services."""
    services = {
        "document_service": DOCUMENT_SERVICE,
        "support_service": SUPPORT_SERVICE
    }
    
    health_status = {"status": "healthy", "services": {}}
    
    async with httpx.AsyncClient() as client:
        for service_name, service_url in services.items():
            try:
                response = await client.get(f"{service_url}/health", timeout=5.0)
                health_status["services"][service_name] = "healthy"
            except Exception:
                health_status["services"][service_name] = "unhealthy"
                health_status["status"] = "degraded"
    
    return health_status
```

### Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  gateway:
    build: ./gateway
    ports:
      - "8000:8000"
    environment:
      - LIQUID_HIVE_API_KEY=${LIQUID_HIVE_API_KEY}
    depends_on:
      - document-service
      - support-service

  document-service:
    build: ./document-service
    environment:
      - LIQUID_HIVE_API_KEY=${LIQUID_HIVE_API_KEY}
    
  support-service:
    build: ./support-service
    environment:
      - LIQUID_HIVE_API_KEY=${LIQUID_HIVE_API_KEY}
    
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=enterprise_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Best Practices

### Error Handling and Retry Logic

```python
import asyncio
import logging
from typing import Optional, Callable, Any
from functools import wraps

class RetryableError(Exception):
    """Exception that indicates an operation should be retried."""
    pass

def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for async functions with retry logic."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff_factor ** attempt)
                        logging.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logging.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
            
            raise last_exception
        return wrapper
    return decorator

class RobustLiquidHiveClient:
    """Wrapper around LiquidHiveClient with robust error handling."""
    
    def __init__(self, *args, **kwargs):
        from liquid_hive import LiquidHiveClient
        self.client = LiquidHiveClient(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
    
    @retry_async(max_attempts=3, delay=1.0, exceptions=(Exception,))
    async def chat(self, message: str, **kwargs) -> Optional[dict]:
        """Chat with retry logic and error handling."""
        try:
            response = await self.client.chat(message, **kwargs)
            return response
        except Exception as e:
            self.logger.error(f"Chat request failed: {e}")
            if "rate limit" in str(e).lower():
                # Handle rate limiting specifically
                await asyncio.sleep(60)  # Wait 1 minute
                raise RetryableError(f"Rate limited: {e}")
            raise
    
    @retry_async(max_attempts=2, delay=2.0)
    async def health_check(self) -> dict:
        """Health check with retry."""
        return await self.client.health()
    
    async def chat_with_fallback(
        self, 
        message: str, 
        fallback_response: str = "I'm sorry, I'm experiencing technical difficulties."
    ) -> dict:
        """Chat with fallback response on failure."""
        try:
            return await self.chat(message)
        except Exception as e:
            self.logger.error(f"Chat failed with fallback: {e}")
            return {
                "message": fallback_response,
                "model_used": "fallback",
                "error": str(e)
            }

# Usage
async def robust_chat_example():
    client = RobustLiquidHiveClient(api_key="your-api-key")
    
    # This will automatically retry on failure
    response = await client.chat("Hello, how are you?")
    print(response)
    
    # This will provide a fallback response if all retries fail
    response = await client.chat_with_fallback(
        "Complex query that might fail",
        fallback_response="Please try again later."
    )
    print(response)
```

### Rate Limiting and Throttling

```python
import asyncio
import time
from collections import deque
from typing import Optional

class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
    
    async def acquire(self) -> None:
        """Acquire permission to make an API call."""
        now = time.time()
        
        # Remove old calls outside the time window
        while self.calls and self.calls[0] <= now - self.time_window:
            self.calls.popleft()
        
        # Check if we can make a call
        if len(self.calls) >= self.max_calls:
            # Calculate how long to wait
            oldest_call = self.calls[0]
            wait_time = self.time_window - (now - oldest_call)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                return await self.acquire()  # Recursive call after waiting
        
        # Record this call
        self.calls.append(now)

class ThrottledLiquidHiveClient:
    """LiquidHiveClient with built-in rate limiting."""
    
    def __init__(self, api_key: str, base_url: str = None, calls_per_minute: int = 60):
        from liquid_hive import LiquidHiveClient
        self.client = LiquidHiveClient(base_url=base_url, api_key=api_key)
        self.rate_limiter = RateLimiter(calls_per_minute, 60.0)  # 60 seconds
    
    async def chat(self, message: str, **kwargs) -> dict:
        """Rate-limited chat method."""
        await self.rate_limiter.acquire()
        return await self.client.chat(message, **kwargs)
    
    async def health(self) -> dict:
        """Rate-limited health check."""
        await self.rate_limiter.acquire()
        return await self.client.health()

# Usage
async def throttled_example():
    # This client will automatically throttle requests to 30 per minute
    client = ThrottledLiquidHiveClient(
        api_key="your-api-key",
        calls_per_minute=30
    )
    
    # These calls will be automatically throttled
    for i in range(50):
        response = await client.chat(f"Message {i}")
        print(f"Response {i}: {response['message'][:50]}...")
```

This comprehensive documentation covers all major integration scenarios and provides practical, working examples that developers can use as starting points for their own implementations. Each example includes error handling, best practices, and production-ready patterns.