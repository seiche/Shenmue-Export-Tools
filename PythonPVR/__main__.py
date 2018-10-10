#==============================================================
"""
Power VR Python Tools
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

#Import Libraries
import os
import sys


#Import User Libraries
from pvmarchive import *

# Define main function
def main(filepath):

    #Check if filepath exists
    if not os.path.exists(filepath):
        return 1

    #Get file extension
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pvm":
        #PowerVR Archive filetype
        pvm = PvmArchive(filepath)
        pvm.writePngImages()

    elif ext == ".mt5":
        #Shenmue Model filetype
        hrc = ShenmueModel(filepath)
        hrc.writePngImages()

    else:
        print("Unkown file extension: %s"%ext)

    return 0

# Call main function
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python __main__.py <filename>")

    main(sys.argv[1])

#==============================================================
"""
Program End
"""
#==============================================================
