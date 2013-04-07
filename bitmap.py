'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 Copyright (c) 2013 by Jarl Holta 
 
 PyBitmap is free software: You can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 See: http://www.gnu.org/licenses/
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''
import struct, sys, os
from math import ceil

HEX  = '0123456789abcdef';
HEX2 = dict((a+b, HEX.index(a)*16 + HEX.index(b)) for a in HEX for b in HEX);

# Compression types:
CTYPES = {0: "BI_RGB", 1: "BI_RLE8", 2: "BI_RLE4", 3: "BI_BITFIELDS", 4: "BI_JPEG", 5: "BI_PNG"}

# mode => bits and vice versa
MODE2BIT = { "1":1, "P":8, "RGB":24, "RGBA":32 }
BIT2MODE = { 1:("1",'<B'), 8:("P",'<B'), 24:("RGB",'<BBB'), 32:("RGBA",'<BBBB')}


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
  header += struct.pack('<L', 54+256*4+W*H)       # DWORD size in bytes
  header += struct.pack('<H', 0)                  # WORD 0
  header += struct.pack('<H', 0)                  # WORD 0
  header += struct.pack('<L', 54)                 # DWORD offset..
  header += struct.pack('<L', 40)                 # DWORD header size = 40
  header += struct.pack('<L', W)                  # DWORD image width
  header += struct.pack('<L', H)                  # DWORD image height
  header += struct.pack('<H', 1)                  # WORD planes = 1
  header += struct.pack('<H', BPP)                # WORD bits per pixel
  header += struct.pack('<L', 0)                  # DWORD compression = 0
  header += struct.pack('<L', W * H)              # DWORD sizeImage = W*H
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
    colorcount = struct.unpack("<i", b)[0]
    b = f.read(4)                                             # Number of important colors (generally unused)
  else:
    raise IOError("Unsupported bitmap header format")
    
  rawpixels = f.read()                                        # The rest is pixel data
  f.close()
  # Return whatever we need for later abuse
  return (width,height,depth,rawpixels);

  
# Create a bitmap from raw pixel materia, size, and bpp
def _fromRaw(rawpix, size, depth, reverse=True):
  length = depth/8
  if length == 0: length = 1;
  byte_length = size[0]*length
  offset = (4-byte_length) % 4

  if depth == 32: count = 0;
  else: count = 1;
  if depth<=8: colors = 1;
  else: colors = 3;
    
  pixels = []
  for y in xrange(size[1]):
    col = []
    count += offset;
    for x in xrange(size[0]):
      col.append(rawpix[count:count+colors])
      count += length
    pixels.append(col)
      
  if reverse == True: pixels.reverse()   
  return pixels
    

# The class that lates you work with bitmaps
#  
class Bitmap(object):
  def __init__(self):
    self.wd = 0;
    self.ht = 0;
    self.depth = 24;
    self.pixels = []
    self.initalized = False;


  # Create a new bitmap of the given size and background color
  def create(self, width, height, mode='RGB', bkgd=(255,255,255)): 
    if (mode not in MODE2BIT):
      raise SyntaxError("Unknown mode '%s'. Allowed modes: '1', 'P', 'RGB' or 'RGBA'" % mode)
    self.depth = MODE2BIT[mode]
    self.wd = int(ceil(width))
    self.ht = int(ceil(height))
    
    if mode == 'P' or mode == '1': bkgd = struct.pack('<B', bkgd)
    else: bkgd = pack_RGB(bkgd[0],bkgd[1],bkgd[2])
    
    for row in range(0,self.ht):
      self.pixels.append([bkgd] * self.wd)

    self.initalized = True; 
  
  
  # Create a bitmap from raw bitmap meteria
  # EG: A windows buffer bitmap
  def fromBuffer(self, rawpix, size, depth=24, reverse=False):
    self.wd = size[0]
    self.ht = size[1]
    
    self.pixels = _fromRaw(rawpix, size, depth, reverse)
    self.initalized = True

    
  # Open a bitmap using function: _loadFromSource
  def open(self, filename):
    if not(os.path.exists(filename)):
      raise IOError("File '%s' does not exist" % filename)

    bmp = _loadFromSource(filename)
    self.wd = bmp[0];
    self.ht = bmp[1];
    self.depth = bmp[2];
    rawpix = bmp[3];
    
    self.pixels = _fromRaw(rawpix, (self.wd,self.ht), self.depth, True)
    self.initalized = True

    
  # Save the bitmap to any location on the computer
  def save(self, filename):
    if self.initalized:
      pix = []
      padding = row_padding(self.wd, self.depth)
      for i in reversed(self.pixels):
        pix.append("".join(i));
        pix.append(padding);

      header = _constructHeader(self.wd, self.ht, self.depth)
      F = open(filename, 'wb')
      F.write(header + "".join(pix))
      F.close()


  # Set color of pixel(x,y) to what ever given.
  # Appending packed color to list is quicker then appending a tuple
  def setPixel(self, (x,y), c):
    if 0 < self.wd >= x and 0 < self.ht >= y:
      if self.depth == 8: pixel = struct.pack('<B', c)
      else: pixel = pack_RGB(c[0], c[1], c[2])
      self.pixels[y][x] = pixel

  # Get color of pixel(x,y)
  def getPixel(self, x,y):
    if 0 < self.wd >= x and 0 < self.ht >= y:
      bitstring = BIT2MODE[self.depth][1];
      if self.depth == 8: return struct.unpack('<B', self.pixels[y][x])[0]
      return struct.unpack('<BBB', self.pixels[y][x])[::-1]

  def GetPixels(arr):
    pass

  def SetPixels(arr):
    pass

  # Stuff for getting dimensions
  def size(self): return (self.wd, self.ht);
  def width(self): return self.wd;
  def height(self): return self.ht;


# Take it for a spin..!
if __name__ == '__main__':
  bmp = Bitmap()
  bmp.create(1000, 1000, 'RGB', bkgd=(20,100,240))
  #bmp.open("test.bmp")

  W,H = bmp.size();
  bmp.setPixel((0,0), (10,250,30))
  print bmp.getPixel(0,0)

  bmp.save('test.bmp')
