'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 Copyright (c) 2013 by Jarl Holta 
 
 PyBitmap is free software: You can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 - See: http://www.gnu.org/licenses/
 
 PyBitmap is written for PyPy but is compatibe with CPython but the 
 speed when running in CPython in this case is garbage.
 
 This modul only takes 24bit (32bit might WORK) BMPs as it's now.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''
import struct, sys, os
from array import array
import gc, base64

''' Convert a image to a string '''
def ImageToString(image):
    img = Bitmap()
    img.open(image)
    W, H = str(img.width()), str(img.height())
    raw = img._raw()
    encoded = base64.b64encode(raw)
    i = 0
    name = image.split(os.sep)[-1].split('.')[0]
    print name + " = Bitmap()"
    while i<len(encoded):
      if i == 0:
         col = 75 - len(name+".fromString(("+W+","+H+"), ") + 4
         print name + ".fromString(("+W+","+H+"), '" + str(encoded[i:i+col]) + "' +"
         i += col
      elif i+75>=len(encoded):
        print "\t'" + str(encoded[i:i+75]) + "')"
        i += 75
      else:
        print "\t'" + str(encoded[i:i+75] +"' +") 
        i += 75


# Compression types:
CTYPES = {0: "BI_RGB", 1: "BI_RLE8", 2: "BI_RLE4", 3: "BI_BITFIELDS", 4: "BI_JPEG", 5: "BI_PNG"}

# mode => bits and vice versa
MODE2BIT = { "L":8, "RGB":24, "RGBA":32 }
BIT2MODE = { 8:"L", 24:"RGB", 32:"RGBX"}

#Qucik convert lookup for hex to rgb
HEX  = '0123456789abcdef';
HEX2 = dict((a+b, HEX.index(a)*16 + HEX.index(b)) for a in HEX for b in HEX);

# Create the padding in order to bring up the length 
# of the rows to a multiple of four bytes.
def row_padding(width, colordepth):
  byte_length = width*colordepth/8
  padding = (4-byte_length) % 4
  padbytes = ''
  for i in range(padding):
    x = struct.pack('<B',0)
    padbytes += x
  return padbytes
  
# Writing the binary bitmap header before saving
# Windows Version 3 DIB Header specification
def _constructHeader(W,H,BPP,size):
  header = "BM"               
  header += struct.pack('<L', 54+(W*H*3))         # DWORD size in bytes of the file
  header += struct.pack('<H', 2)                  # WORD Reserved1
  header += struct.pack('<H', 2)                  # WORD Reserved2
  header += struct.pack('<L', 54)                 # DWORD offset to the data
  header += struct.pack('<L', 40)                 # DWORD header size = 40
  header += struct.pack('<L', W)                  # DWORD image width
  header += struct.pack('<L', H)                  # DWORD image height
  header += struct.pack('<H', 1)                  # WORD planes = 1
  header += struct.pack('<H', BPP)                # WORD bits per pixel
  header += struct.pack('<L', 0)                  # DWORD compression = 0
  header += struct.pack('<L', W * H)              # DWORD sizeimage = size in bytes of the bitmap = width * height 
  header += struct.pack('<L', 0)                  # DWORD horizontal pixels per meter
  header += struct.pack('<L', 0)                  # DWORD vertical pixels per meter
  header += struct.pack('<L', 0)                  # DWORD number of colors used = (?)
  header += struct.pack('<L', 0)                  # DWORD number of important colors
  return header;

  
# Load a bitmap from a location on the computer
# This might just need some work, as we are unable to load
# every image correctly.
def _loadFromSource(filename):
  f = open(filename, 'rb')

  b = f.read(2)                                         # Bitmap format
  if not b in ["BM", "BA", "CI", "CP", "IC", "PT"]:
    raise SyntaxError("Not a BMP file")
  
  # BITMAPFILEHEADER
  b = f.read(4)                                         # File size
  b = f.read(4)                                         # Reserved 1+2
  b = f.read(4)                                         # Offset to PixelArray
  #DIB Header...
  b = f.read(4)                                         # Header size
  hdr_len = struct.unpack("<i", b)[0]
  
  # OS/2 1.0 Info   
  if hdr_len == 12:
    b = f.read(2)                                       # Width
    width = abs(struct.unpack("<i", b + "\x00\x00")[0])
    b = f.read(2)                                       # Height
    height = abs(struct.unpack("<i", b + "\x00\x00")[0])
    b = f.read(2)                                       # Color planes
    b = f.read(2)                                       # BPP
    depth = struct.unpack("<i", b + "\x00\x00")[0]
    compression = "BI_RGB"
    
  # WIN > 3.0 or OS/2 2.0 Info
  elif hdr_len == 40:
    b = f.read(4)                                       # Width
    width = abs(struct.unpack("<i", b)[0])
    b = f.read(4)                                       # Height
    height = abs(struct.unpack("<i", b)[0])
    b = f.read(2)                                       # Color planes
    b = f.read(2)                                       # BBP
    depth = struct.unpack("<i", b + "\x00\x00")[0]
    b = f.read(4)                                       # Compression type
    try: compression = CTYPES[struct.unpack("<i", b)[0]]
    except: compression = "UNKNOWN"
    
    # Just some error handeling
    if compression != "BI_RGB":
      raise IOError("Unsupported BMP compression '%s'" % compression)
    if depth < 24:
      raise IOError("Unsupported amount of BPP '%s'" % depth)
      
    b = f.read(4)                                       # Image size
    b = f.read(4)                                       # Hrez = X Pixel per meter
    b = f.read(4)                                       # Vrez = Y Pixel per meter
    b = f.read(4)                                       # Num colors in color table
    b = f.read(4)                                       # Num important colors (generally unused)

  else:
    raise IOError("Unsupported bitmap header format")
  
  # We assume the rest is pixeldata...
  rawpixels = f.read()
  f.close()
  
  # Return whatever we need for later abuse
  return (width,height,depth,rawpixels)

 
# flipping the bitmapbuffer horizontal (cols, rows = W,H).
# This might be bugged as i'm cheating...
def flipBitmap(rawpix, cols, rows, depth=24):
  bpr = len(rawpix) / rows
  size = len(rawpix)-(bpr/2)
  temp = []
  i = 0
  while i < size: 
    temp.append(rawpix[i:i+bpr])
    i += bpr
  return "".join(reversed(temp))
    
    
# The class that lets you work with bitmaps
#  
class Bitmap(object):
  def __init__(self):
    self.wd = -1
    self.ht = -1
    self.depth = 24
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
    self.wd = int(width)
    self.ht = int(height)
    bkgd = struct.pack('<BBB', bkgd[0] & 0xFF, 
                              (bkgd[1] >> 8) & 0xFF, 
                              (bkgd[2] >> 16) & 0xFF)
    tmpdata = []
    tmprow  = (bkgd * self.wd)
    padding = row_padding(self.wd, self.depth)
    for _ in xrange(self.ht):
      tmpdata.append(tmprow + padding)
    self.rawpix = "".join(tmpdata) 
    self.pixels = array('c', self.rawpix)
    self.bpr = len(self.pixels) / self.ht
    self.initalized = True; 

    
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
  
  
  # Create a bitmap from raw bitmap meteria
  # EG: A windows buffer bitmap
  def fromBuffer(self, rawpix, size, depth=24, reverse=True):
    self.wd = size[0]
    self.ht = size[1]
    self.depth = depth 
    if not reverse: self.rawpix = rawpix
    else: self.rawpix = flipBitmap(rawpix, self.wd, self.ht, self.depth)
    self.pixels = array('c', self.rawpix)
    self.bpr = len(self.pixels) / self.ht
    self.initalized = True

  
  # Create a bitmap from a base64 string
  def fromString(self, size, encstr):
    self.depth = 24
    self.rawpix = base64.b64decode(encstr)
    self.pixels = array('c', self.rawpix)
    self.wd, self.ht = size[0], size[1]
    self.bpr = len(self.pixels) / self.ht
    self.initalized = True
    
    
  # Save the bitmap to any location on the computer
  def save(self, filename):
    if self.initalized:
      header = _constructHeader(self.wd, self.ht, self.depth, len(self.rawpix))
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
    if (0 <= x < self.wd) and (0 <= y < self.ht):
      mdf = 3
      if self.depth == 32: mdf = 4
      pos = (y*self.bpr) + (x*mdf)
      pack = struct.pack('<BBB', c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF)
      self.pixels[pos] = pack[0]
      self.pixels[pos+1] = pack[1]
      self.pixels[pos+2] = pack[2]


  # Get color of pixel(x,y) - reading from rawdata
  # No safeblock... speed is of the important!
  def getPixel(self, x,y):
    mdf = 3
    if self.depth == 32: mdf = 4
    pos = (y*self.bpr) + (x*mdf)
    b,g,r = struct.unpack('<BBB', self.rawpix[pos:pos+3])
    return r << 16 | g << 8 | b
    
      
  # Get all the colors from each pixel given
  def getPixels(self, seq):
    return [self.getPixel(x,y) for (x,y) in seq]

    
  #Quick append color to a list of pixels  
  def setPixels(self, seq, clr, save=False):
    pack = struct.pack('<BBB', clr & 0xFF, (clr >> 8) & 0xFF, (clr >> 16) & 0xFF)
    for (x,y) in seq: 
      pos = (y*self.bpr) + (x*3)
      self.pixels[pos] = pack[0]
      self.pixels[pos+1] = pack[1]
      self.pixels[pos+2] = pack[2]
    if save: self.writeData() 
    
   
  # Stuff for getting dimensions, and data
  def size(self): return (self.wd, self.ht);
  def width(self): return self.wd;
  def height(self): return self.ht;
  def _raw(self): return self.rawpix;
  
  
  # Might just come in handy to keep memory clear...
  def free(self):
    W = H = -1
    self.initalized = False
    self.pixels = ''
    self.rawpix = ''
    gc.collect()
  
  
  ''' 
   Cool and usefull functions goes bellow here!! 
  '''
  
  # Resize the image using Nearest nabour
  # This could MAY BE possible with just maipulating raw data...
  def resize(self, newW, newH):
    W, H = self.size()
    factx = newW/float(W)
    facty = newH/float(H)
    if (factx,facty) == (1,1): return
    new = Bitmap()
    new.create(newW, newH)
    for x in range(newW):
      for y in range(newH):
        p = self.getPixel(int(x/factx), int(y/facty))
        new.setPixel((x,y), p)

    new.writeData()
    self.free()
    self.depth = 24
    self.rawpix = new._raw()
    self.pixels = array('c', new._raw())
    self.wd, self.ht = newW, newH
    self.bpr = len(self.pixels) / self.ht
    self.initalized = True
    
  def rescale(self, factor): 
    W, H = self.size()
    self.resize(int(W*factor), int(H*factor))
    

# Take it for a spin..!
if __name__ == '__main__':
  bmp = Bitmap()
  bmp.create(1000, 1000, 'RGB', bkgd=(20,100,240))
  #bmp.open("test.bmp")
  
  W,H = bmp.size()
  for x in range(W):
    for y in range(H):
        bmp.setPixel((0,0), bmp.getPixel(0,0))

  bmp.save('test.bmp')
