#!/usr/bin/python
########################################################################################################################
# This script generates planet surface like "Star Control 2" game did.
# It uses the so called "Fault Formation" algorithm. You can find its detailed description in the internet.
# The algorithm generates 8 bit "grayscale" planet surface image consisting of pixels with values from 0 to 255.
# Those pixels are then "colorized" by mapping each value to RGB color.
#
# Base elevation parameter sets the initial value of all "grayscale" pixels before the algorithm starts working.
# For each iteration of the algorithm two non-intersecting random lines are generated from the top to the bottom
# margin of the surface so that they divide area into two parts. Pixel values from one part are incremented by the 
# elevation delta parameter. Pixels from the other part are decremented by the same value. After a given number
# of iterations a "grayscale" surface is generated.
#
# The next step is "colorizing" the surface. The colorizing is done by applying linear gradients between color nodes.
# When the script starts there're two color nodes that map surface 8 bit pixels from black to white. You may click on
# a color node to change its color. Also you may click on a gradient to create new color node. To delete color node,
# right click on it.
#
# When you're done generating and colorizing the planet's surface, you may left click on the surface image to save it
# as a PNG image. Also space.py script will be started to render the planet in a separate OpenGL window.
#
# If you have any suggestions, comments or propositions, feel free to write me a letter to 
# Maksym Ganenko <buratin.barabanus at Google Mail>
########################################################################################################################

import random, numpy, time, os, atexit
import traceback, threading, subprocess
import Tkinter, tkColorChooser, PngImagePlugin
from Tkinter import *
from ttk import *
from PIL import Image, ImageTk, ImageDraw

IMAGE_WIDTH         = 512
IMAGE_HEIGHT        = 256
OUTPUT_FILE         = "planet.png"

PARAMS              = [
    ("name",            "title",                "min",      "max",          "format",   "value"),
    ("iterationsNum",   "Iterations num",       0,          10000,          "%d",       2000),
    ("baseElevation",   "Base elevation",       0,          255,            "%d",       100),
    ("elevationDelta",  "Elevation delta",      0,          10,             "%d",       2),
    ("randomSeed",      "Random seed",          0,          0xffffffff,     "%8X",      random.randint(0, 0xffffffff))
]

########################################################################################################################

gRoot               = Tk()

gPlanetSourceImage  = None
gPlanetCanvasImage  = None
gPlanetPalette      = None

gGenerateThread     = None
gSphereProc         = None

gColorMapFrame      = None
gColorMapItems      = None

gProgressCanvas     = None
gStatusLabel        = None

gNonHoverColor      = None

gProgressVar        = DoubleVar(value = 0)
gParamsMap          = { }

########################################################################################################################

def createParam(params, name, value, format):
    param, label = IntVar(value = value), StringVar(value = value)
    param.trace("w", lambda *foo: label.set(format % param.get()))
    params[name] = param
    return param, label

def extractColor(widget):
    return widget.winfo_rgb(widget.cget("bg"))

def interpolateColor(k, colorStart, colorFinish):
    r = int(numpy.interp(k, [0, 1], [colorStart[0], colorFinish[0]])) >> 8
    g = int(numpy.interp(k, [0, 1], [colorStart[1], colorFinish[1]])) >> 8
    b = int(numpy.interp(k, [0, 1], [colorStart[2], colorFinish[2]])) >> 8
    return (r, g, b)

def createColorMapButton(color):
    w = Canvas(gColorMapFrame, width = 20, height = 20, bg = color)
    w.bind("<ButtonRelease-1>", onChooseColor)
    w.bind("<ButtonRelease-2>", onDeletePoint)
    w.bind("<Enter>", onHoverEnter)
    w.bind("<Leave>", onHoverLeave)
    return w

def createColorMapGradient():
    w = Canvas(gColorMapFrame, width = 20, height = 10)
    w.bind("<ButtonRelease-1>", onGradientClick)
    w.bind("<Enter>", onHoverEnter)
    w.bind("<Leave>", onHoverLeave)
    return w

def showStatus(text):
    gStatusLabel.config(text = text)
    gStatusLabel.grid()
    gStatusLabel.update()
    gStatusLabel.after(1000, lambda: gStatusLabel.grid_remove())

def onSaveTexture(event):
    if not gPlanetSourceImage or gGenerateThread.isAlive(): return
    if event.widget.cget("highlightbackground") == gNonHoverColor: return
    
    # generate meta information

    meta = PngImagePlugin.PngInfo()
    for key in gParamsMap.keys():
        meta.add_text(key, str(gParamsMap[key].get()))
    for i in range(0, len(gColorMapItems), 2):
        meta.add_text("color%d" % (i // 2), gColorMapItems[i].cget("bg"))

    # save image

    gPlanetSourceImage.convert("RGB").save(OUTPUT_FILE, pnginfo = meta)
    showStatus("Saved to " + OUTPUT_FILE)

    # start 3d sphere process

    global gSphereProc
    if gSphereProc: gSphereProc.kill()

    w, h = gRoot.winfo_reqwidth(), gRoot.winfo_reqheight()
    top = gRoot.winfo_children()[0]
    gSphereProc = subprocess.Popen([
        "python", "space.py",
        "--texture", OUTPUT_FILE,
        "--winsize", "{0};{0}".format(h),
        "--winpos", "{0};{1}".format(gRoot.winfo_x() + w, top.winfo_rooty())
    ])

def onProgressUpdate(*ignore):
    value = gProgressVar.get()
    canvas = gProgressCanvas
    canvas.delete(ALL)
    canvas.create_rectangle(0, 0, int(IMAGE_WIDTH // 2 * value), 20, fill = "#777777")
    if value > 0: canvas.grid()
    else:         canvas.grid_remove()

def onGradientClick(event):
    if event.widget.cget("highlightbackground") == gNonHoverColor: return
    if event.widget.winfo_width() <= 60: return

    # create new gradient and button at given position
    index = gColorMapItems.index(event.widget)
    start = extractColor(gColorMapItems[index - 1])
    finish = extractColor(gColorMapItems[index + 1])
    color = "#%02x%02x%02x" % interpolateColor(0.5, start, finish)

    gColorMapItems.insert(index, createColorMapButton(color))
    gColorMapItems.insert(index, createColorMapGradient())

    generatePalette()

def onDeletePoint(event):
    if event.widget.cget("highlightbackground") == gNonHoverColor: return
    if len(gColorMapItems) == 3: return
    event.widget.config(highlightbackground = gNonHoverColor)   
    index = gColorMapItems.index(event.widget)

    # shift colors
    for i in range(index, len(gColorMapItems) - 2, 2):
        gColorMapItems[i].config(bg = gColorMapItems[i + 2].cget("bg"))

    for i in range(2):
        gColorMapFrame.columnconfigure(len(gColorMapItems) - 1, weight = 0)
        w = gColorMapItems.pop()
        w.grid_forget()
        w.destroy()

    generatePalette()

def onChooseColor(event):
    if event.widget.cget("highlightbackground") == gNonHoverColor: return
    event.widget.config(highlightbackground = gNonHoverColor)
    (rgb, hex) = tkColorChooser.askcolor(event.widget.cget("bg"))
    if hex:
        event.widget.config(bg = hex)
        generatePalette()

def onHoverEnter(event):
    event.widget.config(highlightbackground = "#777777")

def onHoverLeave(event):
    event.widget.config(highlightbackground = gNonHoverColor)

def generatePalette():
    for i, w in enumerate(gColorMapItems):
        if i % 2 == 0:
            w.grid(row = 0, column = i)
        else:
            w.grid(row = 0, column = i, sticky = W + E, padx = (5, 8))
            gColorMapFrame.columnconfigure(i, weight = 1)

    palette = [ ]
    gradientsNum = len(gColorMapItems) // 2
    for i in range(gradientsNum):
        canvas = gColorMapItems[i * 2 + 1]
        start = extractColor(gColorMapItems[i * 2])
        finish = extractColor(gColorMapItems[i * 2 + 2])
        
        paletteLen = int(round(256 * (i + 1) / gradientsNum)) - int(round(256 * i / gradientsNum))
        for k in range(paletteLen):
            palette += list(interpolateColor(float(k) / (paletteLen - 1), start, finish))
        
        canvas.update()
        canvas.delete(ALL)
        width = canvas.winfo_width()
        for k in range(width):
            canvas.create_line(k, 0, k, 100, 
                    fill = "#%02x%02x%02x" % interpolateColor(float(k) / (width - 1), start, finish))

    global gPlanetPalette
    gPlanetPalette = palette
    if gPlanetSourceImage:
        gPlanetSourceImage.putpalette(palette)
        gPlanetCanvasImage.paste(gPlanetSourceImage)

########################################################################################################################

class GenerateThread(threading.Thread):
    def __init__(self, **params):
        threading.Thread.__init__(self)
        self.iterationsNum, self.baseElevation = params["iterationsNum"].get(), params["baseElevation"].get()
        self.elevationDelta, self.randomSeed = params["elevationDelta"].get(), params["randomSeed"].get()
        self.stopped = False

    def stop(self):
        self.stopped = True

    def run(self):
        random.seed(self.randomSeed)

        image = Image.new("I", (IMAGE_WIDTH, IMAGE_HEIGHT), self.baseElevation)
        imageArray = numpy.asarray(image)
        stepImage = Image.new("I", (IMAGE_WIDTH, IMAGE_HEIGHT), 0)
        renderer = ImageDraw.Draw(stepImage)

        tprogress = time.clock()
        for i in range(self.iterationsNum):
            if self.stopped: return

            # update progress bar
            if time.clock() - tprogress > 0.15:
                gProgressVar.set(float(i) / self.iterationsNum)
                tprogress = time.clock()

            if random.randint(1, 2) == 1:
                color1, color2 = self.elevationDelta, -self.elevationDelta
            else:
                color1, color2 = -self.elevationDelta, self.elevationDelta

            line0 = (random.randint(0, IMAGE_WIDTH), random.randint(0, IMAGE_WIDTH))
            line1 = (random.randint(0, IMAGE_WIDTH - 1) + line0[0] + 1, random.randint(0, IMAGE_WIDTH - 1) + line0[1] + 1)

            renderer.rectangle([0, 0, IMAGE_WIDTH, IMAGE_HEIGHT], fill = color1)

            p0 = (line0[0], 0)
            p1 = (line1[0], 0)
            p2 = (line1[1], IMAGE_HEIGHT)
            p3 = (line0[1], IMAGE_HEIGHT)
            renderer.polygon([p0, p1, p2, p3], fill = color2)

            p0 = (p0[0] - IMAGE_WIDTH, p0[1])
            p1 = (p1[0] - IMAGE_WIDTH, p1[1])
            p2 = (p2[0] - IMAGE_WIDTH, p2[1])
            p3 = (p3[0] - IMAGE_WIDTH, p3[1])
            renderer.polygon([p0, p1, p2, p3], fill = color2)

            imageArray = imageArray + numpy.asarray(stepImage)

        global gPlanetSourceImage
        gPlanetSourceImage = Image.fromarray(imageArray).convert(mode = "P")
        gPlanetSourceImage.putpalette(gPlanetPalette)
        gPlanetCanvasImage.paste(gPlanetSourceImage)
        gProgressVar.set(0)

def generateSurface(*ignored):
    global gGenerateThread
    if gGenerateThread: gGenerateThread.stop()
    for param in gParamsMap.keys():
        gParamsMap[param].set(gParamsMap[param].get())
    gGenerateThread = GenerateThread(**gParamsMap)
    gGenerateThread.start()

########################################################################################################################

gRoot.title("Planet surface generator")

top = Frame(gRoot)
top.grid(sticky = W + E + S + N)
top.columnconfigure(1, weight = 1)

# canvas

w = Canvas(top, width = IMAGE_WIDTH, height = IMAGE_HEIGHT)
w.bind("<ButtonRelease-1>", onSaveTexture)
w.bind("<Enter>", onHoverEnter)
w.bind("<Leave>", onHoverLeave)
w.grid(row = 0, column = 0, columnspan = 3, padx = 5, pady = 5)
gPlanetCanvasImage = ImageTk.PhotoImage(Image.new("P", (IMAGE_WIDTH, IMAGE_HEIGHT), 0))
w.create_image(IMAGE_WIDTH // 2 + 3, IMAGE_HEIGHT // 2 + 3, image = gPlanetCanvasImage)
gNonHoverColor = w.cget("highlightbackground") 

# color map

gColorMapFrame = Frame(top, width = IMAGE_WIDTH, height = 25)
gColorMapFrame.grid(row = 1, column = 0, columnspan = 3, sticky = W + E, padx = 5, pady = 5)

gColorMapItems = [ createColorMapButton("black"), createColorMapGradient(), createColorMapButton("white") ]

# params

header = PARAMS[0]
for i, record in enumerate(PARAMS[1:]):
    r = dict(zip(header, record))
    param, label = createParam(gParamsMap, r["name"], r["value"], r["format"])

    w = Label(top, text = r["title"])
    w.grid(row = 2 + i, column = 0, sticky = W, padx = 5, pady = 5)

    w = Scale(top, from_ = r["min"], to = r["max"], variable = param,
            orient = HORIZONTAL, command = generateSurface)
    w.grid(row = 2 + i, column = 1, sticky = W + E, padx = 5, pady = 5)

    w = Tkinter.Label(top, textvariable = label, width = 9, fg = "white", bg = "black")
    w.grid(row = 2 + i, column = 2, sticky = E, padx = 5, pady = 5)

# progress bar

gProgressVar.trace("w", onProgressUpdate)
w = Canvas(top, width = IMAGE_WIDTH // 2, height = 10)
w.grid(row = 0, column = 0, columnspan = 3, padx = 5, pady = 5)
gProgressCanvas = w

# status label

w = Tkinter.Label(top, text = "", bg = "black", fg = "white")
w.grid(row = 0, column = 0, columnspan = 3, padx = 5, pady = 5)
w.grid_remove()
gStatusLabel = w

generatePalette()
generateSurface()

atexit.register(lambda: gSphereProc and gSphereProc.kill())

gRoot.resizable(width = False, height = False)
gRoot.focus_force()
gRoot.mainloop()

########################################################################################################################