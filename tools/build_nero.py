import bpy, math, os, sys
from mathutils import Vector

# LAST ZONE / NERO - original first-pass game character blockout.
# Blender background build: blender -b --python tools/build_nero.py -- --output characters/nero/nero.glb

def arg_value(flag, default):
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    return args[args.index(flag)+1] if flag in args else default

out_path=os.path.abspath(arg_value("--output","characters/nero/nero.glb"))
os.makedirs(os.path.dirname(out_path),exist_ok=True)
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)

def mat(name,color,metal=0.0,rough=0.65):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1)
    m.use_nodes=True; bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(*color,1)
    bs.inputs["Metallic"].default_value=metal
    bs.inputs["Roughness"].default_value=rough
    return m

skin=mat("NERO | skin",(.43,.25,.17))
black=mat("NERO | tactical graphite",(.035,.05,.06),.15)
armor=mat("NERO | armor charcoal",(.075,.095,.10),.35)
fabric=mat("NERO | field uniform",(.16,.19,.17))
olive=mat("NERO | webbing olive",(.25,.23,.15))
boots=mat("NERO | boots",(.025,.03,.03))
visor=mat("NERO | visor",(.025,.12,.13),.65,.22)
glow=mat("NERO | green status lights",(.02,.65,.28),.25,.3)
metal=mat("NERO | gunmetal",(.10,.12,.13),.8,.28)

def uv(name,loc,scale,material,seg=24,rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings, location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    for p in o.data.polygons:p.use_smooth=True
    return o
def cube(name,loc,scale,material,bevel=.06):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o=bpy.context.object; o.name=name; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(material)
    if bevel:
        mod=o.modifiers.new("Soft manufactured edges","BEVEL"); mod.width=bevel; mod.segments=3
        o.modifiers.new("Weighted corner normals","WEIGHTED_NORMAL")
    return o
def cyl(name,loc,radius,depth,material,rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=loc, rotation=rotation)
    o=bpy.context.object; o.name=name; o.data.materials.append(material)
    mod=o.modifiers.new("Edge bevel","BEVEL"); mod.width=.025; mod.segments=2
    o.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
    return o

# Feet and articulated legs
for side,label in [(-1,"L"),(1,"R")]:
    x=side*.16
    uv("NERO_"+label+"_boot",(x,-.06,.12),(.14,.28,.13),boots)
    cube("NERO_"+label+"_ankle",(x,0,.34),(.17,.19,.25),fabric)
    uv("NERO_"+label+"_shin",(x,0,.59),(.14,.16,.31),fabric)
    cube("NERO_"+label+"_knee_pad",(x,-.145,.79),(.20,.075,.19),armor)
    uv("NERO_"+label+"_thigh",(x,0,1.04),(.19,.20,.34),fabric)
    cube("NERO_"+label+"_thigh_pouch",(x*1.55,-.18,1.05),(.12,.09,.20),olive)
# pelvis and torso
cube("NERO_pelvis",(0,0,1.35),(.48,.32,.27),fabric)
uv("NERO_torso",(0,0,1.72),(.39,.25,.48),fabric)
# chest armor / vest
cube("NERO_plate_carrier",(0,-.205,1.77),(.57,.14,.48),armor,.09)
cube("NERO_upper_chest_plate",(0,-.292,1.91),(.39,.045,.20),metal,.035)
for x in [-.19,.19]:
    cube("NERO_magazine_pouch",(x,-.30,1.66),(.13,.09,.19),olive,.025)
    cube("NERO_shoulder_guard",(x*1.65,0,2.04),(.22,.27,.20),armor,.07)
# belt
cube("NERO_belt",(0,-.01,1.48),(.54,.37,.09),black,.025)
cube("NERO_buckle",(0,-.205,1.48),(.11,.035,.07),metal,.01)
# neck, head, helmet
cyl("NERO_neck",(0,0,2.16),.105,.16,skin)
uv("NERO_head",(0,-.005,2.36),(.19,.18,.25),skin)
uv("NERO_helmet_shell",(0,.005,2.52),(.225,.21,.16),armor)
cube("NERO_helmet_front_mount",(0,-.205,2.50),(.12,.035,.07),metal,.02)
uv("NERO_visor",(0,-.17,2.39),(.155,.045,.065),visor)
for x in [-.18,.18]:
    cyl("NERO_helmet_side_rail",(x,0,2.49),.035,.20,metal,(math.pi/2,0,0))
# arms angled down, shoulder/elbow/forearm, gloves
for side,label in [(-1,"L"),(1,"R")]:
    x=side*.48
    uv("NERO_"+label+"_upper_arm",(x,-.005,1.82),(.14,.15,.29),fabric)
    uv("NERO_"+label+"_elbow",(side*.55,-.015,1.56),(.13,.14,.13),armor)
    uv("NERO_"+label+"_forearm",(side*.59,-.045,1.38),(.12,.14,.24),fabric)
    cube("NERO_"+label+"_wrist_guard",(side*.61,-.17,1.25),(.16,.08,.10),armor)
    uv("NERO_"+label+"_glove",(side*.62,-.06,1.17),(.12,.12,.13),black)
# radio, backpack and readable green details
cube("NERO_backpack",(0,.25,1.78),(.40,.20,.48),black,.08)
cube("NERO_backpack_top",(0,.26,2.02),(.28,.18,.12),olive,.04)
for x in [-.20,.20]:
    uv("NERO_green_status",(x,-.31,1.92),(.025,.018,.025),glow,12,8)
# small shoulder insignia
cube("NERO_left_arm_patch",(-.57,-.13,1.84),(.10,.025,.10),glow,.015)

# Ground origin, camera-friendly forward is -Y. Apply transforms and export selected mesh objects.
bpy.ops.object.select_all(action="SELECT")
for o in bpy.context.selected_objects:
    if o.type=="MESH":
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=out_path, export_format="GLB", use_selection=True, export_apply=True)
print("NERO GLB exported:",out_path)
