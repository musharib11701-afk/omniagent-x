import os
import urllib.parse
import sqlite3
from typing import List, Optional, Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uses Environment Variable (Set locally in .env or system environment)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

DB_FILE = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_msg(user_id: str, role: str, content: str):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)', (user_id, role, content))
    conn.commit()
    conn.close()

def load_history(user_id: str):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    cursor = conn.cursor()
    cursor.execute('SELECT role, content FROM history WHERE user_id = ? ORDER BY id ASC', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

class ChatRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = "default_user"
    history: Optional[List[Any]] = []

@app.get("/api/history/{user_id}")
async def get_history(user_id: str):
    return {"history": load_history(user_id)}

@app.post("/api/history/clear/{user_id}")
async def clear_user_history(user_id: str):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM history WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return {"status": "cleared"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        user_prompt = request.prompt.strip()
        user_id = request.user_id or "default_user"

        # 1. Check for Image Generation Intent
        if any(kw in user_prompt.lower() for kw in ["image", "picture", "draw", "photo", "generate pic"]):
            encoded_prompt = urllib.parse.quote(user_prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
            ai_resp = f"Here is your generated image for **'{user_prompt}'**:\n\n![Generated Image]({image_url})"
            save_msg(user_id, "user", user_prompt)
            save_msg(user_id, "assistant", ai_resp)
            return {"response": ai_resp}

        # 2. Build system instructions & load past memory
        messages = [
            {
                "role": "system",
                "content": (
                    "You are OmniAgent-X, a master AI assistant and WebGL 3D Game Engine Architect. "
                    "Remember past context provided by the user. "
                    "When asked for a game, output full standard single-file complete HTML inside ```html ``` blocks."
                )
            }
        ]

        # Load previous conversation history from SQLite
        past_history = load_history(user_id)
        for msg in past_history[-10:]:  # Include last 10 messages for memory context
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Append current user prompt
        messages.append({"role": "user", "content": user_prompt})

        # Save current user prompt to DB
        save_msg(user_id, "user", user_prompt)

        # 3. Handle Game Engine Direct Generation
        if any(word in user_prompt.lower() for word in ["game", "fps", "zombie", "3d", "shooter", "code"]):
            game_html = """```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>OmniAgent-X 3D Zombie Survival Engine</title>
    <style>
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: #000; font-family: sans-serif; }
        #canvas-container { width: 100%; height: 100%; position: absolute; }
        #ui-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; display: flex; justify-content: space-between; padding: 20px; box-sizing: border-box; z-index: 5; }
        #crosshair { position: absolute; top: 50%; left: 50%; width: 10px; height: 10px; transform: translate(-50%, -50%); border: 2px solid #fff; border-radius: 50%; background: rgba(255,0,0,0.6); }
        .hud { background: rgba(0,0,0,0.8); border: 1px solid #38bdf8; padding: 10px 18px; border-radius: 8px; color: #38bdf8; font-family: monospace; font-size: 1.2rem; }
        #blocker { position: absolute; width: 100%; height: 100%; background: rgba(0,0,0,0.85); display: flex; flex-direction: column; justify-content: center; align-items: center; color: white; cursor: pointer; z-index: 20; text-align: center; }
    </style>
    <script src="[https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js](https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js)"></script>
    <script src="[https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/PointerLockControls.js](https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/PointerLockControls.js)"></script>
</head>
<body>
    <div id="blocker">
        <h1 style="font-size:3rem; color:#ef4444;">ZOMBIE SURVIVAL 3D</h1>
        <p style="font-size:1.5rem; color:#22c55e; font-weight:bold;">CLICK ANYWHERE TO START</p>
        <p>WASD = Move | MOUSE = Look | LEFT CLICK = Shoot</p>
    </div>
    <div id="canvas-container"></div>
    <div id="ui-overlay">
        <div class="hud">HEALTH: <span id="hp">100</span>%</div>
        <div class="hud">SCORE: <span id="score">0</span></div>
        <div id="crosshair"></div>
    </div>
    <script>
        let scene, camera, renderer, controls;
        let moveForward = false, moveBackward = false, moveLeft = false, moveRight = false;
        let prevTime = performance.now();
        const velocity = new THREE.Vector3();
        let zombies = [], score = 0, health = 100, gunGroup;

        function init() {
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x050508);
            scene.fog = new THREE.FogExp2(0x050508, 0.04);
            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.y = 1.7;

            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            document.getElementById('canvas-container').appendChild(renderer.domElement);

            scene.add(new THREE.AmbientLight(0x222233, 0.8));
            const flashlight = new THREE.SpotLight(0xffffff, 2, 40, Math.PI / 6);
            camera.add(flashlight);
            flashlight.target.position.set(0, 0, -1);
            camera.add(flashlight.target);

            const floor = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), new THREE.MeshStandardMaterial({ color: 0x1e293b }));
            floor.rotation.x = -Math.PI / 2;
            scene.add(floor);
            scene.add(new THREE.GridHelper(80, 40, 0x38bdf8, 0x0f172a));

            controls = new THREE.PointerLockControls(camera, document.body);
            const blocker = document.getElementById('blocker');
            blocker.addEventListener('click', () => controls.lock());
            controls.addEventListener('lock', () => blocker.style.display = 'none');
            controls.addEventListener('unlock', () => blocker.style.display = 'flex');
            scene.add(controls.getObject());

            document.addEventListener('keydown', (e) => {
                if (e.code==='KeyW') moveForward=true; if (e.code==='KeyS') moveBackward=true;
                if (e.code==='KeyA') moveLeft=true; if (e.code==='KeyD') moveRight=true;
            });
            document.addEventListener('keyup', (e) => {
                if (e.code==='KeyW') moveForward=false; if (e.code==='KeyS') moveBackward=false;
                if (e.code==='KeyA') moveLeft=false; if (e.code==='KeyD') moveRight=false;
            });
            document.addEventListener('mousedown', () => { if (controls.isLocked) shoot(); });

            gunGroup = new THREE.Group();
            const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.6), new THREE.MeshStandardMaterial({ color: 0x334155 }));
            barrel.rotation.x = Math.PI / 2;
            barrel.position.set(0.2, -0.2, -0.4);
            gunGroup.add(barrel);
            camera.add(gunGroup);

            for (let i = 0; i < 5; i++) spawnZombie();
            animate();
        }

        function spawnZombie() {
            const z = new THREE.Group();
            const torso = new THREE.Mesh(new THREE.BoxGeometry(0.6, 1.2, 0.4), new THREE.MeshStandardMaterial({ color: 0x16a34a }));
            torso.position.y = 0.9;
            z.add(torso);
            const a = Math.random() * Math.PI * 2, d = 15 + Math.random() * 15;
            z.position.set(Math.cos(a)*d, 0, Math.sin(a)*d);
            z.userData = { hp: 2 };
            scene.add(z);
            zombies.push(z);
        }

        function shoot() {
            const raycaster = new THREE.Raycaster();
            raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);
            const hits = raycaster.intersectObjects(zombies, true);
            if (hits.length > 0) {
                let hit = hits[0].object;
                while (hit.parent && !zombies.includes(hit)) hit = hit.parent;
                if (zombies.includes(hit)) {
                    hit.userData.hp -= 1;
                    if (hit.userData.hp <= 0) {
                        scene.remove(hit);
                        zombies = zombies.filter(z => z !== hit);
                        score += 100;
                        document.getElementById('score').textContent = score;
                        spawnZombie();
                    }
                }
            }
        }

        function animate() {
            requestAnimationFrame(animate);
            const time = performance.now();
            if (controls.isLocked) {
                const delta = (time - prevTime) / 1000;
                velocity.x -= velocity.x * 10.0 * delta;
                velocity.z -= velocity.z * 10.0 * delta;
                if (moveForward) velocity.z -= 40.0 * delta;
                if (moveBackward) velocity.z += 40.0 * delta;
                if (moveLeft) velocity.x -= 40.0 * delta;
                if (moveRight) velocity.x += 40.0 * delta;
                controls.moveRight(-velocity.x * delta);
                controls.moveForward(-velocity.z * delta);

                zombies.forEach(z => {
                    const dir = new THREE.Vector3().subVectors(camera.position, z.position);
                    dir.y = 0; dir.normalize();
                    z.position.addScaledVector(dir, 1.5 * delta);
                    z.lookAt(camera.position.x, z.position.y, camera.position.z);
                });
            }
            prevTime = time;
            renderer.render(scene, camera);
        }
        window.onload = init;
    </script>
</body>
</html>
```"""
            ai_resp = f"I have generated the 3D Zombie Survival Engine for you:\n\n{game_html}"
            save_msg(user_id, "assistant", ai_resp)
            return {"response": ai_resp}

        # 4. Standard LLM Conversation via Groq
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4,
            max_tokens=2048,
        )

        ai_resp = completion.choices[0].message.content
        save_msg(user_id, "assistant", ai_resp)

        return {"response": ai_resp}

    except Exception as e:
        print(f"Backend Exception: {e}")
        return {"response": f"⚠️ **Backend Error:** {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)