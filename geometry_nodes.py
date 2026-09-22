# 3D JAMBA | geometry_nodes.py
# Procedural Geometry Node tree generators for structural and environmental elements:
# Foliage/Trees, Grass/Ground, Buildings/Houses, Walls/Fences, Streets/Footpaths, Light Poles, Robots/Tech

import bpy
import math


def _ensure_geo_interface(ng):
    """Ensure Geometry In and Out sockets exist across Blender 3.x, 4.x, and 5.x."""
    if hasattr(ng, "interface"):
        # Blender 4.0+ & 5.0+ API
        has_in = any(s.name == "Geometry" and s.in_out == "INPUT" for s in ng.interface.items_tree)
        has_out = any(s.name == "Geometry" and s.in_out == "OUTPUT" for s in ng.interface.items_tree)
        if not has_in:
            ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        if not has_out:
            ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    else:
        # Blender 3.x fallback
        if "Geometry" not in ng.inputs:
            ng.inputs.new("NodeSocketGeometry", "Geometry")
        if "Geometry" not in ng.outputs:
            ng.outputs.new("NodeSocketGeometry", "Geometry")


# ---------------------------------------------------------------------------
# 1. Procedural Stylized Tree Foliage & Plant Node Tree
# ---------------------------------------------------------------------------
def get_or_create_foliage_nodetree():
    tree_name = "JAMBA_TreeFoliage_Nodes"
    if tree_name in bpy.data.node_groups:
        return bpy.data.node_groups[tree_name]

    ng = bpy.data.node_groups.new(name=tree_name, type="GeometryNodeTree")
    _ensure_geo_interface(ng)

    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    input_node  = nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    output_node = nodes.new("NodeGroupOutput")
    output_node.location = (600, 0)

    # Distribute points on surface of canopy or plant
    dist_node = nodes.new("GeometryNodeDistributePointsOnFaces")
    dist_node.location = (-150, 150)
    dist_node.distribute_method = "RANDOM"
    dist_node.inputs["Density"].default_value = 16.0

    inst_node = nodes.new("GeometryNodeInstanceOnPoints")
    inst_node.location = (150, 150)

    # Stylized faceted leaf cluster
    leaf_node = nodes.new("GeometryNodeMeshCube")
    leaf_node.location = (-150, -150)
    leaf_node.inputs["Size"].default_value = (0.35, 0.35, 0.12)

    rand_rot = nodes.new("FunctionNodeRandomValue")
    rand_rot.location = (-150, 350)
    rand_rot.data_type = "FLOAT_VECTOR"
    rand_rot.inputs["Min"].default_value = (-math.pi, -math.pi, -math.pi)
    rand_rot.inputs["Max"].default_value = (math.pi, math.pi, math.pi)

    rand_scale = nodes.new("FunctionNodeRandomValue")
    rand_scale.location = (-150, -320)
    rand_scale.data_type = "FLOAT"
    rand_scale.inputs["Min"].default_value = 0.6
    rand_scale.inputs["Max"].default_value = 1.3

    join_node = nodes.new("GeometryNodeJoinGeometry")
    join_node.location = (400, 0)

    links.new(input_node.outputs["Geometry"], dist_node.inputs["Mesh"])
    links.new(dist_node.outputs["Points"], inst_node.inputs["Points"])
    links.new(leaf_node.outputs["Mesh"], inst_node.inputs["Instance"])
    links.new(rand_rot.outputs["Value"], inst_node.inputs["Rotation"])
    links.new(rand_scale.outputs["Value"], inst_node.inputs["Scale"])

    links.new(input_node.outputs["Geometry"], join_node.inputs["Geometry"])
    links.new(inst_node.outputs["Instances"], join_node.inputs["Geometry"])
    links.new(join_node.outputs["Geometry"], output_node.inputs["Geometry"])

    return ng


# ---------------------------------------------------------------------------
# 2. Procedural Grass & Ground Scatter Node Tree
# ---------------------------------------------------------------------------
def get_or_create_grass_nodetree():
    tree_name = "JAMBA_GrassScatter_Nodes"
    if tree_name in bpy.data.node_groups:
        return bpy.data.node_groups[tree_name]

    ng = bpy.data.node_groups.new(name=tree_name, type="GeometryNodeTree")
    _ensure_geo_interface(ng)

    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    input_node  = nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    output_node = nodes.new("NodeGroupOutput")
    output_node.location = (600, 0)

    dist_node = nodes.new("GeometryNodeDistributePointsOnFaces")
    dist_node.location = (-150, 150)
    dist_node.distribute_method = "RANDOM"
    dist_node.inputs["Density"].default_value = 2.5

    inst_node = nodes.new("GeometryNodeInstanceOnPoints")
    inst_node.location = (150, 150)

    blade_node = nodes.new("GeometryNodeMeshCone")
    blade_node.location = (-150, -150)
    blade_node.inputs["Radius Top"].default_value = 0.01
    blade_node.inputs["Radius Bottom"].default_value = 0.08
    blade_node.inputs["Depth"].default_value = 0.35
    blade_node.inputs["Vertices"].default_value = 4

    rand_rot = nodes.new("FunctionNodeRandomValue")
    rand_rot.location = (-150, 350)
    rand_rot.data_type = "FLOAT_VECTOR"
    rand_rot.inputs["Min"].default_value = (-0.2, -0.2, -math.pi)
    rand_rot.inputs["Max"].default_value = (0.2, 0.2, math.pi)

    rand_scale = nodes.new("FunctionNodeRandomValue")
    rand_scale.location = (-150, -320)
    rand_scale.data_type = "FLOAT"
    rand_scale.inputs["Min"].default_value = 0.5
    rand_scale.inputs["Max"].default_value = 1.2

    join_node = nodes.new("GeometryNodeJoinGeometry")
    join_node.location = (400, 0)

    links.new(input_node.outputs["Geometry"], dist_node.inputs["Mesh"])
    links.new(dist_node.outputs["Points"], inst_node.inputs["Points"])
    links.new(blade_node.outputs["Mesh"], inst_node.inputs["Instance"])
    links.new(rand_rot.outputs["Value"], inst_node.inputs["Rotation"])
    links.new(rand_scale.outputs["Value"], inst_node.inputs["Scale"])

    links.new(input_node.outputs["Geometry"], join_node.inputs["Geometry"])
    links.new(inst_node.outputs["Instances"], join_node.inputs["Geometry"])
    links.new(join_node.outputs["Geometry"], output_node.inputs["Geometry"])

    return ng


# ---------------------------------------------------------------------------
# 3. Procedural Building Architectural Details (Ledges, Cornices, Framing)
# ---------------------------------------------------------------------------
def get_or_create_building_nodetree():
    tree_name = "JAMBA_BuildingDetails_Nodes"
    if tree_name in bpy.data.node_groups:
        return bpy.data.node_groups[tree_name]

    ng = bpy.data.node_groups.new(name=tree_name, type="GeometryNodeTree")
    _ensure_geo_interface(ng)

    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    input_node  = nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    output_node = nodes.new("NodeGroupOutput")
    output_node.location = (600, 0)

    mesh_to_curve = nodes.new("GeometryNodeMeshToCurve")
    mesh_to_curve.location = (-150, 150)

    curve_to_mesh = nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.location = (150, 150)

    profile_circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
    profile_circle.location = (-150, -150)
    profile_circle.inputs["Radius"].default_value = 0.08
    profile_circle.inputs["Resolution"].default_value = 6

    join_node = nodes.new("GeometryNodeJoinGeometry")
    join_node.location = (400, 0)

    links.new(input_node.outputs["Geometry"], mesh_to_curve.inputs["Mesh"])
    links.new(mesh_to_curve.outputs["Curve"], curve_to_mesh.inputs["Curve"])
    links.new(profile_circle.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])

    links.new(input_node.outputs["Geometry"], join_node.inputs["Geometry"])
    links.new(curve_to_mesh.outputs["Mesh"], join_node.inputs["Geometry"])
    links.new(join_node.outputs["Geometry"], output_node.inputs["Geometry"])

    return ng


# ---------------------------------------------------------------------------
# 4. Procedural Wall / Fence / Parapet Coping & Cap Trim
# ---------------------------------------------------------------------------
def get_or_create_wall_nodetree():
    tree_name = "JAMBA_WallTrim_Nodes"
    if tree_name in bpy.data.node_groups:
        return bpy.data.node_groups[tree_name]

    ng = bpy.data.node_groups.new(name=tree_name, type="GeometryNodeTree")
    _ensure_geo_interface(ng)

    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    input_node  = nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    output_node = nodes.new("NodeGroupOutput")
    output_node.location = (600, 0)

    # Edge coping / wall trim
    mesh_to_curve = nodes.new("GeometryNodeMeshToCurve")
    mesh_to_curve.location = (-150, 150)

    curve_to_mesh = nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.location = (150, 150)

    profile_circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
    profile_circle.location = (-150, -150)
    profile_circle.inputs["Radius"].default_value = 0.06
    profile_circle.inputs["Resolution"].default_value = 4  # square diamond bevel

    join_node = nodes.new("GeometryNodeJoinGeometry")
    join_node.location = (400, 0)

    links.new(input_node.outputs["Geometry"], mesh_to_curve.inputs["Mesh"])
    links.new(mesh_to_curve.outputs["Curve"], curve_to_mesh.inputs["Curve"])
    links.new(profile_circle.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])

    links.new(input_node.outputs["Geometry"], join_node.inputs["Geometry"])
    links.new(curve_to_mesh.outputs["Mesh"], join_node.inputs["Geometry"])
    links.new(join_node.outputs["Geometry"], output_node.inputs["Geometry"])

    return ng


# ---------------------------------------------------------------------------
# 5. Procedural Street & Footpath / Sidewalk Curb Nodes
# ---------------------------------------------------------------------------
def get_or_create_street_nodetree():
    tree_name = "JAMBA_StreetFootpath_Nodes"
    if tree_name in bpy.data.node_groups:
        return bpy.data.node_groups[tree_name]

    ng = bpy.data.node_groups.new(name=tree_name, type="GeometryNodeTree")
    _ensure_geo_interface(ng)

    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    input_node  = nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    output_node = nodes.new("NodeGroupOutput")
    output_node.location = (600, 0)

    # Convert boundary edges into raised roadside curbs
    mesh_to_curve = nodes.new("GeometryNodeMeshToCurve")
    mesh_to_curve.location = (-150, 150)

    curve_to_mesh = nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.location = (150, 150)

    profile_circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
    profile_circle.location = (-150, -150)
    profile_circle.inputs["Radius"].default_value = 0.12
    profile_circle.inputs["Resolution"].default_value = 4

    join_node = nodes.new("GeometryNodeJoinGeometry")
    join_node.location = (400, 0)

    links.new(input_node.outputs["Geometry"], mesh_to_curve.inputs["Mesh"])
    links.new(mesh_to_curve.outputs["Curve"], curve_to_mesh.inputs["Curve"])
    links.new(profile_circle.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])

    links.new(input_node.outputs["Geometry"], join_node.inputs["Geometry"])
    links.new(curve_to_mesh.outputs["Mesh"], join_node.inputs["Geometry"])
    links.new(join_node.outputs["Geometry"], output_node.inputs["Geometry"])

    return ng


# ---------------------------------------------------------------------------
# 6. Procedural Light Post & Lantern Crown Nodes
# ---------------------------------------------------------------------------
def get_or_create_lightpost_nodetree():
    tree_name = "JAMBA_LightPost_Nodes"
    if tree_name in bpy.data.node_groups:
        return bpy.data.node_groups[tree_name]

    ng = bpy.data.node_groups.new(name=tree_name, type="GeometryNodeTree")
    _ensure_geo_interface(ng)

    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    input_node  = nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    output_node = nodes.new("NodeGroupOutput")
    output_node.location = (600, 0)

    mesh_to_curve = nodes.new("GeometryNodeMeshToCurve")
    mesh_to_curve.location = (-150, 150)

    curve_to_mesh = nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.location = (150, 150)

    profile_circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
    profile_circle.location = (-150, -150)
    profile_circle.inputs["Radius"].default_value = 0.04
    profile_circle.inputs["Resolution"].default_value = 6

    join_node = nodes.new("GeometryNodeJoinGeometry")
    join_node.location = (400, 0)

    links.new(input_node.outputs["Geometry"], mesh_to_curve.inputs["Mesh"])
    links.new(mesh_to_curve.outputs["Curve"], curve_to_mesh.inputs["Curve"])
    links.new(profile_circle.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])

    links.new(input_node.outputs["Geometry"], join_node.inputs["Geometry"])
    links.new(curve_to_mesh.outputs["Mesh"], join_node.inputs["Geometry"])
    links.new(join_node.outputs["Geometry"], output_node.inputs["Geometry"])

    return ng


# ---------------------------------------------------------------------------
# 7. Procedural Structural / Robot / Armor Tech Edge Nodes
# ---------------------------------------------------------------------------
def get_or_create_structural_tech_nodetree():
    tree_name = "JAMBA_StructuralTech_Nodes"
    if tree_name in bpy.data.node_groups:
        return bpy.data.node_groups[tree_name]

    ng = bpy.data.node_groups.new(name=tree_name, type="GeometryNodeTree")
    _ensure_geo_interface(ng)

    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    input_node  = nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    output_node = nodes.new("NodeGroupOutput")
    output_node.location = (600, 0)

    mesh_to_curve = nodes.new("GeometryNodeMeshToCurve")
    mesh_to_curve.location = (-150, 150)

    curve_to_mesh = nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.location = (150, 150)

    profile_circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
    profile_circle.location = (-150, -150)
    profile_circle.inputs["Radius"].default_value = 0.03
    profile_circle.inputs["Resolution"].default_value = 4

    join_node = nodes.new("GeometryNodeJoinGeometry")
    join_node.location = (400, 0)

    links.new(input_node.outputs["Geometry"], mesh_to_curve.inputs["Mesh"])
    links.new(mesh_to_curve.outputs["Curve"], curve_to_mesh.inputs["Curve"])
    links.new(profile_circle.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])

    links.new(input_node.outputs["Geometry"], join_node.inputs["Geometry"])
    links.new(curve_to_mesh.outputs["Mesh"], join_node.inputs["Geometry"])
    links.new(join_node.outputs["Geometry"], output_node.inputs["Geometry"])

    return ng


# ---------------------------------------------------------------------------
# Public Application Functions
# ---------------------------------------------------------------------------
def apply_foliage_geometry_nodes(obj):
    """Apply stylized leaf scattering to an object using Geometry Nodes."""
    try:
        ng = get_or_create_foliage_nodetree()
        mod = obj.modifiers.new(name="JAMBA_Foliage", type="NODES")
        mod.node_group = ng
    except Exception as e:
        print(f"[3D JAMBA] Note applying foliage geonodes to {obj.name}: {e}")


def apply_grass_geometry_nodes(obj):
    """Apply stylized grass tuft scattering to a ground plane."""
    try:
        ng = get_or_create_grass_nodetree()
        mod = obj.modifiers.new(name="JAMBA_Grass", type="NODES")
        mod.node_group = ng
    except Exception as e:
        print(f"[3D JAMBA] Note applying grass geonodes: {e}")


def apply_building_geometry_nodes(obj):
    """Apply stylized architectural ledges and framing via Geometry Nodes."""
    try:
        ng = get_or_create_building_nodetree()
        mod = obj.modifiers.new(name="JAMBA_BuildingLedges", type="NODES")
        mod.node_group = ng
    except Exception as e:
        print(f"[3D JAMBA] Note applying building geonodes: {e}")


def apply_wall_geometry_nodes(obj):
    """Apply top wall coping and structural stone trim."""
    try:
        ng = get_or_create_wall_nodetree()
        mod = obj.modifiers.new(name="JAMBA_WallTrim", type="NODES")
        mod.node_group = ng
    except Exception as e:
        print(f"[3D JAMBA] Note applying wall geonodes: {e}")


def apply_street_geometry_nodes(obj):
    """Apply roadside curb and footpath border nodes."""
    try:
        ng = get_or_create_street_nodetree()
        mod = obj.modifiers.new(name="JAMBA_StreetCurb", type="NODES")
        mod.node_group = ng
    except Exception as e:
        print(f"[3D JAMBA] Note applying street geonodes: {e}")


def apply_lamp_post_geometry_nodes(obj):
    """Apply light pole lantern collar and crown nodes."""
    try:
        ng = get_or_create_lightpost_nodetree()
        mod = obj.modifiers.new(name="JAMBA_LightCrown", type="NODES")
        mod.node_group = ng
    except Exception as e:
        print(f"[3D JAMBA] Note applying light post geonodes: {e}")


def apply_structural_tech_geometry_nodes(obj):
    """Apply structural bevels, armor seams, and robotic panelling."""
    try:
        ng = get_or_create_structural_tech_nodetree()
        mod = obj.modifiers.new(name="JAMBA_TechBevel", type="NODES")
        mod.node_group = ng
    except Exception as e:
        print(f"[3D JAMBA] Note applying tech geonodes: {e}")


import re

def apply_procedural_geometry_nodes(obj, obj_type=None):
    """
    Intelligently routes any structural, environmental, or mechanical object
    to its optimal Geometry Nodes procedural enhancer.
    Uses regex word boundaries so 'tree' does not collide with 'street'.
    """
    if obj is None:
        return

    name_lower = obj.name.lower().replace("_", " ").replace("-", " ")
    type_lower = (obj_type or "").lower().replace("_", " ").replace("-", " ")
    combined = f"{type_lower} {name_lower}"

    # 1. Streets / Roads / Footpaths / Sidewalks / Paths (check first before tree/foliage)
    if re.search(r"\b(street|road|footpath|sidewalk|pavement|path|curb|kerb|asphalt|highway|lane)\b", combined):
        apply_street_geometry_nodes(obj)
        return

    # 2. Foliage / Trees / Leaves / Plants / Shrubs
    if re.search(r"\b(tree|trees|foliage|leaves|leaf|plant|plants|bush|canopy|branch|branches|bamboo|shrub)\b", combined):
        apply_foliage_geometry_nodes(obj)
        return

    # 3. Grass / Lawn / Ground terrain
    if re.search(r"\b(grass|lawn|meadow|ground_scatter|field)\b", combined):
        apply_grass_geometry_nodes(obj)
        return

    # 4. Light posts / Street lamps / Lanterns / Poles
    if re.search(r"\b(light|lamp|lantern|pole|streetlight|lamppost)\b", combined):
        apply_lamp_post_geometry_nodes(obj)
        return

    # 5. Walls / Fences / Parapets / Dividers
    if re.search(r"\b(wall|fence|parapet|barrier|partition|divider|gate)\b", combined):
        apply_wall_geometry_nodes(obj)
        return

    # 6. Buildings / Houses / Architecture / Exterior / Interior facades
    if re.search(r"\b(building|house|architecture|facade|roof|room|exterior|interior|tower|pillar|column)\b", combined):
        apply_building_geometry_nodes(obj)
        return

    # 7. Robots / Mechanical / Tech / Armor / Cybernetic
    if re.search(r"\b(robot|mech|cyber|armor|machine|tech|droid|cyborg|mechsuit)\b", combined):
        apply_structural_tech_geometry_nodes(obj)
        return
