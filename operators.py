import bpy
import os
import base64

from bpy.types import Operator
from . import scene_builder, network


# ---------------------------------------------------------------------------
# BIKE CHASE DEMO  (new primary demo operator)
# ---------------------------------------------------------------------------
class JAMBA_OT_BikeChaseDemo(Operator):
    """Load the Bike Chase sequence demo scene"""
    bl_idname      = "jamba.bike_chase_demo"
    bl_label       = "Bike Chase Demo"
    bl_description = (
        "Load a full bike-chase blockout scene: street, vehicles, "
        "4 cinematic camera angles. No API required."
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.jamba_props
        props.status_message = "Building Bike Chase Demo..."
        try:
            scene_builder.apply_bike_chase_demo(context)
            self.report({"INFO"}, "Bike Chase Demo loaded! Press Space to play.")
        except Exception as e:
            self.report({"ERROR"}, "Demo failed: {}".format(str(e)))
            props.status_message = "Demo error: {}".format(str(e)[:60])
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Generate Scene
# ---------------------------------------------------------------------------
class JAMBA_OT_Generate(Operator):
    """Send the scene prompt to the AI backend and blockout the 3D scene"""
    bl_idname      = "jamba.generate"
    bl_label       = "Generate Scene"
    bl_description = (
        "Package the prompt, reference images, aspect ratio and duration "
        "into a JSON payload and POST it to the configured AI backend"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.jamba_props

        if props.is_generating:
            self.report({"WARNING"}, "Generation already in progress")
            return {"CANCELLED"}

        if not props.prompt.strip():
            self.report({"WARNING"}, "Please enter a scene prompt first")
            return {"CANCELLED"}

        ref_images = []
        for i in range(1, 11):
            attr = f"ref_image_{i:02d}"
            raw  = getattr(props, attr, "").strip()
            if raw:
                abs_path = bpy.path.abspath(raw)
                if os.path.isfile(abs_path):
                    try:
                        ext = os.path.splitext(abs_path)[1].lower().replace(".", "")
                        mime = f"image/{ext}" if ext in ("png", "jpeg", "webp", "gif") else "image/jpeg"
                        if ext == "jpg":
                            mime = "image/jpeg"
                        with open(abs_path, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("utf-8")
                        ref_images.append({
                            "mime_type": mime,
                            "data": b64,
                            "filename": os.path.basename(abs_path)
                        })
                    except Exception as e:
                        print(f"[3D JAMBA] Warning reading reference image {abs_path}: {e}")

        duration     = props.duration
        total_frames = duration * 24

        payload = {
            "prompt":           props.prompt.strip(),
            "aspect_ratio":     props.aspect_ratio,
            "duration_seconds": duration,
            "fps":              24,
            "total_frames":     total_frames,
            "reference_images": ref_images,
        }

        # Ensure valid live endpoint (auto-switch away from old localhost default)
        endpoint = props.api_endpoint.strip()
        if not endpoint or "localhost" in endpoint or "127.0.0.1" in endpoint:
            endpoint = "https://jamba-backend.unreallify.workers.dev"
            props.api_endpoint = endpoint

        props.is_generating  = True
        props.status_message = "Generating scene via Gemini AI..."

        api_key = props.gemini_api_key.strip()
        network.send_generation_request(payload, endpoint, api_key=api_key)
        self.report({"INFO"}, "Request sent - building scene asynchronously")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Clear Blockout
# ---------------------------------------------------------------------------
class JAMBA_OT_ClearScene(Operator):
    """Remove all 3D JAMBA generated objects and cameras"""
    bl_idname      = "jamba.clear_scene"
    bl_label       = "Clear Blockout"
    bl_description = "Delete all JAMBA proxy meshes and cameras from the scene"
    bl_options     = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Remove all JAMBA cameras
        for obj in list(bpy.data.objects):
            if obj.name.startswith("Jutsu_") or obj.name.startswith("JAMBA_CAM"):
                bpy.data.objects.remove(obj, do_unlink=True)

        # Remove blockout collection
        col = bpy.data.collections.get("JAMBA_Blockout")
        if col:
            for obj in list(col.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(col)

        # Clear timeline markers
        context.scene.timeline_markers.clear()

        # Orphan mesh cleanup
        for block in list(bpy.data.meshes):
            if block.users == 0:
                bpy.data.meshes.remove(block)

        context.scene.jamba_props.status_message = "Scene cleared"
        self.report({"INFO"}, "JAMBA scene cleared")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# API Settings
# ---------------------------------------------------------------------------
class JAMBA_OT_EditEndpoint(Operator):
    """Edit API settings: Gemini API Key & Cloudflare Endpoint"""
    bl_idname      = "jamba.edit_endpoint"
    bl_label       = "Gemini & API Settings"
    bl_description = "Configure your Google Gemini API Key and Cloudflare Worker URL"
    bl_options     = {"REGISTER"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=520)

    def draw(self, context):
        layout = self.layout
        props  = context.scene.jamba_props

        box = layout.box()
        box.label(text="Google Gemini Direct API (Recommended):", icon="WORLD_DATA")
        box.prop(props, "gemini_api_key", text="Gemini API Key")
        box.label(text="Auto-switches: gemini-3.8-flash -> gemini-3.5-flash -> fallbacks", icon="CHECKMARK")

        layout.separator()
        box2 = layout.box()
        box2.label(text="Cloudflare Worker Gateway URL:", icon="LINKED")
        box2.prop(props, "api_endpoint", text="Worker URL")

    def execute(self, context):
        self.report({"INFO"}, "API Settings saved")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Render Playblast Animation
# ---------------------------------------------------------------------------
class JAMBA_OT_RenderPlayblast(Operator):
    """Render the viewport playblast animation to video in the selected output folder"""
    bl_idname      = "jamba.render_playblast"
    bl_label       = "Render Animation (Playblast)"
    bl_description = "Render viewport playblast animation as video to the selected output folder"
    bl_options     = {"REGISTER"}

    def execute(self, context):
        scene = context.scene
        props = scene.jamba_props

        raw_folder = props.output_folder.strip()
        if not raw_folder and scene.render.filepath:
            raw_folder = scene.render.filepath.strip()

        if not raw_folder:
            self.report({"WARNING"}, "Please select a valid Output Folder first")
            props.status_message = "Select an Output Folder before rendering"
            return {"CANCELLED"}

        folder = os.path.normpath(bpy.path.abspath(raw_folder))
        # If user pointed to a file instead of a directory, keep its directory
        if os.path.isfile(folder):
            folder = os.path.dirname(folder)
        if not folder.endswith(os.sep):
            folder += os.sep

        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            self.report({"ERROR"}, f"Invalid output directory: {e}")
            props.status_message = f"Folder error: {str(e)[:40]}"
            return {"CANCELLED"}

        # Set Blender's render filepath directly to the chosen folder (no extra subfolder or prefix)
        scene.render.filepath = folder
        props.output_folder = folder

        # Apply all requested settings: Eevee, 24fps, 1920x1080, FFMPEG video, Solid Flat, Overlays off
        scene_builder.configure_blender_render_and_viewport(scene)

        self.report({"INFO"}, f"Rendering Playblast animation to: {folder}")
        props.status_message = f"Rendering Playblast -> {folder}"

        # Trigger Render Playblast (Viewport Render Animation)
        try:
            bpy.ops.render.opengl('INVOKE_DEFAULT', animation=True, view_context=True)
        except Exception:
            try:
                bpy.ops.render.opengl(animation=True)
            except Exception as ex:
                self.report({"ERROR"}, f"Playblast failed: {ex}")
                props.status_message = f"Playblast error: {str(ex)[:40]}"
                return {"CANCELLED"}

        return {"FINISHED"}


CLASSES = [
    JAMBA_OT_BikeChaseDemo,
    JAMBA_OT_Generate,
    JAMBA_OT_ClearScene,
    JAMBA_OT_EditEndpoint,
    JAMBA_OT_RenderPlayblast,
]
