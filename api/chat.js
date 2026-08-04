module.exports = async function handler(req, res) {
  // Always return JSON, even on preflight/wrong methods
  if (req.method !== 'POST') {
    return res.status(200).json({ reply: 'API route is working! Please send a POST request.' });
  }

  try {
    const { message } = req.body || {};
    const cleanMessage = (message || '').trim();

    if (!cleanMessage) {
      return res.status(200).json({ reply: 'Please enter a prompt!' });
    }

    // 1. IMAGE GENERATION ROUTE ( Pollinations.ai )
    const isImagePrompt = /^(make|generate|draw|create)\b.*(image|picture|photo|artwork)/i.test(cleanMessage);
    if (isImagePrompt) {
      const encodedPrompt = encodeURIComponent(cleanMessage);
      const imageUrl = `https://image.pollinations.ai/prompt/${encodedPrompt}?width=800&height=600&nologo=true`;
      
      return res.status(200).json({
        reply: `Here is your generated image:<br><br><img src="${imageUrl}" style="max-width:100%; border-radius:12px; margin-top:10px;" />`
      });
    }

    // 2. TEXT CHAT ROUTE (Google Gemini API)
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return res.status(200).json({ reply: 'Error: GEMINI_API_KEY is not set in Vercel Environment Variables.' });
    }

    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: cleanMessage }] }]
      })
    });

    const data = await response.json();

    if (data.error) {
      return res.status(200).json({ reply: `Gemini API Error: ${data.error.message}` });
    }

    const replyText = data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response generated.';
    return res.status(200).json({ reply: replyText });

  } catch (err) {
    return res.status(200).json({ reply: `Server Error: ${err.message}` });
  }
};
