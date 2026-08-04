const express = require('express');
const path = require('path');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const app = express();
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.post('/api/chat', async (req, res) => {
  try {
    const { message, image, thinkingMode } = req.body;
    const cleanMessage = (message || '').trim();

    // 1. FREE IMAGE GENERATION HANDLER
    const isImagePrompt = /^(make|generate|draw|create)\b.*(image|picture|photo|artwork)/i.test(cleanMessage);
    if (isImagePrompt) {
      const encodedPrompt = encodeURIComponent(cleanMessage);
      const imageUrl = `https://image.pollinations.ai/prompt/${encodedPrompt}?width=800&height=600&nologo=true`;
      
      return res.json({
        reply: `Here is your generated image:\n\n![${cleanMessage}](${imageUrl})`
      });
    }

    // 2. TEXT CHAT HANDLER (Gemini API)
    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
    const modelName = thinkingMode === 'flash' ? 'gemini-1.5-flash' : 'gemini-1.5-pro';
    const model = genAI.getGenerativeModel({ model: modelName });

    let contents = [];
    if (image) {
      const base64Data = image.split(',')[1];
      const mimeType = image.split(';')[0].split(':')[1];
      contents.push({ inlineData: { data: base64Data, mimeType } });
    }
    if (cleanMessage) {
      contents.push(cleanMessage);
    }

    const result = await model.generateContent(contents);
    const responseText = result.response.text();

    res.json({ reply: responseText });

  } catch (error) {
    console.error("API Error:", error);
    if (error.status === 429 || error.message?.includes('429')) {
      return res.status(429).json({ 
        error: "Free tier rate limit reached. Please wait 15-20 seconds before asking again!" 
      });
    }
    res.status(500).json({ error: error.message || "Failed to process request." });
  }
});

module.exports = app;
