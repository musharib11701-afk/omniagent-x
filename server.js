const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Uses Environment Variable (Set locally in .env or on host dashboard)
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || "";

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

app.post('/api/chat', async (req, res) => {
  try {
    const { message, image, toolMode, thinkingMode } = req.body;

    if (!message && !image) {
      return res.status(400).json({ error: "Message or image is required" });
    }

    // --- TOOL GENERATOR: IMAGE CREATION ---
    if (toolMode === 'image' || (message && (message.toLowerCase().includes('create image') || message.toLowerCase().includes('generate image')))) {
      const cleanPrompt = message ? message.replace(/create image|generate image/gi, '').trim() : 'cosmic space galaxy nebula';
      const encodedPrompt = encodeURIComponent(cleanPrompt || 'cosmic galaxy');
      const imageUrl = `https://image.pollinations.ai/prompt/${encodedPrompt}?width=1024&height=1024&nologo=true`;

      return res.json({
        thinking: `[Tool Executed: Image Generator]\n- Synthesizing artwork for: "${cleanPrompt}"`,
        reply: `Here is your generated image for **"${cleanPrompt || 'cosmic galaxy'}"**:\n\n![AI Generated Image](${imageUrl})`
      });
    }

    // --- GEMINI MULTIMODAL PAYLOAD ---
    const parts = [];

    if (image) {
      const base64Data = image.split(',')[1] || image;
      const mimeType = image.split(';')[0].split(':')[1] || 'image/png';
      parts.push({
        inline_data: {
          mime_type: mimeType,
          data: base64Data
        }
      });
    }

    if (message) {
      parts.push({ text: message });
    }

    // Safe models available on Google's Free Tier
    const candidateModels = [
      'gemini-1.5-flash',
      'gemini-2.0-flash',
      'gemini-1.5-flash-8b'
    ];

    let replyText = null;
    let modelUsed = '';
    let isRateLimited = false;

    for (const model of candidateModels) {
      try {
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-goog-api-key': GEMINI_API_KEY
          },
          body: JSON.stringify({ contents: [{ parts }] })
        });

        const data = await response.json();

        if (data.candidates?.[0]?.content?.parts?.[0]?.text) {
          replyText = data.candidates[0].content.parts[0].text;
          modelUsed = model;
          break;
        } else if (data.error) {
          console.error(`Gemini (${model}) API Error:`, data.error.message);
          if (data.error.code === 429 || data.error.status === 'RESOURCE_EXHAUSTED' || data.error.message.includes('limit: 0')) {
            isRateLimited = true;
          }
        }
      } catch (e) {
        console.error(`Attempt failed for ${model}:`, e.message);
      }
    }

    if (replyText) {
      const thinkingLog = thinkingMode === 'thinking'
        ? `[Deep Thinking Core: ${modelUsed}]\n1. Multimodal payload parsed.\n2. Neural inference complete.`
        : `[Fast Mode: ${modelUsed}] Direct neural response generated.`;
      return res.json({ thinking: thinkingLog, reply: replyText });
    }

    // Clean user-friendly message on rate limit / free tier cooldown
    if (isRateLimited) {
      return res.json({
        thinking: `[OmniAgent Rate-Limit Shield]\n⏳ Google Free Tier Cooldown Active.`,
        reply: `⏳ **Google AI Free Tier Cooldown**\n\nGoogle limits rapid consecutive requests on free API keys. Please wait **15-20 seconds** and send your message again!`
      });
    }

    return res.json({
      thinking: `[OmniAgent Neural Core]\n⚠️ API Connection Error`,
      reply: `⚠️ Couldn't reach Gemini right now. Please check API Key configurations!`
    });

  } catch (err) {
    console.error("Server Error:", err);
    res.status(500).json({ reply: `⚠️ Internal Server Error: ${err.message}` });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 OmniAgent active & listening at http://localhost:${PORT}`);
});