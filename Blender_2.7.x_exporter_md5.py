# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

#"""
#Name: 'idTech 4 (.md5)...'
#Blender: 266
#Group: 'Export'
#Tooltip: 'Export idTech 4 MD5'
#
#"""

# v1.1.0 - Gert De Roost adds bones export filtering and bone reparenting
# v1.0.6 - CodeManX fixed whatever was there left to fix :)
# v1.0.5 - Mike Campagnini fixed previous fix
# v1.0.4 - CodeManX fixed GUI for Blender 2.66
# v1.0.3 - Mike Campagnini made scale work again, even for baseframe mesh;
# v1.0.2 - motorsep's fugly hack to flip orientation values for baseframe {}; otherwise idTech 4 ragdolls break;

bl_info = { # changed from bl_addon_info in 2.57 -mikshaw
			"name": "Export idTech4 (.md5) by CodemanX 09/12/2013",
			"author": "Paul Zirkle aka Keless, credit to der_ton",
			"version": (1, 1, 0),
			"blender": (2, 65, 4),
			"location": "File > Export > Skeletal Mesh/Animation Data (.md5mesh/.md5anim)",
			"description": "Export idTech4 (.md5)",
			"warning": "",
			"wiki_url": "http://wiki.blender.org/index.php/Extensions:2.5/Py/"\
						"Scripts/File_I-O/idTech4_md5",
			"tracker_url": "http://www.katsbits.com/smforum/index.php?topic=167.0",
			"category": "Import-Export" } # changed from "Import/Export" -katsbits

import bpy, struct, math, os, time, sys, mathutils
from bpy.app.handlers import persistent

scale = 1.0

# Auto-enable fake user to rescue unused actions
@persistent
def fakeuser_for_actions(scene):
	for action in bpy.data.actions:
		action.use_fake_user = True

#MATH UTILTY

# Vector.cross(other)
def vector_crossproduct(v1, v2):
	return [
		v1[1] * v2[2] - v1[2] * v2[1],
		v1[2] * v2[0] - v1[0] * v2[2],
		v1[0] * v2[1] - v1[1] * v2[0],
		]

# Matrix4 * Vector3
def point_by_matrix(p, m):
	#print( str(type( p )) + " " + str(type(m)) )
	return [p[0] * m[0][0] + p[1] * m[1][0] + p[2] * m[2][0] + m[3][0],
			p[0] * m[0][1] + p[1] * m[1][1] + p[2] * m[2][1] + m[3][1],
			p[0] * m[0][2] + p[1] * m[1][2] + p[2] * m[2][2] + m[3][2]]

# Matrix3 * Vector3
def vector_by_matrix(p, m):
	return [p[0] * m.col[0][0] + p[1] * m.col[1][0] + p[2] * m.col[2][0],
			p[0] * m.col[0][1] + p[1] * m.col[1][1] + p[2] * m.col[2][1],
			p[0] * m.col[0][2] + p[1] * m.col[1][2] + p[2] * m.col[2][2]]

# Vector.normalized()
# or
# if Vector.length == 0.0:
#	 Vector((1,0,0))
# else:
#	 Vector.normalized()
def vector_normalize(v):
	l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
	try:
		return v[0] / l, v[1] / l, v[2] / l
	except:
		return 1, 0, 0

def matrix2quaternion(m):
	s = math.sqrt(abs(m.col[0][0] + m.col[1][1] + m.col[2][2] + m.col[3][3]))
	if s == 0.0:
		x = abs(m.col[2][1] - m.col[1][2])
		y = abs(m.col[0][2] - m.col[2][0])
		z = abs(m.col[1][0] - m.col[0][1])
		if	 (x >= y) and (x >= z): return 1.0, 0.0, 0.0, 0.0
		elif (y >= x) and (y >= z): return 0.0, 1.0, 0.0, 0.0
		else:						return 0.0, 0.0, 1.0, 0.0
	return quaternion_normalize([
		-(m.col[2][1] - m.col[1][2]) / (2.0 * s),
		-(m.col[0][2] - m.col[2][0]) / (2.0 * s),
		-(m.col[1][0] - m.col[0][1]) / (2.0 * s),
		0.5 * s,
		])

def matrix_invert(m):
	det = (m.col[0][0] * (m.col[1][1] * m.col[2][2] - m.col[2][1] * m.col[1][2])
		   - m.col[1][0] * (m.col[0][1] * m.col[2][2] - m.col[2][1] * m.col[0][2])
		   + m.col[2][0] * (m.col[0][1] * m.col[1][2] - m.col[1][1] * m.col[0][2]))
	if det == 0.0: return None
	det = 1.0 / det
	r = [ [
			  det * (m.col[1][1] * m.col[2][2] - m.col[2][1] * m.col[1][2]),
			  - det * (m.col[0][1] * m.col[2][2] - m.col[2][1] * m.col[0][2]),
			  det * (m.col[0][1] * m.col[1][2] - m.col[1][1] * m.col[0][2]),
			  0.0,
			  ], [
			  - det * (m.col[1][0] * m.col[2][2] - m.col[2][0] * m.col[1][2]),
			  det * (m.col[0][0] * m.col[2][2] - m.col[2][0] * m.col[0][2]),
			  - det * (m.col[0][0] * m.col[1][2] - m.col[1][0] * m.col[0][2]),
			  0.0
		  ], [
			  det * (m.col[1][0] * m.col[2][1] - m.col[2][0] * m.col[1][1]),
			  - det * (m.col[0][0] * m.col[2][1] - m.col[2][0] * m.col[0][1]),
			  det * (m.col[0][0] * m.col[1][1] - m.col[1][0] * m.col[0][1]),
			  0.0,
			  ] ]
	r.append([
		-(m.col[3][0] * r[0][0] + m.col[3][1] * r[1][0] + m.col[3][2] * r[2][0]),
		-(m.col[3][0] * r[0][1] + m.col[3][1] * r[1][1] + m.col[3][2] * r[2][1]),
		-(m.col[3][0] * r[0][2] + m.col[3][1] * r[1][2] + m.col[3][2] * r[2][2]),
		1.0,
		])
	return r

# Quaternion.normalized()
def quaternion_normalize(q):
	l = math.sqrt(q.col[0] * q.col[0] + q.col[1] * q.col[1] + q.col[2] * q.col[2] + q.col[3] * q.col[3])
	return q.col[0] / l, q.col[1] / l, q.col[2] / l, q.col[3] / l

#shader material
class Material:
	name = "" #string
	def __init__(self, textureFileName):
		self.name = textureFileName

	def to_md5mesh(self):
		return self.name;

#the 'Model' class, contains all submeshes
class Mesh:
	name = "" #string
	submeshes = [] #array of SubMesh
	next_submesh_id = 0 #int

	def __init__(self, name):
		self.name = name
		self.submeshes = []

		self.next_submesh_id = 0

	def to_md5mesh(self):
		meshnumber = 0
		buf = ""
		for submesh in self.submeshes:
			buf=buf + "mesh {\n"
			#buf=buf + "mesh {\n\t// meshes: " + submesh.name + "\n"  # used for Sauerbraten -mikshaw
			meshnumber += 1
			buf=buf + submesh.to_md5mesh()
			buf=buf + "}\n\n"

		return buf

#submeshes reference a parent mesh
class SubMesh:
	def __init__(self, mesh, material):
		self.material = material
		self.vertices = []
		self.faces = []
		self.nb_lodsteps = 0
		self.springs = []
		self.weights = []

		self.next_vertex_id = 0
		self.next_weight_id = 0

		self.mesh = mesh
		self.name = mesh.name
		self.id = mesh.next_submesh_id
		mesh.next_submesh_id += 1
		mesh.submeshes.append(self)

	def bindtomesh (self, mesh):
		# HACK: this is needed for md5 output, for the time being...
		# appending this submesh to the specified mesh, disconnecting it from the original one
		self.mesh.submeshes.remove(self)
		self.mesh = mesh
		self.id = mesh.next_submesh_id
		mesh.next_submesh_id += 1
		mesh.submeshes.append(self)

	def generateweights(self):
		self.weights = []
		self.next_weight_id = 0
		for vert in self.vertices:
			vert.generateweights()

	def reportdoublefaces(self):
		for face in self.faces:
			for face2 in self.faces:
				if not face == face2:
					if (not face.vertex1==face2.vertex1) and (not face.vertex1==face2.vertex2) and (not face.vertex1==face2.vertex3):
						return
					if (not face.vertex2==face2.vertex1) and (not face.vertex2==face2.vertex2) and (not face.vertex2==face2.vertex3):
						return
					if (not face.vertex3==face2.vertex1) and (not face.vertex3==face2.vertex2) and (not face.vertex3==face2.vertex3):
						return
					print('doubleface! %s %s' % (face, face2))

	def to_md5mesh(self):
		self.generateweights()

		self.reportdoublefaces()

		buf="\tshader \"%s\"\n\n" % (self.material.to_md5mesh())
		if len(self.weights) == 0:
			buf=buf + "\tnumverts 0\n"
			buf=buf + "\n\tnumtris 0\n"
			buf=buf + "\n\tnumweights 0\n"
			return buf

		# output vertices
		buf=buf + "\tnumverts %i\n" % (len(self.vertices))
		vnumber = 0
		for vert in self.vertices:
			buf = buf + "\tvert %i %s\n" % (vnumber, vert.to_md5mesh())
			vnumber += 1

		# output faces
		buf = buf + "\n\tnumtris %i\n" % (len(self.faces))
		facenumber = 0
		for face in self.faces:
			buf = buf + "\ttri %i %s\n" % (facenumber, face.to_md5mesh())
			facenumber += 1

		# output weights
		buf=buf + "\n\tnumweights %i\n" % (len(self.weights))
		weightnumber = 0
		for weight in self.weights:
			buf = buf + "\tweight %i %s\n" % (weightnumber, weight.to_md5mesh())
			weightnumber += 1

		return buf

#vertex class contains and outputs 'verts' but also generates 'weights' data
class Vertex:
	def __init__(self, submesh, loc, normal):
		self.loc = loc
		self.normal = normal
		self.collapse_to = None
		self.face_collapse_count = 0
		self.maps = []
		self.influences = []
		self.weights = []
		self.weight = None
		self.firstweightindx = 0
		self.cloned_from = None
		self.clones = []

		self.submesh = submesh
		self.id = submesh.next_vertex_id
		submesh.next_vertex_id += 1
		submesh.vertices.append(self)

	def generateweights(self):
		self.firstweightindx = self.submesh.next_weight_id

		#dgis: The weight are normalized here
		sum = 0.0
		for influence in self.influences: sum += influence.weight

		for influence in self.influences:
			if sum != 0:
				influence.weight = influence.weight / sum

		for influence in self.influences:
			weightindx = self.submesh.next_weight_id
			self.submesh.next_weight_id += 1
			newweight = Weight(influence.bone, influence.weight, self, weightindx, self.loc[0], self.loc[1], self.loc[2])
			self.submesh.weights.append(newweight)
			self.weights.append(newweight)

	def to_md5mesh(self):
		if self.maps:
			buf = self.maps[0].to_md5mesh()
		else:
			buf = "( %f %f )" % (self.loc[0], self.loc[1])
		buf = buf + " %i %i" % (self.firstweightindx, len(self.influences))
		return buf

#texture coordinate map
class Map:
	def __init__(self, u, v):
		self.u = u
		self.v = v

	def to_md5mesh(self):
		buf = "( %f %f )" % (self.u, self.v)
		return buf

#NOTE: uses global 'scale' to scale the size of model verticies
#generated and stored in Vertex class
class Weight:
	def __init__(self, bone, weight, vertex, weightindx, x, y, z):
		self.bone = bone
		self.weight = weight
		self.vertex = vertex
		self.indx = weightindx
		invbonematrix = matrix_invert(self.bone.matrix)
		self.x, self.y, self.z = point_by_matrix ((x, y, z), invbonematrix)

	def to_md5mesh(self):
		global scale
		buf = "%i %f ( %f %f %f )" % (self.bone.id, self.weight, self.x * scale, self.y * scale, self.z * scale)
		return buf

#used by SubMesh class
class Influence:
	def __init__(self, bone, weight):
		self.bone = bone
		self.weight = weight

#outputs the 'tris' data
class Face:
	def __init__(self, submesh, vertex1, vertex2, vertex3):
		self.vertex1 = vertex1
		self.vertex2 = vertex2
		self.vertex3 = vertex3

		self.can_collapse = 0

		self.submesh = submesh
		submesh.faces.append(self)

	def to_md5mesh(self):
		buf = "%i %i %i" % (self.vertex1.id, self.vertex3.id, self.vertex2.id)
		return buf

#holds bone skeleton data and outputs header above the Mesh class
class Skeleton:
	def __init__(self, MD5Version = 10, commandline = ""):
		self.bones = []
		self.MD5Version = MD5Version
		self.commandline = commandline
		self.next_bone_id = 0

	def to_md5mesh(self, numsubmeshes):

		buf = "MD5Version %i\n" % (self.MD5Version)
		buf = buf + "commandline \"%s\"\n\n" % (self.commandline)
		buf = buf + "numJoints %i\n" % (self.next_bone_id)
		buf = buf + "numMeshes %i\n\n" % (numsubmeshes)
		buf = buf + "joints {\n"
		for bone in self.bones:
			buf = buf + bone.to_md5mesh()
		buf = buf + "}\n\n"
		return buf

#held by Skeleton, generates individual 'joint' data
class Bone:
	def __init__(self, skeleton, parent, name, mat, theboneobj):
		self.parent = parent #Bone
		self.name = name	 #string
		self.children = [] #list of Bone objects
		self.theboneobj = theboneobj #Blender.Armature.Bone
		# HACK: this flags if the bone is animated in the one animation that we export
		self.is_animated = 0 # = 1, if there is an ipo that animates this bone

		self.matrix = mat
		if parent:
			parent.children.append(self)

		self.skeleton = skeleton
		self.id = skeleton.next_bone_id
		skeleton.next_bone_id += 1
		skeleton.bones.append(self)

		BONES[name] = self

	def to_md5mesh(self):
		global scale
		buf= "\t\"%s\"\t" % (self.name)
		parentindex = -1
		if self.theboneobj.ReparentBool:
			name = self.theboneobj.ReparentName
			for parb in self.skeleton.bones:
				if parb.name == name:
					parentindex = parb.id
					break
		elif self.parent:
			parentindex = self.parent.id
		buf = buf+"%i " % (parentindex)

		pos1, pos2, pos3= self.matrix.col[3][0], self.matrix.col[3][1], self.matrix.col[3][2]
		buf = buf + "( %f %f %f ) " % (pos1 * scale, pos2 * scale, pos3 * scale)
		#qx, qy, qz, qw = matrix2quaternion(self.matrix)
		#if qw < 0:
		#	 qx = -qx
		#	 qy = -qy
		#	 qz = -qz
		m = self.matrix
		#bquat = self.matrix.to_quat()	  #changed from matrix.toQuat() in blender 2.4x script
		bquat = self.matrix.to_quaternion()	   #changed from to_quat in 2.57 -mikshaw
		bquat.normalize()
		qx = bquat.x
		qy = bquat.y
		qz = bquat.z
		if bquat.w > 0:
			qx = -qx
			qy = -qy
			qz = -qz
		buf = buf + "( %f %f %f )\t\t// " % (qx, qy, qz)
		if self.theboneobj.ReparentBool:
			buf = buf + "%s" % (self.theboneobj.ReparentName)
		elif self.parent:
			buf = buf + "%s" % (self.parent.name)

		buf = buf + "\n"
		return buf

class MD5Animation:
	def __init__(self, md5skel, MD5Version = 10, commandline = ""):
		self.framedata = [] # framedata[boneid] holds the data for each frame
		self.bounds = []
		self.baseframe = []
		self.skeleton = md5skel
		self.boneflags = []	   # stores the md5 flags for each bone in the skeleton
		self.boneframedataindex = [] # stores the md5 framedataindex for each bone in the skeleton
		self.MD5Version = MD5Version
		self.commandline = commandline
		self.numanimatedcomponents = 0
		self.framerate = bpy.data.scenes[0].render.fps
		self.numframes = 0
		for b in self.skeleton.bones:
			self.framedata.append([])
			self.baseframe.append([])
			self.boneflags.append(0)
			self.boneframedataindex.append(0)

	def to_md5anim(self):
		global scale
		currentframedataindex = 0
		for bone in self.skeleton.bones:
			if (len(self.framedata[bone.id]) > 0):
				if (len(self.framedata[bone.id]) > self.numframes):
					self.numframes = len(self.framedata[bone.id])
				(x,y,z),(qw,qx,qy,qz) = self.framedata[bone.id][0]
				self.baseframe[bone.id] = (x * scale, y * scale, z * scale, qx * -1, qy * -1, qz * -1)
				self.boneframedataindex[bone.id] = currentframedataindex
				self.boneflags[bone.id] = 63
				currentframedataindex += 6
				self.numanimatedcomponents = currentframedataindex
			else:
				#rot = bone.pmatrix.to_quaternion().normalize()
				rot=bone.matrix.to_quaternion()
				rot.normalize()
				qx = rot.x * -1
				qy = rot.y * -1
				qz = rot.z * -1
				#if rot.w > 0:
				#	 qx = -qx
				#	 qy = -qy
				#	 qz = -qz
				self.baseframe.col[bone.id]= (bone.matrix.col[3][0]*scale, bone.matrix.col[3][1]*scale, bone.matrix.col[3][2]*scale, qx, qy, qz)

		buf = "MD5Version %i\n" % (self.MD5Version)
		buf = buf + "commandline \"%s\"\n\n" % (self.commandline)
		buf = buf + "numFrames %i\n" % (self.numframes)
		buf = buf + "numJoints %i\n" % (len(self.skeleton.bones))
		buf = buf + "frameRate %i\n" % (self.framerate)
		buf = buf + "numAnimatedComponents %i\n\n" % (self.numanimatedcomponents)
		buf = buf + "hierarchy {\n"

		# CoDEmanX: TODO - Sort bones, root - parents - children
		for bone in self.skeleton.bones:
			parentindex = -1
			flags = self.boneflags[bone.id]
			framedataindex = self.boneframedataindex[bone.id]
			parentbone = None
			if bone.theboneobj.ReparentBool:
				name = bone.theboneobj.ReparentName
				for parb in self.skeleton.bones:
					if parb.name == name:
						parentindex = parb.id
						parentbone = parb
						break
			elif bone.parent:
				parentindex=bone.parent.id
			buf = buf + "\t\"%s\"\t%i %i %i\t//" % (bone.name, parentindex, flags, framedataindex)
			if parentbone:
				buf = buf + " " + parentbone.name
			elif bone.parent:
				buf = buf + " " + bone.parent.name
			buf = buf + "\n"
		buf = buf + "}\n\n"

		buf = buf + "bounds {\n"
		for b in self.bounds:
			buf = buf + "\t( %f %f %f ) ( %f %f %f )\n" % (b)
		buf = buf + "}\n\n"

		buf = buf + "baseframe {\n"
		for b in self.baseframe:
			buf = buf + "\t( %f %f %f ) ( %f %f %f )\n" % (b)
		buf = buf + "}\n\n"

		for f in range(0, self.numframes):
			buf = buf + "frame %i {\n" % (f)
			for b in self.skeleton.bones:
				if (len(self.framedata[b.id]) > 0):
					(x,y,z),(qw,qx,qy,qz) = self.framedata[b.id][f]
					if qw > 0:
						qx, qy, qz = -qx, -qy, -qz
					buf = buf + "\t%f %f %f %f %f %f\n" % (x * scale, y * scale, z * scale, qx, qy, qz)
			buf = buf + "}\n\n"

		return buf

	def addkeyforbone(self, boneid, time, loc, rot):
		# time is ignored. the keys are expected to come in sequentially
		# it might be useful for future changes or modifications for other export formats
		self.framedata[boneid].append((loc, rot))
		return

def getminmax(listofpoints):
	if len(listofpoints) == 0:
		return ([0,0,0],[0,0,0])
	min = [listofpoints[0][0], listofpoints[0][1], listofpoints[0][2]] # correct [n][m]?
	max = [listofpoints[0][0], listofpoints[0][1], listofpoints[0][2]]
	if len(listofpoints) > 1:
		for i in range(1, len(listofpoints)):
			if listofpoints[i][0] > max[0]: max[0] = listofpoints[i][0]
			if listofpoints[i][1] > max[1]: max[1] = listofpoints[i][1]
			if listofpoints[i][2] > max[2]: max[2] = listofpoints[i][2]
			if listofpoints[i][0] < min[0]: min[0] = listofpoints[i][0]
			if listofpoints[i][1] < min[1]: min[1] = listofpoints[i][1]
			if listofpoints[i][2] < min[2]: min[2] = listofpoints[i][2]
	return (min, max)

def generateboundingbox(objects, md5animation, framerange):
	scn = bpy.context.scene #Blender.Scene.getCurrent()
	#context = scene.render #scene.getRenderingContext()
	# EDITED FOR KOT
	for i in range(framerange[0], framerange[1] + 1):
		corners = []
		#context.currentFrame(i)
		#scene.makeCurrent()
		scn.frame_set(i)

		for obj in scn.objects:
			data = obj.data #obj.getData()
			#if (type(data) is Blender.Types.NMeshType) and data.faces:
			if obj.type == 'MESH' and len(data.polygons)>0: ##data.faces:
				#obj.makeDisplayList()
				#(lx, ly, lz) = obj.getLocation()
				#(lx, ly, lz ) = obj.location
				(lx, ly, lz ) = obj.matrix_world.to_translation()
				#bbox = obj.getBoundBox()
				bbox = obj.bound_box
				matrix = [[1.0, 0.0, 0.0, 0.0],
						  [0.0, 1.0, 0.0, 0.0],
						  [0.0, 0.0, 1.0, 0.0],
						  [0.0, 0.0, 0.0, 1.0]]
				for v in bbox:
					#corners.append(point_by_matrix (v, matrix))
					corners.append(obj.matrix_world*mathutils.Vector((v[0],v[1],v[2])))
		(min, max) = getminmax(corners)
		md5animation.bounds.append((min[0] * scale, min[1] * scale, min[2] * scale, max[0] * scale, max[1] * scale, max[2] * scale))

#exporter settings
class md5Settings:
	def __init__(self,
				 savepath,
				 scale,
				 rotate,
				 #exportMode,
				 actions,
				 sel_only,
				 prefix,
				 name
	):
		self.savepath = savepath
		self.scale = scale
		self.rotate = rotate
		#self.exportMode = exportMode
		self.md5actions = actions
		self.sel_only = sel_only
		self.name = name
		self.prefix = prefix

#scale = 1.0

#SERIALIZE FUNCTION
def save_md5(settings):

	## CoDEmanX: replace frame range export by action export
	for a in settings.md5actions:
		if a.export_action:
			print("Export action '%s'" % a.name)

	print("Exporting selected objects...")
	bpy.ops.object.mode_set(mode='OBJECT')

	global BONES, scale # MC
	scale = settings.scale

	thearmature = 0	   #null to start, will assign in next section

	#first pass on selected data, pull one skeleton
	skeleton = Skeleton(10, "Exported from Blender by io_export_md5.py by Paul Zirkle")
	bpy.context.scene.frame_set(bpy.context.scene.frame_start)
	BONES = {}

	## CoDEmanX: currently selection, make this an option?
	for obj in bpy.context.selected_objects:
		if obj.type == 'ARMATURE':
			#skeleton.name = obj.name
			thearmature = obj
			w_matrix = obj.matrix_world

			#define recursive bone parsing function
			def treat_bone(b, parent = None, reparent = False):
				if not(reparent) and (parent and not b.parent.name == parent.name):
					return #only catch direct children

				mat = mathutils.Matrix(w_matrix) * mathutils.Matrix(b.matrix_local) #reversed order of multiplication from 2.4 to 2.5!!! ARRRGGG
				## CoDEmanX: row-major change in 2.62 / -Z90 correction?

				bone = Bone(skeleton, parent, b.name, mat, b)

				if (b.children):
					for child in b.children:
						if child.Export and not child.ReparentBool:
							treat_bone(child, bone)

				for brp in thearmature.data.bones:
					if brp.Export and brp.ReparentBool and brp.ReparentName == b.name:
						treat_bone(brp, bone, True)

			for b in thearmature.data.bones:
				if (not b.parent): #only treat root bones'
					if b.Export:
						print("root bone: " + b.name)
						treat_bone(b)

			break #only pull one skeleton out
	else:
		print ("No armature! Quitting...")
		return

	#second pass on selected data, pull meshes
	meshes = []
	for obj in bpy.context.selected_objects:
		if ((obj.type == 'MESH') and ( len(obj.data.vertices.values()) > 0 )): ##CoDEmanX: why values()? --> creates copy, same as vertices[:]
			#for each non-empty mesh

			##CoDEmanX: bmesh, replace with to_mesh!
			me = obj.data
			if not me.tessfaces and me.polygons:
				me.calc_tessface()

			mesh = Mesh(obj.name)
			print("Processing mesh: " + obj.name)
			meshes.append(mesh)

			numTris = 0
			numWeights = 0
			for f in me.tessfaces:
				numTris += len(f.vertices) - 2
			for v in me.vertices:
				numWeights += len( v.groups )

			if settings.rotate:
				from mathutils import Vector
				## CoDEmanX: how to?
				w_matrix = Vector((0,1,1)) * obj.matrix_world #fails?

				'''
				for ob in bpy.data.objects:
					if ob.type != 'MESH':
						continue
					me = ob.to_mesh(bpy.context.scene, True, 'PREVIEW')
					me.transform(Matrix.Rotation(radians(90), 4, 'Z') * ob.matrix_world)
				'''

			else:
				pass

			w_matrix = obj.matrix_world
			verts = me.vertices

			uv_textures = me.tessface_uv_textures
			faces = []
			for f in me.tessfaces:
				faces.append( f )

			createVertexA = 0
			createVertexB = 0
			createVertexC = 0

			while faces:
				material_index = faces[0].material_index
				try:
					mat_name = me.materials[0].name
				except IndexError:
					mat_name = "no_material"

				material = Material(mat_name) #call the shader name by the material's name

				submesh = SubMesh(mesh, material)
				vertices = {}
				for face in faces[:]:
					# der_ton: i added this check to make sure a face has at least 3 vertices.
					# (pdz) also checks for and removes duplicate verts
					if len(face.vertices) < 3: # throw away faces that have less than 3 vertices
						faces.remove(face)
					elif face.vertices[0] == face.vertices[1]:	  #throw away degenerate triangles
						faces.remove(face)
					elif face.vertices[0] == face.vertices[2]:
						faces.remove(face)
					elif face.vertices[1] == face.vertices[2]:
						faces.remove(face)
					elif face.material_index == material_index:
						#all faces in each sub-mesh must have the same material applied
						faces.remove(face)

						if not face.use_smooth :
							p1 = verts[ face.vertices[0] ].co
							p2 = verts[ face.vertices[1] ].co
							p3 = verts[ face.vertices[2] ].co
							normal = (w_matrix.to_3x3() * (p3-p2).cross(p1-p2)).normalized()

							#normal = vector_normalize(vector_by_matrix(vector_crossproduct( \
							#	 [p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2]], \
							#	 [p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2]], \
							#	 ), w_matrix))

						#for each vertex in this face, add unique to vertices dictionary
						face_vertices = []
						for i in range(len(face.vertices)):
							vertex = False
							if face.vertices[i] in vertices:
								vertex = vertices[face.vertices[i]] #type of Vertex
							if not vertex: #found unique vertex, add to list
								coord = w_matrix * verts[face.vertices[i]].co #point_by_matrix( verts[face.vertices[i]].co, w_matrix ) #TODO: fix possible bug here
								if face.use_smooth:
									normal = w_matrix.to_3x3() * verts[face.vertices[i]].normal
									#normal = vector_normalize(vector_by_matrix( verts[face.vertices[i]].normal, w_matrix ))
								vertex = vertices[face.vertices[i]] = Vertex(submesh, coord, normal)
								createVertexA += 1

								influences = []
								for j in range(len(me.vertices[face.vertices[i]].groups)):
									inf = [obj.vertex_groups[me.vertices[face.vertices[i]].groups[j].group].name, me.vertices[face.vertices[i]].groups[j].weight]
									influences.append(inf)

								if not influences:
									print("There is a vertex without attachment to a bone in mesh: " + mesh.name)
									# sum = 0.0
									# for bone_name, weight in influences: sum += weight

									# for bone_name, weight in influences:
									# if sum != 0:
									# try:
									# vertex.influences.append(Influence(BONES[bone_name], weight / sum))
									# except:
									# continue
									# else: # we have a vertex that is probably not skinned. export anyway
									# try:
									# vertex.influences.append(Influence(BONES[bone_name], weight))
									# except:
									# continue
								#dgis: Because faces can share vertices, the weights normalization will be done later (when serializing the vertices)!
								for bone_name, weight in influences:
									try:
										vertex.influences.append(Influence(BONES[bone_name], weight))
									except:
										continue

										#print( "vert " + str( face.vertices[i] ) + " has " + str(len( vertex.influences ) ) + " influences ")

							elif not face.use_smooth:
								# We cannot share vertex for non-smooth faces, since Cal3D does not
								# support vertex sharing for 2 vertices with different normals.
								# => we must clone the vertex.

								old_vertex = vertex
								vertex = Vertex(submesh, vertex.loc, normal)
								createVertexB += 1
								vertex.cloned_from = old_vertex
								vertex.influences = old_vertex.influences
								old_vertex.clones.append(vertex)

							hasFaceUV = len(uv_textures) > 0 #borrowed from export_obj.py

							if hasFaceUV:
								uv = [uv_textures.active.data[face.index].uv[i][0], uv_textures.active.data[face.index].uv[i][1]]
								uv[1] = 1.0 - uv[1] # should we flip Y? yes, new in Blender 2.5x
								if not vertex.maps: vertex.maps.append(Map(*uv))
								elif (vertex.maps[0].u != uv[0]) or (vertex.maps[0].v != uv[1]):
									# This vertex can be shared for Blender, but not for MD5
									# MD5 does not support vertex sharing for 2 vertices with
									# different UV texture coodinates.
									# => we must clone the vertex.

									for clone in vertex.clones:
										if (clone.maps[0].u == uv[0]) and (clone.maps[0].v == uv[1]):
											vertex = clone
											break
									else: # Not yet cloned...	 (PDZ) note: this ELSE belongs attached to the FOR loop.. python can do that apparently
										old_vertex = vertex
										vertex = Vertex(submesh, vertex.loc, vertex.normal)
										createVertexC += 1
										vertex.cloned_from = old_vertex
										vertex.influences = old_vertex.influences
										vertex.maps.append(Map(*uv))
										old_vertex.clones.append(vertex)

							face_vertices.append(vertex)

						# Split faces with more than 3 vertices
						for i in range(1, len(face.vertices) - 1):
							Face(submesh, face_vertices[0], face_vertices[i], face_vertices[i+1])
					else:
						print( "found face with invalid material!!!!" )
			print("created verts at A " + str(createVertexA) + ", B " + str(createVertexB) + ", C " + str(createVertexC))

	# Export animations

	## CoDEmanX: rewrite!

	if not thearmature.animation_data:
		thearmature.animation_data_create()

	orig_action = thearmature.animation_data.action

	for a in settings.md5actions:
		if not a.export_action and settings.sel_only:
			continue

		arm_action = bpy.data.actions.get(a.name, False)
		if not arm_action:
			continue

		if len(arm_action.pose_markers) < 2:
			frame_range = (int(arm_action.frame_range[0]), int(arm_action.frame_range[1]))
		else:
			pm_frames = [pm.frame for pm in arm_action.pose_markers]
			frame_range = (min(pm_frames), max(pm_frames))

		rangestart = frame_range[0]
		rangeend = frame_range[1]


		thearmature.animation_data.action = arm_action
		#arm_action = thearmature.animation_data.action
		#rangestart = 0
		#rangeend = 0
		#if arm_action:
		ANIMATIONS = {}
		animation = ANIMATIONS[arm_action.name] = MD5Animation(skeleton)

		#rangestart = int(bpy.context.scene.frame_start) # int( arm_action.frame_range[0] )
		#rangeend = int(bpy.context.scene.frame_end) #int( arm_action.frame_range[1] )
		currenttime = rangestart
		while currenttime <= rangeend:
			bpy.context.scene.frame_set(currenttime)
			time = (currenttime - 1.0) / 24.0 #(assuming default 24fps for md5 anim)
			pose = thearmature.pose

			for bonename in thearmature.data.bones.keys():
				posebonemat = mathutils.Matrix(pose.bones[bonename].matrix) # @ivar poseMatrix: The total transformation of this PoseBone including constraints. -- different from localMatrix

				try:
					bone = BONES[bonename] #look up md5bone
				except:
					continue
				if bone.parent: # need parentspace-matrix
					parentposemat = mathutils.Matrix(pose.bones[bone.parent.name].matrix) # @ivar poseMatrix: The total transformation of this PoseBone including constraints. -- different from localMatrix
					#posebonemat = parentposemat.invert() * posebonemat #reverse order of multiplication!!!
					parentposemat.invert() # mikshaw
					posebonemat = parentposemat * posebonemat # mikshaw
				else:
					posebonemat = thearmature.matrix_world * posebonemat	#reverse order of multiplication!!!
				loc = [posebonemat.col[3][0],
					   posebonemat.col[3][1],
					   posebonemat.col[3][2],
					   ] ## CoDEmanX: row-major?
				#rot = posebonemat.to_quat().normalize()
				rot = posebonemat.to_quaternion() # changed from to_quat in 2.57 -mikshaw
				rot.normalize() # mikshaw
				rot = [rot.w, rot.x, rot.y, rot.z]
				
				animation.addkeyforbone(bone.id, time, loc, rot)
			currenttime += 1

		# MOVED ANIM EXPORT CODE
		#if(settings.exportMode == "mesh & anim" or settings.exportMode == "anim only"):
		if True:
			#md5anim_filename = settings.savepath + ".md5anim"
			import os.path

			if settings.prefix:
				if settings.name:
					prefix_str = settings.name + "_"
				else:
					prefix_str = os.path.splitext(os.path.split(settings.savepath)[1])[0] + "_"
			else:
				prefix_str = ""

			md5anim_filename = os.path.split(settings.savepath)[0] + os.path.sep + prefix_str + arm_action.name + ".md5anim"

			#save animation file
			if len(ANIMATIONS) > 0:
				anim = ANIMATIONS.popitem()[1] #ANIMATIONS.values()[0]
				#print(str(anim))
				try:
					file = open(md5anim_filename, 'w')
				except IOError:
					errmsg = "IOError " #%s: %s" % (errno, strerror)
				objects = []
				for submesh in meshes[0].submeshes:
					if len(submesh.weights) > 0:
						obj = None
						for sob in bpy.context.selected_objects:
							if sob and sob.type == 'MESH' and sob.name == submesh.name:
								obj = sob
						objects.append (obj)
				generateboundingbox(objects, anim, [rangestart, rangeend])
				buffer = anim.to_md5anim()
				file.write(buffer)
				file.close()
				print( "saved anim to " + md5anim_filename )
			else:
				print( "No md5anim file was generated." )
				# END MOVED

	thearmature.animation_data.action = orig_action

	# here begins md5mesh and anim output
	# this is how it works
	# first the skeleton is output, using the data that was collected by the above code in this export function
	# then the mesh data is output (into the same md5mesh file)

	## CoDEmanX: replace? shall mesh only be supported?
	#if( settings.exportMode == "mesh & anim" or settings.exportMode == "mesh only" ):
	if True:
		md5mesh_filename = settings.savepath #+ ".md5mesh" ## already has extension?!

		#save all submeshes in the first mesh
		if len(meshes) > 1:
			for mesh in range (1, len(meshes)):
				for submesh in meshes[mesh].submeshes:
					submesh.bindtomesh(meshes[0])
		if (md5mesh_filename != ""):
			try:
				file = open(md5mesh_filename, 'w')
			except IOError:
				errmsg = "IOError " #%s: %s" % (errno, strerror)
			buffer = skeleton.to_md5mesh(len(meshes[0].submeshes))
			#for mesh in meshes:
			buffer = buffer + meshes[0].to_md5mesh()
			file.write(buffer)
			file.close()
			print("saved mesh to " + md5mesh_filename)
		else:
			print("No md5mesh file was generated.")

##########
#export class registration and interface
from bpy.props import *

class ActionsPropertyGroup(bpy.types.PropertyGroup):
	'''PropertyGroup for all Actions to be displayed in a template_list'''
	export_action = BoolProperty(default=False, name="") #make default true?

class ActionsUIList(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		if self.layout_type in {'DEFAULT', 'COMPACT'}:
			layout.prop(item, "export_action", text=item.name)
		elif self.layout_type in {'GRID'}:
			layout.alignment = 'CENTER'
			layout.prop(item, "export_action", text="")

class SelectActionOperator(bpy.types.Operator):
	'''(De-)Select all actions or invert selection for export'''
	bl_idname = "export.md5_select_actions"
	bl_label = "Select actions"

	action = EnumProperty(items=(("SELECT","Select all",""),
								 ("DESELECT","Deselect all",""),
								 ("INVERT","Invert selection","")),
						  default="SELECT")


	def execute(self, context):
		#print("\n\n### Try accessing md5actions...\n")
		#print(list(context.active_operator.md5actions))
		for a in context.active_operator.md5actions:
			if self.action == "DESELECT":
				a.export_action = False
			elif self.action == "INVERT":
				a.export_action = not a.export_action
			else:
				a.export_action = True
		return {'FINISHED'}
		
		
class WeightsOn(bpy.types.Operator):
	bl_idname = "export.md5_set_with_weights"
	bl_label = "Set Export on bones with weights to True"

	def execute(self, context):
		armobj = context.active_object
		if armobj.type == 'ARMATURE':
			arm = armobj.data
			for obj in context.scene.objects:
				if obj.type == 'MESH':
					for mod in obj.modifiers:
						if mod.type == 'ARMATURE':
							if mod.object == armobj:
								for vg in obj.vertex_groups:
									for bone in arm.bones:
										if bone.name == vg.name:
											bone.Export = True
			for bone in arm.bones:
				if bone.name == "origin":
					bone.Export = True
		return {'FINISHED'}
	
	
class Reset(bpy.types.Operator):
	bl_idname = "export.md5_reset_bones"
	bl_label = "Reset custom bones data to default"

	def execute(self, context):
		obj = context.active_object
		if obj.type == 'ARMATURE':
			arm = obj.data
			for bone in arm.bones:
				bone.Export = False
				bone.ReparentBool = False
				bone.ReparentName = "not set"
		return {'FINISHED'}
	
	
		
class MD5Panel(bpy.types.Panel):
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_label = "Bone MD5 Export"

	def draw(self, context):
		
		obj = context.active_object
		if obj:
			if obj.type == 'ARMATURE':
				arm = obj.data
				bone = arm.bones.active
				self.layout.operator("export.md5_set_with_weights", text = "Initialize")
				self.layout.operator("export.md5_reset_bones", text = "Reset All")
				if not(bone == None):
					self.layout.prop(bone, "Export")
					if bone.Export and len(arm.bones) > 1:
						self.layout.prop(bone, "ReparentBool")
						if bone.ReparentBool:
							self.layout.prop(bone, "ReparentName")
							self.layout.prop(bone, "ReparentNameHelper")




from bpy_extras.io_utils import ExportHelper
import os.path

class ExportMD5(bpy.types.Operator, ExportHelper):
	'''Export to Quake Model 5 (.md5)'''
	bl_idname = "export.md5"
	bl_label = 'Export MD5'

	# ExportHelper mixin class uses this
	## CoDEmanX: Should md5anim / md5cam be shwon as well?
	filename_ext = ".md5"

	filter_glob = StringProperty(
		default="*.md5mesh;*.md5anim;*.md5camera",
		options={'HIDDEN'},
		)

	logenum = [("console","Console","log to console"),
			   ("append","Append","append to log file"),
			   ("overwrite","Overwrite","overwrite log file")]

	#search for list of actions to export as .md5anims
	#md5animtargets = []
	#for anim in bpy.data.actions:
	#	 md5animtargets.append((anim.name, anim.name, anim.name))

	#md5animtarget = None
	#if (len(md5animtargets) > 0):
	#	 md5animtarget = EnumProperty(name="Anim", items = md5animtargets, description = "choose animation to export", default = md5animtargets[0])

	exportModes = [("mesh & anim", "Mesh & Anim", "Export .md5mesh and .md5anim files."),
				   ("anim only", "Anim only.", "Export .md5anim only."),
				   ("mesh only", "Mesh only.", "Export .md5mesh only.")]

	filepath = StringProperty(subtype='FILE_PATH', name="File Path", description="Filepath for exporting", maxlen=1024, default= "")
	filename = StringProperty(subtype='FILE_NAME', name="File Name", default="")
	md5name = StringProperty(name="MD5 Name", description="MD3 header name / skin path (64 bytes)", maxlen=64, default="")
	#md5exportList = EnumProperty(name="Exports", items=exportModes, description="Choose export mode.", default='mesh & anim')
	#md5logtype = EnumProperty(name="Save log", items=logenum, description="File logging options",default = 'console')
	md5scale = FloatProperty(name="Scale", description="Scale all objects from world origin (0,0,0)", default=1.0, precision=5)
	#md5offsetx = FloatProperty(name="Offset X", description="Transition scene along x axis", default=0.0, precision=5)
	#md5offsety = FloatProperty(name="Offset Y", description="Transition scene along y axis", default=0.0, precision=5)
	#md5offsetz = FloatProperty(name="Offset Z", description="Transition scene along z axis", default=0.0, precision=5)

	## CoDEmanX:
	md5anim = BoolProperty(name="Animation", default=True)
	md5sfra = IntProperty(name="Start Frame")
	md5efra = IntProperty(name="End Frame")
	md5cam = BoolProperty(name="Camera", default=False)
	md5cp = StringProperty(name="Filename", default="my_cam")

	md5type = EnumProperty(items=(('0', 'Mesh / Anims', 'Export Meshes and Animations (actions)'),('1', 'Camera', 'Export first Camera in scene')), name="Export")

	#bpy.types.Scene.my_settings = CollectionProperty(type=ActionsPropertyGroup)
	md5actions = CollectionProperty(type=ActionsPropertyGroup)
	#bpy.types.Scene.my_settings_idx = IntProperty()
	md5actions_idx = IntProperty()

	use_sel_only = BoolProperty(name="Only selected from list:")
	use_prefix = BoolProperty(name="Prefix with MD5name", description="Use MD5name as prefix for MD5anim files. If no MD5name has been set, MD5mesh filename will be used.")

	use_rotate = BoolProperty(name="Correct rotation", default=False)


	def check(self, context):

		if self.md5type == '1':
			self.filename_ext = '.md5camera'
			self.filter_glob = '*.md5camera' # no effect?
		else:
			self.filename_ext = '.md5mesh'
			self.filter_glob = '*.md5mesh;*.md5anim'

		#print("CHECK -", self.filename)
		if self.filename.startswith(('.md5camera', '.md5mesh')):
			self.filename = '' #NEEDS FIX!


		return ExportHelper.check(self, context)
		#return super(self).check(self, context)

	def draw(self, context):

		"""
		if self.md5type == '1':
			self.filename_ext = '.md5camera'
		else:
			self.filename_ext = '.md5mesh'
		"""
		#self.draw(context) # Force filename_ext update?

		#print("DRAW -", self.filename_ext)

		layout = self.layout

		layout.prop(self, "md5type", expand=True)

		if self.md5type == '0':
			col = layout.column()
			#col.label("Meshes:")
			#col.prop(self, "use_rotate")

			box = col.box()
			box.prop(self, "md5name")
			sub = box.row()
			sub.enabled = len(self.md5name) == 0
			sub.label(os.path.splitext(self.filename)[0])
			box.prop(self, "md5scale")

			col = layout.column()
			'''
			box = col.box()
			box.prop(self, "md5anim", "Animation:")
			sub = box.column(align=True)
			sub.active = self.md5anim
			sub.prop(self, "md5sfra")
			sub.prop(self, "md5efra")
			'''
			'''
			box = layout.box()
			box.prop(self, "md5cam")
			sub = box.row()
			sub.active = self.md5cam
			sub.prop(self, "md5cp")
			'''

			a_count = len(self.md5actions)
			#print(a_count, "init")
			if a_count == 0:
				a_count_str = "No animation data!"
				#print("no anim at all")
			else:
				if self.use_sel_only:
					a_count = len([a for a in self.md5actions if a.export_action])
					a_count_str = str(a_count)
					#print("use sel, actions avail")
				else:
					a_count_str = str(a_count) + " (all)"
					#print("use all, actions avail")

			layout.label("Export actions: %s" % a_count_str)

			if a_count > 0 or self.use_sel_only:
				layout.prop(self, "use_sel_only")

				col = layout.column()
				col.active = self.use_sel_only
				col.template_list("ActionsUIList", "", self, "md5actions", self, "md5actions_idx",
								  rows=len(self.md5actions))

				sub = col.row(align=True)
				sub.operator("export.md5_select_actions", "Select").action = "SELECT" # Why is default="SELECT" not working???
				sub.operator("export.md5_select_actions", "Deselect").action = "DESELECT"
				sub.operator("export.md5_select_actions", "Invert").action = "INVERT"

				layout.prop(self, "use_prefix")
		else:
			layout.label("Not yet implemented")


	def execute(self, context):
		settings = md5Settings(savepath = self.filepath,
							   scale = self.md5scale,
							   rotate = self.use_rotate,
							   #exportMode = self.md5exportList,
							   actions = self.md5actions,
							   sel_only = self.use_sel_only,
							   prefix = self.use_prefix,
							   name = self.md5name)
		save_md5(settings)
		return {'FINISHED'}

	def invoke(self, context, event):
		self.md5sfra = context.scene.frame_start
		self.md5efra = context.scene.frame_end

		actions = self.md5actions
		actions.clear()
		for action in bpy.data.actions:
			for fcurve in action.fcurves:
				if fcurve.data_path.startswith("pose.bones"):
					#print("found pose.bones fcurve")
					break
			else:
				print("Skipped action %s, 'cause it has no Armature-related transforms" % action.name)
				continue

			action_item = actions.add()
			action_item.name = action.name

		return super().invoke(context, event)

def menu_func(self, context):
	self.layout.operator(ExportMD5.bl_idname, text="idTech 4 MD5 Export test21", icon='BLENDER')

def register():

	global oldname, oldnamehelper

	oldname = {}
	oldnamehelper = {}
	
	bpy.types.Bone.Export = bpy.props.BoolProperty(
			name = "export", 
			description = "Will this bone be exported?",
			default = False)
	bpy.types.Bone.ReparentBool = bpy.props.BoolProperty(
			name = "reparent", 
			description = "Will this bone be reparented?",
			default = False)
	bpy.types.Bone.ReparentName = bpy.props.StringProperty(
			name = "to", 
			description = "Reparenting to this bone for export",
			default = "")								
	
	bpy.utils.register_module(__name__) #mikshaw
	bpy.types.INFO_MT_file_export.append(menu_func)
	bpy.app.handlers.save_pre.append(fakeuser_for_actions)
	bpy.app.handlers.scene_update_post.append(sceneupdate_handler)

def unregister():
	bpy.utils.unregister_module(__name__) #mikshaw
	bpy.types.INFO_MT_file_export.remove(menu_func)
	bpy.app.handlers.save_pre.remove(fakeuser_for_actions)
	bpy.app.handlers.scene_update_post.remove(sceneupdate_handler)


if __name__ == "__main__":
	register()
	
	
	
@persistent	
def sceneupdate_handler(dummy):

	global oldname

	obj = bpy.context.active_object
	if obj:
		if obj.type == 'ARMATURE':
		
			arm = obj.data
		
			bone = arm.bones.active
				
			if not(bone == None):
			
				if bone.ReparentBool:
					itemlist = []
					found = False
					for bone2 in arm.bones:
						if bone == bone2:
							continue
						if bone2.Export:
							found = True
							itemlist.append((bone2.name, bone2.name, "Select bone for reparenting"))
					bpy.types.Bone.ReparentNameHelper = bpy.props.EnumProperty(
							items = itemlist,
							name = "",
							description = "Bone to reparent to on export")
									
					if found:
						if not(bone in oldname.keys()):
							oldname[bone] = None
						if not(bone.ReparentName == oldname[bone]):
							print (bone.ReparentName)
							try:
								bone.ReparentNameHelper = bone.ReparentName
							except:
								bone.ReparentName = bone.ReparentNameHelper
							oldname[bone] = bone.ReparentName
							oldnamehelper[bone] = bone.ReparentNameHelper
							if bpy.context.area:
								for region in bpy.context.area.regions:
									if region.type == "UI":
										region.tag_redraw()
							
						bone.ReparentName = bone.ReparentNameHelper
						oldname[bone] = bone.ReparentName
						if bpy.context.area:
							for region in bpy.context.area.regions:
								if region.type == "UI":
									region.tag_redraw()
										
	
	
