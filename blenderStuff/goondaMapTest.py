import bpy
import bmesh

import numpy
from PIL import Image

fPath = "/home/adam/stuff/goondaMaps/"
testImage = fPath+"austinTestSmallest.png"


def get_image(image_path):
    # Get a numpy array of an image so that one can access values[x][y].
    image = Image.open(image_path, "r")
    width, height = image.size
    pixel_values = list(image.getdata())
    if image.mode == "RGB":
        channels = 3
    elif image.mode == "L":
        channels = 1
    elif image.mode == "RGBA":
        channels = 4
    else:
        print("Unknown mode: %s" % image.mode)
        return None
    pixel_values = numpy.array(pixel_values).reshape((height, width, channels))
    return pixel_values
    
    
def newMaterial(id):

    mat = bpy.data.materials.get(id)

    if mat is None:
        mat = bpy.data.materials.new(name=id)

    mat.use_nodes = True

    if mat.node_tree:
        mat.node_tree.links.clear()
        mat.node_tree.nodes.clear()

    return mat
    
    
def new_shader(id, type, r, g, b):

    mat = newMaterial(id)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    output = nodes.new(type='ShaderNodeOutputMaterial')

    if type == "diffuse":
        shader = nodes.new(type='ShaderNodeBsdfDiffuse')
        nodes["Diffuse BSDF"].inputs[0].default_value = (r, g, b, 1)

    elif type == "emission":
        shader = nodes.new(type='ShaderNodeEmission')
        nodes["Emission"].inputs[0].default_value = (r, g, b, 1)
        nodes["Emission"].inputs[1].default_value = 1

    elif type == "glossy":
        shader = nodes.new(type='ShaderNodeBsdfGlossy')
        nodes["Glossy BSDF"].inputs[0].default_value = (r, g, b, 1)
        nodes["Glossy BSDF"].inputs[1].default_value = 0

    links.new(shader.outputs[0], output.inputs[0])

    return mat


def make_sphere(material, x, y, z):
    # Create an empty mesh and the object.
    mesh = bpy.data.meshes.new('Basic_Sphere')
    basic_sphere = bpy.data.objects.new("Basic_Sphere", mesh)

    # Add the object into the scene.
    bpy.context.collection.objects.link(basic_sphere)

    # Select the newly created object
    bpy.context.view_layer.objects.active = basic_sphere
    basic_sphere.select_set(True)

    # Construct the bmesh sphere and assign it to the blender mesh.
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=4, v_segments=2, radius=0.1)
    bm.to_mesh(mesh)
    bm.free()

    # bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.ops.object.shade_smooth()
    bpy.context.active_object.data.materials.append(material)
    bpy.context.active_object.location = (x, y, z)
    
    
def make_sphere_image(path):
    data = get_image(path).astype(float) / 255
    #print(data.shape)
    #x = 8
    #y = 8
    #material = new_shader("test_"+str(x)+"_"+str(y), "diffuse", data[x][y][0], data[x][y][1], data[x][y][2])
    #make_sphere(material, x, y, 0)
    for x in range(data.shape[0]):
        for y in range(data.shape[1]):
            material = new_shader("test_"+str(x)+"_"+str(y), "diffuse", data[x][y][0], data[x][y][1], data[x][y][2])
            make_sphere(material, y/10.0, (data.shape[0]-x)/10.0, 0)
    