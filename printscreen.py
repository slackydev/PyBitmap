'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 Only written if for windows as it's now, but I might just take a 
 look at some standard linux API's / Frameworks. 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''
from bmplib import Bitmap
import ctypes
from ctypes.wintypes import HGDIOBJ

user32 = ctypes.windll.user32       
gdi32 = ctypes.windll.gdi32

SRCCOPY = 13369376
BOOL    = ctypes.c_bool
INT   = ctypes.c_int
LONG    = ctypes.c_long
WORD    = ctypes.c_ushort
LPVOID  = ctypes.c_void_p
Structure = ctypes.Structure

LPLONG = ctypes.POINTER(LONG)

class BITMAP(Structure):
    _fields_ = [
        ("bmType",          LONG),
        ("bmWidth",         LONG),
        ("bmHeight",        LONG),
        ("bmWidthBytes",    LONG),
        ("bmPlanes",        WORD),
        ("bmBitsPixel",     WORD),
        ("bmBits",          LPVOID),
    ]


def GetObject(hgdiobj, cbBuffer = None, lpvObject = None):
    _GetObject = gdi32.GetObjectA
    _GetObject.argtypes = [HGDIOBJ, INT, LPVOID]
    _GetObject.restype  = INT
    cbBuffer = ctypes.sizeof(lpvObject)
    _GetObject(hgdiobj, cbBuffer, ctypes.byref(lpvObject))
    return lpvObject

def GetBitmapBits(hbmp):
    _GetBitmapBits = gdi32.GetBitmapBits
    _GetBitmapBits.argtypes = [HGDIOBJ, LONG, LPVOID]
    _GetBitmapBits.restype  = LONG

    bitmap   = GetObject(hbmp, lpvObject = BITMAP())
    cbBuffer = bitmap.bmWidthBytes * bitmap.bmHeight
    lpvBits  = ctypes.create_string_buffer("", cbBuffer)
    _GetBitmapBits(hbmp, cbBuffer, ctypes.byref(lpvBits))
    return lpvBits.raw

    
def screenBuffer(hwnd=False):
    user32.GetDesktopWindow.argtypes = []
    user32.GetWindowRect.argtypes = [LONG,LPLONG]
    user32.GetWindowDC.argtypes = [LONG]
    gdi32.CreateCompatibleDC.argtypes = [LONG]
    gdi32.CreateCompatibleBitmap.argtypes = [LONG, LONG, LONG]
    gdi32.SelectObject.argtypes = [LONG, LONG]
    gdi32.BitBlt.argtypes = [LONG, LONG,LONG,LONG,LONG, LONG,LONG,LONG,LONG]
    
    if not hwnd: hwnd = user32.GetDesktopWindow()
    hwnd = ctypes.c_long(hwnd)
    
    rect = (ctypes.c_int*4)()
    user32.GetWindowRect(hwnd, rect)
    W,H = rect[2]-rect[0], rect[3]-rect[1]

    winDC = user32.GetWindowDC(hwnd)
    cDC = gdi32.CreateCompatibleDC(winDC)
    bmp = gdi32.CreateCompatibleBitmap(winDC, W, H)
    gdi32.SelectObject(cDC, bmp)
    gdi32.BitBlt(cDC, 0,0, W,H, winDC, 0,0, SRCCOPY)
  
    # Image from bitmapbuffer
    raw = ''
    rawbmp = GetBitmapBits(bmp)
        
    #Destroy all objects!
    gdi32.DeleteObject(gdi32.SelectObject(cDC, bmp))
    gdi32.DeleteDC(cDC);
    user32.ReleaseDC(hwnd, winDC)
    
    # Returns a raw buffer that can be used by
    # Bitmaps().fromBuffer(raw, size, 32, False)
    # If I were to guess, it would work with PIL as well.
    return (rawbmp, (W, H))
