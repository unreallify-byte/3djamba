# 3D JAMBA | network.py
# Universal AI Scene Generation with Multi-Model Switching (gemini-3.8-flash -> fallback models)
# Never mocks or fakes scenes; fully asynchronous on background thread.

import bpy
import json
import threading
import urllib.request
import urllib.error
import time

from . import scene_builder

# Shared result bucket (written by worker thread, read by timer)
_result = {"data": None, "error": None, "done": False, "model": ""}
_lock   = threading.Lock()

# Verified Gemini API Key default
_DEFAULT_GEMINI_KEY = "AQ.Ab8RN6Ih5UNPNlWXrCdnMGeK1N9m2ereMQCpbO014wFZzTQCvA"

# Universal System Prompt: instructs Gemini to decompose ANY subject into 3D primitives
UNIVERSAL_SYSTEM_PROMPT = """You are an expert 3D Concept Sculptor, Architectural Level Designer, and Cinematic Director for Blender blockouts.
Decompose the entire scene into an expressive, cohesive 3D spatial blockout using basic primitives (cube, sphere, cylinder, cone, plane, torus).

CRITICAL GENERAL RULES:
1. UNIVERSAL COMPOUND PRIMITIVE DECOMPOSITION:
   Allowed primitives: 'cube', 'sphere', 'cylinder', 'cone', 'plane', 'torus'.
   NEVER represent a complex subject (character, creature, beast, monster, dragon, vehicle, robot, or building) with a single generic shape!
   You MUST deconstruct every entity into its component anatomical and structural primitives:
   - Dragons / Beasts / Monsters / Aliens:
     Break down into Head ('sphere'/'cone'), Horns ('cone'), Jaws, Neck segments (3-5 'cylinder'/'sphere' pieces), Torso/Chest ('cube'/'sphere'), Wings (thin flat angled 'cube'/'plane' segments), Legs, Claws, and Tail segments (tapering 'cylinder'/'sphere' pieces).
   - Humanoids / Ninjas / Warriors / Characters:
     Break down into Head ('sphere'), Torso ('cube'), Pelvis ('cube'), Upper Arms ('cylinder'), Forearms ('cylinder'), Hands ('sphere'/'cube'), Thighs ('cylinder'), Calves ('cylinder'), Feet ('cube'), and held items/weapons.
   - Robots / Mechs / Machines:
     Break down into Chassis/Hull, Cockpit, Joint Spheres, Limb Cylinders, Armor Plating, Foot Pads, and weapon mounts.
   - Vehicles / Cars / Spaceships:
     Break down into Main Body Hull, Cockpit/Canopy, Wheels/Treads/Thrusters, Spoilers, Wings.
   - Architecture & Cityscapes:
     Ground plane, Walls, Floors, Pillars/Columns, Arches, Roofs, Doors, Windows, Stairs, Streetlights.
   - Nature & Landscapes:
     Ground terrain plane, Tree trunks ('cylinder') with foliage canopy ('sphere'/'cone'), rocks ('sphere'/'cube'), grass patches.

2. WORLD COORDINATES & SCALES:
   - Provide realistic world coordinates (location [x, y, z]).
   - Provide realistic dimensions (scale [sx, sy, sz]).
   - Provide rotation in radians [rx, ry, rz].

3. CAMERA CHOREOGRAPHY:
   - Generate 3 to 5 camera keyframes along the timeline (time_pct from 0.0 to 1.0).
   - CRITICAL: Camera location Z must ALWAYS be >= 0.35m (strictly above ground, NEVER subterranean).

OUTPUT JSON SCHEMA:
{
  "camera_keyframes": [
    { "time_pct": 0.0, "location": [0.0, -8.0, 2.0], "rotation": [1.4, 0.0, 0.0] },
    { "time_pct": 0.5, "location": [6.0, -5.0, 2.5], "rotation": [1.3, 0.0, 0.6] },
    { "time_pct": 1.0, "location": [0.0, -8.0, 2.0], "rotation": [1.4, 0.0, 0.0] }
  ],
  "objects": [
    {
      "name": "Ground_Plane",
      "primitive": "plane",
      "type": "ground",
      "location": [0.0, 0.0, 0.0],
      "scale": [25.0, 25.0, 1.0],
      "rotation": [0.0, 0.0, 0.0]
    }
  ]
}
Allowed primitive values: 'cube', 'sphere', 'cylinder', 'cone', 'plane', 'torus'.
Return ONLY valid JSON matching this schema."""


# ---------------------------------------------------------------------------
# Direct Gemini Multi-Model Generator
# ---------------------------------------------------------------------------
def _generate_with_gemini_direct(payload: dict, api_key: str):
    """
    Directly query Google Gemini API with automatic model failover.
    Priority:
      1. gemini-3.8-flash (primary, 7s timeout - catches 503 capacity instantly)
      2. gemini-3.5-flash-lite (fast 15s fallback)
      3. gemini-3.5-flash (deep 35s fallback)
      4. gemini-3.6-flash (25s fallback)
      5. gemini-3.1-flash-lite (15s fallback)
    """
    user_prompt = payload.get("prompt", "A 3D cinematic scene")
    duration    = payload.get("duration_seconds", 15)
    aspect_ratio= payload.get("aspect_ratio", "16_9")
    ref_images  = payload.get("reference_images", [])

    content_parts = [
        {"text": f"{UNIVERSAL_SYSTEM_PROMPT}\n\nUser Scene Description: \"{user_prompt}\".\nDuration: {duration} seconds.\nAspect Ratio: {aspect_ratio}."}
    ]

    # Multimodal image attachments
    for img_path in ref_images:
        try:
            import os, base64
            if img_path and os.path.isfile(img_path):
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                mime = "image/png" if img_path.lower().endswith(".png") else "image/jpeg"
                content_parts.append({
                    "inline_data": {
                        "mime_type": mime,
                        "data": b64
                    }
                })
        except Exception as e:
            print(f"[3D JAMBA] Warning reading ref image {img_path}: {e}")

    gemini_payload = {
        "contents": [{"parts": content_parts}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    body_bytes = json.dumps(gemini_payload).encode("utf-8")

    model_cascade = [
        ("gemini-3.8-flash", 7),
        ("gemini-3.5-flash-lite", 15),
        ("gemini-3.5-flash", 35),
        ("gemini-3.6-flash", 25),
        ("gemini-3.1-flash-lite", 15),
    ]

    last_err = ""
    for model_name, timeout_sec in model_cascade:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "Blender-JAMBA/5.0"}
        )
        print(f"[3D JAMBA] Querying Gemini model '{model_name}' (timeout: {timeout_sec}s)...")
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw_bytes = resp.read()
                resp_json = json.loads(raw_bytes.decode("utf-8"))
                candidates = resp_json.get("candidates", [])
                if not candidates:
                    last_err = f"{model_name}: No candidates returned"
                    continue
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    last_err = f"{model_name}: Empty content parts"
                    continue
                text_content = parts[0].get("text", "")
                parsed_scene = json.loads(text_content)
                print(f"[3D JAMBA] SUCCESS with model '{model_name}'!")
                return parsed_scene, model_name
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace")
            print(f"[3D JAMBA] Model '{model_name}' HTTP Error {he.code}: {err_body[:120]}")
            last_err = f"{model_name} (HTTP {he.code})"
            # Immediately switch to next model on 503 (No capacity) or 429 (Rate limit)
            continue
        except Exception as e:
            print(f"[3D JAMBA] Model '{model_name}' failed: {e}")
            last_err = f"{model_name} ({e})"
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


# ---------------------------------------------------------------------------
# Background worker thread
# ---------------------------------------------------------------------------
def _post_payload(payload: dict, endpoint: str, api_key: str = "") -> None:
    # 1. If API key is provided, query Google Gemini directly with multi-model switching
    key_to_use = api_key.strip() if api_key and api_key.strip() else _DEFAULT_GEMINI_KEY

    try:
        data, model_used = _generate_with_gemini_direct(payload, key_to_use)
        with _lock:
            _result.update({"data": data, "error": None, "done": True, "model": model_used})
        return
    except Exception as gemini_direct_err:
        print(f"[3D JAMBA] Direct Gemini cascade exception: {gemini_direct_err}")
        # If direct failed and endpoint is specified and not dummy, try endpoint
        if endpoint and "http" in endpoint and "localhost" not in endpoint:
            try:
                print(f"[3D JAMBA] Trying Cloudflare endpoint fallback: {endpoint}")
                body = json.dumps(payload).encode("utf-8")
                request = urllib.request.Request(
                    endpoint,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept":       "application/json",
                        "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Blender/5.0",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=45) as resp:
                    raw  = resp.read().decode("utf-8")
                    data = json.loads(raw)
                    model_used = resp.headers.get("X-Model-Used", "Cloudflare")
                with _lock:
                    _result.update({"data": data, "error": None, "done": True, "model": model_used})
                return
            except Exception as ep_err:
                print(f"[3D JAMBA] Endpoint fallback failed: {ep_err}")

        # If everything failed, report the real error honestly
        with _lock:
            _result.update({
                "data": None,
                "error": str(gemini_direct_err),
                "done": True,
                "model": ""
            })


# ---------------------------------------------------------------------------
# Blender timer callback (runs on main thread, safe to call bpy)
# ---------------------------------------------------------------------------
def _poll_result():
    with _lock:
        done  = _result["done"]
        data  = _result["data"]
        error = _result["error"]
        model = _result.get("model", "")

    if not done:
        return 0.5  # not ready yet - keep polling

    # Finished
    scene = bpy.context.scene
    props = scene.jamba_props
    props.is_generating = False

    if error:
        # Report honest error to user - NEVER spawn a fake mock scene!
        props.status_message = f"Error: {str(error)[:80]}"
        print(f"[3D JAMBA ERROR] {error}")
    else:
        _apply_api_response(bpy.context, data, model)

    # Redraw 3D Viewports
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

    return None


def _apply_api_response(context, data: dict, model_used: str = "") -> None:
    """Parse API JSON and construct the Blender scene with zero hardcoding."""
    props        = context.scene.jamba_props
    total_frames = scene_builder.configure_scene(
        context, props.aspect_ratio, props.duration
    )
    camera_kfs   = data.get("camera_keyframes", [])
    scene_builder.create_jutsu_camera(context, camera_kfs, total_frames)

    objects_list = data.get("objects", [])
    if objects_list:
        scene_builder.build_blockout_geometry(context, objects_list)

    scene_builder.configure_blender_render_and_viewport(context.scene)
    if model_used:
        props.status_message = f"Scene generated via {model_used} ({len(objects_list)} objects)"
    else:
        props.status_message = f"Scene generated ({len(objects_list)} objects)"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def send_generation_request(payload: dict, endpoint: str = "", api_key: str = "") -> None:
    global _result
    with _lock:
        _result = {"data": None, "error": None, "done": False, "model": ""}

    t = threading.Thread(
        target=_post_payload,
        args=(payload, endpoint, api_key),
        daemon=True,
        name="JAMBA_NetworkThread",
    )
    t.start()

    if not bpy.app.timers.is_registered(_poll_result):
        bpy.app.timers.register(_poll_result, first_interval=0.5)
