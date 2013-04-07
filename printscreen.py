'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 This is a placeholder file, taking printscreen with it only works with 
 third party module: pywin32, therefor also only works on Windows.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''
from bitmap import Bitmap
import win32gui,  win32ui,  win32con

def prtScn(hwnd=False):
    if not hwnd: hwnd = win32gui.GetDesktopWindow()

    SX,SY,EX,EY = win32gui.GetWindowRect(hwnd)
    W,H = EX-SX, EY-SY

    wDC = win32gui.GetWindowDC(hwnd)
    dcObj = win32ui.CreateDCFromHandle(wDC)
    cDC = dcObj.CreateCompatibleDC()

    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(dcObj, W, H)
    cDC.SelectObject(bmp)
    cDC.BitBlt((0, 0), (W,H), dcObj, (0,0), win32con.SRCCOPY)
  
    # Image from bitmapbuffer
    bmpinfo = bmp.GetInfo()
    rawbmp = bmp.GetBitmapBits(True)

    BMP = Bitmap();
    BMP.fromBuffer(rawbmp, (bmpinfo['bmWidth'], bmpinfo['bmHeight']), 32)
        
    # Destroy all objects!
    dcObj.DeleteDC(); 
    cDC.DeleteDC(); 
    win32gui.ReleaseDC(hwnd, wDC)
    win32gui.DeleteObject(bmp.GetHandle())

    #return image
    return BMP


if __name__ == '__main__':
  bmp = prtScn()
  #bmp = Bitmap()
  #bmp.open('sub.bmp')
  #bmp.create(1000, 1000, 'P', bkgd=90)

  bmp.setPixel((10,10),(255,0,0))
  bmp.setPixel((11,10),(0,0,0))
  bmp.setPixel((12,10),(0,0,0))
  print bmp.getPixel(10,10)
  
  bmp.save('test.bmp')
