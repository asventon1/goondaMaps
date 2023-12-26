import urllib.request
import json
import re
import base64
import struct
import math
import png
from PIL import Image
import numpy as np
import liblas
import pyautogui
import time
import clipboard
import os

def getDepth(panoId: str):
    panoUrl = ("https://www.google.com/maps/photometa/v1?authuser=0&hl=en&gl=uk&pb=!1m4!1smaps_sv.tactile!11m2!2m1!1b1!2m2!1sen!2suk!3m3!1m2!1e2!2s" +
            panoId +
            "!4m57!1e1!1e2!1e3!1e4!1e5!1e6!1e8!1e12!2m1!1e1!4m1!1i48!5m1!1e1!5m1!1e2!6m1!1e1!6m1!1e2!9m36!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e3!2b1!3e2!1m3!1e3!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e1!2b0!3e3!1m3!1e4!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e3")
    contents = urllib.request.urlopen(panoUrl).read()
    contents = json.loads(contents[4:])
    contents = contents[1][0][5][0][5][1][2]
    decoded = decode(contents)
    depthMap = parse(decoded)
    return depthMap

def decode(rawDepthMap: str):

    # Add '=' until the length of the string is a multiple of 4
    while len(rawDepthMap) % 4 != 0:
        rawDepthMap += '='
    
    # Replace '-' with '+' and '_' with '/'
    rawDepthMap = re.sub("-", '+', rawDepthMap)
    rawDepthMap = re.sub("_", '/', rawDepthMap)

    # Decode and decompress data
    decompressedDepthMap = base64.b64decode(rawDepthMap)

    # Convet output of decompressor to array of bytes
    depthMap = bytearray(decompressedDepthMap)

    return depthMap

# gets the header information from the start of the bytearray
def parseHeader(depthMap: bytearray):
    return {
        "headerSize" : depthMap[0],
        # gets the first byte as a uint8 or unsigned char
        "numberOfPlanes" : struct.unpack('H', depthMap[1:3])[0],
        # gets the second and third bytes as a uint16 or unsigned short
        # the 'H' designates as uint16
        # table of what the diferent letters mean:
        # https://blog.finxter.com/convert-bytes-to-floating-point-numbers/
        "width" : struct.unpack('H', depthMap[3:5])[0],
        "height" : struct.unpack('H', depthMap[5:7])[0],
        "offset" : struct.unpack('H', depthMap[7:9])[0]
    }

def parsePlanes(header, depthMap):
    planes = []
    indices = []
    for i in range(header["width"] * header["height"]):
        indices.append(depthMap[header["offset"] + i])
    for i in range(header["numberOfPlanes"]):
        byteOffset = (header["offset"] +
            header["width"] * header["height"] + i*4*4)
        n = [
            struct.unpack('f', depthMap[byteOffset:byteOffset+4])[0],
            struct.unpack('f', depthMap[byteOffset+4:byteOffset+8])[0],
            struct.unpack('f', depthMap[byteOffset+8:byteOffset+12])[0]
        ]
        d = struct.unpack('f', depthMap[byteOffset+12:byteOffset+16])[0]
        planes.append({
            "n" : n,
            "d" : d
        })
    return { "planes": planes, "indices" : indices }

def computeDepthMap(header , indices, planes):
    w = header["width"]
    h = header["height"]
    depthMap = [0.0] * (w*h)
    sin_theta = [0.0] * h
    cos_theta = [0.0] * h
    sin_phi = [0.0] * w
    cos_phi = [0.0] * w
    for y in range(h):
        theta = (h - y - 0.5) / h * math.pi
        sin_theta[y] = math.sin(theta)
        cos_theta[y] = math.cos(theta)
    for x in range(w):
        phi = (w - x - 0.5) / w * 2 * math.pi + math.pi/2
        sin_phi[x] = math.sin(phi)
        cos_phi[x] = math.cos(phi)
    for y in range(h):
        for x in range(w):
            planeIdx = indices[y*w +x]
            v = [
                sin_theta[y] * cos_phi[x],
                sin_theta[y] * sin_phi[x],
                cos_theta[y]
            ]
            if(planeIdx > 0):
                plane = planes[planeIdx]
                t = abs(plane["d"] / (v[0]*plane["n"][0] +
                    v[1]*plane["n"][1] + v[2]*plane["n"][2]))
                depthMap[y*w + (w-x-1)] = t
            else:
                depthMap[y*w + (w-x-1)] = 9999999999999999999.0
    return {
        "width" : w,
        "height" : h,
        "depthMap" : depthMap
    }

def parse(depthMap: bytearray):
    header = parseHeader(depthMap)
    data = parsePlanes(header, depthMap)
    depthMap = computeDepthMap(header, data["indices"], data["planes"])
    return depthMap

def saveDepthMapAsPng(depthMapDict, imagePath):
    width = depthMapDict["width"]
    height = depthMapDict["height"]
    depthMap = depthMapDict["depthMap"]
    scale = 4
    imgFlat = [ min(255, int(i * scale)) for i in depthMap ]
    img = [ imgFlat[i:i+width] for i in range(0, len(imgFlat), width)]
    with open(imagePath, 'wb') as f:
        w = png.Writer(width, height, greyscale = True)
        w.write(f, img)

def getImage(image_path):
    # Get a numpy array of an image so that one can access values[x][y].
    image = Image.open(image_path, "r")
    width, height = image.size
    pixel_values = list(image.getdata())
    if image.mode == "RGB":
        channels = 3
    elif image.mode == "L":
        channels = 1
    elif image.mode == "RGBA":
        channels = 4
    else:
        print("Unknown mode: %s" % image.mode)
        return None
    pixel_values = np.array(pixel_values).reshape((height, width, channels))
    return pixel_values

def makeLas():
    f = liblas.file.File("new_file.las", mode="w")
    for x in range(10):
        for y in range(10):
            for z in range(10):
                pt = liblas.point.Point()
                pt.x = x
                pt.y = y
                pt.z = z
                color = liblas.color.Color()
                color.red = 255
                color.blue = 255
                color.green = 255
                pt.color = color
                f.write(pt)
    f.close()

def makeLasImage():
    f = liblas.file.File("new_image.las", mode="w")
    data = getImage("../austinTestSmaller.png")
    for z in range(10):
        for x in range(data.shape[0]):
            for y in range(data.shape[1]):
                pt = liblas.point.Point()
                pt.x = x
                pt.y = y
                pt.z = z
                color = liblas.color.Color()
                color.red = data[x][y][0]
                color.green = data[x][y][1]
                color.blue = data[x][y][2]
                pt.color = color
                f.write(pt)
    f.close()

def makeLasImageSphere():
    f = liblas.file.File("new_image.las", mode="w")
    data = getImage("../austinTestSmaller.png")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            pt = liblas.point.Point()
            x, y, z = imageCoordsTo3d(i, j, data.shape[0], data.shape[1], 1000)
            pt.x = x
            pt.y = y
            pt.z = z
            color = liblas.color.Color()
            color.red = data[i][j][0]
            color.green = data[i][j][1]
            color.blue = data[i][j][2]
            pt.color = color
            f.write(pt)
    f.close()

def makeLasModel():
    oLat = 30.267139
    oLon = -97.7432157
    oElevation = 150
    f = liblas.file.File("newer_image.las", mode="w")
    images = os.listdir("../pics")
    for image in images[:2]:
        metaData = image[:-4].split("=")
        id = metaData[0]
        lat = float(metaData[1])
        lon = float(metaData[2])
        rotation = int(metaData[3])
        elevation = int(metaData[4])
        data = getImage("../pics/"+image)
        depthData = getImage("../maps/"+image)
        print(id, lat, lon)
        offsetX, offsetY = getDistanceFromOrigin(oLat, oLon, lat, lon)
        print(offsetX, offsetY)
        for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    pt = liblas.point.Point()
                    depth = depthData[i][-j][0]
                    if(depth == 255):
                        continue
                    scale = 10
                    x, y, z = imageCoordsTo3d(i, j, data.shape[0], data.shape[1], depth*scale, rotation)
                    pt.x = -(x + offsetX*scale)
                    pt.y = y + offsetY*scale
                    pt.z = z + (elevation-oElevation)*scale
                    color = liblas.color.Color()
                    color.red = data[i][j][0]
                    color.green = data[i][j][1]
                    color.blue = data[i][j][2]
                    pt.color = color
                    f.write(pt)
    f.close()

def imageCoordsTo3d(x, y, width, height, r, thetaOffset):
    theta = 2 * math.pi * (float(y) / height) - math.pi - deg2rad(thetaOffset)
    other = math.pi * (1-(float(x) / width)) - (math.pi / 2)
    x = r * math.cos(other) * math.cos(theta)
    y = r * math.cos(other) * math.sin(theta)
    z = r * math.sin(other)
    return (x, y, z)

def getImagesFromStreet():
    with open("image_urls.txt", "r") as f:
        i = 0
        for url in f:
            pyautogui.click(1000, 130)
            pyautogui.click()
            pyautogui.click()
            tempName = "/home/adam/stuff/goondaMaps/pics/austinTest"+str(i)+".png"
            pyautogui.typewrite(tempName)
            pyautogui.click(2000, 250)
            pyautogui.click()
            pyautogui.click()
            pyautogui.typewrite(url)
            pyautogui.click(400, 420)
            time.sleep(1)
            pyautogui.click(3755, 600)
            pyautogui.click(2500, 770)
            pyautogui.hotkey("ctrlleft", "c")
            id = clipboard.paste()
            pyautogui.click(2500, 840)
            pyautogui.hotkey("ctrlleft", "c")
            location = clipboard.paste().split(", ")
            pyautogui.click(2440, 1050)
            pyautogui.hotkey("ctrlleft", "c")
            rotation = clipboard.paste().split("°")[0]
            pyautogui.click(2440, 1130)
            pyautogui.hotkey("ctrlleft", "c")
            elevation = clipboard.paste().split(" ")[0]
            name = f"{id}={location[0]}={location[1]}={rotation}={elevation}.png"
            print(name)
            os.system(f"ffmpeg -i {tempName} -vf scale=512:256 ../pics/{name}")
            os.system(f"rm {tempName}")
            depthMapDict = getDepth(id)
            saveDepthMapAsPng(depthMapDict, f"../maps/{name}")
            i += 1

def getDistanceFromOrigin(oLat, oLon, lat, lon):
    R = 20925721.784777 # Radius of the earth in ft
    C = R * 2 * math.pi
    dLat = (lat-oLat) / 360 * C
    dLon = (lon-oLon) / 360 * C
    return (dLat, dLon)

def getDistanceFromLatLon(lat1,lon1,lat2,lon2):
    R = 20925721.784777 # Radius of the earth in ft
    dLat = deg2rad(lat2-lat1)  # deg2rad below
    dLon = deg2rad(lon2-lon1) 
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)) 
    d = R * c # Distance in ft
    return d

def deg2rad(deg):
  return deg * (math.pi/180)

if __name__ == "__main__":
    #depthMapDict = getDepth("n4K1vO7E4bfsbEiHKakEmg")
    #saveDepthMapAsPng(depthMapDict)
    #image = getImage("../austinTestSmallest.png")
    #print(image)
    makeLasModel()
    #getImagesFromStreet()