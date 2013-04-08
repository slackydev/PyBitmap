'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 Copyright (c) 2013 by Jarl Holta 
 
 PyBitmap is free software: You can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 - See: http://www.gnu.org/licenses/
 
 This modul only takes 24bit BMPs as it's now.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''
import struct, sys, os
from array import array
from math import ceil
import gc

# Compression types:
CTYPES = {0: "BI_RGB", 1: "BI_RLE8", 2: "BI_RLE4", 3: "BI_BITFIELDS", 4: "BI_JPEG", 5: "BI_PNG"}

# mode => bits and vice versa
MODE2BIT = { "L":8, "RGB":24, "RGBA":32 }
BIT2MODE = { 8:"L", 24:"RGB", 32:"RGBX"}

#Qucik convert lookup for hex to rgb
HEX  = '0123456789abcdef';
HEX2 = dict((a+b, HEX.index(a)*16 + HEX.index(b)) for a in HEX for b in HEX);

# Create the padding for each row (bmp requires this).
def row_padding(width, colordepth):
  '''returns any necessary row padding'''
  byte_length = width*colordepth/8
  padding = (4-byte_length) % 4
  padbytes = ''
  for i in range(padding):
    x = struct.pack('<B',0)
    padbytes += x
  return padbytes


# Pack the color
def pack_RGB(r, g, b):
  '''Accepts bytes: 0-255. Returns a packed string'''
  return struct.pack('<BBB',b,g,r)

# Pack the HEX-color - Not used ATM
def pack_hex_color(hex_color):
  '''pack with HEX? IE: 'AA6600'. Returns a packed string'''
  hex_color = hex_color.lower()
  r,g,b = (HEX2[hex_color[0:2]], HEX2[hex_color[2:4]], HEX2[hex_color[4:6]])
  return pack_RGB(r, g, b)

  
# Writing the binary bitmap before saving
def _constructHeader(W,H,BPP):
  header = "BM"
  header += struct.pack('<L', 54+256*4+W*H)       # DWORD size in bytes of the file
  header += struct.pack('<H', 0)                  # WORD 0
  header += struct.pack('<H', 0)                  # WORD 0
  header += struct.pack('<L', 54)                 # DWORD offset to the data
  header += struct.pack('<L', 40)                 # DWORD header size = 40
  header += struct.pack('<L', W)                  # DWORD image width
  header += struct.pack('<L', H)                  # DWORD image height
  header += struct.pack('<H', 1)                  # WORD planes = 1
  header += struct.pack('<H', BPP)                # WORD bits per pixel
  header += struct.pack('<L', 0)                  # DWORD compression = 0
  header += struct.pack('<L', W * H)              # DWORD sizeimage = size in bytes of the bitmap = width * height 
  header += struct.pack('<L', 0)                  # DWORD horiz pixels per meter (?)
  header += struct.pack('<L', 0)                  # DWORD ver pixels per meter (?)
  header += struct.pack('<L', 0)                  # DWORD number of colors used = (?)
  header += struct.pack('<L', 0)                  # DWORD number of important colors
  return header;

  
# Load a bitmap from a location on the computer
def _loadFromSource(filename):
  f = open(filename)
  b = f.read(2)                                               # Bitmap format
  if not b in ["BM", "BA", "CI", "CP", "IC", "PT"]:
    raise SyntaxError("Not a BMP file")
     
  b = f.read(4)                                               # Shit
  b = f.read(4)                                               # Shit
  b = f.read(4)                                               # Shit
  b = f.read(4)                                               # Header length
  hdr_len = struct.unpack("<i", b)[0]
    
  # OS/2 1.0 core   
  if hdr_len == 12:
    b = f.read(2)                                             # Width
    width = abs(struct.unpack("<i", b + "\x00\x00"))
    b = f.read(2)                                             # Height
    height = abs(struct.unpack("<i", b + "\x00\x00"))
    b = f.read(2)                                             # Color planes
    #planes = struct.unpack("<i", b + "\x00\x00")
    b = f.read(2)                                             # BPP
    depth = struct.unpack("<i", b + "\x00\x00")
    compression = "BI_RGB"
    hres = None
    vres = None
    colorcount = None
    impcolors = None
    
  # WIN > 3.0 or OS/2 2.0 INFO
  elif hdr_len == 40:
    b = f.read(4)                                             # Width
    width = abs(struct.unpack("<i", b)[0])
    b = f.read(4)                                             # Height
    height = abs(struct.unpack("<i", b)[0])
    b = f.read(2)                                             # Color planes
    #planes = struct.unpack("<i", b + "\x00\x00")[0]
    b = f.read(2)                                             # BBP
    depth = struct.unpack("<i", b + "\x00\x00")[0]
    b = f.read(4)                                             # Compression type
    try: compression = CTYPES[struct.unpack("<i", b)[0]]
    except: compression = "UNKNOWN"

    if compression != "BI_RGB":
      raise IOError("Unsupported BMP compression '%s'" % compression)

    b = f.read(4)                                             # Hres
    b = f.read(4)                                             # Vres
    b = f.read(4)                                             # Number of palette colors
    #colors = struct.unpack("<i", b)[0]
    b = f.read(4)                                             # Number of important colors (generally unused)
    b = f.read(4)                                             # I don't know why I had to add this.
  else: raise IOError("Unsupported bitmap header format")
    
  rawpixels = f.read()                                        # The rest is pixel data
  f.close()
  # Return whatever we need for later abuse
  return (width,height,depth,rawpixels);

 
# flipping the bitmapbuffer horizontal (cols, rows = W,H).
def flipBitmap(rawpix, cols, rows, depth=24):
  size = rows*(cols*(depth/8))
  bpr = len(rawpix) / rows
  temp = []
  i = 0
  while i < size:
    temp.append(rawpix[i:i+bpr])
    i += bpr
  return "".join(reversed(temp))
    
    
# The class that lates you work with bitmaps
#  
class Bitmap(object):
  def __init__(self):
    self.wd = -1;
    self.ht = -1;
    self.depth = 24;
    self.pixels = ''
    self.rawpix = ''
    self.bpr = 0
    self.initalized = False;
    

  # Create a new bitmap of the given size and background color
  def create(self, width, height, mode='RGB', bkgd=(255,255,255)): 
    if (width <= 0 and height <= 0):
      raise SyntaxError("Width and height must be positive")
    if (mode not in MODE2BIT):
      raise SyntaxError("Unknown mode '%s'. Allowed modes: 'L', 'RGB' or 'RGBA'" % mode)
    self.depth = MODE2BIT[mode]
    self.wd = int(ceil(width))
    self.ht = int(ceil(height))
    
    bkgd = pack_RGB(bkgd[0],bkgd[1],bkgd[2])
    tmpdata = []
    tmprow  = (bkgd * self.wd)
    padding = row_padding(self.wd, self.depth)
    for _ in xrange(self.ht):
      tmpdata.append(tmprow + padding)
    self.rawpix = "".join(tmpdata) 
    self.pixels = array('c', self.rawpix)
    self.bpr = len(self.pixels) / self.ht
    self.initalized = True; 
  
  
  # Create a bitmap from raw bitmap meteria
  # EG: A windows buffer bitmap
  def fromBuffer(self, rawpix, size, depth=24, reverse=True):
    self.wd = size[0]
    self.ht = size[1]
    self.depth = depth 
    if not(reverse): self.rawpix = rawpix
    else: self.rawpix = flipBitmap(rawpix, self.wd, self.ht, self.depth)
    self.pixels = array('c', self.rawpix)
    self.bpr = len(self.pixels) / self.ht
    self.initalized = True

    
  # Open a bitmap using function: _loadFromSource
  def open(self, filename):
    if not(os.path.exists(filename)):
      raise IOError("File '%s' does not exist" % filename)

    bmp = _loadFromSource(filename)
    self.wd = bmp[0]
    self.ht = bmp[1]
    self.depth = bmp[2]
    self.rawpix = flipBitmap(bmp[3], self.wd, self.ht, self.depth)
    self.pixels = array('c', self.rawpix)
    self.bpr = len(self.pixels) / self.ht
    self.initalized = True
    
    
  # Save the bitmap to any location on the computer
  def save(self, filename):
    if self.initalized:
      header = _constructHeader(self.wd, self.ht, self.depth)
      F = open(filename, 'wb')
      F.write(header + flipBitmap(self.rawpix, self.wd, self.ht, self.depth))
      F.close()

      
  # writeData() allows you to store the colordata after modification 
  # in to our "real" pixelmap so it can later be used by getPixel()
  def writeData(self):
    if self.initalized:
      self.rawpix = self.pixels.tostring()

  # discardData() allows you to remove the modification made by setPixel() 
  # This way you will be able to avoid mistakes, and we just really need this.
  def dropData():
    if self.initalized:
      self.pixels = array('c', self.rawpix)
      

  # Set color of pixel(x,y).
  # Appending packed color to array is quicker then appending to raw
  def setPixel(self, (x,y), c):
    if 0 < self.wd >= x and 0 < self.ht >= y:
      pos = (y*self.bpr) + (x*3)
      pack = pack_RGB(c[0], c[1], c[2])
      self.pixels[pos] = pack[0]
      self.pixels[pos+1] = pack[1]
      self.pixels[pos+2] = pack[2]


  # Get color of pixel(x,y) - reading from rawdata
  def getPixel(self, x,y):
    if 0 < self.wd >= x and 0 < self.ht >= y:
      pos = (y*self.bpr) + (x*3)
      b,g,r = struct.unpack('<BBB', self.rawpix[pos:pos+3])
      return r,g,b
      

  def GetPixels(arr):
    pass

  def SetPixels(arr):
    pass

  # Stuff for getting dimensions
  def size(self): return (self.wd, self.ht);
  def width(self): return self.wd;
  def height(self): return self.ht;
  
  # I do not see why.. but okay. Let's just...
  def free(self):
    W = H = -1
    self.initalized = False
    self.pixels = self.rawpix = ''
    gc.collect()

# Take it for a spin..!
if __name__ == '__main__':
  bmp = Bitmap()
  bmp.create(1000, 1000, 'RGB', bkgd=(20,100,240))
  #bmp.open("test.bmp")
  
  #One million iterations with set and GetPixel
  W,H = bmp.size()
  for x in range(W):
    for y in range(H):
        bmp.setPixel((0,0), bmp.getPixel(0,0))
  bmp.writeData
  bmp.save('test.bmp')
