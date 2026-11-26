import bpy, os, zipfile, json, struct, math, shutil
from mathutils import Vector

ROOT = os.path.abspath("nero_repair_work")
SRC_ZIP = os.path.abspath("Nero 1.zip")
OUT_ZIP = os.path.abspath("Nero 1 REPAIRED.zip")
if os.path.exists(ROOT): shutil.rmtree(ROOT)
os.makedirs(ROOT, exist_ok=True)
with zipfile.ZipFile(SRC_ZIP) as z: z.extractall(ROOT)
asset_root = os.path.join(ROOT, "NERO_FINAL")
if not os.path.isdir(asset_root):
    raise RuntimeError("Expected NERO_FINAL folder was not found in Nero 1.zip")

# Repair invalid GLB JSON chunk padding: GLB requires JSON padding bytes to be spaces.
repair_notes = []
for folder, _, files in os.walk(asset_root):
    for name in files:
        if not name.lower().endswith(".glb"): continue
        path = os.path.join(folder, name)
        data = bytearray(open(path, "rb").read())
        if len(data) < 20 or data[:4] != b"glTF":
            raise RuntimeError("Invalid GLB header: " + path)
        version, total = struct.unpack_from("<II", data, 4)
        if version != 2 or total != len(data):
            raise RuntimeError("Invalid GLB version/length: " + path)
        chunk_len, chunk_type = struct.unpack_from("<II", data, 12)
        if chunk_type != 0x4E4F534A or 20 + chunk_len > len(data):
            raise RuntimeError("Missing/invalid GLB JSON chunk: " + path)
        chunk = bytes(data[20:20+chunk_len])
        decoded = chunk.decode("utf-8")
        _, consumed = json.JSONDecoder().raw_decode(decoded)
        padding = decoded[consumed:]
        if any(ch != " " for ch in padding):
            fixed = decoded[:consumed] + (" " * (len(decoded)-consumed))
            data[20:20+chunk_len] = fixed.encode("utf-8")
            open(path, "wb").write(data)
            repair_notes.append("Fixed JSON padding: " + os.path.relpath(path, asset_root))
        json.loads(bytes(data[20:20+chunk_len]).decode("utf-8"))
repair_notes.append("All GLB JSON chunks parse and use valid space padding.")

# Rebuild character FBX from the authoritative, imported GLB so the old duplicate FBX is not retained.
bpy.ops.wm.read_factory_settings(use_empty=True)
main_glb = os.path.join(asset_root, "Models", "NERO_Final.glb")
bpy.ops.import_scene.gltf(filepath=main_glb)
character_objects = list(bpy.context.scene.objects)
character_meshes = [o for o in character_objects if o.type == "MESH"]
character_rigs = [o for o in character_objects if o.type == "ARMATURE"]
if not character_meshes or not character_rigs:
    raise RuntimeError("Main NERO GLB did not import with mesh and armature.")
bpy.ops.object.select_all(action="DESELECT")
for obj in character_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = character_rigs[0]
fbx_path = os.path.join(asset_root, "Models", "NERO_Final.fbx")
bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True, object_types={'ARMATURE','MESH'}, add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True, path_mode='COPY', embed_textures=True)
repair_notes.append("Re-exported NERO_Final.fbx from the imported rigged GLB using Blender.")

# Build a distinct, original, low-poly tactical rifle mesh. It is a separate weapon asset,
# designed to attach to the NERO weapon socket in Unity; it is not a copy of the character.
bpy.ops.wm.read_factory_settings(use_empty=True)
parts = []
def material(name, color, metallic=0.0, roughness=0.55):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1.0)
    bs.inputs["Metallic"].default_value = metallic
    bs.inputs["Roughness"].default_value = roughness
    return m
mat_body = material("Rifle_Matte_Graphite", (0.055,0.065,0.075), 0.55, 0.42)
mat_metal = material("Rifle_Black_Steel", (0.018,0.022,0.027), 0.82, 0.3)
mat_poly = material("Rifle_Dark_Polymer", (0.095,0.105,0.11), 0.08, 0.72)
mat_accent = material("Rifle_Control_Detail", (0.32,0.20,0.075), 0.5, 0.38)
def cube(name, loc, scale, mat, bevel=0.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o=bpy.context.object; o.name=name; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod=o.modifiers.new("Machined_Edges","BEVEL"); mod.width=bevel; mod.segments=2
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.materials.append(mat); parts.append(o); return o
def cyl(name, loc, radius, depth, mat, vertices=16, axis='X'):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    o=bpy.context.object; o.name=name
    if axis=='X': o.rotation_euler[1]=math.radians(90)
    elif axis=='Y': o.rotation_euler[0]=math.radians(90)
    o.data.materials.append(mat); parts.append(o); return o

# X axis is the weapon's length: stock at rear (-X), muzzle at front (+X).
cube("Receiver_Main", (0.00,0,0.02), (0.46,0.16,0.19), mat_body, 0.035)
cube("Upper_Receiver", (0.02,0,0.135), (0.50,0.145,0.065), mat_body, 0.018)
cube("Handguard", (0.38,0,0.045), (0.42,0.145,0.145), mat_poly, 0.025)
cyl("Barrel", (0.72,0,0.045), 0.031, 0.48, mat_metal, 20)
cyl("Muzzle_Brake", (0.98,0,0.045), 0.052, 0.10, mat_metal, 16)
cube("Collapsible_Stock", (-0.43,0,0.035), (0.42,0.105,0.13), mat_poly, 0.035)
cube("Stock_Buttpad", (-0.65,0,0.035), (0.055,0.13,0.16), mat_metal, 0.018)
cube("Pistol_Grip", (-0.02,0,-0.19), (0.12,0.105,0.30), mat_poly, 0.025)
cube("Magazine", (0.16,0,-0.20), (0.13,0.105,0.32), mat_body, 0.025)
cube("Magazine_Base", (0.16,0,-0.365), (0.15,0.12,0.035), mat_metal, 0.01)
cube("Top_Picatinny_Rail", (0.16,0,0.19), (0.64,0.055,0.035), mat_metal, 0.006)
cube("Optic_Sight_Base", (0.02,0,0.235), (0.14,0.075,0.055), mat_metal, 0.008)
cube("Optic_Sight", (0.02,0,0.29), (0.10,0.06,0.08), mat_poly, 0.012)
cube("Front_Sight", (0.57,0,0.235), (0.045,0.05,0.10), mat_metal, 0.006)
cube("Side_Rail_Left", (0.39,-0.083,0.045), (0.32,0.018,0.045), mat_metal, 0.005)
cube("Side_Rail_Right", (0.39,0.083,0.045), (0.32,0.018,0.045), mat_metal, 0.005)
cube("Trigger_Guard_Top", (-0.02,0,-0.085), (0.16,0.025,0.025), mat_metal, 0.008)
cube("Trigger_Guard_Front", (0.06,0,-0.12), (0.025,0.025,0.07), mat_metal, 0.008)
cube("Trigger_Guard_Rear", (-0.10,0,-0.12), (0.025,0.025,0.07), mat_metal, 0.008)
cube("Selector_Switch", (-0.10,-0.095,0.06), (0.07,0.025,0.025), mat_accent, 0.006)
cube("Bolt_Handle", (0.13,-0.105,0.06), (0.10,0.035,0.035), mat_metal, 0.008)
for i in range(5):
    cube("Handguard_Slot_%02d"%i, (0.26+i*0.055,-0.078,0.04), (0.025,0.009,0.065), mat_metal, 0.003)
# Join to a single clean mesh while preserving material slots.
bpy.ops.object.select_all(action='DESELECT')
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.join()
rifle=bpy.context.object; rifle.name="LAST_ZONE_Rifle_Assault_01"
# Origin at receiver centre; all geometry stays in one mesh for simple socket attachment.
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
rifle_path_glb=os.path.join(asset_root,"Weapons","Rifle_Model.glb")
rifle_path_fbx=os.path.join(asset_root,"Weapons","Rifle_Model.fbx")
os.makedirs(os.path.dirname(rifle_path_glb),exist_ok=True)
bpy.ops.export_scene.gltf(filepath=rifle_path_glb, export_format='GLB', use_selection=True, export_apply=True)
bpy.ops.export_scene.fbx(filepath=rifle_path_fbx, use_selection=True, object_types={'MESH'}, add_leaf_bones=False, path_mode='AUTO')
repair_notes.append("Replaced duplicate Rifle_Model files with a separate low-poly tactical rifle mesh (receiver, barrel, muzzle, stock, grip, magazine, rail and sights).")
repair_notes.append("Rifle is a standalone mesh; attach it to Weapon_Attach_R_Hand / Weapon_Attach_L_Hand in Unity and align using the game's weapon socket transforms.")

# Update documentation honestly; do not claim Unity, deformation, or mobile performance validation.
docs=os.path.join(asset_root,"Documentation"); os.makedirs(docs,exist_ok=True)
open(os.path.join(docs,"Blender_Test_Report.txt"),"w").write(
"BLENDER REPAIR / VALIDATION\n"
"- Main NERO GLB imported successfully with mesh, armature and animation actions.\n"
"- GLB JSON chunk padding repaired to valid space padding where required.\n"
"- Main character FBX re-exported from the imported GLB.\n"
"- Separate tactical rifle mesh generated and exported as GLB and FBX.\n"
"- LOD0/LOD1/LOD2 are preserved as distinct GLB assets; import must be revalidated in the follow-up workflow.\n"
"- Unity runtime, retargeting, in-game ADS alignment, deformation quality and Android performance are NOT certified by this Blender batch.\n")
open(os.path.join(docs,"Known_Issues.txt"),"w").write(
"REMAINING QA ITEMS (NOT CLAIMED COMPLETE)\n"
"- Unity import and runtime validation still required.\n"
"- Test every animation in motion and inspect deformation/clipping in Blender/Unity.\n"
"- Verify weapon socket transforms, hand grip alignment, ADS camera alignment and muzzle orientation in the game.\n"
"- Tune LOD screen-size thresholds and verify visual transitions in Unity.\n"
"- Inspect PBR texture channel packing, UVs, normals and material appearance under game lighting.\n"
"- Validate hitboxes, collision capsule, SFX/VFX sockets and Android draw calls/performance in the game build.\n"
"- Face is stylized low-poly; AAA sculpt/detail pass is outside this automated repair.\n")
open(os.path.join(docs,"Rifle_Integration.txt"),"w").write(
"RIFLE MODEL: LAST_ZONE_Rifle_Assault_01\n"
"Files: Weapons/Rifle_Model.glb and Weapons/Rifle_Model.fbx\n"
"Standalone low-poly tactical rifle mesh with separate material slots.\n"
"Attach to NERO skeleton Weapon_Attach_R_Hand. Use Weapon_Attach_L_Hand for left-hand support alignment.\n"
"Unity must set the final local position/rotation/scale per the game's weapon socket convention; validate ADS and muzzle direction in-game.\n")

# Validate all GLB JSON headers after edits and ensure the rifle is no longer a duplicate of the character.
for folder, _, files in os.walk(asset_root):
    for name in files:
        if name.lower().endswith(".glb"):
            p=os.path.join(folder,name); b=open(p,"rb").read()
            ln,typ=struct.unpack_from("<II",b,12)
            if typ!=0x4E4F534A: raise RuntimeError("Invalid JSON chunk after repair: "+p)
            json.loads(b[20:20+ln].decode("utf-8"))
if open(main_glb,"rb").read()==open(rifle_path_glb,"rb").read():
    raise RuntimeError("Rifle GLB is still identical to the character GLB.")
repair_notes.append("Post-repair GLB JSON validation: PASS.")
open(os.path.join(docs,"Repair_Notes.txt"),"w").write("\n".join(repair_notes)+"\n")

# Deterministic archive creation; keep source folder layout at archive root.
if os.path.exists(OUT_ZIP): os.remove(OUT_ZIP)
with zipfile.ZipFile(OUT_ZIP,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for folder, dirs, files in os.walk(asset_root):
        dirs.sort()
        for name in sorted(files):
            p=os.path.join(folder,name)
            arc=os.path.relpath(p,ROOT)
            z.write(p,arc)
print("\n".join(repair_notes))
print("REPAIRED ZIP:", OUT_ZIP, os.path.getsize(OUT_ZIP))
