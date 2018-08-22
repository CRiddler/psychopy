#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OpenGL related helper functions.

"""

# Part of the PsychoPy library
# Copyright (C) 2018 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

import ctypes
from collections import namedtuple
import pyglet.gl as GL  # using Pyglet for now
from contextlib import contextmanager

# -----------------------------------
# Framebuffer Objects (FBO) Functions
# -----------------------------------
#
# The functions below simplify the creation and management of Framebuffer
# Objects (FBOs). FBO are containers for image buffers (textures or
# renderbuffers) frequently used for off-screen rendering.
#

# FBO descriptor
Framebuffer = namedtuple(
    'Framebuffer',
    ['id',
     'target',
     'userData']
)


def createFramebuffer(attachments=()):
    """Create a Framebuffer Object.

    Parameters
    ----------
    attachments : :obj:`list` or :obj:`tuple` of :obj:`tuple`
        Optional attachments to initialize the Framebuffer with. Attachments are
        specified as a list of tuples. Each tuple must contain an attachment
        point (e.g. GL_COLOR_ATTACHMENT0, GL_DEPTH_ATTACHMENT, etc.) and a
        buffer descriptor type (Renderbuffer or TexImage2D). If using a combined
        depth/stencil format such as GL_DEPTH24_STENCIL8, GL_DEPTH_ATTACHMENT
        and GL_STENCIL_ATTACHMENT must be passed the same buffer. Alternatively,
        one can use GL_DEPTH_STENCIL_ATTACHMENT instead. If using multisample
        buffers, all attachment images must use the same number of samples!. As
        an example, one may specify attachments as 'attachments=((
        GL.GL_COLOR_ATTACHMENT0, frameTexture), (GL.GL_DEPTH_STENCIL_ATTACHMENT,
        depthRenderBuffer))'.

    Returns
    -------
    :obj:`Framebuffer`
        Framebuffer descriptor.

    Notes
    -----
        - All buffers must have the same number of samples.
        - The 'userData' field of the returned descriptor is a dictionary that
          can be used to store arbitrary data associated with the FBO.
        - Framebuffers need a single attachment to be complete.

    Examples
    --------
    # empty framebuffer with no attachments
    fbo = createFramebuffer()  # invalid until attachments are added

    # create a render target with multiple color texture attachments
    colorTex = createTexImage2D(1024,1024)  # empty texture
    depthRb = createRenderbuffer(800,600,internalFormat=GL.GL_DEPTH24_STENCIL8)

    # attach images
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, fbo.id)
    framebufferAttachment(GL.GL_COLOR_ATTACHMENT0, colorTex)
    framebufferAttachment(GL.GL_DEPTH_ATTACHMENT, depthRb)
    framebufferAttachment(GL.GL_STENCIL_ATTACHMENT, depthRb)
    # or framebufferAttachment(GL.GL_DEPTH_STENCIL_ATTACHMENT, depthRb)
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    # above is the same as
    with framebufferBindingContext(fbo):
        framebufferAttachment(GL.GL_COLOR_ATTACHMENT0, colorTex)
        framebufferAttachment(GL.GL_DEPTH_ATTACHMENT, depthRb)
        framebufferAttachment(GL.GL_STENCIL_ATTACHMENT, depthRb)

    # examples of userData some custom function might access
    fbo.userData['flags'] = ['left_eye', 'clear_before_use']

    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, fb.id)  # bind for drawing

    # depth only texture (for shadow mapping?)
    depthTex = createTexImage2D(800, 600,
                                internalFormat=GL.GL_DEPTH_COMPONENT24,
                                pixelFormat=GL.GL_DEPTH_COMPONENT)
    fbo = createFramebuffer([(GL.GL_DEPTH_ATTACHMENT, depthTex)])  # is valid

    # discard FBO descriptor, just give me the ID
    frameBuffer = createFramebuffer().id

    """
    fboId = GL.GLuint()
    GL.glGenFramebuffers(1, ctypes.byref(fboId))

    # create a framebuffer descriptor
    fboDesc = Framebuffer(fboId, GL.GL_FRAMEBUFFER, dict())

    # initial attachments for this framebuffer
    if attachments:
        with framebufferBindingContext(fboDesc):
            for attachPoint, imageBuffer in attachments:
                framebufferAttachment(attachPoint, imageBuffer)

    return fboDesc


def framebufferAttachment(attachPoint, imageBuffer):
    """Attach an image to a specified attachment point on the presently bound
    FBO.

    Parameters
    ----------
    attachPoint :obj:`int`
        Attachment point for 'imageBuffer' (e.g. GL.GL_COLOR_ATTACHMENT0).
    imageBuffer : :obj:`TexImage2D` or :obj:`Renderbuffer`
        Framebuffer-attachable buffer descriptor.

    Returns
    -------
    None

    Examples
    --------
    # with descriptors colorTex and depthRb
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, fbo)
    framebufferAttachment(GL.GL_COLOR_ATTACHMENT0, colorTex)
    framebufferAttachment(GL.GL_DEPTH_STENCIL_ATTACHMENT, depthRb)
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, lastBoundFbo)

    # same as above, but using a context manager
    with framebufferBindingContext(fbo):
        framebufferAttachment(GL.GL_COLOR_ATTACHMENT0, colorTex)
        framebufferAttachment(GL.GL_DEPTH_STENCIL_ATTACHMENT, depthRb)

    """
    # We should also support binding GL names specified as integers. Right now
    # you need as descriptor which contains the target and name for the buffer.
    #
    if isinstance(imageBuffer, (TexImage2D, TexImage2DMultisample)):
        GL.glFramebufferTexture2D(
            GL.GL_FRAMEBUFFER,
            attachPoint,
            imageBuffer.target,
            imageBuffer.id, 0)
    elif isinstance(imageBuffer, Renderbuffer):
        GL.glFramebufferRenderbuffer(
            GL.GL_FRAMEBUFFER,
            attachPoint,
            imageBuffer.target,
            imageBuffer.id)


def framebufferIsComplete():
    """Check if the currently bound framebuffer is complete.

    Returns
    -------
    :obj:`bool'

    """
    return GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) == \
           GL.GL_FRAMEBUFFER_COMPLETE


def deleteFramebuffer(fbo):
    """Delete a framebuffer.

    Returns
    -------
    :obj:`None'

    """
    GL.glDeleteFramebuffers(
        1, fbo.id if isinstance(fbo, Framebuffer) else int(fbo))


def blitFramebuffer(srcRect, dstRect=None, filter=GL.GL_LINEAR):
    """Copy a block of pixels between framebuffers via blitting. Read and draw
    framebuffers must be bound prior to calling this function. Beware, the
    scissor box and viewport are changed when this is called to dstRect.

    Parameters
    ----------
    srcRect : :obj:`list` of :obj:`int`
        List specifying the top-left and bottom-right coordinates of the region
        to copy from (<X0>, <Y0>, <X1>, <Y1>).
    dstRect : :obj:`list` of :obj:`int` or :obj:`None`
        List specifying the top-left and bottom-right coordinates of the region
        to copy to (<X0>, <Y0>, <X1>, <Y1>). If None, srcRect is used for
        dstRect.
    filter : :obj:`int`
        Interpolation method to use if the image is stretched, default is
        GL_LINEAR, but can also be GL_NEAREST.

    Returns
    -------
    None

    Examples
    --------
    # bind framebuffer to read pixels from
    GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, srcFbo)

    # bind framebuffer to draw pixels to
    GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, dstFbo)

    gltools.blitFramebuffer((0,0,800,600), (0,0,800,600))

    # unbind both read and draw buffers
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    """
    # in most cases srcRect and dstRect will be the same.
    if dstRect is None:
        dstRect = srcRect

    # GL.glViewport(*dstRect)
    # GL.glEnable(GL.GL_SCISSOR_TEST)
    # GL.glScissor(*dstRect)
    GL.glBlitFramebuffer(srcRect[0], srcRect[1], srcRect[2], srcRect[3],
                         dstRect[0], dstRect[1], dstRect[2], dstRect[3],
                         GL.GL_COLOR_BUFFER_BIT,  # colors only for now
                         filter)

    # GL.glDisable(GL.GL_SCISSOR_TEST)


@contextmanager
def framebufferBindingContext(fbo):
    """Context manager for Framebuffer Object bindings. This function yields
    the framebuffer name as an integer.

    Parameters
    ----------
    fbo :obj:`int` or :obj:`Framebuffer`
        OpenGL Framebuffer Object name/ID or descriptor.

    Yields
    -------
    int
        OpenGL name of the framebuffer bound in the context.

    Returns
    -------
    None

    Examples
    --------
    # FBO bound somewhere deep in our code
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, someOtherFBO)

    ...

    # create a new FBO, but we have no idea what the currently bound FBO is
    fbo = createFramebuffer()

    # use a context to bind attachments
    with bindFBO(fbo):
        attachFrambufferImage(GL.GL_COLOR_ATTACHMENT0, colorTex)
        attachFrambufferImage(GL.GL_DEPTH_ATTACHMENT, depthRb)
        attachFrambufferImage(GL.GL_STENCIL_ATTACHMENT, depthRb)
        isComplete = gltools.checkFramebufferComplete())

    # someOtherFBO is still bound!

    """
    prevFBO = GL.GLint()
    GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING, ctypes.byref(prevFBO))
    toBind = fbo.id if isinstance(fbo, Framebuffer) else int(fbo)
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, toBind)
    try:
        yield toBind
    finally:
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, prevFBO.value)


# ------------------------------
# Renderbuffer Objects Functions
# ------------------------------
#
# The functions below handle the creation and management of Renderbuffers
# Objects.
#

# Renderbuffer descriptor type
Renderbuffer = namedtuple(
    'Renderbuffer',
    ['id',
     'target',
     'width',
     'height',
     'internalFormat',
     'samples',
     'multiSample',  # boolean, check if a texture is multisample
     'userData']  # dictionary for user defined data
)


def createRenderbuffer(width, height, internalFormat=GL.GL_RGBA8, samples=1):
    """Create a new Renderbuffer Object with a specified internal format. A
    multisample storage buffer is created if samples > 1.

    Renderbuffers contain image data and are optimized for use as render
    targets. See https://www.khronos.org/opengl/wiki/Renderbuffer_Object for
    more information.

    Parameters
    ----------
    width : :obj:`int`
        Buffer width in pixels.
    height : :obj:`int`
        Buffer height in pixels.
    internalFormat : :obj:`int`
        Format for renderbuffer data (e.g. GL_RGBA8, GL_DEPTH24_STENCIL8).
    samples : :obj:`int`
        Number of samples for multi-sampling, should be >1 and power-of-two.
        Work with one sample, but will raise a warning.

    Returns
    -------
    :obj:`Renderbuffer`
        A descriptor of the created renderbuffer.

    Notes
    -----
    The 'userData' field of the returned descriptor is a dictionary that can
    be used to store arbitrary data associated with the buffer.

    """
    width = int(width)
    height = int(height)

    # create a new renderbuffer ID
    rbId = GL.GLuint()
    GL.glGenRenderbuffers(1, ctypes.byref(rbId))
    GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, rbId)

    if samples > 1:
        # determine if the 'samples' value is valid
        maxSamples = getIntegerv(GL.GL_MAX_SAMPLES)
        if (samples & (samples - 1)) != 0:
            raise ValueError('Invalid number of samples, must be power-of-two.')
        elif samples <= 0 or samples > maxSamples:
            raise ValueError('Invalid number of samples, must be <{}.'.format(
                maxSamples))

        # create a multisample render buffer storage
        GL.glRenderbufferStorageMultisample(
            GL.GL_RENDERBUFFER,
            samples,
            internalFormat,
            width,
            height)

    else:
        GL.glRenderbufferStorage(
            GL.GL_RENDERBUFFER,
            internalFormat,
            width,
            height)

    # done, unbind it
    GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, 0)

    return Renderbuffer(rbId,
                        GL.GL_RENDERBUFFER,
                        width,
                        height,
                        internalFormat,
                        samples,
                        samples > 1,
                        dict())


def deleteRenderbuffer(renderBuffer):
    """Free the resources associated with a renderbuffer. This invalidates the
    renderbuffer's ID.

    Returns
    -------
    :obj:`None'

    """
    GL.glDeleteRenderbuffers(1, renderBuffer.id)


# -----------------
# Texture Functions
# -----------------

# 2D texture descriptor. You can 'wrap' existing texture IDs with TexImage2D to
# use them with functions that require that type as input.
#
#   texId = getTextureIdFromAPI()
#   texDesc = TexImage2D(texId, GL.GL_TEXTURE_2D, 1024, 1024)
#   attachFramebufferImage(fbo, texDesc, GL.GL_COLOR_ATTACHMENT0)
#   # examples of custom userData some function might access
#   texDesc.userData['flags'] = ['left_eye', 'clear_before_use']
#
TexImage2D = namedtuple(
    'TexImage2D',
    ['id',
     'target',
     'width',
     'height',
     'internalFormat',
     'pixelFormat',
     'dataType',
     'unpackAlignment',
     'samples',  # always 1
     'multisample',  # always False
     'userData'])


def createTexImage2D(width, height, target=GL.GL_TEXTURE_2D, level=0,
                     internalFormat=GL.GL_RGBA8, pixelFormat=GL.GL_RGBA,
                     dataType=GL.GL_FLOAT, data=None, unpackAlignment=4,
                     texParameters=()):
    """Create a 2D texture in video memory. This can only create a single 2D
    texture with targets GL_TEXTURE_2D or GL_TEXTURE_RECTANGLE.

    Parameters
    ----------
    width : :obj:`int`
        Texture width in pixels.
    height : :obj:`int`
        Texture height in pixels.
    target : :obj:`int`
        The target texture should only be either GL_TEXTURE_2D or
        GL_TEXTURE_RECTANGLE.
    level : :obj:`int`
        LOD number of the texture, should be 0 if GL_TEXTURE_RECTANGLE is the
        target.
    internalFormat : :obj:`int`
        Internal format for texture data (e.g. GL_RGBA8, GL_R11F_G11F_B10F).
    pixelFormat : :obj:`int`
        Pixel data format (e.g. GL_RGBA, GL_DEPTH_STENCIL)
    dataType : :obj:`int`
        Data type for pixel data (e.g. GL_FLOAT, GL_UNSIGNED_BYTE).
    data : :obj:`ctypes` or :obj:`None`
        Ctypes pointer to image data. If None is specified, the texture will be
        created but pixel data will be uninitialized.
    unpackAlignment : :obj:`int`
        Alignment requirements of each row in memory. Default is 4.
    texParameters : :obj:`list` of :obj:`tuple` of :obj:`int`
        Optional texture parameters specified as a list of tuples. These values
        are passed to 'glTexParameteri'. Each tuple must contain a parameter
        name and value. For example, texParameters=[(GL.GL_TEXTURE_MIN_FILTER,
        GL.GL_LINEAR), (GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)]

    Returns
    -------
    :obj:`TexImage2D`
        A TexImage2D descriptor.

    Notes
    -----
    The 'userData' field of the returned descriptor is a dictionary that can
    be used to store arbitrary data associated with the texture.

    Previous textures are unbound after calling 'createTexImage2D'.

    Examples
    --------
    import pyglet.gl as GL  # using Pyglet for now

    # empty texture
    textureDesc = createTexImage2D(1024, 1024, internalFormat=GL.GL_RGBA8)

    # load texture data from an image file using Pillow and NumPy
    from PIL import Image
    import numpy as np
    im = Image.open(imageFile)  # 8bpp!
    im = im.transpose(Image.FLIP_TOP_BOTTOM)  # OpenGL origin is at bottom
    im = im.convert("RGBA")
    pixelData = np.array(im).ctypes  # convert to ctypes!

    width = pixelData.shape[1]
    height = pixelData.shape[0]
    textureDesc = gltools.createTexImage2D(
        texture_array.shape[1],
        texture_array.shape[0],
        internalFormat=GL.GL_RGBA,
        pixelFormat=GL.GL_RGBA,
        dataType=GL.GL_UNSIGNED_BYTE,
        data=texture_array.ctypes,
        unpackAlignment=1,
        texParameters=[(GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR),
                       (GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)])

    GL.glBindTexture(GL.GL_TEXTURE_2D, textureDesc.id)

    """
    width = int(width)
    height = int(height)

    if width <= 0 or height <= 0:
        raise ValueError("Invalid image dimensions {} x {}.".format(
            width, height))

    if target == GL.GL_TEXTURE_RECTANGLE:
        if level != 0:
            raise ValueError("Invalid level for target GL_TEXTURE_RECTANGLE, "
                             "must be 0.")
        GL.glEnable(GL.GL_TEXTURE_RECTANGLE)

    colorTexId = GL.GLuint()
    GL.glGenTextures(1, ctypes.byref(colorTexId))
    GL.glBindTexture(target, colorTexId)
    GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, int(unpackAlignment))
    GL.glTexImage2D(target, level, internalFormat,
                    width, height, 0,
                    pixelFormat, dataType, data)

    # apply texture parameters
    if texParameters:
        for pname, param in texParameters:
            GL.glTexParameteri(target, pname, param)

    GL.glBindTexture(target, 0)

    return TexImage2D(colorTexId,
                      target,
                      width,
                      height,
                      internalFormat,
                      pixelFormat,
                      dataType,
                      unpackAlignment,
                      1,
                      False,
                      dict())


# Descriptor for 2D mutlisampled texture
TexImage2DMultisample = namedtuple(
    'TexImage2D',
    ['id',
     'target',
     'width',
     'height',
     'internalFormat',
     'samples',
     'multisample',
     'userData'])


def createTexImage2DMultisample(width, height,
                                target=GL.GL_TEXTURE_2D_MULTISAMPLE, samples=1,
                                internalFormat=GL.GL_RGBA8, texParameters=()):
    """Create a 2D multisampled texture.

    Parameters
    ----------
    width : :obj:`int`
        Texture width in pixels.
    height : :obj:`int`
        Texture height in pixels.
    target : :obj:`int`
        The target texture (e.g. GL_TEXTURE_2D_MULTISAMPLE).
    samples : :obj:`int`
        Number of samples for multi-sampling, should be >1 and power-of-two.
        Work with one sample, but will raise a warning.
    internalFormat : :obj:`int`
        Internal format for texture data (e.g. GL_RGBA8, GL_R11F_G11F_B10F).
    texParameters : :obj:`list` of :obj:`tuple` of :obj:`int`
        Optional texture parameters specified as a list of tuples. These values
        are passed to 'glTexParameteri'. Each tuple must contain a parameter
        name and value. For example, texParameters=[(GL.GL_TEXTURE_MIN_FILTER,
        GL.GL_LINEAR), (GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)]

    Returns
    -------
    :obj:`TexImage2DMultisample`
        A TexImage2DMultisample descriptor.

    """
    width = int(width)
    height = int(height)

    if width <= 0 or height <= 0:
        raise ValueError("Invalid image dimensions {} x {}.".format(
            width, height))

    # determine if the 'samples' value is valid
    maxSamples = getIntegerv(GL.GL_MAX_SAMPLES)
    if (samples & (samples - 1)) != 0:
        raise ValueError('Invalid number of samples, must be power-of-two.')
    elif samples <= 0 or samples > maxSamples:
        raise ValueError('Invalid number of samples, must be <{}.'.format(
            maxSamples))

    colorTexId = GL.GLuint()
    GL.glGenTextures(1, ctypes.byref(colorTexId))
    GL.glBindTexture(target, colorTexId)
    GL.glTexImage2DMultisample(
        target, samples, internalFormat, width, height, GL.GL_TRUE)

    # apply texture parameters
    if texParameters:
        for pname, param in texParameters:
            GL.glTexParameteri(target, pname, param)

    GL.glBindTexture(target, 0)

    return TexImage2DMultisample(colorTexId,
                                 target,
                                 width,
                                 height,
                                 internalFormat,
                                 samples,
                                 True,
                                 dict())


def deleteTexture(texture):
    """Free the resources associated with a texture. This invalidates the
    texture's ID.

    Returns
    -------
    :obj:`None'

    """
    GL.glDeleteTextures(1, texture.id)


# ---------------------------
# Vertex Buffer Objects (VBO)
# ---------------------------


Vertexbuffer = namedtuple(
    'Vertexbuffer',
    ['id',
     'vertexSize',
     'count',
     'indices',
     'usage',
     'bufferType',
     'dtype']
)


def createVertexbuffer(vertexData, vertexSize=3, bufferType=GL.GL_VERTEX_ARRAY):
    """Create a static, single-storage Vertex Buffer Object (VBO).

    Parameters
    ----------
    vertexData : :obj:`list` or :obj:`tuple` of :obj:`float`
        Coordinates as a 1D array of floats (e.g. [X0, Y0, Z0, X1, Y1, Z1, ...])
    vertexSize : :obj:`int`
        Number of coordinates per-vertex, default is 3.
    bufferType : :obj:`int`
        The type of data stored in the buffer (e.g. GL_VERTEX_ARRAY,
        GL_TEXTURE_COORD_ARRAY, GL_NORMAL_ARRAY, etc.)

    Returns
    -------
    Vertexbuffer
        A descriptor with vertex buffer information.

    Examples
    --------
    # vertices of a triangle
    verts = [ 1.0,  1.0, 0.0,   # v0
              0.0, -1.0, 0.0,   # v1
             -1.0,  1.0, 0.0]   # v2

    # load vertices to graphics device, return a descriptor
    vboDesc = createVertexbuffer(verts, 3)

    # draw
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vboDesc.id)
    GL.glVertexPointer(vboDesc.vertexSize, vboDesc.dtype, 0, None)
    GL.glEnableClientState(vboDesc.bufferType)
    GL.glDrawArrays(GL.GL_TRIANGLES, 0, vboDesc.indices)
    GL.glFlush()

    """
    # convert values to ctypes float array
    count = len(vertexData)
    c_array = (GL.GLfloat * count)(*vertexData)

    # create a vertex buffer ID
    vboId = GL.GLuint()
    GL.glGenBuffers(1, ctypes.byref(vboId))

    # new vertex descriptor
    vboDesc = Vertexbuffer(vboId,
                           vertexSize,
                           count,
                           int(count / vertexSize),
                           GL.GL_STATIC_DRAW,
                           bufferType,
                           GL.GL_FLOAT)  # always float

    # bind and upload
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vboId)
    GL.glBufferData(GL.GL_ARRAY_BUFFER,
                    ctypes.sizeof(c_array),
                    c_array,
                    GL.GL_STATIC_DRAW)
    # GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    return vboDesc


def drawVertexbuffers(vertexBuffer, *args, mode=GL.GL_TRIANGLES, flush=True):
    """Draw a vertex buffer using glDrawArrays. This method does not require
    shaders.

    Parameters
    ----------
    vertexBuffer : :obj:`Vertexbuffer`
        Vertex buffer descriptor, must have 'bufferType' as GL_VERTEX_ARRAY.
        Optional vertex buffer descriptors can be passed as seperate arguments,
        they must have 'bufferTypes' as GL_TEXTURE_COORD_ARRAY, GL_NORMAL_ARRAY
        or GL_COLOR_ARRAY.
    mode : :obj:`int`
        Drawing mode to use (e.g. GL_TRIANGLES, GL_QUADS, GL_POINTS, etc.)
    flush : :obj:`bool`
        Flush queued drawing commands before returning.

    Returns
    -------
    None

    Examples
    --------
    # vertices of a triangle
    verts = [ 1.0,  1.0, 0.0,   # v0
              0.0, -1.0, 0.0,   # v1
             -1.0,  1.0, 0.0]   # v2

    # triangle vertex colors
    colors = [1.0, 0.0, 0.0,  # v0
              0.0, 1.0, 0.0,  # v1
              0.0, 0.0, 1.0]  # v2

    # load vertices to graphics device, return a descriptor
    vertexBuffer = createVertexbuffer(verts, 3)
    colorBuffer = createVertexbuffer(c, 3, GL.GL_COLOR_ARRAY)

    # draw the VBO
    drawVertexbuffer(vertexBuffer, colorBuffer, GL.GL_TRIANGLES)

    """
    # must have a vertex pointer
    assert vertexBuffer.bufferType == GL.GL_VERTEX_ARRAY

    # bind and set the vertex pointer
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vertexBuffer.id)
    GL.glVertexPointer(vertexBuffer.vertexSize, vertexBuffer.dtype, 0, None)
    GL.glEnableClientState(vertexBuffer.bufferType)

    # handle additional buffers
    if args:
        for buffer in args:
            # check if the number of indicies are the same
            if vertexBuffer.indices != buffer.indices:
                raise RuntimeError("Vertex buffer indices do not match!")

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer.id)
            if buffer.bufferType == GL.GL_TEXTURE_COORD_ARRAY:
                GL.glTexCoordPointer(buffer.dtype, 0, None)
            elif buffer.bufferType == GL.GL_NORMAL_ARRAY:
                GL.glNormalPointer(buffer.dtype, 0, None)
            elif buffer.bufferType == GL.GL_COLOR_ARRAY:
                GL.glColorPointer(buffer.vertexSize, buffer.dtype, 0, None)

            GL.glEnableClientState(buffer.bufferType)

    GL.glDrawArrays(mode, 0, vertexBuffer.indices)  # draw arrays

    # reset
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
    GL.glDisableClientState(vertexBuffer.bufferType)
    if args:
        for vbo in args:
            GL.glDisableClientState(vbo.bufferType)

    if flush:
        GL.glFlush()


def deleteVertexbuffer(vbo):
    """Delete a vertex buffer.

    Returns
    -------
    :obj:`None'

    """
    GL.glDeleteBuffers(1, vbo.id)


# -----------------------------
# Misc. OpenGL Helper Functions
# -----------------------------

def getIntegerv(parName):
    """Get a single integer parameter value, return it as a Python integer.

    Parameters
    ----------
    pName : :obj:`int'
        OpenGL property enum to query (e.g. GL_MAJOR_VERSION).

    Returns
    -------
    int

    """
    val = GL.GLint()
    GL.glGetIntegerv(parName, val)

    return int(val.value)


def getFloatv(parName):
    """Get a single float parameter value, return it as a Python float.

    Parameters
    ----------
    pName : :obj:`float'
        OpenGL property enum to query.

    Returns
    -------
    int

    """
    val = GL.GLfloat()
    GL.glGetFloatv(parName, val)

    return float(val.value)


def getString(parName):
    """Get a single string parameter value, return it as a Python UTF-8 string.

    Parameters
    ----------
    pName : :obj:`int'
        OpenGL property enum to query (e.g. GL_VENDOR).

    Returns
    -------
    str

    """
    val = ctypes.cast(GL.glGetString(parName), ctypes.c_char_p).value
    return val.decode('UTF-8')


# OpenGL information type
OpenGLInfo = namedtuple(
    'OpenGLInfo',
    ['vendor',
     'renderer',
     'version',
     'majorVersion',
     'minorVersion',
     'doubleBuffer',
     'maxTextureSize',
     'stereo',
     'maxSamples',
     'extensions',
     'userData'])


def getOpenGLInfo():
    """Get general information about the OpenGL implementation on this machine.
    This should provide a consistent means of doing so regardless of the OpenGL
    interface we are using.

    Returns are dictionary with the following fields:

        vendor, renderer, version, majorVersion, minorVersion, doubleBuffer,
        maxTextureSize, stereo, maxSamples, extensions

    Supported extensions are returned as a list in the 'extensions' field. You
    can check if a platform supports an extension by checking the membership of
    the extension name in that list.

    Returns
    -------
    OpenGLInfo

    """
    return OpenGLInfo(getString(GL.GL_VENDOR),
                      getString(GL.GL_RENDERER),
                      getString(GL.GL_VERSION),
                      getIntegerv(GL.GL_MAJOR_VERSION),
                      getIntegerv(GL.GL_MINOR_VERSION),
                      getIntegerv(GL.GL_DOUBLEBUFFER),
                      getIntegerv(GL.GL_MAX_TEXTURE_SIZE),
                      getIntegerv(GL.GL_STEREO),
                      getIntegerv(GL.GL_MAX_SAMPLES),
                      [i for i in getString(GL.GL_EXTENSIONS).split(' ')],
                      dict())
