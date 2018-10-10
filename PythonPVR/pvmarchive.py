#==============================================================
"""

PvmArchive Class
Class for parsing and interfacing with power vr archives

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

import os
import png
import math
from PIL import Image
from bitstream import BitStream

BIT_0 = 0x01
BIT_1 = 0x02
BIT_2 = 0x04
BIT_3 = 0x08

class PvmArchive:

    #File Format Constants
    PVMH = 0x484D5650
    PVRT = 0x54525650

    def __init__(self, filepath):
        self.bs = BitStream(filepath)
        self.texList = self.readHeader()
        print(self.texList)

    def readHeader(self):
        #Create array
        texList = []

        #Check for PVMH file header
        iff = self.bs.readUInt()
        if iff != PvmArchive.PVMH:
            return 0

        #Offset of first texture entry
        texOfs = self.bs.readUInt()
        self.bs.setOffset()

        #Read flags and number of textures
        flags = self.bs.readUShort()
        nbTex = self.bs.readUShort()

        for i in range(nbTex):
            tex = { 'id' : self.bs.readUShort() }

            if flags & BIT_3:
                #Filename bit flag
                tex['name'] = self.bs.readStr(0x1C)
            if flags & BIT_2:
                #File format bitflag
                tex['format'] = self.bs.readUShort()
            if flags & BIT_1:
                #File dimensions bit flag
                tex['size'] = self.bs.readUShort()
            if flags & BIT_0:
                #Global Index bit flag
                tex['index'] = self.bs.readUInt()

            texList.append(tex)

        self.bs.seek_set(texOfs)
        return texList

    def writePngImages(self):

        #Loop through each texture
        for tex in self.texList:

            self.bs.seek_set(0)
            offset = self.bs.tell() % 4
            self.bs.seek_cur(offset)

            #Look for PVRT file header
            if not self.bs.find(PvmArchive.PVRT):
                #If not found, raise an error
                print("PVRT not found: 0x%x"%self.bs.tell())
                return 0

            #Length of pvr texture
            pvrLen = self.bs.readUInt()
            self.bs.setOffset()

            #Create PvrImage to convert bitmap
            print("Name: %s, Pos: 0x%x"%(tex['name'],self.bs.tell()))
            pvr = PvrTexture(self.bs, False, True)
            bitmap = pvr.getBitmap()
            imgName = "output/" + tex['name'] + '.png'
            png.from_array(bitmap, 'RGBA').save(imgName)

            #img = Image.open(imgName)
            #img = img.rotate(180)
            #img.save(imgName)

            print("")

        return 1


#==============================================================
"""
Shenmue Model Class
SHenmue contains textures inside the model file, this class
read the internal PVR Textures and exports them as PNG
"""
#==============================================================

class ShenmueModel:

    HRCM = 0x4D435248
    TEXD = 0x44584554
    PVRT = 0x54525650

    def __init__(self, filepath):
        self.fp = os.path.basename(filepath)
        self.bs = BitStream(filepath)
        self.iff = self.bs.readUInt()
        self.texOfs = self.bs.readUInt()

    def writePngImages(self):
        #Seek to texture offset
        self.bs.seek_set(self.texOfs)

        #Check offset for texture definition
        iff = self.bs.readUInt()
        if iff != ShenmueModel.TEXD:
            return 0
        iffLen = self.bs.readUInt()
        #Read number of textures
        nbTex = self.bs.readUInt()
        texBase = os.path.splitext(self.fp)[0]

        #Loop through each texture
        for i in range(nbTex):

            #Look for pvr file header
            if not self.bs.find(ShenmueModel.PVRT):
                return 0

            #Length of pvrFile
            pvrLen = self.bs.readUInt()
            pvr = PvrTexture(self.bs, False, True)
            bitmap = pvr.getBitmap()

            if len(bitmap) == 0:
                continue

            texName = "output/%s_%02d.png" % (texBase, i)
            print(texName)
            png.from_array(bitmap, 'RGBA').save(texName)

        return 1


#==============================================================
"""
PvrTexture Class
Class for converting PVR Textures to RGBA bitmaps

-= Color Format Reference =-
ARGB_1555             = 0x00
RGB_565               = 0x01
ARGB_4444             = 0x02
YUV_422               = 0x03
BUMP	              = 0x04
RGB_555               = 0x05
ARGB_8888             = 0x06
YUV_420               = 0x06

-= Data Format Reference  =-
TWIDDLED	          = 0x01
TWIDDLED_MM           = 0x02
VQ	                  = 0x03
VQ_MM	              = 0x04
PALETTIZE4	          = 0x05
PALETTIZE4_MM         = 0x06
PALETTIZE8	          = 0x07
PALETTIZE8_MM         = 0x08
RECTANGLE	          = 0x09
STRIDE	              = 0x0B
TWIDDLED_RECTANGLE    = 0x0D
ABGR			      = 0x0E
ABGR_MM			      = 0x0F
SMALLVQ               = 0x10
SMALLVQ_MM            = 0x11
TWIDDLED_MM_ALIAS     = 0x12

"""
#==============================================================

class PvrTexture:

    #Conversion constants
    BYTE_SIZE       = 1
    WORD_SIZE       = 2
    CODE_COMPONENTS = 4
    LOOKUP_TABLE    = {}

    #Flag test lists
    RECTANGLE       =   0x09
    SMALLVQ_LIST    = [ 0x10, 0x11 ]
    TWIDDLED_LIST   = [ 0x01, 0x02, 0x0D, 0x12 ]
    VECTOR_LIST     = [ 0x03, 0x04, 0x10, 0x11 ]
    MIPMAP_LIST     = [ 0x02, 0x04, 0x06, 0x08, 0x0F, 0x11, 0x12 ]
    UNSUPPORTED     = [ 0x05, 0x06, 0x07, 0x08, 0x0B, 0x0E, 0x0F ]

    def __init__(self, bs, flipX = False, flipY = False):
        self.bs = bs
        self.flipX = flipX
        self.flipY = flipY
        self.color_format = self.bs.readByte()
        self.data_format  = self.bs.readByte()
        self.bs.seek_cur(0x02)
        self.width  = self.bs.readUShort()
        self.height = self.bs.readUShort()
        self.flags  = self.setTexFlags()
        self.bitmap = self.createBitmap()

    def getBitmap(self):
        return self.bitmap

    def setTexFlags(self):
        #Abbreviate data format
        df = self.data_format

        # Create data flags dict
        flags = {
            'codebook_size' : 256,
            'isMipmap'      : df in PvrTexture.MIPMAP_LIST,
            'isCompressed'  : df in PvrTexture.VECTOR_LIST,
            'isTwiddled'    : df in PvrTexture.TWIDDLED_LIST,
            'isRectangle'   : df == PvrTexture.RECTANGLE
        }

        #If not custom codebook size return
        if df not in PvrTexture.SMALLVQ_LIST:
            return flags

        #Look up small codebook size
        if  self.width <= 16:
            flags['codebook_size'] = 16
        elif self.width == 32 and not flags['isMipmap']:
            flags['codebook_size'] = 32
        elif self.width == 32 and flags['isMipmap']:
            flags['codebook_size'] = 64
        elif self.width == 64 and not flags['isMipmap']:
            flags['codebook_size'] = 128

        return flags

    def createBitmap(self):
        #Codebook array for VQ
        codebook = []

        #Mipwidth and height
        mipWidth  = self.width
        mipHeight = self.height

        #Set offset after reading flags
        self.bs.setOffset()

        #VQ Compression read codebook in array
        if self.flags['isCompressed']:
            print("Reading VQ codebook")

            #Each codebook is 2x2
            mipWidth = mipWidth / 2
            mipHeight = mipHeight / 2

            #Read each codebook entry
            for i in range(self.flags['codebook_size']):
                codebook.append(self.readCodebookEntry())

            #Set offset for seek absolute
            self.bs.setOffset()

        #Read past smaller mipmap offsets
        if self.flags['isMipmap']:
            print("Seeking past mipmap data")
            seekOfs = self.getMipmapSize()
            self.bs.seek_cur(seekOfs)

            #Set offset for seek absolute
            self.bs.setOffset()

        #Detwiddle texture data
        if self.flags['isTwiddled']:

            #Square texture
            if mipWidth == mipHeight:
                #Detwiddle image data
                print("Square twiddled")
                dstArray = self.detwiddle(mipWidth, mipHeight)

            #Rectangular (wide) texture
            elif mipWidth > mipHeight:
                print("Rectangle (wide) Twiddled")
                width = int(mipWidth/2)
                height = mipHeight

                if self.width != self.height*2:
                    print("Returning none (wide)")
                    return []

                #Left Array
                self.bs.seek_set(0)
                leftArray  = self.detwiddle(width, height)
                print("Left Array: %d"%len(leftArray))

                #Seek to end of left array
                self.bs.seek_set(width * height * 2)
                self.bs.setOffset()

                #Right Array
                rightArray = self.detwiddle(width, height)
                print("Right Array: %d"%len(rightArray))
                #Merge the two arrays together

                bitmap = []
                for y in range(self.height):
                    line = []

                    for x in range(self.width/2):
                        line.append(leftArray.pop(0))

                    for x in range(self.width/2):
                        line.append(rightArray.pop(0))

                    row = []
                    if self.flipX:
                        for pixel in reversed(line):
                            row.extend(pixel)
                    else:
                        for pixel in line:
                            row.extend(pixel)

                    if self.flipY:
                        bitmap.insert(0, row)
                    else:
                        bitmap.append(row)

                return bitmap
            #Rectangular (tall) texture
            elif mipWidth < mipHeight:
                print("Rectangle (tall) Twiddled")

                if self.width*2 != self.height:
                    print("Returning none (tall)")
                    return []

                #Top Array
                self.bs.seek_set(0)
                topArray = self.detwiddle(mipWidth, mipWidth)

                #Seek to end of left array
                self.bs.seek_set(mipWidth * mipHeight)
                self.bs.setOffset()

                #Bottom Array
                bottomArray = self.detwiddle(mipWidth, mipWidth)

                #Merge the two arrays together
                bitmap = []
                print(len(topArray))
                print(len(bottomArray))
                print(self.width * self.height)
                print("Height: %d Width: %d"%(self.height, self.width))
                topLength = len(topArray)

                #topArray + bottomArray
                for y in range(self.width):
                    line = []
                    for x in range(self.width):
                        line.append(topArray.pop(0))

                    row = []
                    if self.flipX:
                        for pixel in reversed(line):
                            row.extend(pixel)
                    else:
                        for pixel in line:
                            row.extend(pixel)

                    if self.flipY:
                        bitmap.insert(0, row)
                    else:
                        bitmap.append(row)

                for y in range(self.width):
                    line = []
                    for x in range(self.width):
                        line.append(bottomArray.pop(0))

                    row = []
                    if self.flipX:
                        for pixel in reversed(line):
                            row.extend(pixel)
                    else:
                        for pixel in line:
                            row.extend(pixel)

                    if self.flipY:
                        bitmap.insert(0, row)
                    else:
                        bitmap.append(row)

                #print(bitmap)
                return bitmap

            bitmap = self.convert2dArray(dstArray)
            return bitmap

        #Create image from Codebook
        if self.flags['isCompressed']:
            print("VQ Compressed Decode")

            #Decoded order of image data
            imgData = self.detwiddle(mipWidth, mipHeight)
            #Array to put data into
            dstArray = [None] * (self.width * self.height)
            #Destination position in dstArray
            x , y = 0 , 0
            for index in imgData:

                #Get codebook entry
                color = codebook[index]
                #Assign 2x2 pixels for codebook entry
                n = 0
                for xOfs in range(2):
                    for yOfs in range(2):
                        i = (y * 2 + yOfs) * self.width + (x * 2 + xOfs)
                        dstArray[i] = color[n]
                        n += 1
                #Incement destination position
                x += 1
                if x == mipWidth:
                    x = 0
                    y += 1

            bitmap = self.convert2dArray(dstArray)
            return bitmap

        elif self.flags['isRectangle']:
            dstArray = []

            for y in range(self.height):
                for x in range(self.width):

                    short = self.bs.readUShort()
                    color = self.convertColor(short)

                    dstArray.append(color)

            bitmap = self.convert2dArray(dstArray)
            return bitmap
        #Unsupported data format
        else:
            print("Unknown format error")
            print("Data format:", self.data_format)
            print(self.flags)
            return 0

        return 1

    def convert2dArray(self, array):
        bitmap = []

        for y in range(self.height):
            line = []

            for x in range(self.width):
                line.append(array[y * self.height + x])

            row = []
            if self.flipX:
                for pixel in reversed(line):
                    row.extend(pixel)
            else:
                for pixel in line:
                    row.extend(pixel)

            if self.flipY:
                bitmap.insert(0, row)
            else:
                bitmap.append(row)

        return bitmap

    def readCodebookEntry(self):
        #Read short for each entry
        a = self.bs.readUShort()
        b = self.bs.readUShort()
        c = self.bs.readUShort()
        d = self.bs.readUShort()
        #Convert short to colors
        a = self.convertColor(a)
        b = self.convertColor(b)
        c = self.convertColor(c)
        d = self.convertColor(d)
        #Return entry tupple
        return (a, b, c, d)

    def getMipmapSize(self):
        mipCount = 0
        seekOfs = 0
        width = self.width

        #Find number of mipmaps
        while width:
            mipCount = mipCount + 1
            width = int(width / 2)

        #For each map increment seekOfs
        while mipCount:
            #Calculate mipmap dimensions
            mipWidth  = self.width  >> (mipCount - 1)
            mipHeight = self.height >> (mipCount - 1)
            mipSize = mipWidth * mipHeight

            #Decremement mipCount
            mipCount -= 1

            #Seek past mipmap area
            if mipCount > 0:
                if self.flags['isCompressed']:
                    seekOfs += int(mipSize / PvrTexture.CODE_COMPONENTS)
                else:
                    seekOfs += PvrTexture.WORD_SIZE * mipSize
            #Seek past 1x1 Mipmap
            else:
                if self.flags['isCompressed']:
                    seekOfs += PvrTexture.BYTE_SIZE
                else:
                    seekOfs += PvrTexture.WORD_SIZE

        #Return offset to seek past
        return seekOfs

    def detwiddle(self, width, heigth):
        #Create a temporary array
        array = [None] * (width * heigth)

        #Loop over each row
        for y in range(heigth):
            #Loop over each column
            for x in range(width):
                #Get untwiddled location
                i = self.untwiddle(x, y)

                #Seek to location and read to index
                if self.flags['isCompressed']:
                    #For VQ only change order to be decoded
                    self.bs.seek_set(i * PvrTexture.BYTE_SIZE)
                    array[y * heigth + x] = self.bs.readByte()
                else:
                    #For normal twiddled convert the color
                    self.bs.seek_set(i * PvrTexture.WORD_SIZE)
                    short = self.bs.readUShort()
                    array[y * heigth + x] = self.convertColor(short)

        #Return detwiddled array
        return array

    def untwiddle(self, x, y):
        #String key for lookup table
        key = "%d:%d"%(x,y)

        #Use value if found in lookup table
        if key in PvrTexture.LOOKUP_TABLE:
            return PvrTexture.LOOKUP_TABLE[key]

        #Internal function to calculate position
        def untwiddleValue(val):
            untwiddled = 0
            for i in range(10):
                shift = int(math.pow(2, i))
                if val & shift :
                    untwiddled = untwiddled | (shift << i)
            return untwiddled

        #Get position from internal function
        pos = untwiddleValue(y)  |  untwiddleValue(x) << 1
        #Set position to lookup table
        PvrTexture.LOOKUP_TABLE[key] = pos
        #Return converted position
        return pos

    def convertColor(self, short):
        #Color format constants
        ARGB_1555 = 0x00
        ARGB_0565 = 0x01
        ARGB_4444 = 0x02

        if self.color_format == ARGB_1555:
            a = 0xFF if (short & (1<<15)) else 0
            r = (short >> 7) & 0xf8
            g = (short >> 2) & 0xf8
            b = (short << 3) & 0xf8
        elif self.color_format == ARGB_0565:
            a = 0xff
            r = (short >> 8) & (0x1f<<3)
            g = (short >> 3) & (0x3f<<2)
            b = (short << 3) & (0x1f<<3)
        elif self.color_format == ARGB_4444:
            a = (short >> 8) & 0xf0
            r = (short >> 4) & 0xf0
            g = (short >> 0) & 0xf0
            b = (short << 4) & 0xf0
        else:
            #Unsupported color type
            return 0

        #Return color tupple
        return (r, g, b, a)




#==============================================================
"""
Program End
"""
#==============================================================
