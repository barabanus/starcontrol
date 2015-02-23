#!/usr/bin/python
########################################################################################################################
# This script renders a rotatiting planet in the space with a given texture applied.
# To close the window, use left click or press any key.
#
# If you have any suggestions, comments or propositions, feel free to write me a letter to 
# Maksym Ganenko <buratin.barabanus at Google Mail>
########################################################################################################################

from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *
from PIL import Image
import numpy, sys, time
import argparse

parser = argparse.ArgumentParser(description = "Render lonely planet in 3D")
parser.add_argument("--texture", help = "texture input file", default = "planet.png")
parser.add_argument("--winsize", help = "window width and height like w;h", default = "400;400")
parser.add_argument("--winpos", help = "window x and y position like x;y", default = "-1;-1")
args = vars(parser.parse_args())

TEXTURE         = args["texture"]
WINSIZE         = map(int, args["winsize"].split(";"))
WINPOS          = map(int, args["winpos"].split(";"))

ANGLE_PER_SEC   = 15                # planet rotation speed

gSurfaceTex     = None              # planet surface texture
gSphereQuad     = None              # sphere GLU quadratic object

########################################################################################################################

def loadTexture(filename):
    image = Image.open(filename)
    imageData = numpy.array(list(image.getdata()), numpy.uint8)

    texture = glGenTextures(1)
    glPixelStorei(GL_UNPACK_ALIGNMENT,1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.size[0], image.size[1], 0, GL_RGB, GL_UNSIGNED_BYTE, imageData)

    return texture

def onDisplay():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glPushMatrix()
    color = [1, 1, 1, 1]
    glMaterialfv(GL_FRONT, GL_DIFFUSE, color)

    glRotatef(time.time() % 360 * ANGLE_PER_SEC, 0, 1, 0)
    glRotatef(90, 1, 0, 0)
    gluQuadricTexture(gSphereQuad, True)
    gluSphere(gSphereQuad, 2.11, 100, 100)

    glPopMatrix()
    glutSwapBuffers()
    glutPostRedisplay()

########################################################################################################################

glutInit(sys.argv)
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH | GLUT_MULTISAMPLE)
glutInitWindowSize(*WINSIZE)
glutInitWindowPosition(*WINPOS)
glutCreateWindow("Somewhere in the space")

glClearColor(0, 0, 0, 1)
glShadeModel(GL_SMOOTH)
glEnable(GL_CULL_FACE)
glEnable(GL_DEPTH_TEST)
glEnable(GL_LIGHTING)
glLightfv(GL_LIGHT0, GL_POSITION, [ -10, 0, 8, 1 ])
glLightf(GL_LIGHT0, GL_CONSTANT_ATTENUATION, 0.1)
glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0.05)
glEnable(GL_LIGHT0)

gSurfaceTex = loadTexture(TEXTURE)
gSphereQuad = gluNewQuadric()

glEnable(GL_TEXTURE_2D)

glutDisplayFunc(onDisplay)
glutKeyboardFunc(lambda *foo: exit())
glutMouseFunc(lambda button, *foo: button == GLUT_LEFT_BUTTON and exit())

glMatrixMode(GL_PROJECTION)
gluPerspective(40, 1, 1, 40)
glMatrixMode(GL_MODELVIEW)
gluLookAt(0, 0, 10, 0, 0, 0, 0, 1, 0)
glPushMatrix()
glutMainLoop()

########################################################################################################################