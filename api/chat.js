const { GoogleGenerativeAI } = require('@google/generative-ai');

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { message, image, thinkingMode } = req.body || {};
    const cleanMessage = (message || '').trim();

    // 1. Image Generation Prompt Check
    const isImagePrompt = /^(make|generate|draw|create)\b.*(image|picture|photo|artwork)/i.test(cleanMessage);
    if (isImagePrompt) {
      const encodedPrompt = encodeURIComponent(cleanMessage);
      const imageUrl = `https://image.pollinations.ai/prompt/${encodedPrompt}?width=800&height=600&nologo=true`;
      
      return res.status(200).json({
        reply: `Here is your generated image:\n\n![${cleanMessage}](${imageUrl})`
      });
    }

    // 2. Gemini Text Chat Processing
    if (!process.env.GEMINI_API_KEY) {
      return res.status(500).json({ error: 'GEMINI_API_KEY environment variable missing in Vercel.' });
    }

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

    return res.status(200).json({ reply: responseText });

  } catch (error) {
    console.error("API Error:", error);
    if (error.status === 429 || error.message?.includes('429')) {
      return res.status(429).json({ 
        error: "Free tier rate limit reached. Please wait 15-20 seconds before asking again!" 
      });
    }
    return res.status(500).json({ error: error.message || "Failed to process request." });
  }
};
