"""Render Metabole's original, illustrative Seoul miniature (Blender 5).

blender --background --factory-startup --python frontend/art/landing/build_scene.py
Offline authoring only. No Blender or 3D runtime is shipped to the browser.
"""

import math
import os
import random
from pathlib import Path

import bpy
from mathutils import Vector


ART = Path(__file__).resolve().parent
OUTPUT = Path(os.environ.get("METABOLE_RENDER_DIR", "/tmp/metabole-landing-renders"))
OUTPUT.mkdir(parents=True, exist_ok=True)
random.seed(17)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, roughness=0.65, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


CREAM = material("porcelain · warm ivory", (0.87, 0.84, 0.74))
WHITE = material("chalk · off white", (0.98, 0.97, 0.9))
BASE = material("atlas · pale limestone", (0.73, 0.79, 0.68))
TEAL = material("metabole · forest teal", (0.012, 0.17, 0.12))
MINT = material("sage · soft green", (0.32, 0.56, 0.41))
PALE = material("pistachio · foliage", (0.59, 0.73, 0.43))
WATER = material("Han river · celadon", (0.12, 0.46, 0.40), 0.32)
WATER_LINE = material("water highlights", (0.60, 0.85, 0.73), 0.4)
GLASS = material("opaque tinted glass", (0.10, 0.28, 0.23), 0.32)
ROAD = material("paths · sandstone", (0.70, 0.71, 0.61))
WOOD = material("timber · soft walnut", (0.42, 0.29, 0.19))
TERRA = material("terracotta accents", (0.68, 0.33, 0.22))


def finish(obj, name, mat, bevel=0):
    obj.name = name
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("soft ceramic edges", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        obj.modifiers.new("weighted corner normals", "WEIGHTED_NORMAL")
    return obj


def box(name, xyz, size, mat, bevel=0.045):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz)
    obj = bpy.context.object
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, bevel)


def cylinder(name, xyz, radius, depth, mat, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=xyz)
    return finish(bpy.context.object, name, mat, 0.025)


def sphere(name, xyz, size, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=xyz)
    obj = bpy.context.object
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(obj, name, mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def line(name, coords, mat, thickness=0.025):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = thickness
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(coords) - 1)
    for point, xyz in zip(spline.points, coords):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def extruded_polygon(name, points, bottom, top, mat, bevel=0.08):
    count = len(points)
    vertices = [(x, y, bottom) for x, y in points] + [(x, y, top) for x, y in points]
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    faces += [(i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat, bevel)


def tree(x, y, scale=1, ground=0.48):
    cylinder("tree trunk", (x, y, ground + 0.28 * scale), 0.048 * scale, 0.56 * scale, WOOD, 12)
    sphere("rounded tree canopy", (x, y, ground + 0.65 * scale), (0.27 * scale, 0.25 * scale, 0.38 * scale), random.choice([MINT, PALE]))


def building(x, y, width, depth, height, mat=CREAM):
    ground = 0.48
    box("city block", (x, y, ground + height / 2), (width, depth, height), mat, 0.075)
    box("flat roof lip", (x, y, ground + height), (width + 0.055, depth + 0.055, 0.085), WHITE)
    rows = max(1, int(height / 0.42))
    columns = max(1, int(width / 0.33))
    for row in range(rows):
        for col in range(columns):
            wx = x + (col - (columns - 1) / 2) * width / (columns + 0.35)
            wz = ground + 0.25 + row * (height - 0.25) / rows
            box("front window", (wx, y - depth / 2 - 0.014, wz), (width / (columns + 0.35) * 0.53, 0.026, 0.20), GLASS, 0.01)
    for row in range(rows):
        box("side window", (x + width / 2 + 0.014, y, ground + 0.25 + row * (height - 0.25) / rows), (0.025, depth * 0.44, 0.20), GLASS, 0.01)
    if height > 1.8:
        box("rooftop room", (x + width * 0.12, y + depth * 0.12, ground + height + 0.14), (width * 0.43, depth * 0.50, 0.26), mat)


def shop(x, y, width=1.5, depth=1.1, color=TEAL, cafe=False):
    h = 1.05
    box("neighborhood shop", (x, y, 0.48 + h / 2), (width, depth, h), WHITE, 0.065)
    box("shop parapet", (x, y, 1.57), (width + 0.09, depth + 0.09, 0.12), CREAM)
    front = y - depth / 2
    box("storefront glazing", (x, front - 0.025, 0.88), (width * 0.86, 0.05, 0.7), GLASS)
    for dx in [-width * 0.43, 0, width * 0.43]:
        box("storefront mullion", (x + dx, front - 0.06, 0.88), (0.065, 0.07, 0.73), color, 0.012)
    box("shop fascia", (x, front - 0.06, 1.30), (width * 0.97, 0.09, 0.16), color)
    count = 7
    for i in range(count):
        awning = box("striped shop awning", (x - width / 2 + (i + 0.5) * width / count, front - 0.22, 1.23), (width / count, 0.49, 0.07), color if i % 2 == 0 else WHITE, 0.015)
        awning.rotation_euler.x = 0.20
    if cafe:
        bpy.ops.object.text_add(location=(x, front - 0.112, 1.28), rotation=(math.pi / 2, 0, 0))
        text = bpy.context.object
        text.name = "cafe sign"
        text.data.body = "C A F E"
        text.data.align_x = "CENTER"
        text.data.align_y = "CENTER"
        text.data.size = 0.105
        text.data.extrude = 0.001
        text.data.materials.append(WHITE)
        for dx in [-0.48, 0.46]:
            table_x, table_y = x + dx, front - 0.87
            cylinder("cafe table", (table_x, table_y, 0.86), 0.20, 0.065, WOOD)
            cylinder("table leg", (table_x, table_y, 0.66), 0.027, 0.36, TEAL, 12)
            for dy in [-0.27, 0.26]:
                cylinder("terrace stool", (table_x, table_y + dy, 0.68), 0.09, 0.055, MINT)
                cylinder("stool leg", (table_x, table_y + dy, 0.56), 0.022, 0.22, WOOD, 12)


# A deliberately illustrative city footprint, not geographic/parcel geometry.
outline = [(-5.6, -1.65), (-5.3, -2.7), (-4.0, -3.35), (-2.2, -3.65), (-0.7, -3.50), (0.8, -3.80), (2.4, -3.45), (3.2, -2.9), (4.8, -2.35), (5.5, -1.1), (5.5, 0.8), (4.7, 2.0), (3.45, 2.5), (2.65, 3.20), (1.2, 3.60), (-0.4, 3.30), (-1.7, 3.55), (-3.0, 2.80), (-4.6, 2.15), (-5.5, 0.75)]
extruded_polygon("Seoul atlas plinth", outline, -0.12, 0.40, CREAM, 0.16)
extruded_polygon("city green surface", [(x * 0.975, y * 0.975) for x, y in outline], 0.38, 0.47, BASE, 0.06)


def river_y(x):
    return 0.48 * math.sin(x * 0.65) - 0.02


xs = [-5.5 + i * 11 / 100 for i in range(101)]
river = [(x, river_y(x) - 0.50) for x in xs] + [(x, river_y(x) + 0.50) for x in reversed(xs)]
extruded_polygon("Han river ribbon", river, 0.475, 0.49, WATER, 0)
for offset in [-0.53, 0.53]:
    line("riverside promenade", [(x, river_y(x) + offset, 0.51) for x in xs[2:-2]], WHITE, 0.048)
for x in [-4.4, -3.6, -1.1, 0.1, 3.1, 4.2]:
    line("quiet river ripple", [(x + t * 0.12, river_y(x + t * 0.12) + 0.14, 0.503) for t in range(5)], WATER_LINE, 0.011)

# Roads and pocket parks create readable neighborhoods in the small render.
for y in [-1.40, 1.32]:
    box("neighborhood street", (0, y, 0.49), (8.7, 0.26, 0.03), ROAD, 0.03)
for x in [-3.9, -0.5, 2.35]:
    box("south neighborhood lane", (x, -2.30, 0.50), (0.23, 1.9, 0.025), ROAD, 0.025)

# Two modest bridges across the stylized river.
for x in [-2.6, 2.1]:
    y = river_y(x)
    box("river bridge", (x, y, 0.68), (0.55, 1.55, 0.17), WHITE, 0.05)
    box("bridge road", (x, y, 0.773), (0.40, 1.59, 0.025), ROAD, 0.015)
    for side in [-0.27, 0.27]:
        line("bridge railing", [(x + side, y - 0.78, 0.93), (x + side, y + 0.78, 0.93)], WHITE, 0.022)
        for i in range(6):
            cylinder("bridge post", (x + side, y - 0.72 + i * 0.29, 0.85), 0.016, 0.18, WHITE, 8)

# North skyline, with varied heights and breathing room.
for data in [(-4.1, 1.85, 0.80, 0.7, 1.35), (-3.05, 2.0, 0.85, 0.85, 2.1), (-2.0, 2.48, 0.65, 0.73, 1.4), (0.35, 2.30, 0.75, 0.8, 2.5), (1.40, 2.05, 0.80, 0.85, 1.8), (2.5, 2.02, 0.7, 0.80, 2.9), (3.6, 1.60, 0.77, 0.9, 1.5), (4.45, 0.95, 0.60, 0.60, 1.15)]:
    building(*data, mat=random.choice([CREAM, WHITE, CREAM, MINT]))

# Namsan and its slender observation tower suggest Seoul without visual clutter.
sphere("Namsan ceramic hill", (-0.92, 1.65, 0.44), (0.79, 0.73, 0.46), MINT)
cylinder("N Seoul tower shaft", (-0.92, 1.65, 1.94), 0.077, 2.20, WHITE)
cylinder("observation lower deck", (-0.92, 1.65, 2.67), 0.24, 0.10, CREAM)
cylinder("observation glazing", (-0.92, 1.65, 2.80), 0.21, 0.18, GLASS)
cylinder("observation upper deck", (-0.92, 1.65, 2.93), 0.27, 0.09, WHITE)
cylinder("tower antenna", (-0.92, 1.65, 3.25), 0.026, 0.60, TEAL, 16)

shop(-2.55, -2.10, color=TEAL, cafe=True)
shop(0.50, -2.50, width=1.50, color=MINT)
building(2.10, -2.18, 0.87, 0.95, 1.52, CREAM)
building(3.45, -1.55, 0.98, 0.80, 1.18, WHITE)
building(-4.45, -1.30, 0.64, 0.72, 0.91, TERRA)

for x, y, scale in [(-4.85, 0.9, 1), (-3.80, 2.57, 0.85), (-1.60, 2.90, 0.8), (0.95, 3.02, 0.85), (3.15, 2.32, 0.85), (4.67, -0.76, 1), (3.94, -2.24, 0.90), (2.9, -2.87, 0.9), (1.6, -3.1, 0.65), (-0.65, -2.4, 0.8), (-1.00, -3.10, 0.75), (-4.1, -2.48, 0.8), (-3.6, -0.72, 0.7), (0.25, 0.90, 0.65), (1.20, -0.4, 0.65), (-4.8, -2.0, 0.7)]:
    tree(x, y, scale)

# Tiny benches, a riverside kiosk, and stepping stones complete the model.
for x, y in [(-3.8, -0.35), (0.4, -0.80), (3.65, 0.85)]:
    box("riverside bench", (x, y, 0.65), (0.42, 0.14, 0.055), WOOD, 0.02)
    for dx in [-0.14, 0.14]:
        box("bench foot", (x + dx, y, 0.56), (0.04, 0.11, 0.17), TEAL, 0.01)

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = int(os.environ.get("METABOLE_SAMPLES", "96"))
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 5
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.resolution_x = 1600
scene.render.resolution_y = 1400
scene.render.resolution_percentage = int(os.environ.get("METABOLE_RENDER_PERCENT", "100"))
scene.world.color = (0.65, 0.65, 0.65)
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.80, 0.84, 0.78, 1)
background.inputs["Strength"].default_value = 0.65
scene.view_settings.view_transform = "AgX"


def light(name, xyz, energy, size, color):
    bpy.ops.object.light_add(type="AREA", location=xyz)
    obj = bpy.context.object
    obj.name = name
    obj.data.energy = energy
    obj.data.shape = "DISK"
    obj.data.size = size
    obj.data.color = color
    obj.rotation_euler = (Vector((0, 0, 0)) - obj.location).to_track_quat("-Z", "Y").to_euler()


light("large warm softbox", (-5, -7, 12), 1750, 7, (1.0, 0.94, 0.82))
light("cool fill", (6, -1, 8), 950, 6, (0.80, 0.94, 1.0))
light("top rim", (0, 6, 10), 1450, 5, (1.0, 0.99, 0.89))
bpy.ops.object.camera_add(location=(11, -16, 13))
camera = bpy.context.object
camera.name = "Atlas orthographic camera"
camera.rotation_euler = (Vector((0, 0, 0.70)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 13.4
scene.camera = camera
scene.render.filepath = str(OUTPUT / "seoul-diorama.png")
bpy.ops.wm.save_as_mainfile(filepath=str(ART / "seoul-atlas.blend"), compress=True)
bpy.ops.render.render(write_still=True)

# The pin is an independently rendered foreground layer for CSS floating.
for obj in list(scene.objects):
    if obj.type not in {"LIGHT", "CAMERA"}:
        obj.hide_render = True

# A teardrop silhouette with an inset ivory circle, facing the camera.
pin_outline = [(0, -1.04)]
for i in range(41):
    angle = math.radians(-40 + i * 260 / 40)
    pin_outline.append((math.cos(angle) * 0.69, 0.29 + math.sin(angle) * 0.69))
pin = extruded_polygon("Metabole ceramic location pin", pin_outline, -0.10, 0.13, TEAL, 0.09)
pin.rotation_euler.x = math.pi / 2
pin.location.z = 1.0
dot = cylinder("pin ivory inset", (0, -0.175, 1.34), 0.245, 0.035, WHITE, 64)
dot.rotation_euler.x = math.pi / 2
camera.location = (2.0, -8.0, 3.0)
camera.rotation_euler = (Vector((0, 0, 1.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.ortho_scale = 2.75
scene.render.resolution_x = 256
scene.render.resolution_y = 320
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUTPUT / "location-pin.png")
bpy.ops.wm.save_as_mainfile(filepath=str(ART / "location-pin.blend"), compress=True)
bpy.ops.render.render(write_still=True)
print(f"Metabole renders written to {OUTPUT}")
