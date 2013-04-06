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
import time as t

HEX  = '0123456789abcdef';
HEX2 = dict((a+b, HEX.index(a)*16 + HEX.index(b)) for a in HEX for b in HEX);
CTYPES = {0: "BI_RGB", 1: "BI_RLE8", 2: "BI_RLE4", 3: "BI_BITFIELDS", 4: "BI_JPEG", 5: "BI_PNG"}


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
def pack_color(red, green, blue):
  '''Accepts bytes: 0-255. Returns a packed string'''
  return struct.pack('<BBB',blue,green,red)[::-1]


# Pack the HEX-color - Not used ATM
def pack_hex_color(hex_color):
  '''pack with HEX? IE: 'AA6600'. Returns a packed string'''
  hex_color = hex_color.lower()
  r,g,b = (HEX2[hex_color[0:2]], HEX2[hex_color[2:4]], HEX2[hex_color[4:6]])
  return pack_color(r, g, b)


class Bitmap(object):
  def __init__(self):
    self.wd = 0;
    self.ht = 0;
    self.depth = 24;
    self.pixels = []
    self.initalized = False;


  # Create a new bitmap of the given size and color
  def create(self, width, height, bkgd=(255,255,255)): 
    self.wd = int(ceil(width));
    self.ht = int(ceil(height));
    bkgd = pack_color(bkgd[0],bkgd[1],bkgd[2])
    for row in range(0,self.ht):
      self.pixels.append([bkgd] * self.wd)

    self.initalized = True; 


  # Open a bitmap using function: _loadFromSource
  def open(self, filename):
    if not(os.path.exists(filename)):
      raise IOError("File '%s' does not exist" % filename)
    if not(24 <= self.depth <= 32):
      raise SyntaxError("Not 24 or 32 bpp bitmap")

    rawpix = self._loadFromSource(filename)

    byte_length = self.wd*self.depth/8
    offset = (4-byte_length) % 4

    count = 4;
    for y in range(self.ht):
      col = []
      for x in range(self.wd):
        col.append(rawpix[count:count+3])
        count += 3
      count += offset;
      self.pixels.append(col)

    self.pixels.reverse()
    self.initalized = True

  # Save the bitmap
  def save(self, filename):
    if self.initalized:
      pix = []
      padding = row_padding(self.wd, self.depth)
      for i in reversed(self.pixels):
        pix.append("".join(i))
        pix.append(padding)

      header = self._writeBitMap()
      F = open(filename, 'wb')
      F.write(header + "".join(pix))
      F.close()


  # Set color of pixel(x,y) to what ever given.
  # Appending packed color to list is quicker then appending a tuple
  def setPixel(self, (x,y), c):
    if 0 < self.wd >= x and 0 < self.ht >= y:
      self.pixels[y][x] = pack_color(c[0], c[1], c[2])

  # Get color of pixel(x,y)
  def getPixel(self, x,y):
    if 0 < self.wd >= x and 0 < self.ht >= y:
      return struct.unpack('<BBB', self.pixels[y][x])

  def GetPixels(arr):
    pass

  def SetPixels(arr):
    pass

  # Stuff for getting dimensions
  def size(self): return (self.wd, self.ht);
  def width(self): return self.wd;
  def height(self): return self.ht;


  # Load a bitmap from a location on the computer
  def _loadFromSource(self, filename):
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
      self.wd = abs(struct.unpack("<i", b + "\x00\x00"))
      b = f.read(2)                                             # Height
      self.ht = abs(struct.unpack("<i", b + "\x00\x00"))
      b = f.read(2)                                             # Color planes
      #planes = struct.unpack("<i", b + "\x00\x00")
      b = f.read(2)                                             # BPP
      self.depth = struct.unpack("<i", b + "\x00\x00")
      compression = "BI_RGB"
      hres = None
      vres = None
      colorcount = None
      impcolors = None
    
    # WIN > 3.0 or OS/2 2.0 INFO
    elif hdr_len == 40:
      b = f.read(4)                                             # Width
      self.wd = abs(struct.unpack("<i", b)[0])
      b = f.read(4)                                             # Height
      self.ht = abs(struct.unpack("<i", b)[0])
      b = f.read(2)                                             # Color planes
      self.planes = struct.unpack("<i", b + "\x00\x00")[0]
      b = f.read(2)                                             # BBP
      self.depth = struct.unpack("<i", b + "\x00\x00")[0]
      b = f.read(4)                                             # Compression type
      try: compression = CTYPES[struct.unpack("<i", b)[0]]
      except: compression = "UNKNOWN"

      if compression != "BI_RGB":
        raise IOError("Unsupported BMP compression '%s'" % compression)

      b = f.read(4)                                             # Hres
      b = f.read(4)                                             # Vres
      b = f.read(4)                                             # Number of palette colors
      self.colorcount = struct.unpack("<i", b)[0]
      b = f.read(4)                                             # Number of important colors (generally unused)

    else:
      raise IOError("Unsupported bitmap header format")
    
    rawpixels = f.read()                                        # The rest is pixel data
    f.close()

    # Return whatever we need for later abuse
    return rawpixels;                  


  # Writing the binary bitmap before saving
  def _writeBitMap(self):
    header = "BM"
    header += struct.pack('<L', 54+256*4+self.wd*self.ht)  # DWORD size in bytes of the file
    header += struct.pack('<H', 0)                         # WORD 0
    header += struct.pack('<H', 0)                         # WORD 0
    header += struct.pack('<L', 54)                        # DWORD offset to the data
    header += struct.pack('<L', 40)                        # DWORD header size = 40
    header += struct.pack('<L', self.wd)                   # DWORD image width
    header += struct.pack('<L', self.ht)                   # DWORD image height
    header += struct.pack('<H', 1)                         # WORD planes = 1
    header += struct.pack('<H', self.depth)                # WORD bits per pixel
    header += struct.pack('<L', 0)                         # DWORD compression = 0
    header += struct.pack('<L', self.wd * self.ht)         # DWORD sizeimage = size in bytes of the bitmap = width * height 
    header += struct.pack('<L', 0)                         # DWORD horiz pixels per meter (?)
    header += struct.pack('<L', 0)                         # DWORD ver pixels per meter (?)
    header += struct.pack('<L', 0)                         # DWORD number of colors used = (?)
    header += struct.pack('<L', 0)                         # DWORD number of important colors

    return header;


# Now lets test it! :D
if __name__ == '__main__':
  
  bmp = Bitmap()
  bmp.create(1000, 1000, (20,100,240))
  #bmp.open("test.bmp")

  W,H = bmp.size();
  tx = t.time()
  for x in range(W):
    for y in range(H):
      o = bmp.getPixel(x,y) #bmp.setPixel((x,y), bmp.getPixel(x,y));
  print "Time used: %f sec" % (t.time()-tx)

  bmp.save('test.bmp')
