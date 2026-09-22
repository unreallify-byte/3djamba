import os
import bpy
from bpy.props import StringProperty, IntProperty, EnumProperty, BoolProperty
from bpy.types import PropertyGroup


def _update_output_folder(self, context):
    try:
        val = self.output_folder.strip()
        if val:
            norm = os.path.normpath(bpy.path.abspath(val))
            if not norm.endswith(os.sep):
                norm += os.sep
            if context and hasattr(context, "scene") and context.scene:
                context.scene.render.filepath = norm
    except Exception:
        pass


class JAMBAProperties(PropertyGroup):
    """Master property group - attached to bpy.types.Scene.jamba_props"""

    # Scene Prompt
    prompt: StringProperty(
        name="Scene Prompt",
        description=(
            "Describe the scene, action, characters, environment, "
            "and camera framing in natural language"
        ),
        default="",
        maxlen=4096,
    )

    # Reference Images - 10 individual slots
    ref_image_01: StringProperty(name="Reference Image 1",  subtype="FILE_PATH", default="")
    ref_image_02: StringProperty(name="Reference Image 2",  subtype="FILE_PATH", default="")
    ref_image_03: StringProperty(name="Reference Image 3",  subtype="FILE_PATH", default="")
    ref_image_04: StringProperty(name="Reference Image 4",  subtype="FILE_PATH", default="")
    ref_image_05: StringProperty(name="Reference Image 5",  subtype="FILE_PATH", default="")
    ref_image_06: StringProperty(name="Reference Image 6",  subtype="FILE_PATH", default="")
    ref_image_07: StringProperty(name="Reference Image 7",  subtype="FILE_PATH", default="")
    ref_image_08: StringProperty(name="Reference Image 8",  subtype="FILE_PATH", default="")
    ref_image_09: StringProperty(name="Reference Image 9",  subtype="FILE_PATH", default="")
    ref_image_10: StringProperty(name="Reference Image 10", subtype="FILE_PATH", default="")

    # Cinematic Settings
    aspect_ratio: EnumProperty(
        name="Aspect Ratio",
        description="Output aspect ratio - drives resolution_x / resolution_y",
        items=[
            ("16_9",   "16:9 Landscape",    "Standard widescreen (1920 x 1080)"),
            ("9_16",   "9:16 Vertical",     "Portrait / mobile (1080 x 1920)"),
            ("1_1",    "1:1 Square",        "Square format (1080 x 1080)"),
            ("2_39_1", "2.39:1 Anamorphic", "Cinematic anamorphic (2390 x 1000)"),
        ],
        default="16_9",
    )

    duration: IntProperty(
        name="Duration (sec)",
        description="Scene duration in seconds - governs timeline length and keyframe spacing",
        default=15,
        min=1,
        max=60,
    )

    # Output Folder for Playblast Animation
    output_folder: StringProperty(
        name="Output Folder",
        description="Destination directory for rendered playblast video animations",
        subtype="DIR_PATH",
        default="",
        update=_update_output_folder,
    )

    # Runtime / Status
    is_generating:  BoolProperty(name="Generating", default=False)
    status_message: StringProperty(name="Status",   default="Ready")
    gemini_api_key: StringProperty(
        name="Gemini API Key",
        description="Optional: Google Gemini API key for direct connection (bypasses Cloudflare)",
        subtype="PASSWORD",
        default="",
    )
    api_endpoint:   StringProperty(
        name="API Endpoint",
        description="Backend URL that receives the generation payload",
        default="https://jamba-backend.unreallify.workers.dev",
    )


CLASSES = [JAMBAProperties]
