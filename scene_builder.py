# 3D JAMBA | scene_builder.py
# High-speed bike chase sequence with curved roads, vehicle dodging, banking/lean, and 4 dynamic cinematic cameras

import bpy
import math
import mathutils
try:
    from . import geometry_nodes
except ImportError:
    import geometry_nodes

RESOLUTION_MAP = {
    "16_9":   (1920, 1080),
    "9_16":   (1080, 1920),
    "1_1":    (1080, 1080),
    "2_39_1": (2390, 1000),
}

_COL_NAME = "JAMBA_Blockout"
_FPS      = 24


# ---------------------------------------------------------------------------
# Scene / Timeline Configuration
# ---------------------------------------------------------------------------
def configure_scene(context, aspect_ratio_key, duration_seconds):
    scene = context.scene
    scene.render.fps    = _FPS
    total_frames        = duration_seconds * _FPS
    scene.frame_start   = 1
    scene.frame_end     = total_frames
    scene.frame_current = 1
    res_x, res_y = RESOLUTION_MAP.get(aspect_ratio_key, (1920, 1080))
    scene.render.resolution_x          = res_x
    scene.render.resolution_y          = res_y
    scene.render.resolution_percentage = 100
    return total_frames


# ---------------------------------------------------------------------------
# Collection Helpers
# ---------------------------------------------------------------------------
def _ensure_collection(scene):
    col = bpy.data.collections.get(_COL_NAME)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    else:
        col = bpy.data.collections.new(_COL_NAME)
        scene.collection.children.link(col)
    return col


def _clear_jamba_scene():
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        if (obj.name.startswith("Jutsu_") or
                obj.name.startswith("JAMBA_") or
                obj.name.startswith("HeroBike") or
                obj.name.startswith("Chase") or
                obj.name.startswith("Traffic") or
                obj.name.startswith("Oncoming") or
                obj.name.startswith("Street_") or
                obj.name.startswith("Sidewalk_") or
                obj.name.startswith("Kerb_") or
                obj.name.startswith("Bldg_") or
                obj.name.startswith("Tree_") or
                obj.name.startswith("Lamp_") or
                obj.name.startswith("Barrier_")):
            bpy.data.objects.remove(obj, do_unlink=True)
    scene.camera = None
    scene.timeline_markers.clear()

    col = bpy.data.collections.get(_COL_NAME)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)

    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in list(bpy.data.cameras):
        if block.users == 0:
            bpy.data.cameras.remove(block)


# ---------------------------------------------------------------------------
# Materials  --  Solid Viewport Display Colors (Zero Render Lag)
# ---------------------------------------------------------------------------
def _make_mat(name, r, g, b, roughness=0.88):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name)

    mat.diffuse_color      = (r, g, b, 1.0)
    mat.roughness          = roughness
    mat.specular_intensity = 0.1
    mat.metallic           = 0.0

    mat.use_nodes = True
    if mat.node_tree:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
            bsdf.inputs["Roughness"].default_value  = roughness
            bsdf.inputs["Metallic"].default_value   = 0.0
    return mat


def configure_blender_render_and_viewport(scene=None):
    """
    Configures Blender settings as requested:
    1. Viewport Shading: Solid, Lighting: Flat, Color: Material.
    2. Overlays & Gizmos disabled (no outlines, grids, origins, gizmos).
    3. Render Engine: If Cycles, switch to default Eevee.
    4. Framerate: 24 fps, Resolution: 1920 x 1080 @ 100%.
    5. Media Type: Video (FFMPEG, MP4 / H.264) with File Extensions enabled.
    6. Camera view enabled in viewport.
    """
    if scene is None:
        scene = bpy.context.scene

    # 1. Switch Cycles to Eevee
    if getattr(scene.render, 'engine', '') == 'CYCLES':
        try:
            scene.render.engine = 'BLENDER_EEVEE_NEXT'
        except Exception:
            try:
                scene.render.engine = 'BLENDER_EEVEE'
            except Exception:
                pass

    # 2. Frame rate: 24fps & Resolution: 1920x1080
    scene.render.fps = 24
    scene.render.fps_base = 1.0
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    # 3. Media Type: Video (Blender 5.0+) & File format FFMPEG (MP4 / H264)
    scene.render.use_file_extension = True
    img_settings = scene.render.image_settings
    if hasattr(img_settings, 'media_type'):
        try:
            img_settings.media_type = 'VIDEO'
        except Exception:
            pass

    try:
        img_settings.file_format = 'FFMPEG'
    except Exception:
        pass

    try:
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    except Exception:
        pass

    # 4. Viewport Shading: Solid, Flat lighting, Material colors, Outline, Shadow, Cavity, Hide overlays
    try:
        # Collect all unique 3D spaces from active windows and bpy.data.screens
        seen_spaces = set()
        all_screens = list(bpy.data.screens)
        wm = bpy.context.window_manager
        if wm:
            for win in wm.windows:
                if win.screen and win.screen not in all_screens:
                    all_screens.append(win.screen)

        for screen in all_screens:
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D' and space not in seen_spaces:
                            seen_spaces.add(space)
                            shd = space.shading
                            shd.type = 'SOLID'
                            shd.light = 'FLAT'              # Flat lighting
                            shd.color_type = 'MATERIAL'     # Plain solid colors
                            
                            # 3 requested settings:
                            shd.show_object_outline = True  # Outline checked
                            shd.show_shadows = True         # Shadow checked
                            shd.show_cavity = True          # Cavity checked
                            if hasattr(shd, 'cavity_type'):
                                try:
                                    shd.cavity_type = 'BOTH'
                                except Exception:
                                    pass

                            # Disable overlays & gizmos (clean viewport render)
                            if hasattr(space, 'overlay'):
                                space.overlay.show_overlays = False
                            if hasattr(space, 'show_gizmo'):
                                space.show_gizmo = False

                            # Switch to Camera view if scene has a camera
                            if scene.camera and hasattr(space, 'region_3d'):
                                space.region_3d.view_perspective = 'CAMERA'
                    area.tag_redraw()
    except Exception as e:
        print("[3D JAMBA] Viewport/render config note:", e)


# ---------------------------------------------------------------------------
# Mesh Creation Helpers
# ---------------------------------------------------------------------------
def _add_mesh(col, name, prim, location, scale, rotation, mat):
    loc = (float(location[0]), float(location[1]), float(location[2]))
    bpy.ops.object.select_all(action="DESELECT")
    p = str(prim).upper()
    if p in ("CUBE", "BOX"):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    elif p in ("SPHERE", "BALL", "UV_SPHERE", "HEAD", "JOINT"):
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.5, segments=14, ring_count=8, location=loc)
    elif p in ("CYLINDER", "TUBE", "PILLAR", "LIMB", "TRUNK", "TENTACLE"):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.5, depth=1.0, vertices=16, location=loc)
    elif p in ("CONE", "SPIKE", "HORN", "SNOUT", "PYRAMID"):
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.5, depth=1.0, vertices=16, location=loc)
    elif p in ("PLANE", "GROUND", "TERRAIN", "FLOOR", "WING"):
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc)
    elif p in ("TORUS", "RING", "HALO"):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.5, minor_radius=0.15, location=loc)
    else:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)

    obj = bpy.context.active_object
    if obj is None:
        return None
    obj.name           = name
    obj.scale          = (float(scale[0]), float(scale[1]), float(scale[2]))
    obj.rotation_euler = (float(rotation[0]), float(rotation[1]), float(rotation[2]))
    if mat:
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def _create_ribbon_mesh(col, name, left_offset, right_offset, z_height, mat, step_m=3.0, y_min=-40.0, y_max=320.0):
    """Generate smooth ribbon meshes following the road curve."""
    verts = []
    faces = []
    y = y_min
    idx = 0
    while y <= y_max + 0.1:
        xc, dx_dy = road_spline(y)
        ang = math.atan2(dx_dy, 1.0)
        nx = math.cos(ang)
        ny = -math.sin(ang)

        lx = xc + left_offset * nx
        ly = y + left_offset * ny
        rx = xc + right_offset * nx
        ry = y + right_offset * ny

        verts.append((lx, ly, z_height))
        verts.append((rx, ry, z_height))

        if idx > 0:
            v0 = (idx - 1) * 2
            v1 = v0 + 1
            v2 = idx * 2 + 1
            v3 = idx * 2
            faces.append((v0, v1, v2, v3))
        idx += 1
        y += step_m

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    if mat:
        obj.data.materials.append(mat)
    col.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# Road Curve Mathematics (Continuous Catmull-Rom Spline)
# ---------------------------------------------------------------------------
ROAD_SPLINE_POINTS = [
    (-60, 0),
    (-20, 0),
    (0, 0),
    (25, 0),
    (65, -16),
    (105, -24),
    (150, 0),
    (195, 26),
    (240, 18),
    (280, -8),
    (320, 0),
    (360, 0),
    (420, 0),
]

def road_spline(y):
    """Return centerline X and dX/dY derivative at coordinate Y."""
    pts = ROAD_SPLINE_POINTS
    if y <= pts[0][0]:
        return pts[0][1], 0.0
    if y >= pts[-1][0]:
        return pts[-1][1], 0.0

    idx = 0
    while idx < len(pts) - 2 and pts[idx + 1][0] < y:
        idx += 1

    p0 = pts[max(0, idx - 1)]
    p1 = pts[idx]
    p2 = pts[idx + 1]
    p3 = pts[min(len(pts) - 1, idx + 2)]

    span = p2[0] - p1[0]
    t = (y - p1[0]) / span
    m1 = (p2[1] - p0[1]) / (p2[0] - p0[0]) * span
    m2 = (p3[1] - p1[1]) / (p3[0] - p1[0]) * span

    t2 = t * t
    t3 = t2 * t
    h00 = 2*t3 - 3*t2 + 1
    h10 = t3 - 2*t2 + t
    h01 = -2*t3 + 3*t2
    h11 = t3 - t2

    x = h00 * p1[1] + h10 * m1 + h01 * p2[1] + h11 * m2
    dh00 = 6*t2 - 6*t
    dh10 = 3*t2 - 4*t + 1
    dh01 = -6*t2 + 6*t
    dh11 = 3*t2 - 2*t
    dx_dt = dh00 * p1[1] + dh10 * m1 + dh01 * p2[1] + dh11 * m2
    return x, dx_dt / span


def road_pos_and_heading(y, lateral_offset=0.0):
    """Calculate world position (X, Y) and road tangent angle for lane offset."""
    xc, dx_dy = road_spline(y)
    angle = math.atan2(dx_dy, 1.0)
    nx = math.cos(angle)
    ny = -math.sin(angle)
    px = xc + lateral_offset * nx
    py = y + lateral_offset * ny
    return px, py, angle


# ---------------------------------------------------------------------------
# Curved Street Environment Construction
# ---------------------------------------------------------------------------
def _build_curved_street(col, mats):
    # 1. Road surface (-5m to +5m wide)
    _create_ribbon_mesh(col, "Street_Road", -5.0, 5.0, 0.0, mats["road"])

    # 2. Centre lane divider (-0.14m to +0.14m)
    _create_ribbon_mesh(col, "Street_CentreLine", -0.14, 0.14, 0.015, mats["line"])

    # 3. Sidewalks on left (-9.2m to -5.0m) and right (+5.0m to +9.2m)
    _create_ribbon_mesh(col, "Sidewalk_Right", 5.0, 9.2, 0.07, mats["sidewalk"])
    _create_ribbon_mesh(col, "Sidewalk_Left", -9.2, -5.0, 0.07, mats["sidewalk"])

    # 4. Kerbs
    _create_ribbon_mesh(col, "Kerb_Right", 4.8, 5.2, 0.12, mats["kerb"])
    _create_ribbon_mesh(col, "Kerb_Left", -5.2, -4.8, 0.12, mats["kerb"])

    # 5. Buildings along both sides of the curving road
    bldg_mats = [mats["bldg_rose"], mats["bldg_lavender"], mats["bldg_mint"], mats["bldg_tan"]]
    bldg_sizes = [
        (6.0, 9.0, 7.0), (8.0, 11.0, 9.0), (5.5, 7.5, 6.5),
        (7.0, 12.0, 8.5), (6.5, 8.0, 6.0), (9.0, 13.0, 10.0)
    ]

    y_pos = -20.0
    b_idx = 0
    while y_pos <= 300.0:
        # Right side building (+14m offset)
        px_r, py_r, ang_r = road_pos_and_heading(y_pos, 14.5)
        bw, bd, bh = bldg_sizes[b_idx % len(bldg_sizes)]
        m_r = bldg_mats[b_idx % len(bldg_mats)]
        _add_mesh(col, f"Bldg_R_{b_idx+1:02d}", "CUBE",
                  (px_r, py_r, bh * 0.5), (bw, bd, bh), (0, 0, -ang_r), m_r)

        # Left side building (-14m offset)
        px_l, py_l, ang_l = road_pos_and_heading(y_pos, -14.5)
        bw_l, bd_l, bh_l = bldg_sizes[(b_idx + 2) % len(bldg_sizes)]
        m_l = bldg_mats[(b_idx + 2) % len(bldg_mats)]
        _add_mesh(col, f"Bldg_L_{b_idx+1:02d}", "CUBE",
                  (px_l, py_l, bh_l * 0.5), (bw_l, bd_l, bh_l), (0, 0, -ang_l), m_l)

        # Trees on sidewalk (offsets +7.0m and -7.0m)
        if b_idx % 2 == 0:
            tx_r, ty_r, _ = road_pos_and_heading(y_pos + 6.0, 7.0)
            _add_mesh(col, f"Tree_R_{b_idx+1:02d}", "CYLINDER", (tx_r, ty_r, 1.6), (0.35, 0.35, 3.2), (0, 0, 0), mats["trunk"])
            _add_mesh(col, f"TreeTop_R_{b_idx+1:02d}", "SPHERE", (tx_r, ty_r, 4.0), (1.4, 1.4, 1.6), (0, 0, 0), mats["foliage"])

            tx_l, ty_l, _ = road_pos_and_heading(y_pos + 6.0, -7.0)
            _add_mesh(col, f"Tree_L_{b_idx+1:02d}", "CYLINDER", (tx_l, ty_l, 1.6), (0.35, 0.35, 3.2), (0, 0, 0), mats["trunk"])
            _add_mesh(col, f"TreeTop_L_{b_idx+1:02d}", "SPHERE", (tx_l, ty_l, 4.0), (1.4, 1.4, 1.6), (0, 0, 0), mats["foliage"])

        # Street lamps every 24m
        if b_idx % 3 == 0:
            lx_r, ly_r, l_ang = road_pos_and_heading(y_pos, 5.8)
            _add_mesh(col, f"Lamp_R_{b_idx+1:02d}", "CYLINDER", (lx_r, ly_r, 2.6), (0.1, 0.1, 5.2), (0, 0, 0), mats["lamp_post"])
            _add_mesh(col, f"LampHead_R_{b_idx+1:02d}", "CUBE", (lx_r - 0.3 * math.cos(l_ang), ly_r + 0.3 * math.sin(l_ang), 5.2), (0.6, 0.3, 0.15), (0, 0, -l_ang), mats["lamp_head"])

        b_idx += 1
        y_pos += 15.0

    # Parked cars and barriers on curbs
    for py_bar in [35.0, 115.0, 205.0]:
        bx, by, bang = road_pos_and_heading(py_bar, 4.2)
        _add_mesh(col, f"Barrier_{int(py_bar)}", "CUBE", (bx, by, 0.25), (0.4, 2.0, 0.5), (0, 0, -bang + 0.2), mats["barrier"])


# ---------------------------------------------------------------------------
# Vehicle Model Construction with Proper Parenting
# ---------------------------------------------------------------------------
_WHEEL_ROT = (0.0, math.radians(90), 0.0)
_WHEEL_SC  = (0.60, 0.60, 0.13)
_WHEEL_Z   = 0.30

def _create_vehicle_group(col, name, build_func, mats):
    root = bpy.data.objects.new(f"{name}_Root", None)
    root.empty_display_size = 0.5
    root.empty_display_type = 'ARROWS'
    col.objects.link(root)

    children = build_func(col, name, mats)
    for ch in children:
        if ch:
            ch.parent = root
    return root


def _build_hero_bike_parts(col, prefix, mats):
    hb = _add_mesh(col, f"{prefix}_Body", "CUBE", (0, 0, 0.45), (0.48, 1.40, 0.40), (0,0,0), mats["hero_body"])
    ht = _add_mesh(col, f"{prefix}_Tank", "CUBE", (0, 0.1, 0.72), (0.38, 0.55, 0.22), (0,0,0), mats["hero_body"])
    hr = _add_mesh(col, f"{prefix}_Rider", "CUBE", (0, -0.1, 1.02), (0.40, 0.44, 0.68), (math.radians(-14),0,0), mats["hero_rider"])
    hh = _add_mesh(col, f"{prefix}_Helmet", "SPHERE", (0, -0.05, 1.52), (0.26, 0.26, 0.26), (0,0,0), mats["hero_helm"])
    hwf = _add_mesh(col, f"{prefix}_Wheel_Front", "CYLINDER", (0, 0.60, _WHEEL_Z), _WHEEL_SC, _WHEEL_ROT, mats["tire"])
    hwr = _add_mesh(col, f"{prefix}_Wheel_Rear", "CYLINDER", (0, -0.60, _WHEEL_Z), _WHEEL_SC, _WHEEL_ROT, mats["tire"])
    hff = _add_mesh(col, f"{prefix}_FrontFork", "CUBE", (0, 0.60, 0.52), (0.06, 0.06, 0.50), (math.radians(10),0,0), mats["metal"])
    hhb = _add_mesh(col, f"{prefix}_Handlebar", "CUBE", (0, 0.05, 0.88), (0.70, 0.08, 0.06), (0,0,0), mats["metal"])
    hex_ = _add_mesh(col, f"{prefix}_Exhaust", "CYLINDER", (0.35, -0.5, 0.28), (0.05, 0.05, 0.80), (math.radians(90),0,0), mats["metal"])
    return [hb, ht, hr, hh, hwf, hwr, hff, hhb, hex_]


def _build_car_parts(col, prefix, mat_body, mat_glass, mat_tire):
    cb = _add_mesh(col, f"{prefix}_Body", "CUBE", (0, 0, 0.52), (2.0, 4.2, 1.04), (0,0,0), mat_body)
    cr = _add_mesh(col, f"{prefix}_Roof", "CUBE", (0, 0, 1.28), (1.60, 2.20, 0.56), (0,0,0), mat_glass)
    wfl = _add_mesh(col, f"{prefix}_WFL", "CYLINDER", (1.05, 1.4, _WHEEL_Z), _WHEEL_SC, _WHEEL_ROT, mat_tire)
    wfr = _add_mesh(col, f"{prefix}_WFR", "CYLINDER", (-1.05, 1.4, _WHEEL_Z), _WHEEL_SC, _WHEEL_ROT, mat_tire)
    wrl = _add_mesh(col, f"{prefix}_WRL", "CYLINDER", (1.05, -1.4, _WHEEL_Z), _WHEEL_SC, _WHEEL_ROT, mat_tire)
    wrr = _add_mesh(col, f"{prefix}_WRR", "CYLINDER", (-1.05, -1.4, _WHEEL_Z), _WHEEL_SC, _WHEEL_ROT, mat_tire)
    return [cb, cr, wfl, wfr, wrl, wrr]


def _build_chase_bike_parts(col, prefix, mats):
    cbb  = _add_mesh(col, f"{prefix}_Body", "CUBE", (0, 0, 0.44), (0.46, 1.30, 0.38), (0,0,0), mats["chase_bike"])
    cbr  = _add_mesh(col, f"{prefix}_Rider", "CUBE", (0, 0, 0.98), (0.38, 0.42, 0.64), (math.radians(-10),0,0), mats["chase_rider"])
    cbh  = _add_mesh(col, f"{prefix}_Helmet", "SPHERE", (0, 0, 1.45), (0.23, 0.23, 0.23), (0,0,0), mats["chase_helm"])
    cbwf = _add_mesh(col, f"{prefix}_Wheel_F", "CYLINDER", (0, 0.60, _WHEEL_Z), _WHEEL_SC, _WHEEL_ROT, mats["tire"])
    cbwr = _add_mesh(col, f"{prefix}_Wheel_R", "CYLINDER", (0, -0.60, _WHEEL_Z), _WHEEL_SC, _WHEEL_ROT, mats["tire"])
    return [cbb, cbr, cbh, cbwf, cbwr]


def _build_all_vehicles(col, mats):
    v = {}
    v["hero"] = _create_vehicle_group(col, "HeroBike", _build_hero_bike_parts, mats)
    v["chase_car1"] = _create_vehicle_group(
        col, "ChaseCar1",
        lambda c, n, m: _build_car_parts(c, n, m["chase_car"], m["car_glass"], m["tire"]), mats)
    v["chase_bike"] = _create_vehicle_group(col, "ChaseBike", _build_chase_bike_parts, mats)

    # Traffic Cars
    v["traffic_car1"] = _create_vehicle_group(
        col, "TrafficCar1",
        lambda c, n, m: _build_car_parts(c, n, m["bldg_tan"], m["car_glass"], m["tire"]), mats)
    v["traffic_van"] = _create_vehicle_group(
        col, "TrafficVan",
        lambda c, n, m: _build_car_parts(c, n, m["car_blue"], m["car_glass"], m["tire"]), mats)
    v["oncoming1"] = _create_vehicle_group(
        col, "Oncoming1",
        lambda c, n, m: _build_car_parts(c, n, m["oncoming1"], m["car_glass"], m["tire"]), mats)
    v["oncoming2"] = _create_vehicle_group(
        col, "Oncoming2",
        lambda c, n, m: _build_car_parts(c, n, m["oncoming2"], m["car_glass"], m["tire"]), mats)
    return v


# ---------------------------------------------------------------------------
# High-Speed Trajectories, Dodging & Leaning Animation
# ---------------------------------------------------------------------------
def _hero_lane_dodge(y):
    """Dynamic dodging profile: weaves left and right around traffic cars."""
    if y < 25.0:
        return 2.0
    elif y < 65.0:
        t = (y - 25.0) / 40.0
        s = 0.5 - 0.5 * math.cos(t * math.pi)
        return 2.0 - s * 4.4    # Swerve LEFT to -2.4m dodging TrafficCar1
    elif y < 90.0:
        return -2.4             # Taking the inside curve
    elif y < 125.0:
        t = (y - 90.0) / 35.0
        s = 0.5 - 0.5 * math.cos(t * math.pi)
        return -2.4 + s * 4.6   # Cut back RIGHT to +2.2m dodging OncomingCar1
    elif y < 145.0:
        return 2.2
    elif y < 185.0:
        t = (y - 145.0) / 40.0
        s = 0.5 - 0.5 * math.cos(t * math.pi)
        return 2.2 - s * 4.2    # Swoop LEFT to -2.0m overtaking TrafficVan
    elif y < 210.0:
        return -2.0
    elif y < 245.0:
        t = (y - 210.0) / 35.0
        s = 0.5 - 0.5 * math.cos(t * math.pi)
        return -2.0 + s * 3.8   # Weave back RIGHT to +1.8m dodging OncomingCar2
    else:
        return 1.8              # Full throttle straightaway


def _get_hero_transform(f, total_frames):
    p = max(0.0, min(1.0, (f - 1) / float(total_frames - 1)))
    # High-speed sprint: 265 meters traveled in 15 seconds!
    y = p * 265.0
    d = _hero_lane_dodge(y)
    px, py, _ = road_pos_and_heading(y, d)

    # Velocity & turning rate for heading yaw + physics banking
    df = 0.5
    p_fwd = max(0.0, min(1.0, (f - 1 + df) / float(total_frames - 1)))
    p_bwd = max(0.0, min(1.0, (f - 1 - df) / float(total_frames - 1)))
    y_fwd = p_fwd * 265.0
    y_bwd = p_bwd * 265.0
    fx, fy, _ = road_pos_and_heading(y_fwd, _hero_lane_dodge(y_fwd))
    bx, by, _ = road_pos_and_heading(y_bwd, _hero_lane_dodge(y_bwd))

    vx = fx - bx
    vy = fy - by
    yaw = -math.atan2(vx, vy)

    # Lateral acceleration & bank roll angle
    ax = (fx - px) - (px - bx)
    ay = (fy - py) - (py - by)
    spd = max(1e-4, math.hypot(vx, vy))
    alat = (ax * vy - ay * vx) / spd
    # Realistic deep bike lean: roll into turn up to 28 degrees
    roll = max(-math.radians(28), min(math.radians(28), alat * 48.0))

    return (px, py, 0.0), (0.0, roll, yaw)


def _animate_all_vehicles(vehicles, total_frames):
    # Keyframe every 3 frames for ultra-smooth 60fps trajectory
    key_step = 3
    frames = list(range(1, total_frames + 1, key_step))
    if total_frames not in frames:
        frames.append(total_frames)

    for f in frames:
        p = max(0.0, min(1.0, (f - 1) / float(total_frames - 1)))

        # 1. HERO BIKE (High speed, banking, dodging)
        h_loc, h_rot = _get_hero_transform(f, total_frames)
        v_hero = vehicles["hero"]
        v_hero.location = h_loc
        v_hero.rotation_euler = h_rot
        v_hero.keyframe_insert(data_path="location", frame=f)
        v_hero.keyframe_insert(data_path="rotation_euler", frame=f)

        # 2. CHASE CAR 1 (Fast chase right behind hero, 11m back)
        y_cc = max(-18.0, (p * 265.0) - 11.5)
        # Car follows hero path with slight smoothing
        d_cc = _hero_lane_dodge(y_cc) * 0.75 + 0.3
        cc_x, cc_y, cc_ang = road_pos_and_heading(y_cc, d_cc)
        # Car chassis roll leans slightly outward in turns
        _, dx_dy = road_spline(y_cc)
        cc_roll = max(-math.radians(6), min(math.radians(6), -dx_dy * 0.08))
        v_cc = vehicles["chase_car1"]
        v_cc.location = (cc_x, cc_y, 0.0)
        v_cc.rotation_euler = (0.0, cc_roll, -cc_ang)
        v_cc.keyframe_insert(data_path="location", frame=f)
        v_cc.keyframe_insert(data_path="rotation_euler", frame=f)

        # 3. CHASE BIKE (Aggressive sportbike pursuit, 19m back, offset -1.8m)
        y_cb = max(-26.0, (p * 265.0) - 19.0)
        d_cb = _hero_lane_dodge(y_cb) * 0.85 - 1.6
        cb_x, cb_y, cb_ang = road_pos_and_heading(y_cb, d_cb)
        cb_roll = max(-math.radians(24), min(math.radians(24), -dx_dy * 0.38))
        v_cb = vehicles["chase_bike"]
        v_cb.location = (cb_x, cb_y, 0.0)
        v_cb.rotation_euler = (0.0, cb_roll, -cb_ang)
        v_cb.keyframe_insert(data_path="location", frame=f)
        v_cb.keyframe_insert(data_path="rotation_euler", frame=f)

        # 4. TRAFFIC CAR 1 (Normal steady speed in right lane, Y: 45 -> 140m)
        y_t1 = 45.0 + p * 95.0
        t1_x, t1_y, t1_ang = road_pos_and_heading(y_t1, 2.0)
        v_t1 = vehicles["traffic_car1"]
        v_t1.location = (t1_x, t1_y, 0.0)
        v_t1.rotation_euler = (0.0, 0.0, -t1_ang)
        v_t1.keyframe_insert(data_path="location", frame=f)
        v_t1.keyframe_insert(data_path="rotation_euler", frame=f)

        # 5. ONCOMING CAR 1 (Steady speed oncoming towards chase, Y: 135 -> 25m)
        y_oc1 = 135.0 - p * 110.0
        oc1_x, oc1_y, oc1_ang = road_pos_and_heading(y_oc1, -2.1)
        v_oc1 = vehicles["oncoming1"]
        v_oc1.location = (oc1_x, oc1_y, 0.0)
        v_oc1.rotation_euler = (0.0, 0.0, -oc1_ang + math.pi)
        v_oc1.keyframe_insert(data_path="location", frame=f)
        v_oc1.keyframe_insert(data_path="rotation_euler", frame=f)

        # 6. TRAFFIC VAN (Slow utility van in right lane, Y: 140 -> 215m)
        y_tv = 140.0 + p * 75.0
        tv_x, tv_y, tv_ang = road_pos_and_heading(y_tv, 2.1)
        v_tv = vehicles["traffic_van"]
        v_tv.location = (tv_x, tv_y, 0.0)
        v_tv.rotation_euler = (0.0, 0.0, -tv_ang)
        v_tv.keyframe_insert(data_path="location", frame=f)
        v_tv.keyframe_insert(data_path="rotation_euler", frame=f)

        # 7. ONCOMING CAR 2 (Oncoming in chicane section, Y: 255 -> 145m)
        y_oc2 = 255.0 - p * 110.0
        oc2_x, oc2_y, oc2_ang = road_pos_and_heading(y_oc2, -2.0)
        v_oc2 = vehicles["oncoming2"]
        v_oc2.location = (oc2_x, oc2_y, 0.0)
        v_oc2.rotation_euler = (0.0, 0.0, -oc2_ang + math.pi)
        v_oc2.keyframe_insert(data_path="location", frame=f)
        v_oc2.keyframe_insert(data_path="rotation_euler", frame=f)


# ---------------------------------------------------------------------------
# Camera Setup & Smooth Tracking Helpers
# ---------------------------------------------------------------------------
def _look_at(cam_loc, target_loc):
    try:
        import mathutils
        cv  = mathutils.Vector((float(cam_loc[0]), float(cam_loc[1]), float(cam_loc[2])))
        tv  = mathutils.Vector((float(target_loc[0]), float(target_loc[1]), float(target_loc[2])))
        diff = tv - cv
        if diff.length < 0.001:
            return (math.radians(80), 0.0, 0.0)
        q = diff.normalized().to_track_quat('-Z', 'Y')
        return q.to_euler()
    except Exception:
        return (math.radians(80), 0.0, 0.0)


def _cam_kf(cam_obj, frame, location, look_target):
    # Clamp camera Z strictly above ground level (Z >= 0.35m) so camera never goes subterranean
    loc = (float(location[0]), float(location[1]), max(float(location[2]), 0.35))
    rot = _look_at(loc, look_target)
    cam_obj.location       = loc
    cam_obj.rotation_euler = rot
    cam_obj.keyframe_insert(data_path="location",       frame=frame)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def _smooth_cam_safe(cam_obj):
    try:
        if not cam_obj.animation_data or not cam_obj.animation_data.action:
            return
        action = cam_obj.animation_data.action
        fcurves = getattr(action, 'fcurves', None)
        if fcurves is not None:
            for fc in fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.easing        = 'EASE_IN_OUT'
            return
        # Layered action fallback
        layers = getattr(action, 'layers', None)
        if layers:
            for layer in layers:
                strips = getattr(layer, 'strips', None)
                if not strips:
                    continue
                for strip in strips:
                    slots = getattr(action, 'slots', None)
                    if slots:
                        for slot in slots:
                            try:
                                cb = strip.channelbag(slot)
                                if cb:
                                    for fc in cb.fcurves:
                                        for kp in fc.keyframe_points:
                                            kp.interpolation = 'BEZIER'
                                            kp.easing        = 'EASE_IN_OUT'
                            except Exception:
                                pass
    except Exception:
        pass


def _make_camera(scene, name, lens=35):
    old = bpy.data.objects.get(name)
    if old:
        d = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if d and d.users == 0:
            bpy.data.cameras.remove(d)
    cam_data            = bpy.data.cameras.new(name=name)
    cam_data.lens       = lens
    cam_data.clip_start = 0.05
    cam_data.clip_end   = 3000.0
    cam_obj = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam_obj)
    return cam_obj


def _setup_curved_chase_cameras(context, total_frames):
    scene = context.scene
    TF    = total_frames
    scene.timeline_markers.clear()

    seg1_s, seg1_e = 1,              TF // 4
    seg2_s, seg2_e = TF // 4 + 1,    TF // 2
    seg3_s, seg3_e = TF // 2 + 1,    (TF * 3) // 4
    seg4_s, seg4_e = (TF * 3) // 4 + 1, TF

    KF_STEP = 4

    # -----------------------------------------------------------------------
    # SHOT 1: Low Rear Tire Cam (28mm) -- Frames 1 to 90
    # Skimming inches off the asphalt behind the rear tire, tracking the lean & chasers
    # -----------------------------------------------------------------------
    cam1 = _make_camera(scene, "JAMBA_CAM1_BackTire", lens=28)
    for frame in list(range(seg1_s, seg1_e + 1, KF_STEP)) + [seg1_e]:
        h_loc, h_rot = _get_hero_transform(frame, TF)
        yaw = h_rot[2]
        # Offset: 1.1m right, -2.4m behind, 0.28m high
        cx = h_loc[0] + 1.1 * math.cos(yaw) - (-2.4) * math.sin(yaw)
        cy = h_loc[1] + 1.1 * math.sin(yaw) + (-2.4) * math.cos(yaw)
        cz = 0.28
        tx = h_loc[0] + 3.0 * (-math.sin(yaw))
        ty = h_loc[1] + 3.0 * math.cos(yaw)
        tz = 0.65
        _cam_kf(cam1, frame, (cx, cy, cz), (tx, ty, tz))
    _smooth_cam_safe(cam1)

    # -----------------------------------------------------------------------
    # SHOT 2: Third-Person Elevated Pursuit Cam (35mm) -- Frames 91 to 180
    # Captures the massive sweeping right curve and deep banking
    # -----------------------------------------------------------------------
    cam2 = _make_camera(scene, "JAMBA_CAM2_ThirdPerson", lens=35)
    for frame in list(range(seg2_s, seg2_e + 1, KF_STEP)) + [seg2_e]:
        h_loc, h_rot = _get_hero_transform(frame, TF)
        yaw = h_rot[2]
        t = (frame - seg2_s) / float(max(1, seg2_e - seg2_s))
        drift_x = 1.0 + t * 1.5
        cx = h_loc[0] + drift_x * math.cos(yaw) - (-5.5) * math.sin(yaw)
        cy = h_loc[1] + drift_x * math.sin(yaw) + (-5.5) * math.cos(yaw)
        cz = 2.4
        tx = h_loc[0] + 5.0 * (-math.sin(yaw))
        ty = h_loc[1] + 5.0 * math.cos(yaw)
        tz = 0.8
        _cam_kf(cam2, frame, (cx, cy, cz), (tx, ty, tz))
    _smooth_cam_safe(cam2)

    # -----------------------------------------------------------------------
    # SHOT 3: Close Side-Tracking Cam (50mm) -- Frames 181 to 270
    # Lateral view as bike slices through traffic chicane
    # -----------------------------------------------------------------------
    cam3 = _make_camera(scene, "JAMBA_CAM3_SideTrack", lens=50)
    for frame in list(range(seg3_s, seg3_e + 1, KF_STEP)) + [seg3_e]:
        h_loc, h_rot = _get_hero_transform(frame, TF)
        yaw = h_rot[2]
        cx = h_loc[0] + 4.8 * math.cos(yaw) - 0.5 * math.sin(yaw)
        cy = h_loc[1] + 4.8 * math.sin(yaw) + 0.5 * math.cos(yaw)
        cz = 1.2
        tx = h_loc[0]
        ty = h_loc[1]
        tz = 0.85
        _cam_kf(cam3, frame, (cx, cy, cz), (tx, ty, tz))
    _smooth_cam_safe(cam3)

    # -----------------------------------------------------------------------
    # SHOT 4: Dynamic Front Sweeping Orbit (28mm) -- Frames 271 to 360
    # Looking back at hero sprinting forward at top speed into the straightaway
    # -----------------------------------------------------------------------
    cam4 = _make_camera(scene, "JAMBA_CAM4_FrontOrbit", lens=28)
    for frame in list(range(seg4_s, seg4_e + 1, KF_STEP)) + [seg4_e]:
        h_loc, h_rot = _get_hero_transform(frame, TF)
        yaw = h_rot[2]
        t = (frame - seg4_s) / float(max(1, seg4_e - seg4_s))
        ang_offset = math.radians(130) + t * (math.radians(-40) - math.radians(130))
        rad = 7.5
        cz  = 1.3 + t * 1.1
        cx = h_loc[0] + rad * math.sin(yaw + ang_offset)
        cy = h_loc[1] + rad * math.cos(yaw + ang_offset)
        tx = h_loc[0]
        ty = h_loc[1]
        tz = 0.9
        _cam_kf(cam4, frame, (cx, cy, cz), (tx, ty, tz))
    _smooth_cam_safe(cam4)

    # Timeline Markers for automatic camera switching
    m1 = scene.timeline_markers.new("SHOT1_BackTire",    frame=seg1_s)
    m1.camera = cam1
    m2 = scene.timeline_markers.new("SHOT2_ThirdPerson", frame=seg2_s)
    m2.camera = cam2
    m3 = scene.timeline_markers.new("SHOT3_SideTrack",   frame=seg3_s)
    m3.camera = cam3
    m4 = scene.timeline_markers.new("SHOT4_FrontOrbit",  frame=seg4_s)
    m4.camera = cam4

    scene.camera = cam1


# ---------------------------------------------------------------------------
# Jutsu Camera & API Blockout Geometry (for AI-generated scenes)
# ---------------------------------------------------------------------------
def create_jutsu_camera(context, keyframes, total_frames):
    scene = context.scene
    old = bpy.data.objects.get("Jutsu_Camera")
    if old:
        d = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if d and d.users == 0:
            bpy.data.cameras.remove(d)
    cam_data            = bpy.data.cameras.new(name="Jutsu_Camera")
    cam_data.lens       = 35
    cam_data.clip_start = 0.1
    cam_data.clip_end   = 2000.0
    cam_obj = bpy.data.objects.new("Jutsu_Camera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    if keyframes:
        for kf in keyframes:
            time_pct = float(kf.get("time_pct", 0.0))
            frame    = max(1, int(round(time_pct * total_frames)))
            loc      = kf.get("location", [0.0, -5.0, 1.7])
            rot      = kf.get("rotation", [math.radians(80), 0.0, 0.0])
            # CAMERA FLOOR LIMITER: Clamp Z >= 0.35m so camera never penetrates the ground plane
            cam_loc  = (float(loc[0]), float(loc[1]), max(float(loc[2]), 0.35))
            cam_obj.location       = cam_loc
            cam_obj.rotation_euler = (float(rot[0]), float(rot[1]), float(rot[2]))
            cam_obj.keyframe_insert(data_path="location",       frame=frame)
            cam_obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        _smooth_cam_safe(cam_obj)
    else:
        cam_obj.location       = (0.0, -8.0, 1.7)
        cam_obj.rotation_euler = (math.radians(80), 0.0, 0.0)
    return cam_obj


_TYPE_MAP = {
    "character": "CUBE",   "person": "CUBE",   "human": "CUBE",   "ninja": "CUBE",
    "warrior":   "CUBE",   "robot":  "CUBE",   "prop":  "CUBE",   "cube": "CUBE",
    "katana":    "CUBE",   "sword":  "CUBE",   "blade": "CUBE",   "scarf": "CUBE",
    "building":  "CUBE",   "house":  "CUBE",   "wall":  "CUBE",   "architecture": "CUBE",
    "creature":  "SPHERE", "animal": "SPHERE", "rock":  "SPHERE", "stone": "SPHERE", "sphere": "SPHERE",
    "tree":      "CYLINDER","bamboo":"CYLINDER","trunk":"CYLINDER","log":"CYLINDER",
    "pillar":    "CYLINDER","column":"CYLINDER","cylinder":"CYLINDER","lamp":"CYLINDER","post":"CYLINDER",
    "grass":     "CONE",   "cone":   "CONE",   "plant": "CONE",   "shrub": "CONE", "roof": "CONE",
    "ground":    "PLANE",  "floor":  "PLANE",  "water": "PLANE",  "plane": "PLANE",
    "street":    "PLANE",  "road":   "PLANE",  "footpath":"PLANE","sidewalk":"PLANE",
    "torus":     "TORUS",  "ring":   "TORUS",
}

def _get_blockout_material(obj_type="prop", name=""):
    combined = f"{obj_type} {name}".lower()
    if any(k in combined for k in ("head", "face", "skin")):
        return _make_mat("JAMBA_Mat_Skin", 0.85, 0.72, 0.68)
    if any(k in combined for k in ("ninja", "torso", "chest", "cloth", "pelvis", "scarf")):
        return _make_mat("JAMBA_Mat_Cloth", 0.32, 0.38, 0.48)
    if any(k in combined for k in ("blade", "sword", "katana", "metal", "steel", "armor")):
        return _make_mat("JAMBA_Mat_Metal", 0.82, 0.85, 0.90)
    if any(k in combined for k in ("guard", "tsuba", "hilt", "gold", "horn", "cap")):
        return _make_mat("JAMBA_Mat_Gold", 0.88, 0.72, 0.35)
    if any(k in combined for k in ("dragon", "alien", "tentacle", "creature", "beast", "monster")):
        return _make_mat("JAMBA_Mat_Creature", 0.38, 0.70, 0.62)
    if any(k in combined for k in ("wing", "membrane")):
        return _make_mat("JAMBA_Mat_Wing", 0.65, 0.52, 0.75)
    if any(k in combined for k in ("foliage", "leaves", "leaf", "bamboo", "grass", "plant", "bush")):
        return _make_mat("JAMBA_Mat_Foliage", 0.36, 0.65, 0.42)
    if any(k in combined for k in ("trunk", "wood", "branch", "bark", "log")):
        return _make_mat("JAMBA_Mat_Wood", 0.48, 0.36, 0.28)
    if any(k in combined for k in ("rock", "stone", "lantern", "pillar", "monument")):
        return _make_mat("JAMBA_Mat_Stone", 0.62, 0.64, 0.68)
    if any(k in combined for k in ("ground", "floor", "terrain", "sand")):
        return _make_mat("JAMBA_Mat_Ground", 0.76, 0.72, 0.62)
    if any(k in combined for k in ("vehicle", "car", "bike")):
        return _make_mat("JAMBA_Mat_Veh", 0.80, 0.42, 0.38)
    if any(k in combined for k in ("arm", "leg", "thigh", "calf", "hand", "foot", "limb")):
        return _make_mat("JAMBA_Mat_Limbs", 0.44, 0.42, 0.56)

    return _make_mat("JAMBA_Mat_Prop", 0.76, 0.70, 0.54)





def _weld_and_snap_scene(col, created_objs):
    """
    1. Locks ground plane strictly to Z = 0.0.
    2. Snaps all grounded objects (characters, buildings, trees, lamps, vehicles)
       so their lowest vertex sits flush on Z = 0.0 (preventing half-buried legs or subterranean clipping).
    3. Eliminates floating gaps between adjacent body parts.
    """
    for obj in created_objs:
        if not obj or not obj.data or not hasattr(obj.data, "vertices"):
            continue

        name_lower = obj.name.lower()

        # Ground plane is strictly flat at Z = 0.0
        if any(k in name_lower for k in ("ground", "floor", "terrain", "plane")):
            obj.location.z = 0.0
            continue

        # Compute object lowest world Z
        bpy.context.view_layer.update()
        try:
            world_z = [(obj.matrix_world @ mathutils.Vector(v.co)).z for v in obj.data.vertices]
            if not world_z:
                continue
            min_z = min(world_z)
        except Exception:
            min_z = obj.location.z - abs(obj.scale.z) / 2.0

        # If buried underground (min_z < 0), lift flush to Z = 0.0
        if min_z < -0.001:
            obj.location.z += (-min_z)
        # If hovering slightly off the ground (0 < min_z <= 0.45) on grounded root objects, snap flush
        elif 0.001 < min_z <= 0.45 and not any(k in name_lower for k in (
            "head", "neck", "arm", "hand", "shoulder", "elbow", "torso",
            "blade", "guard", "hilt", "canopy", "roof", "lantern", "tentacle"
        )):
            obj.location.z -= min_z


def build_blockout_geometry(context, objects_list):
    scene = context.scene
    col   = _ensure_collection(scene)
    bpy.ops.object.select_all(action="DESELECT")

    created_objs = []

    for i, entry in enumerate(objects_list):
        obj_type = str(entry.get("type", "prop")).lower()
        obj_name = str(entry.get("name", f"JAMBA_Object_{i+1:03d}"))
        location = entry.get("location", [0.0, 0.0, 0.0])
        scale    = entry.get("scale",    [1.0, 1.0, 1.0])
        rotation = entry.get("rotation", [0.0, 0.0, 0.0])

        raw_prim = entry.get("primitive") or entry.get("shape")
        if raw_prim and str(raw_prim).upper() in ("CUBE", "SPHERE", "CYLINDER", "CONE", "PLANE", "TORUS"):
            prim = str(raw_prim).upper()
        elif obj_type.upper() in ("CUBE", "SPHERE", "CYLINDER", "CONE", "PLANE", "TORUS"):
            prim = obj_type.upper()
        else:
            prim = _TYPE_MAP.get(obj_type, "CUBE")

        mat = _get_blockout_material(obj_type, obj_name)
        obj = _add_mesh(col, obj_name, prim, location, scale, rotation, mat)
        if obj:
            created_objs.append(obj)
            # Apply procedural geometry nodes according to structural / environmental type
            geometry_nodes.apply_procedural_geometry_nodes(obj, obj_type)

    # Universal post-process: ground snapping (Z >= 0) and floor alignment
    _weld_and_snap_scene(col, created_objs)

    bpy.ops.object.select_all(action="DESELECT")
    configure_blender_render_and_viewport(scene)



# ---------------------------------------------------------------------------
# Main Entry Point: Fast Curving Bike Chase Sequence
# ---------------------------------------------------------------------------
def apply_bike_chase_demo(context):
    scene = context.scene
    props = scene.jamba_props

    # 15 seconds @ 24 fps = 360 frames
    props.aspect_ratio = "16_9"
    props.duration     = 15
    total_frames       = configure_scene(context, "16_9", 15)

    _clear_jamba_scene()
    col = _ensure_collection(scene)

    mats = {
        "road":          _make_mat("JAMBA_Road_Mat",      0.18, 0.18, 0.22),
        "line":          _make_mat("JAMBA_Line_Mat",      0.92, 0.88, 0.68),
        "sidewalk":      _make_mat("JAMBA_Sidewalk_Mat",  0.53, 0.68, 0.58),
        "kerb":          _make_mat("JAMBA_Kerb_Mat",      0.76, 0.72, 0.62),
        "bldg_rose":     _make_mat("JAMBA_BldgRose_Mat",  0.75, 0.53, 0.58),
        "bldg_lavender": _make_mat("JAMBA_BldgLav_Mat",   0.58, 0.54, 0.74),
        "bldg_mint":     _make_mat("JAMBA_BldgMint_Mat",  0.53, 0.72, 0.62),
        "bldg_tan":      _make_mat("JAMBA_BldgTan_Mat",   0.76, 0.70, 0.54),
        "trunk":         _make_mat("JAMBA_Trunk_Mat",     0.52, 0.40, 0.32),
        "foliage":       _make_mat("JAMBA_Foliage_Mat",   0.46, 0.68, 0.50),
        "lamp_post":     _make_mat("JAMBA_LampPost_Mat",  0.32, 0.34, 0.38),
        "lamp_head":     _make_mat("JAMBA_LampHead_Mat",  0.92, 0.82, 0.48),
        "car_blue":      _make_mat("JAMBA_CarBlue_Mat",   0.42, 0.62, 0.78),
        "barrier":       _make_mat("JAMBA_Barrier_Mat",   0.85, 0.52, 0.35),
        "tire":          _make_mat("JAMBA_Tire_Mat",      0.12, 0.12, 0.14),
        "metal":         _make_mat("JAMBA_Metal_Mat",     0.70, 0.72, 0.76),
        "car_glass":     _make_mat("JAMBA_Glass_Mat",     0.25, 0.28, 0.34),
        "hero_body":     _make_mat("JAMBA_HeroBody_Mat",  0.36, 0.66, 0.78),
        "hero_rider":    _make_mat("JAMBA_HeroRider_Mat", 0.55, 0.50, 0.74),
        "hero_helm":     _make_mat("JAMBA_HeroHelmet_Mat",0.92, 0.52, 0.36),
        "chase_car":     _make_mat("JAMBA_ChaseCar_Mat",  0.82, 0.34, 0.32),
        "chase_bike":    _make_mat("JAMBA_ChaseBike_Mat", 0.60, 0.32, 0.55),
        "chase_rider":   _make_mat("JAMBA_ChaseRider_Mat",0.28, 0.30, 0.36),
        "chase_helm":    _make_mat("JAMBA_ChaseHelmet_Mat",0.86, 0.76, 0.28),
        "oncoming1":     _make_mat("JAMBA_Oncoming1_Mat", 0.86, 0.68, 0.36),
        "oncoming2":     _make_mat("JAMBA_Oncoming2_Mat", 0.44, 0.66, 0.86),
    }

    _build_curved_street(col, mats)
    vehicles = _build_all_vehicles(col, mats)
    _animate_all_vehicles(vehicles, total_frames)
    _setup_curved_chase_cameras(context, total_frames)

    configure_blender_render_and_viewport(scene)
    props.status_message = "Fast Chase Sequence loaded! Press Space to play."
