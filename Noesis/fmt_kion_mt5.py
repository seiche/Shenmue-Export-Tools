#==============================================================
"""

Noesis Shenmue Model Import Addon
Copyright Benjamin Collins 2016,2018

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.

"""
#==============================================================

import math
import noesis
import struct
import rapi
from inc_noesis import *
from inc_powervr import *

def registerNoesisTypes():
    #handle = noesis.register("Shenmue Dreamcast Model", ".mt5")
    #handle = noesis.register("Shenmue Dreamcast Model", ".hcm")
    #noesis.setHandlerTypeCheck(handle, noepyCheckType)
    #noesis.setHandlerLoadModel(handle, noepyLoadModel)
    #noesis.logPopup()
    return 0

def noepyCheckType(data):
    noesis.logFlush()
    bs = NoeBitStream(data)
    iff = bs.readBytes(0x04).decode("ASCII")
    if iff == "HRCM":
        return 1
    return 0

def noepyLoadModel(data, mdlList):
    ctx = rapi.rpgCreateContext()
    model = ShenmueMt5(data)
    model.parse()
    rapi.rpgClearBufferBinds()
    noeMat = NoeModelMaterials(model.noeTextures, model.noeMaterials)
    rapi.rpgBindPositionBuffer(model.vertex_list, noesis.RPGEODATA_FLOAT, 0x0C)
    rapi.rpgBindNormalBuffer(model.normal_list, noesis.RPGEODATA_FLOAT, 0x0C)
    rapi.rpgBindUV1Buffer(model.uv_list, noesis.RPGEODATA_FLOAT, 0x08)

    for strip in model.polygon_list:
        rapi.rpgSetMaterial("material[%s]"%strip['texId'])
        rapi.rpgCommitTriangles(strip['face'], noesis.RPGEODATA_USHORT, int(len(strip['face'])/2), noesis.RPGEO_TRIANGLE, 0)
    mdl = rapi.rpgConstructModel()
    mdl.setModelMaterials(noeMat)
    mdlList.append(mdl)
    rapi.setPreviewOption("noTextureLoad", "1")
    rapi.rpgOptimize()
    return 1

class ShenmueMt5:

    def __init__(self, data):
        self.tex_ofs = 0
        self.model_ofs = 0

        self.vertex_ofs = 0
        self.vertex_list = []
        self.normal_list = []
        self.uv_list = []
        self.polygon_list = []
        self.texture_list = []
        self.uv_table = {}
        self.bs = NoeBitStream(data)
        self.noeMaterials = []
        self.noeTextures = []

    def parse(self):
        self.bs.seek(0x04)
        self.tex_ofs = self.bs.readUInt()
        self.model_ofs = self.bs.readUInt()
        self.bs.seek(self.model_ofs, NOESEEK_ABS)
        self.crawl_nodes()
        self.read_textures()
        self.generateNoeTextures()
        self.alignVertexMap()
        self.generate_buffer()
        return 1

    def read_textures(self):
        self.bs.seek(self.tex_ofs, NOESEEK_ABS)
        iff = self.bs.readBytes(0x04).decode("ASCII").rstrip("\0")
        if iff != "TEXD":
            return
        return
        self.bs.seek(0x04, NOESEEK_REL)
        nbTex = self.bs.readUInt()
        for i in range(nbTex):
            iff = self.bs.readBytes(0x04).decode("ASCII").rstrip("\0")
            if iff != "TEXN":
                return
            self.bs.seek(0x14, NOESEEK_REL)
            texId = self.bs.readUInt()
            texName = "texure[%d]"%texId

            iff = self.bs.readBytes(0x04).decode("ASCII").rstrip("\0")
            if iff != "PVRT":
                return
            texLen = self.bs.readUInt()
            texData = self.bs.readBytes(texLen)
            tex = PvrTexture(texData,texId,texName)
            tex.convert()
            self.texture_list.append(tex)

    def generateNoeTextures(self):
        for tex in self.texture_list:
            texId = tex.get_id()
            name = tex.get_name()
            width = tex.get_width()
            height = tex.get_height()
            bitmap = tex.get_bitmap()
            tex = NoeTexture(name, width, height, bitmap, noesis.NOESISTEX_RGBA32)
            self.noeTextures.append(tex)
            matName = "material[%d]"%texId
            noemat = NoeMaterial(matName, name)
            self.noeMaterials.append(noemat)

    def crawl_nodes(self):
        node = self.read_node()

        if node['model']:
            self.bs.seek(node['model'], NOESEEK_ABS)
            model = self.read_model()

            if model['vertex']:
                self.bs.seek(model['vertex'], NOESEEK_ABS)
                self.read_vertex_list(model['nbVertex'])

            if model['polygon']:
                self.bs.seek(model['polygon'], NOESEEK_ABS)
                self.read_polygon_list()

            if model['vertex']:
                self.vertex_ofs = self.vertex_ofs + model['nbVertex']

        if node['child']:
            self.bs.seek(node['child'])
            self.crawl_nodes()

        if node['sibling']:
            self.bs.seek(node['sibling'])
            self.crawl_nodes()

    def read_node(self):
        node = {}
        node['flag'] = self.bs.readUInt()
        node['model'] = self.bs.readUInt()
        node['rot'] = {}
        node['rot']['x'] = self.bs.readUInt()
        node['rot']['y'] = self.bs.readUInt()
        node['rot']['z'] = self.bs.readUInt()
        node['scl'] = {}
        node['scl']['x'] = self.bs.readFloat()
        node['scl']['y'] = self.bs.readFloat()
        node['scl']['z'] = self.bs.readFloat()
        node['pos'] = {}
        node['pos']['x'] = self.bs.readFloat()
        node['pos']['y'] = self.bs.readFloat()
        node['pos']['z'] = self.bs.readFloat()
        node['child'] = self.bs.readUInt()
        node['sibling'] = self.bs.readUInt()
        node['parent'] = self.bs.readUInt()
        node['unknown01'] = self.bs.readUInt()
        node['unknown02'] = self.bs.readUInt()
        return node

    def read_model(self):
        model = {}
        model['flag'] = self.bs.readUInt()
        model['vertex'] = self.bs.readUInt()
        model['nbVertex'] = self.bs.readUInt()
        model['polygon'] = self.bs.readUInt()
        model['center'] = {}
        model['center']['x'] = self.bs.readFloat()
        model['center']['y'] = self.bs.readFloat()
        model['center']['z'] = self.bs.readFloat()
        model['radius'] = self.bs.readFloat()
        return model

    def read_vertex_list(self, nbVertex):
        for i in range(nbVertex):
            vertex = {}
            x = self.bs.readFloat()
            y = self.bs.readFloat()
            z = self.bs.readFloat()
            vertex['pos'] = [x, y, z]
            x = self.bs.readFloat()
            y = self.bs.readFloat()
            z = self.bs.readFloat()
            vertex['norm'] = [x, y, z]
            self.vertex_list.append(vertex)

    def read_polygon_list(self):
        polygon = {}

        strip_start = False
        polygon_start = False
        while self.bs.tell() < self.bs.getSize() - 4:
            head = self.bs.readUShort()
            flag = self.bs.readUShort()

            if head == 0x8000 and flag == 0xFFFF:
                return
            elif head == 0x0002 and flag == 0x0010:
                polygon_start = True
            elif head == 0x0003 and flag == 0x0010:
                polygon_start = True
            elif polygon_start and head == 0x0009:
                polygon['texId'] = flag
            elif polygon_start and head == 0x11:
                strip_start = True # index, u, v
            elif polygon_start and head == 0x13:
                strip_start = True # index
            elif polygon_start and head == 0x1c:
                strip_start = True # index, u0, v0, u1, v1

            if strip_start:
                polygon['strips'] = []
                nbStrips = self.bs.readUShort()
                for i in range(nbStrips):
                    strip = []
                    strip_len = abs(self.bs.readShort())
                    for k in range(strip_len):
                        idx = self.bs.readShort() + self.vertex_ofs

                        if head == 0x11 or head == 0x1c:
                            u = self.bs.readShort() / 0x3ff
                            v = self.bs.readShort() / 0x3ff

                        if head == 0x1c:
                            u1 = self.bs.readShort() / 0x3ff
                            v1 = self.bs.readShort() / 0x3ff

                        if idx >= len(self.vertex_list):
                            continue

                        point = {}
                        point['idx'] = idx
                        point['uv'] = [u,v]
                        strip.append(point)
                    polygon['strips'].append(strip)
                strip_start = False
                polygon_start = False
                self.polygon_list.append(polygon)
                polygon = {}
                if self.bs.tell() % 4 == 2:
                    self.bs.seek(2, NOESEEK_REL)

    def alignVertexMap(self):
        for polygon in self.polygon_list:
            texId = polygon['texId']
            for strip in polygon['strips']:
                for i in range(len(strip)):
                    point = strip[i]
                    idx = point['idx']
                    if str(idx) not in self.uv_table:
                        self.uv_table[str(idx)] = [idx]
                        self.vertex_list[idx]['uv'] = point['uv']
                    else:
                        found = False
                        for vpos in self.uv_table[str(idx)]:
                            if self.vertex_list[vpos]['uv'] == point['uv']:
                                idx = vpos
                                found = True
                                break
                        if not found:
                            vertex = self.vertex_list[idx].copy()
                            vertex['uv'] = point['uv']
                            vpos = len(self.vertex_list)
                            self.vertex_list.append(vertex)
                            self.uv_table[str(idx)].append(vpos)
                            idx = vpos
                    strip[i] = idx

    def generate_buffer(self):
        vlist_len = len(self.vertex_list)

        pos = []
        norm = []
        uv = []
        for vertex in self.vertex_list:
            pos.extend(vertex['pos'])
            norm.extend(vertex['norm'])
            if 'uv' in vertex:
                uv.extend(vertex['uv'])
            else:
                uv.extend([0.0, 0.0])
        self.vertex_list = struct.pack('f'*len(pos), *pos)
        self.normal_list = struct.pack('f'*len(norm), *norm)
        self.uv_list = struct.pack('f'*len(uv), *uv)

        tri = []
        for polygon in self.polygon_list:
            texId = polygon['texId']
            for strip in polygon['strips']:
                face = []
                for i in range(len(strip) - 2):
                    a = strip[i]
                    b = strip[i + 1]
                    c = strip[i + 2]
                    if not i%2:
                        face.extend([a,c,b])
                    else:
                        face.extend([a,b,c])
                pack = {}
                pack['texId'] = texId
                pack['face'] = struct.pack('H'*len(face), *face)
                tri.append(pack)
        self.polygon_list = tri
