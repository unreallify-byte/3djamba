# 3D JAMBA | __init__.py
# Blender Add-on: Text-to-Scene Blockout + Cinematic Camera System
# Location: View3D > UI > 3D JAMBA

bl_info = {
    "name":        "3D JAMBA",
    "author":      "3D Ninja",
    "version":     (1, 1, 0),
    "blender":     (3, 0, 0),
    "location":    "View3D > UI > 3D JAMBA",
    "description": "AI-powered text-to-scene blockout with cinematic camera cinematography",
    "category":    "3D View",
}

# Reload sub-modules on re-register (Blender F8 / addon refresh)
if "bpy" in dir():
    import importlib
    from . import properties, operators, panels, scene_builder, network, geometry_nodes
    importlib.reload(properties)
    importlib.reload(geometry_nodes)
    importlib.reload(scene_builder)
    importlib.reload(network)
    importlib.reload(operators)
    importlib.reload(panels)

import bpy
from . import properties, operators, panels

_ALL_CLASSES = properties.CLASSES + operators.CLASSES + panels.CLASSES


def register():
    for cls in _ALL_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.jamba_props = bpy.props.PointerProperty(
        type=properties.JAMBAProperties
    )
    print("[3D JAMBA] Registered  --  View3D > UI > 3D JAMBA")


def unregister():
    for cls in reversed(_ALL_CLASSES):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, "jamba_props"):
        del bpy.types.Scene.jamba_props
    print("[3D JAMBA] Unregistered")


if __name__ == "__main__":
    register()
