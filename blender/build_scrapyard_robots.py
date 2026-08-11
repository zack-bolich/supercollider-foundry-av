import bpy
import math
import os
import sys

OUT = os.path.abspath(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else os.path.abspath('assets')
os.makedirs(OUT, exist_ok=True)


def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
        pass


def mat(name, color, metallic=0.7, rough=0.5, emission=None):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = rough
    if emission:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1)
        bsdf.inputs['Emission Strength'].default_value = 5.0
    return m


def cube(name, loc, scale, material, parent=None, bevel=0.05):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = o.modifiers.new('WeldedEdges', 'BEVEL'); mod.width = bevel; mod.segments = 1
    o.data.materials.append(material)
    if parent:
        world = o.matrix_world.copy(); o.parent = parent; o.matrix_world = world
    return o


def cyl(name, loc, radius, depth, material, parent=None, rot=(math.pi/2,0,0), vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name; o.data.materials.append(material)
    if parent:
        world = o.matrix_world.copy(); o.parent = parent; o.matrix_world = world
    return o


def empty(name, loc=(0,0,0), parent=None):
    o=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(o); o.location=loc
    if parent:
        world = o.matrix_world.copy(); o.parent=parent; o.matrix_world=world
    return o


def add_robot(kind):
    clear()
    rust=mat(f'{kind}_Rust',(0.23,0.055,0.025),0.86,0.46)
    iron=mat(f'{kind}_Iron',(0.105,0.12,0.115),0.92,0.32)
    dark=mat(f'{kind}_BlackIron',(0.025,0.03,0.028),0.95,0.58)
    hot=mat(f'{kind}_Furnace',(0.12,0.018,0.006),0.5,0.25,(1.0,0.12 if kind=='Butcher' else 0.38,0.01))
    accent=mat(f'{kind}_Markings',((0.55,0.16,0.025) if kind=='Butcher' else (0.08,0.25,0.30)),0.72,0.4)
    root=empty(f'{kind}_Root')
    hips=empty(f'{kind}_Hips',(0,0,1.65),root)
    cube(f'{kind}_Pelvis',(0,0,1.65),(.72,.48,.35),dark,hips,.09)
    torso=empty(f'{kind}_Torso',(0,0,1.9),root)
    cube(f'{kind}_Chest',(0,0,2.45),(.92,.48,.78),rust,torso,.12)
    cube(f'{kind}_ChestPlate',(0,-.52,2.5),(.65,.10,.54),iron,torso,.04)
    cyl(f'{kind}_Core',(0,-.64,2.55),.25,.15,hot,torso,(math.pi/2,0,0),16)
    for x in (-.57,0,.57): cube(f'{kind}_Rib_{x}',(x,-.66,2.55),(.06,.05,.45),accent,torso,.01)
    head=empty(f'{kind}_HeadPivot',(0,0,3.25),root)
    cube(f'{kind}_Head',(0,-.03,3.30),(.42,.40,.31),iron,head,.07)
    cube(f'{kind}_Jaw',(0,-.43,3.16),(.34,.12,.10),dark,head,.02)
    cube(f'{kind}_Eye',((-.14 if kind=='Butcher' else .14),-.46,3.36),(.10,.04,.055),hot,head,.01)
    cyl(f'{kind}_ExhaustL',(-.55,.25,3.23),.10,.9,dark,torso,(0,0,0),10)
    cyl(f'{kind}_ExhaustR',(.55,.25,3.23),.10,.9,dark,torso,(0,0,0),10)
    # Legs are independent named pivots for stomps.
    for side,x in [('L',-.52),('R',.52)]:
        leg=empty(f'{kind}_{side}LegPivot',(x,0,1.45),root)
        cube(f'{kind}_{side}Thigh',(x,0,1.05),(.25,.30,.55),iron,leg,.06)
        cyl(f'{kind}_{side}Knee',(x,-.02,.52),.19,.68,accent,leg,(math.pi/2,0,0),12)
        cube(f'{kind}_{side}Shin',(x,0,.38),(.28,.28,.42),rust,leg,.05)
        cube(f'{kind}_{side}Foot',(x,-.25,.06),(.40,.60,.14),dark,leg,.04)
    # Articulated shoulders. The outer robot arm is the signature weapon.
    for side,sx in [('L',-1),('R',1)]:
        pivot=empty(f'{kind}_{side}ArmPivot',(sx*.88,0,2.88),root)
        cyl(f'{kind}_{side}Shoulder',(sx*.88,0,2.88),.28,.62,accent,pivot,(0,math.pi/2,0),12)
        cube(f'{kind}_{side}UpperArm',(sx*1.27,0,2.62),(.48,.24,.20),iron,pivot,.06)
        cyl(f'{kind}_{side}Elbow',(sx*1.70,0,2.43),.18,.45,dark,pivot,(0,math.pi/2,0),12)
        if (kind=='Butcher' and side=='R'):
            cube(f'{kind}_HammerHandle',(2.35,0,2.25),(.78,.10,.10),dark,pivot,.03)
            cube(f'{kind}_HammerHead',(3.10,0,2.25),(.32,.46,.58),iron,pivot,.08)
            cube(f'{kind}_HammerFace',(3.43,0,2.25),(.11,.50,.48),accent,pivot,.02)
        elif (kind=='Ripper' and side=='L'):
            cube(f'{kind}_SawArm',(-2.25,0,2.30),(.72,.18,.14),dark,pivot,.03)
            bpy.ops.mesh.primitive_torus_add(major_radius=.44,minor_radius=.10,major_segments=16,minor_segments=6,location=(-3.0,0,2.3),rotation=(math.pi/2,0,0))
            saw=bpy.context.object;saw.name=f'{kind}_Saw';saw.data.materials.append(accent);saw.parent=pivot
            cyl(f'{kind}_SawHub',(-3.0,0,2.3),.15,.20,hot,pivot,(math.pi/2,0,0),12)
        else:
            cube(f'{kind}_{side}ClawForearm',(sx*2.12,0,2.30),(.46,.20,.17),rust,pivot,.05)
            cube(f'{kind}_{side}ClawA',(sx*2.62,-.14,2.38),(.30,.08,.08),iron,pivot,.02)
            cube(f'{kind}_{side}ClawB',(sx*2.62,.14,2.18),(.30,.08,.08),iron,pivot,.02)
    # Back flywheel.
    bpy.ops.mesh.primitive_torus_add(major_radius=.58,minor_radius=.12,major_segments=18,minor_segments=6,location=(0,.53,2.45),rotation=(math.pi/2,0,0))
    wheel=bpy.context.object;wheel.name=f'{kind}_Flywheel';wheel.data.materials.append(accent);wheel.parent=root
    for i in range(6):
        a=i*math.pi/3
        cube(f'{kind}_Spoke{i}',(math.cos(a)*.28,.56,2.45+math.sin(a)*.28),(.42,.04,.045),iron,root,.01).rotation_euler[1]=-a
    # Triangular armor spikes.
    for x in (-.75,.75):
        bpy.ops.mesh.primitive_cone_add(vertices=4,radius1=.22,radius2=0,depth=.55,location=(x,.15,3.05),rotation=(0,0,0))
        sp=bpy.context.object;sp.name=f'{kind}_ShoulderSpike';sp.data.materials.append(iron);sp.parent=root
    return root


def export_robot(kind, filename):
    root=add_robot(kind)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,filename),export_format='GLB',use_selection=True,export_apply=True,export_yup=True)
    print('EXPORTED',os.path.join(OUT,filename))

export_robot('Butcher','robot-butcher.glb')
export_robot('Ripper','robot-ripper.glb')
