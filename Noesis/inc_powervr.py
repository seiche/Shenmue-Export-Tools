#==============================================================
"""

Noesis Power VR Plugin
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
from inc_noesis import *

def registerNoesisTypes():
	handle = noesis.register("PowerVR Archive", ".kvm")
	noesis.setHandlerTypeCheck(handle, artCheckType)
	noesis.setHandlerLoadRGBA(handle, artLoadRGBA)
	return 1

def artCheckType(data):
    bs = NoeBitStream(data)
    PVMH = 0x484D5650
    if bs.readUInt() == PVMH:
        return 1
    return 0

def artLoadRGBA(data, texList):
    pvmArchive = PvmArchive(data)
    pvrList = pvmArchive.get_textures()
    for pvr in pvrList:
        pvr = NoeTexture(pvr['name'],pvr['width'],pvr['height'],pvr['bitmap'])
        texList.append(pvr)
    return 1

class PvmArchive:

    def __init__(self, data):
        self.bs = NoeBitStream(data)
        self.texList = self.read_header()
        self.parse_textures()

    def read_header(self):
        texList = []
        self.bs.seek(0, NOESEEK_ABS)
        iff = self.bs.readUInt()
        texOfs = self.bs.readUInt() + 0x08
        flags = self.bs.readUShort()
        nbTex = self.bs.readUShort()

        for i in range(nbTex):
            tex = {}
            tex['id'] = self.bs.readUShort()

            if flags & 0x08:
                texName = self.bs.readBytes(0x1C)
                tex['name'] = texName.decode("ASCII").rstrip("\0")
            else:
                tex['name'] = "texture[%d]"%tex['id']
            if flags & 0x04:
                texFormat = self.bs.readUShort()
            if flags & 0x02:
                texWidth = self.bs.readUByte()
                texHeight = self.bs.readUByte()
            if flags & 0x01:
                texIndex = self.bs.readUInt()

            texList.append(tex)
        return texList

    def find(self):
        PVRT = 0x54525650
        while self.bs.tell() < self.bs.getSize() - 4:
            if self.bs.readUInt() == PVRT:
                return 1
        return 0

    def get_textures(self):
        return self.texList

    def parse_textures(self):
        self.bs.seek(0, NOESEEK_ABS)
        for i in range(len(self.texList)):
            tex = self.texList[i]
            if not self.find():
                return 0
            texLen = self.bs.readUInt()
            pvrData = self.bs.readBytes(texLen)
            pvrImg = PvrTexture(pvrData, i)
            tex['width'] = pvrImg.get_width()
            tex['height'] = pvrImg.get_height()
            tex['bitmap'] = pvrImg.get_bitmap()
        return 1

class PvrTexture:
    BYTE_SIZE          = 1
    WORD_SIZE          = 2
    CODE_COMPONENTS    = 4
    LOOKUP_TABLE       = {}

    ARGB_1555          = 0x00
    RGB_565            = 0x01
    ARGB_4444          = 0x02
    YUV_422            = 0x03
    BUMP	           = 0x04
    RGB_555            = 0x05
    ARGB_8888          = 0x06
    YUV_420            = 0x06

    TWIDDLED	       = 0x01
    TWIDDLED_MM        = 0x02
    VQ	               = 0x03
    VQ_MM	           = 0x04
    PALETTIZE4	       = 0x05
    PALETTIZE4_MM      = 0x06
    PALETTIZE8	       = 0x07
    PALETTIZE8_MM      = 0x08
    RECTANGLE	       = 0x09
    STRIDE	           = 0x0B
    TWIDDLED_RECTANGLE = 0x0D
    ABGR			   = 0x0E
    ABGR_MM			   = 0x0F
    SMALLVQ            = 0x10
    SMALLVQ_MM         = 0x11
    TWIDDLED_MM_ALIAS  = 0x12

    def __init__(self, data, texId = -1):
        self.bs = NoeBitStream(data)
        self.codebook = 0
        self.texId = texId
        self.width = None
        self.height = None
        self.mipWidth = None
        self.mipHeight = None
        self.color_format = None
        self.data_format = None

        self.isTwiddled = False
        self.isCompressed = False
        self.isMipmap = False
        self.codebook_size = 256

        self.dst_array = None
        self.read_header()
        self.debug()
        self.bitmap = self.create_bitmap()

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_bitmap(self):
        return self.bitmap

    def get_codebook_size(self):
        if self.width <= 16:
            return 16
        elif self.width == 32 and not self.isMipmap:
            return 32
        elif self.width == 32 and self.isMipmap:
            return 64
        elif self.width == 64 and not self.isMipmap:
            return 128
        else:
            return 256

    def read_header(self):
        self.color_format = self.bs.readUByte()
        self.data_format = self.bs.readUByte()
        self.bs.seek(2, NOESEEK_REL)
        self.width = self.bs.readUShort()
        self.height = self.bs.readUShort()
        data = self.bs.getBuffer(self.bs.tell(), self.bs.getSize())
        self.bs = NoeBitStream(data)

        if (
            self.data_format == PvrTexture.TWIDDLED or
            self.data_format == PvrTexture.TWIDDLED_MM or
            self.data_format == PvrTexture.TWIDDLED_RECTANGLE or
            self.data_format == PvrTexture.TWIDDLED_MM_ALIAS
           ) :
            self.isTwiddled = True

        if (
            self.data_format == PvrTexture.TWIDDLED_MM or
            self.data_format == PvrTexture.PALETTIZE4_MM or
            self.data_format == PvrTexture.PALETTIZE8_MM or
            self.data_format == PvrTexture.ABGR_MM or
            self.data_format == PvrTexture.VQ_MM or
            self.data_format == PvrTexture.SMALLVQ_MM
           ) :
            self.isMipmap = True

        if (
            self.data_format == PvrTexture.SMALLVQ or
            self.data_format == PvrTexture.SMALLVQ_MM
           ) :
           self.codebook_size = self.get_codebook_size()
           self.isCompressed = True

        if (
            self.data_format == PvrTexture.VQ or
            self.data_format == PvrTexture.VQ_MM
           ) :
           self.isCompressed = True

        if (
            self.data_format == PvrTexture.PALETTIZE4 or
            self.data_format == PvrTexture.PALETTIZE4_MM or
            self.data_format == PvrTexture.PALETTIZE8 or
            self.data_format == PvrTexture.PALETTIZE8_MM or
            self.data_format == PvrTexture.STRIDE or
            self.data_format == PvrTexture.ABGR or
            self.data_format == PvrTexture.ABGR_MM
           ) :
            noesis.doException("Non supported pvr data format")

        self.mipWidth = self.width
        self.mipHeight = self.height
        if self.isCompressed:
            self.mipWidth = int(self.mipWidth / 2)
            self.mipHeight = int(self.mipHeight / 2)
        self.dst_array = [None] * (self.mipWidth * self.mipHeight)
        return 1

    def debug(self):
        print("TexId: ", self.texId)
        print("Data format: ", self.data_format)
        print("isTwiddled: ", self.isTwiddled)
        print("vqCompressed: ", self.isCompressed)
        print("isMipmap: ", self.isMipmap)
        print("Codebook Size: ", self.codebook_size)
        print("")

    def get_mipmap_size(self):
        mipCount = 0
        seek_ofs = 0
        width = self.width

        while width :
            mipCount = mipCount + 1
            width = int(width / 2)

        while mipCount:
            mipWidth = (self.width >> (mipCount - 1))
            mipHeight = (self.height >> (mipCount - 1))
            mipSize = mipWidth * mipHeight

            mipCount = mipCount - 1

            if mipCount > 0:
                if self.isCompressed:
                    seek_ofs = seek_ofs + int(mipSize / 4)
                else:
                    seek_ofs = seek_ofs + (PvrTexture.WORD_SIZE * mipSize)
            else:
                if self.isCompressed:
                    seek_ofs = seek_ofs + 1
                else:
                    seek_ofs = seek_ofs + PvrTexture.WORD_SIZE
        return seek_ofs

    def create_bitmap(self):
        tmp_bitmap = []
        if self.isCompressed:
            cb_len = PvrTexture.WORD_SIZE
            cb_len = cb_len * PvrTexture.CODE_COMPONENTS
            cb_len = cb_len * self.codebook_size
            data = self.bs.readBytes(cb_len)
            self.codebook = NoeBitStream(data)
            data = self.bs.getBuffer(self.bs.tell(), self.bs.getSize())
            self.bs = NoeBitStream(data)

        if self.isMipmap:
            seek_ofs = self.get_mipmap_size()
            self.bs.seek(seek_ofs, NOESEEK_REL)
            data = self.bs.getBuffer(self.bs.tell(), self.bs.getSize())
            self.bs = NoeBitStream(data)

        if self.isTwiddled and self.mipWidth == self.mipHeight:
            self.dst_array = self.detwiddle(self.mipWidth, self.mipHeight)

        elif self.isTwiddled and self.mipWidth > self.mipHeight:
            width = int(self.mipWidth / 2)
            height = self.mipHeight

            one = self.detwiddle(width, height)
            self.bs.seek(int(self.bs.getSize() / 2), NOESEEK_ABS)
            data = self.bs.getBuffer(self.bs.tell(), self.bs.getSize())
            self.bs = NoeBitStream(data)
            two = self.detwiddle(width, height)

            idx1 = 0
            idx2 = 0
            for i in range(len(self.dst_array)):
                x = i % self.mipWidth
                if x < width:
                    self.dst_array[i] = one[idx1]
                    idx1 = idx1 + 1
                else:
                    self.dst_array[i] = two[idx2]
                    idx2 = idx2 + 1

        elif self.isTwiddled and self.mipWidth < self.mipHeight:
            width = self.mipWidth
            height = int(self.mipHeight / 2)

            one = self.detwiddle(width, height)
            self.bs.seek(int(self.bs.getSize() / 2), NOESEEK_ABS)
            data = self.bs.getBuffer(self.bs.tell(), self.bs.getSize())
            self.bs = NoeBitStream(data)
            two = self.detwiddle(width, height)

            idx1 = 0
            idx2 = 0
            for i in range(len(self.dst_array)):
                if i < width * height:
                    self.dst_array[i] = one[idx1]
                    idx1 = idx1 + 1
                else:
                    self.dst_array[i] = two[idx2]
                    idx2 = idx2 + 1

        else:
            for i in range(self.mipWidth*self.mipHeight):
                if self.isCompressed :
                    self.dst_array[i] = self.bs.readUByte()
                else :
                    self.dst_array[i] = self.bs.readUShort()

        if self.isCompressed:
            x = 0
            y = 0
            tmp = [None] * (self.width * self.height)

            for i in  range(len(self.dst_array)):
                idx = self.untwiddle(x, y)
                srcPos = self.dst_array[idx]
                srcPos = srcPos * PvrTexture.WORD_SIZE
                srcPos = srcPos * PvrTexture.CODE_COMPONENTS
                self.codebook.seek(srcPos, NOESEEK_ABS)

                for xOfs in range(2):
                    for yOfs in range(2):
                        idx = (y * 2 + yOfs) * self.width + (x * 2 + xOfs)
                        tmp[idx] = self.codebook.readUShort()

                x = x + 1
                if x >= self.mipWidth:
                    x = 0
                    y = y + 1
            self.dst_array = tmp

        for i in  range(len(self.dst_array)):
            if self.color_format == 0:
                color = self.dst_array[i]
                bitmap = self.ARGB_1555(color)
                tmp_bitmap.extend(bitmap)
            elif self.color_format == 1:
                color = self.dst_array[i]
                bitmap = self.ARGB_565(color)
                tmp_bitmap.extend(bitmap)
            elif self.color_format == 2:
                color = self.dst_array[i]
                bitmap = self.ARGB_4444(color)
                tmp_bitmap.extend(bitmap)
            else:
                print("Color format: ", self.color_format)
                noesis.doException("Non supported pvr color format")
        return struct.pack('B'*len(tmp_bitmap), *tmp_bitmap)

    def detwiddle(self, w, h):
        arr = [None] * (w * h)
        for y in range(h):
            for x in range(w):
                i = self.untwiddle(x, y)
                idx = y * h + x
                if self.isCompressed:
                    self.bs.seek(i * PvrTexture.BYTE_SIZE, NOESEEK_ABS)
                    arr[idx] = self.bs.readUByte()
                else:
                    self.bs.seek(i * PvrTexture.WORD_SIZE, NOESEEK_ABS)
                    arr[idx] = self.bs.readUShort()
        return arr

    def untwiddle(self, x, y):
        key = "{0}_{1}".format(x,y)
        if key in PvrTexture.LOOKUP_TABLE:
            return PvrTexture.LOOKUP_TABLE[key]
        def UntwiddleValue(val):
            untwiddled = 0
            for i in range(10):
                shift = int(math.pow(2, i))
                if val & shift :
                    untwiddled = untwiddled | (shift << i)
            return untwiddled

        pos = UntwiddleValue(y)  |  UntwiddleValue(x) << 1
        PvrTexture.LOOKUP_TABLE[key] = pos
        return pos

    def ARGB_1555 (self, v):
        a = 0xFF if (v & (1<<15)) else 0
        r = (v >> (10-3)) & 0xf8
        g = (v >> (5-3)) & 0xf8
        b = (v << 3) & 0xf8
        return [r,g,b,a]

    def ARGB_4444 (self, v):
        a = (v >> (12-4)) & 0xf0
        r = (v >> (8-4)) & 0xf0
        g = (v >> (4-4)) & 0xf0
        b = (v << 4) & 0xf0
        return [r,g,b,a]

    def ARGB_565(self, v):
        a = 0xff
        r = (v >> (11-3)) & (0x1f<<3)
        g = (v >> (5-2)) & (0x3f<<2)
        b = (v << 3) & (0x1f<<3)
        return [r,g,b,a]
