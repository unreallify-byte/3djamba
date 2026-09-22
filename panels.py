# 3D JAMBA | panels.py
# Sidebar UI -- View3D > UI > 3D JAMBA

import bpy
from bpy.types import Panel
from .scene_builder import RESOLUTION_MAP


def _status_icon(msg):
    if not msg or msg == "Ready":
        return "BLANK1"
    m = msg.lower()
    if "error" in m or "fail" in m:
        return "ERROR"
    if "ready" in m or "loaded" in m or "cleared" in m or "success" in m or "built" in m:
        return "CHECKMARK"
    if "sending" in m or "building" in m or "generating" in m or "processing" in m:
        return "SORTTIME"
    return "INFO"


# ---------------------------------------------------------------------------
# Root panel  -- tab "3D JAMBA", demo hero button + status
# ---------------------------------------------------------------------------
class JAMBA_PT_Root(Panel):
    bl_label       = "3D JAMBA"
    bl_idname      = "JAMBA_PT_Root"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "3D JAMBA"         # <-- Tab label on N-panel
    bl_order       = 0

    def draw_header(self, context):
        self.layout.label(text="", icon="CAMERA_DATA")

    def draw(self, context):
        layout = self.layout
        props  = context.scene.jamba_props

        # ---- Bike Chase Demo hero button ---------------------------------
        demo_box = layout.box()
        demo_col = demo_box.column(align=True)
        demo_col.label(text="Quick Demo Scene:", icon="AUTO")
        demo_row         = demo_col.row(align=True)
        demo_row.scale_y = 2.0
        demo_row.operator(
            "jamba.bike_chase_demo",
            text="  Bike Chase Demo",
            icon="AUTO",
        )

        layout.separator(factor=0.4)

        # ---- Status banner -----------------------------------------------
        status_box = layout.box()
        status_row = status_box.row(align=True)
        status_row.label(
            text=props.status_message,
            icon=_status_icon(props.status_message),
        )
        if props.is_generating:
            status_box.row().label(
                text="Processing -- please wait ...", icon="SORTTIME")


# ---------------------------------------------------------------------------
# Scene Prompt sub-panel
# ---------------------------------------------------------------------------
class JAMBA_PT_Prompt(Panel):
    bl_label       = "Scene Prompt"
    bl_idname      = "JAMBA_PT_Prompt"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "3D JAMBA"         # <-- MUST match Root
    bl_parent_id   = "JAMBA_PT_Root"
    bl_order       = 1

    def draw(self, context):
        layout = self.layout
        props  = context.scene.jamba_props
        col = layout.column(align=True)
        col.label(text="Describe your scene:", icon="TEXT")
        col.prop(props, "prompt", text="", expand=True)
        col.separator(factor=0.3)
        char_count = len(props.prompt)
        col.label(
            text="{} / 4096 chars".format(char_count),
            icon="BLANK1" if char_count < 3800 else "ERROR",
        )


# ---------------------------------------------------------------------------
# Reference Images sub-panel
# ---------------------------------------------------------------------------
class JAMBA_PT_References(Panel):
    bl_label       = "Reference Images"
    bl_idname      = "JAMBA_PT_References"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "3D JAMBA"         # <-- MUST match Root
    bl_parent_id   = "JAMBA_PT_Root"
    bl_order       = 2
    bl_options     = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        props  = context.scene.jamba_props
        col    = layout.column(align=True)
        loaded = 0
        for i in range(1, 11):
            attr = "ref_image_{:02d}".format(i)
            val  = getattr(props, attr, "").strip()
            col.prop(props, attr, text="Ref {:02d}".format(i))
            if val:
                loaded += 1
        col.separator(factor=0.5)
        col.label(
            text="{} / 10 reference images provided".format(loaded),
            icon="IMAGE_DATA" if loaded > 0 else "BLANK1",
        )


# ---------------------------------------------------------------------------
# Cinematic Settings sub-panel
# ---------------------------------------------------------------------------
class JAMBA_PT_Settings(Panel):
    bl_label       = "Cinematic Settings"
    bl_idname      = "JAMBA_PT_Settings"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "3D JAMBA"         # <-- MUST match Root
    bl_parent_id   = "JAMBA_PT_Root"
    bl_order       = 3

    def draw(self, context):
        layout = self.layout
        props  = context.scene.jamba_props
        col = layout.column(align=True)
        col.label(text="Aspect Ratio:", icon="RESTRICT_VIEW_OFF")
        col.prop(props, "aspect_ratio", text="")
        col.separator(factor=0.6)
        col.label(text="Duration:", icon="TIME")
        col.prop(props, "duration", text="Seconds", slider=True)
        col.separator(factor=0.6)

        res_x, res_y = RESOLUTION_MAP.get(props.aspect_ratio, (1920, 1080))
        total_frames = props.duration * 24

        box  = col.box()
        bcol = box.column(align=True)
        bcol.scale_y = 0.85
        bcol.label(
            text="FPS: 24   |   Frames: {}".format(total_frames),
            icon="RENDER_ANIMATION",
        )
        bcol.label(
            text="Resolution: {} x {} px".format(res_x, res_y),
            icon="RENDERLAYERS",
        )
        bcol.label(text="4 cinematic shots (15 sec sequence)", icon="CAMERA_DATA")


# ---------------------------------------------------------------------------
# Generate sub-panel
# ---------------------------------------------------------------------------
class JAMBA_PT_Generate(Panel):
    bl_label       = "Generate (AI)"
    bl_idname      = "JAMBA_PT_Generate"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "3D JAMBA"         # <-- MUST match Root
    bl_parent_id   = "JAMBA_PT_Root"
    bl_order       = 4

    def draw(self, context):
        layout = self.layout
        props  = context.scene.jamba_props
        col = layout.column(align=True)

        # AI generate button
        gen_row         = col.row(align=True)
        gen_row.scale_y = 2.0
        if props.is_generating:
            gen_row.enabled = False
            gen_row.operator("jamba.generate", text="Generating ...", icon="SORTTIME")
        else:
            gen_row.operator(
                "jamba.generate", text="  Generate Scene (AI)", icon="PLAY")

        col.separator(factor=0.6)

        util = col.row(align=True)
        util.operator("jamba.clear_scene",   text="Clear Scene",  icon="TRASH")
        util.operator("jamba.edit_endpoint", text="API Settings", icon="PREFERENCES")

        col.separator(factor=0.3)
        prompt_ok = bool(props.prompt.strip())
        col.label(
            text="Prompt ready" if prompt_ok else "Enter a prompt above to use AI",
            icon="CHECKMARK" if prompt_ok else "INFO",
        )


# ---------------------------------------------------------------------------
# Output & Playblast Render sub-panel
# ---------------------------------------------------------------------------
class JAMBA_PT_Render(Panel):
    bl_label       = "Render Playblast"
    bl_idname      = "JAMBA_PT_Render"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "3D JAMBA"
    bl_parent_id   = "JAMBA_PT_Root"
    bl_order       = 5

    def draw(self, context):
        layout = self.layout
        props  = context.scene.jamba_props
        col = layout.column(align=True)

        col.label(text="Select Output Folder:", icon="FILE_FOLDER")
        col.prop(props, "output_folder", text="")

        col.separator(factor=0.6)

        btn_row         = col.row(align=True)
        btn_row.scale_y = 2.0
        btn_row.operator(
            "jamba.render_playblast",
            text="  Render Animation",
            icon="RENDER_ANIMATION",
        )

        col.separator(factor=0.3)
        active_folder = props.output_folder.strip() or context.scene.render.filepath.strip()
        if not active_folder:
            col.label(text="Select output folder to save video", icon="INFO")
        else:
            col.label(text="Ready to render playblast", icon="CHECKMARK")


CLASSES = [
    JAMBA_PT_Root,
    JAMBA_PT_Prompt,
    JAMBA_PT_References,
    JAMBA_PT_Settings,
    JAMBA_PT_Generate,
    JAMBA_PT_Render,
]
