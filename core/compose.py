"""
Jovimetrix - http://www.github.com/amorano/jovimetrix
Composition
"""

from enum import Enum
from typing import Any

import torch
import numpy as np

from loguru import logger

from comfy.utils import ProgressBar

from Jovimetrix import JOV_WEB_RES_ROOT, JOVBaseNode, WILDCARD
from Jovimetrix.sup.lexicon import Lexicon
from Jovimetrix.sup.util import parse_dynamic, parse_parameter, zip_longest_fill, \
    EnumConvertType
from Jovimetrix.sup.image import  channel_merge, \
    channel_solid, channel_swap, cv2tensor_full, \
    image_crop, image_crop_center, image_crop_polygonal, image_grayscale, \
    image_mask, image_mask_add, image_matte, image_transform, \
    image_split, pixel_eval, tensor2cv, \
    image_edge_wrap, image_scalefit, cv2tensor, \
    image_stack, image_mirror, image_blend, \
    color_theory, remap_fisheye, remap_perspective, remap_polar, \
    remap_sphere, image_invert, \
    EnumImageType, EnumColorTheory, EnumProjection, \
    EnumScaleMode, EnumInterpolation, EnumBlendType, \
    EnumEdge, EnumMirrorMode, EnumOrientation, EnumPixelSwizzle, \
    MIN_IMAGE_SIZE

# =============================================================================

JOV_CATEGORY = "COMPOSE"

class EnumCropMode(Enum):
    CENTER = 20
    XY = 0
    FREE = 10

# =============================================================================

class TransformNode(JOVBaseNode):
    NAME = "TRANSFORM (JOV) 🏝️"
    NAME_URL = NAME.split(" (JOV)")[0].replace(" ", "%20")
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    DESCRIPTION = f"{JOV_WEB_RES_ROOT}/node/{NAME_URL}/{NAME_URL}.md"
    HELP_URL = f"{JOV_CATEGORY}#-{NAME_URL}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 0

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {}),
            Lexicon.XY: ("VEC2", {"default": (0, 0,), "step": 0.01, "precision": 4, "round": 0.00001, "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.ANGLE: ("FLOAT", {"default": 0, "min": -180, "max": 180, "step": 0.01, "precision": 4, "round": 0.00001}),
            Lexicon.SIZE: ("VEC2", {"default": (1., 1.), "step": 0.01, "precision": 4, "round": 0.00001, "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.TILE: ("VEC2", {"default": (1., 1.), "step": 0.1,  "precision": 4, "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.EDGE: (EnumEdge._member_names_, {"default": EnumEdge.CLIP.name}),
            Lexicon.MIRROR: (EnumMirrorMode._member_names_, {"default": EnumMirrorMode.NONE.name}),
            Lexicon.PIVOT: ("VEC2", {"default": (0.5, 0.5), "step": 0.005, "precision": 4, "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.PROJECTION: (EnumProjection._member_names_, {"default": EnumProjection.NORMAL.name}),
            Lexicon.TLTR: ("VEC4", {"default": (0, 0, 1, 0), "step": 0.005, "precision": 4, "label": [Lexicon.TOP, Lexicon.LEFT, Lexicon.TOP, Lexicon.RIGHT]}),
            Lexicon.BLBR: ("VEC4", {"default": (0, 1, 1, 1), "step": 0.005, "precision": 4, "label": [Lexicon.BOTTOM, Lexicon.LEFT, Lexicon.BOTTOM, Lexicon.RIGHT]}),
            Lexicon.STRENGTH: ("FLOAT", {"default": 1, "min": 0, "precision": 4, "step": 0.005}),
            Lexicon.MODE: (EnumScaleMode._member_names_, {"default": EnumScaleMode.NONE.name}),
            Lexicon.WH: ("VEC2", {"default": (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), "step": 1, "label": [Lexicon.W, Lexicon.H]}),
            Lexicon.SAMPLE: (EnumInterpolation._member_names_, {"default": EnumInterpolation.LANCZOS4.name}),
            Lexicon.MATTE: ("VEC4", {"default": (0, 0, 0, 255), "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A], "rgb": True})
        }}
        return Lexicon._parse(d, cls.HELP_URL)

    def run(self, **kw) -> tuple[torch.Tensor, torch.Tensor]:
        pA = parse_parameter(Lexicon.PIXEL, kw, None, EnumConvertType.IMAGE)
        offset = parse_parameter(Lexicon.XY, kw, (0, 0), EnumConvertType.VEC2)
        angle = parse_parameter(Lexicon.ANGLE, kw, 1, EnumConvertType.FLOAT)
        size = parse_parameter(Lexicon.SIZE, kw, (1, 1), EnumConvertType.VEC2, zero=0.001)
        edge = parse_parameter(Lexicon.EDGE, kw, EnumEdge.CLIP.name, EnumConvertType.STRING)
        mirror = parse_parameter(Lexicon.MIRROR, kw, EnumMirrorMode.NONE.name, EnumConvertType.STRING)
        mirror_pivot = parse_parameter(Lexicon.PIVOT, kw, (0.5, 0.5), EnumConvertType.VEC2, 0, 1)
        tile_xy = parse_parameter(Lexicon.TILE, kw, (1, 1), EnumConvertType.VEC2INT, 1)
        proj = parse_parameter(Lexicon.PROJECTION, kw, EnumProjection.NORMAL.name, EnumConvertType.STRING)
        tltr = parse_parameter(Lexicon.TLTR, kw, (0, 0, 1, 0), EnumConvertType.VEC4, 0, 1)
        blbr = parse_parameter(Lexicon.BLBR, kw, (0, 1, 1, 1), EnumConvertType.VEC4, 0, 1)
        strength = parse_parameter(Lexicon.STRENGTH, kw, 1, EnumConvertType.FLOAT, 0, 1)
        mode = parse_parameter(Lexicon.MODE, kw, EnumScaleMode.NONE.name, EnumConvertType.STRING)
        wihi = parse_parameter(Lexicon.WH, kw, (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), EnumConvertType.VEC2INT, 1)
        sample = parse_parameter(Lexicon.SAMPLE, kw, EnumInterpolation.LANCZOS4.name, EnumConvertType.STRING)
        matte = parse_parameter(Lexicon.MATTE, kw, (0, 0, 0, 255), EnumConvertType.VEC4INT, 0, 255)
        params = [tuple(x) for x in zip_longest_fill(pA, offset, angle, size, edge, tile_xy, mirror, mirror_pivot, proj, strength, tltr, blbr, mode, wihi, sample, matte)]
        images = []
        pbar = ProgressBar(len(params))
        for idx, (pA, offset, angle, size, edge, tile_xy, mirror, mirror_pivot, proj, strength, tltr, blbr, mode, wihi, sample, matte) in enumerate(params):
            matte = pixel_eval(matte, EnumImageType.BGRA)
            pA = tensor2cv(pA)
            h, w = pA.shape[:2]
            edge = EnumEdge[edge]
            sample = EnumInterpolation[sample]
            pA = image_transform(pA, offset, angle, size, sample, edge)
            pA = image_crop_center(pA, w, h)

            mirror = EnumMirrorMode[mirror]
            if mirror != EnumMirrorMode.NONE:
                mpx, mpy = mirror_pivot
                pA = image_mirror(pA, mirror, mpx, mpy)
                print(pA.shape)
                pA = image_scalefit(pA, w, h, EnumScaleMode.FIT, sample)
                print(pA.shape)

            tx, ty = tile_xy
            if tx != 1. or ty != 1.:
                pA = image_edge_wrap(pA, tx / 2 - 0.5, ty / 2 - 0.5)
                pA = image_scalefit(pA, w, h, EnumScaleMode.FIT, sample)

            proj = EnumProjection[proj]
            match proj:
                case EnumProjection.PERSPECTIVE:
                    x1, y1, x2, y2 = tltr
                    x4, y4, x3, y3 = blbr
                    sh, sw = pA.shape[:2]
                    x1, x2, x3, x4 = map(lambda x: x * sw, [x1, x2, x3, x4])
                    y1, y2, y3, y4 = map(lambda y: y * sh, [y1, y2, y3, y4])
                    pA = remap_perspective(pA, [[x1, y1], [x2, y2], [x3, y3], [x4, y4]])
                case EnumProjection.SPHERICAL:
                    pA = remap_sphere(pA, strength)
                case EnumProjection.FISHEYE:
                    pA = remap_fisheye(pA, strength)
                case EnumProjection.POLAR:
                    pA = remap_polar(pA)

            if proj != EnumProjection.NORMAL:
                pA = image_scalefit(pA, w, h, EnumScaleMode.FIT, sample)

            mode = EnumScaleMode[mode]
            if mode != EnumScaleMode.NONE:
                w, h = wihi
                pA = image_scalefit(pA, w, h, mode, sample)

            images.append(cv2tensor_full(pA, matte))
            pbar.update_absolute(idx)
        return [torch.stack(i, dim=0).squeeze(1) for i in list(zip(*images))]

class BlendNode(JOVBaseNode):
    NAME = "BLEND (JOV) ⚗️"
    NAME_URL = NAME.split(" (JOV)")[0].replace(" ", "%20")
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    DESCRIPTION = f"{JOV_WEB_RES_ROOT}/node/{NAME_URL}/{NAME_URL}.md"
    HELP_URL = f"{JOV_CATEGORY}#-{NAME_URL}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 10

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL_A: (WILDCARD, {"tooltip": "Background Plate"}),
            Lexicon.PIXEL_B: (WILDCARD, {"tooltip": "Image to Overlay on Background Plate"}),
            Lexicon.MASK: (WILDCARD, {"tooltip": "Optional Mask to use for Alpha Blend Operation. If empty, will use the ALPHA of B"}),
            Lexicon.FUNC: (EnumBlendType._member_names_, {"default": EnumBlendType.NORMAL.name, "tooltip": "Blending Operation"}),
            Lexicon.A: ("FLOAT", {"default": 1, "min": 0, "max": 1, "step": 0.01, "tooltip": "Amount of Blending to Perform on the Selected Operation"}),
            Lexicon.FLIP: ("BOOLEAN", {"default": False}),
            Lexicon.INVERT: ("BOOLEAN", {"default": False, "tooltip": "Invert the mask input"}),
            Lexicon.MODE: (EnumScaleMode._member_names_, {"default": EnumScaleMode.NONE.name}),
            Lexicon.WH: ("VEC2", {"default": (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), "step": 1, "label": [Lexicon.W, Lexicon.H]}),
            Lexicon.SAMPLE: (EnumInterpolation._member_names_, {"default": EnumInterpolation.LANCZOS4.name}),
            Lexicon.MATTE: ("VEC4", {"default": (0, 0, 0, 255), "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A], "rgb": True})
        }}
        return Lexicon._parse(d, cls.HELP_URL)

    def run(self, **kw) -> tuple[torch.Tensor, torch.Tensor]:
        pA = parse_parameter(Lexicon.PIXEL_A, kw, None, EnumConvertType.IMAGE)
        pB = parse_parameter(Lexicon.PIXEL_B, kw, None, EnumConvertType.IMAGE)
        mask = parse_parameter(Lexicon.MASK, kw, None, EnumConvertType.IMAGE)
        func = parse_parameter(Lexicon.FUNC, kw, EnumBlendType.NORMAL.name, EnumConvertType.STRING)
        alpha = parse_parameter(Lexicon.A, kw, 1, EnumConvertType.FLOAT, 0, 1)
        flip = parse_parameter(Lexicon.FLIP, kw, False, EnumConvertType.BOOLEAN)
        mode = parse_parameter(Lexicon.MODE, kw, EnumScaleMode.NONE.name, EnumConvertType.STRING)
        wihi = parse_parameter(Lexicon.WH, kw, (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), EnumConvertType.VEC2INT, 1)
        sample = parse_parameter(Lexicon.SAMPLE, kw, EnumInterpolation.LANCZOS4.name, EnumConvertType.STRING)
        matte = parse_parameter(Lexicon.MATTE, kw, (0, 0, 0), EnumConvertType.VEC3INT, 0, 255)
        invert = parse_parameter(Lexicon.INVERT, kw, False, EnumConvertType.BOOLEAN)
        params = [tuple(x) for x in zip_longest_fill(pA, pB, mask, func, alpha, flip, mode, wihi, sample, matte, invert)]
        images = []
        pbar = ProgressBar(len(params))
        for idx, (pA, pB, mask, func, alpha, flip, mode, wihi, sample, matte, invert) in enumerate(params):

            if flip:
                pA, pB = pB, pA

            w, h = MIN_IMAGE_SIZE, MIN_IMAGE_SIZE
            if pA is not None:
                h, w = pA.size()[2:]
            elif pB is not None:
                h, w = pB.size()[2:]

            matte = pixel_eval(matte, EnumImageType.BGRA)
            pA = tensor2cv(pA, width=w, height=h)
            pA = image_matte(pA, matte)
            pB = tensor2cv(pB, width=w, height=h)

            if mask is None:
                mask = image_mask(pB)
            else:
                h, w = pB.shape[:2]
                mask = tensor2cv(mask, EnumImageType.GRAYSCALE, w, h)

            if invert:
                mask = 255 - mask

            func = EnumBlendType[func]
            img = image_blend(pA, pB, mask, func, alpha)
            mode = EnumScaleMode[mode]
            if mode != EnumScaleMode.NONE:
                w, h = wihi
                sample = EnumInterpolation[sample]
                img = image_scalefit(img, w, h, mode, sample)
            img = cv2tensor_full(img, matte)
            images.append(img)
            pbar.update_absolute(idx)
        return [torch.stack(i, dim=0).squeeze(1) for i in list(zip(*images))]

class PixelSplitNode(JOVBaseNode):
    NAME = "PIXEL SPLIT (JOV) 💔"
    NAME_URL = NAME.split(" (JOV)")[0].replace(" ", "%20")
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    DESCRIPTION = f"{JOV_WEB_RES_ROOT}/node/{NAME_URL}/{NAME_URL}.md"
    HELP_URL = f"{JOV_CATEGORY}#-{NAME_URL}"
    RETURN_TYPES = ("MASK", "MASK", "MASK", "MASK",)
    RETURN_NAMES = (Lexicon.RI, Lexicon.GI, Lexicon.BI, Lexicon.MI)
    SORT = 40

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {})
        }}
        return Lexicon._parse(d, cls.HELP_URL)

    def run(self, **kw) -> tuple[torch.Tensor, torch.Tensor]:
        images = []
        pA = parse_parameter(Lexicon.PIXEL, kw, None, EnumConvertType.IMAGE)
        pbar = ProgressBar(len(pA))
        for idx, (pA,) in enumerate(pA):
            pA = tensor2cv(pA)
            pA = image_mask_add(pA)
            pA = [cv2tensor(image_grayscale(x)) for x in image_split(pA)]
            images.append(pA)
            pbar.update_absolute(idx)
        return [torch.stack(i, dim=0).squeeze(1) for i in list(zip(*images))]

class PixelMergeNode(JOVBaseNode):
    NAME = "PIXEL MERGE (JOV) 🫂"
    NAME_URL = NAME.split(" (JOV)")[0].replace(" ", "%20")
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    DESCRIPTION = f"{JOV_WEB_RES_ROOT}/node/{NAME_URL}/{NAME_URL}.md"
    HELP_URL = f"{JOV_CATEGORY}#-{NAME_URL}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 45

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.R: (WILDCARD, {}),
            Lexicon.G: (WILDCARD, {}),
            Lexicon.B: (WILDCARD, {}),
            Lexicon.A: (WILDCARD, {}),
            Lexicon.MATTE: ("VEC4", {"default": (0, 0, 0, 255), "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A], "rgb": True})
        }}
        return Lexicon._parse(d, cls.HELP_URL)

    def run(self, **kw)  -> tuple[torch.Tensor, torch.Tensor]:
        R = parse_parameter(Lexicon.R, kw, None, EnumConvertType.IMAGE)
        G = parse_parameter(Lexicon.G, kw, None, EnumConvertType.IMAGE)
        B = parse_parameter(Lexicon.B, kw, None, EnumConvertType.IMAGE)
        A = parse_parameter(Lexicon.A, kw, None, EnumConvertType.IMAGE)
        if len(R)+len(B)+len(G)+len(A) == 0:
            img = channel_solid(MIN_IMAGE_SIZE, MIN_IMAGE_SIZE, 0, EnumImageType.BGRA)
            return list(cv2tensor_full(img, matte))
        matte = parse_parameter(Lexicon.MATTE, kw, (0, 0, 0), EnumConvertType.VEC3INT, 0, 255)
        params = [tuple(x) for x in zip_longest_fill(R, G, B, A, matte)]
        images = []
        pbar = ProgressBar(len(params))
        for idx, (r, g, b, a, matte) in enumerate(params):
            r = tensor2cv(r, EnumImageType.GRAYSCALE)
            g = tensor2cv(g, EnumImageType.GRAYSCALE)
            b = tensor2cv(b, EnumImageType.GRAYSCALE)
            mask = tensor2cv(a, EnumImageType.GRAYSCALE)
            img = channel_merge([b, g, r, mask])
            images.append(cv2tensor_full(img, matte))
            pbar.update_absolute(idx)
        return [torch.stack(i, dim=0).squeeze(1) for i in list(zip(*images))]

class PixelSwapNode(JOVBaseNode):
    NAME = "PIXEL SWAP (JOV) 🔃"
    NAME_URL = NAME.split(" (JOV)")[0].replace(" ", "%20")
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    DESCRIPTION = f"{JOV_WEB_RES_ROOT}/node/{NAME_URL}/{NAME_URL}.md"
    HELP_URL = f"{JOV_CATEGORY}#-{NAME_URL}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    # OUTPUT_IS_LIST = ()
    SORT = 48

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL_A: (WILDCARD, {}),
            Lexicon.PIXEL_B: (WILDCARD, {}),
            Lexicon.SWAP_R: (EnumPixelSwizzle._member_names_,
                             {"default": EnumPixelSwizzle.RED_A.name}),
            Lexicon.R: ("INT", {"default": 0, "step": 1, "min": 0, "max": 255}),
            Lexicon.SWAP_G: (EnumPixelSwizzle._member_names_,
                             {"default": EnumPixelSwizzle.GREEN_A.name}),
            Lexicon.G: ("INT", {"default": 0, "step": 1, "min": 0, "max": 255}),
            Lexicon.SWAP_B: (EnumPixelSwizzle._member_names_,
                             {"default": EnumPixelSwizzle.BLUE_A.name}),
            Lexicon.B: ("INT", {"default": 0, "step": 1, "min": 0, "max": 255}),
            Lexicon.SWAP_A: (EnumPixelSwizzle._member_names_,
                             {"default": EnumPixelSwizzle.ALPHA_A.name}),
            Lexicon.A: ("INT", {"default": 0, "step": 1, "min": 0, "max": 255}),
        }}
        return Lexicon._parse(d, cls.HELP_URL)

    def run(self, **kw)  -> tuple[torch.Tensor, torch.Tensor]:
        pA = parse_parameter(Lexicon.PIXEL_A, kw, None, EnumConvertType.IMAGE)
        pB = parse_parameter(Lexicon.PIXEL_B, kw, None, EnumConvertType.IMAGE)
        swap_r = parse_parameter(Lexicon.SWAP_R, kw, EnumPixelSwizzle.RED_A.name, EnumConvertType.STRING)
        r = parse_parameter(Lexicon.R, kw, 0, EnumConvertType.INT, 0, 255)
        swap_g = parse_parameter(Lexicon.SWAP_G, kw, EnumPixelSwizzle.GREEN_A.name, EnumConvertType.STRING)
        g = parse_parameter(Lexicon.G, kw, 0, EnumConvertType.INT, 0, 255)
        swap_b = parse_parameter(Lexicon.SWAP_B, kw, EnumPixelSwizzle.BLUE_A.name, EnumConvertType.STRING)
        b = parse_parameter(Lexicon.B, kw, 0, EnumConvertType.INT, 0, 255)
        swap_a = parse_parameter(Lexicon.SWAP_A, kw, EnumPixelSwizzle.ALPHA_A.name, EnumConvertType.STRING)
        a = parse_parameter(Lexicon.A, kw, 0, EnumConvertType.INT, 0, 255)
        params = [tuple(x) for x in zip_longest_fill(pA, pB, r, swap_r, g, swap_g,
                                                     b, swap_b, a, swap_a)]
        images = []
        pbar = ProgressBar(len(params))
        for idx, (pA, pB, r, swap_r, g, swap_g, b, swap_b, a, swap_a) in enumerate(params):
            pA = tensor2cv(pA)
            h, w = pA.shape[:2]
            pB = tensor2cv(pB, width=w, height=h)
            out = channel_solid(w, h, (r,g,b,a), EnumImageType.BGRA)

            def swapper(swap_out:EnumPixelSwizzle, swap_in:EnumPixelSwizzle) -> np.ndarray[Any]:
                target = out
                swap_in = EnumPixelSwizzle[swap_in]
                if swap_in in [EnumPixelSwizzle.RED_A, EnumPixelSwizzle.GREEN_A,
                            EnumPixelSwizzle.BLUE_A, EnumPixelSwizzle.ALPHA_A]:
                    target = pA
                elif swap_in != EnumPixelSwizzle.CONSTANT:
                    target = pB
                if swap_in != EnumPixelSwizzle.CONSTANT:
                    target = channel_swap(pA, swap_out, target, swap_in)
                return target

            out[:,:,0] = swapper(EnumPixelSwizzle.BLUE_A, swap_b)[:,:,0]
            out[:,:,1] = swapper(EnumPixelSwizzle.GREEN_A, swap_g)[:,:,1]
            out[:,:,2] = swapper(EnumPixelSwizzle.RED_A, swap_r)[:,:,2]
            out[:,:,3] = swapper(EnumPixelSwizzle.ALPHA_A, swap_a)[:,:,3]
            images.append(cv2tensor_full(out))
            pbar.update_absolute(idx)
        return [torch.stack(i, dim=0).squeeze(1) for i in list(zip(*images))]

class StackNode(JOVBaseNode):
    NAME = "STACK (JOV) ➕"
    NAME_URL = NAME.split(" (JOV)")[0].replace(" ", "%20")
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    DESCRIPTION = f"{JOV_WEB_RES_ROOT}/node/{NAME_URL}/{NAME_URL}.md"
    HELP_URL = f"{JOV_CATEGORY}#-{NAME_URL}"
    INPUT_IS_LIST = False
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 75

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.AXIS: (EnumOrientation._member_names_, {"default": EnumOrientation.GRID.name}),
            Lexicon.STEP: ("INT", {"min": 1, "step": 1, "default": 1}),
            Lexicon.MODE: (EnumScaleMode._member_names_, {"default": EnumScaleMode.NONE.name}),
            Lexicon.WH: ("VEC2", {"default": (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), "step": 1, "label": [Lexicon.W, Lexicon.H]}),
            Lexicon.SAMPLE: (EnumInterpolation._member_names_, {"default": EnumInterpolation.LANCZOS4.name}),
            Lexicon.MATTE: ("VEC4", {"default": (0, 0, 0, 255), "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A], "rgb": True})
        }}
        return Lexicon._parse(d, cls.HELP_URL)

    def run(self, **kw) -> tuple[torch.Tensor, torch.Tensor]:
        images = []
        images.extend([r for r in parse_dynamic(Lexicon.PIXEL, kw)])
        if len(images) == 0:
            logger.warning("no images to stack")
            return
        axis = parse_parameter(Lexicon.AXIS, kw, EnumOrientation.GRID.name, EnumConvertType.STRING)[0]
        axis = EnumOrientation[axis]
        stride = parse_parameter(Lexicon.STEP, kw, 1, EnumConvertType.INT)[0]
        mode = parse_parameter(Lexicon.MODE, kw, EnumScaleMode.NONE.name, EnumConvertType.STRING)[0]
        mode = EnumScaleMode[mode]
        wihi = parse_parameter(Lexicon.WH, kw, (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), EnumConvertType.VEC2INT, 1)[0]
        sample = parse_parameter(Lexicon.SAMPLE, kw, EnumInterpolation.LANCZOS4.name, EnumConvertType.STRING)[0]
        matte = parse_parameter(Lexicon.MATTE, kw, (0, 0, 0, 255), EnumConvertType.VEC4INT, 0, 255)[0]
        matte = pixel_eval(matte, EnumImageType.BGRA)
        images = [tensor2cv(img) for img in images]
        img = image_stack(images, axis, stride, matte)
        w, h = wihi
        if mode != EnumScaleMode.NONE:
            sample = EnumInterpolation[sample]
            img = image_scalefit(img, w, h, mode, sample)
        return cv2tensor_full(img, matte)

class CropNode(JOVBaseNode):
    NAME = "CROP (JOV) ✂️"
    NAME_URL = NAME.split(" (JOV)")[0].replace(" ", "%20")
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    DESCRIPTION = f"{JOV_WEB_RES_ROOT}/node/{NAME_URL}/{NAME_URL}.md"
    HELP_URL = f"{JOV_CATEGORY}#-{NAME_URL}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 5

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {}),
            Lexicon.FUNC: (EnumCropMode._member_names_, {"default": EnumCropMode.CENTER.name}),
            Lexicon.XY: ("VEC2", {"default": (0, 0), "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.WH: ("VEC2", {"default": (512, 512), "step": 1, "label": [Lexicon.W, Lexicon.H]}),
            Lexicon.TLTR: ("VEC4", {"default": (0, 0, 0, 1), "step": 0.01, "precision": 5, "round": 0.000001, "label": [Lexicon.TOP, Lexicon.LEFT, Lexicon.TOP, Lexicon.RIGHT]}),
            Lexicon.BLBR: ("VEC4", {"default": (1, 0, 1, 1), "step": 0.01, "precision": 5, "round": 0.000001, "label": [Lexicon.BOTTOM, Lexicon.LEFT, Lexicon.BOTTOM, Lexicon.RIGHT]}),
            Lexicon.RGB: ("VEC3", {"default": (0, 0, 0),  "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B], "rgb": True})
        }}
        return Lexicon._parse(d, cls.HELP_URL)

    def run(self, **kw) -> tuple[list[torch.Tensor], list[torch.Tensor]]:
        pA = parse_parameter(Lexicon.PIXEL, kw, None, EnumConvertType.IMAGE)
        func = parse_parameter(Lexicon.FUNC, kw, EnumCropMode.CENTER.name, EnumConvertType.STRING)
        # if less than 1 then use as scalar, over 1 = int(size)
        xy = parse_parameter(Lexicon.XY, kw, (0, 0,), EnumConvertType.VEC2, 1)
        wihi = parse_parameter(Lexicon.WH, kw, (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), EnumConvertType.VEC2INT, 1)
        tltr = parse_parameter(Lexicon.TLTR, kw, (0, 0, 0, 1,), EnumConvertType.VEC4, 0, 1)
        blbr = parse_parameter(Lexicon.BLBR, kw, (1, 0, 1, 1,), EnumConvertType.VEC4, 0, 1)
        color = parse_parameter(Lexicon.RGB, kw, (0, 0, 0,), EnumConvertType.VEC3INT, 0, 255)
        params = [tuple(x) for x in zip_longest_fill(pA, func, xy, wihi, tltr, blbr, color)]
        images = []
        pbar = ProgressBar(len(params))
        for idx, (pA, func, xy, wihi, tltr, blbr, color) in enumerate(params):
            width, height = wihi
            pA = tensor2cv(pA, width=width, height=height)
            func = EnumCropMode[func]
            if func == EnumCropMode.FREE:
                y1, x1, y2, x2 = tltr
                y4, x4, y3, x3 = blbr
                points = [(x1 * width, y1 * height), (x2 * width, y2 * height),
                          (x3 * width, y3 * height), (x4 * width, y4 * height)]
                pA = image_crop_polygonal(pA, points)
            elif func == EnumCropMode.XY:
                pA = image_crop(pA, width, height, xy)
            else:
                pA = image_crop_center(pA, width, height)
            images.append(cv2tensor_full(pA, color))
            pbar.update_absolute(idx)
        return [torch.stack(i, dim=0).squeeze(1) for i in list(zip(*images))]

class ColorTheoryNode(JOVBaseNode):
    NAME = "COLOR THEORY (JOV) 🛞"
    NAME_URL = NAME.split(" (JOV)")[0].replace(" ", "%20")
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    DESCRIPTION = f"{JOV_WEB_RES_ROOT}/node/{NAME_URL}/{NAME_URL}.md"
    HELP_URL = f"{JOV_CATEGORY}#-{NAME_URL}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = (Lexicon.C1, Lexicon.C2, Lexicon.C3, Lexicon.C4, Lexicon.C5)
    SORT = 100

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {}),
            Lexicon.SCHEME: (EnumColorTheory._member_names_, {"default": EnumColorTheory.COMPLIMENTARY.name}),
            Lexicon.VALUE: ("INT", {"default": 45, "min": -90, "max": 90, "step": 1, "tooltip": "Custom angle of separation to use when calculating colors"}),
            Lexicon.INVERT: ("BOOLEAN", {"default": False})
        }}
        return Lexicon._parse(d, cls.HELP_URL)

    def run(self, **kw) -> tuple[list[torch.Tensor], list[torch.Tensor]]:
        pA = parse_parameter(Lexicon.PIXEL, kw, None, EnumConvertType.IMAGE)
        scheme = parse_parameter(Lexicon.SCHEME, kw, EnumColorTheory.COMPLIMENTARY.name, EnumConvertType.STRING)
        user = parse_parameter(Lexicon.VALUE, kw, 0, EnumConvertType.INT, -180, 180)
        invert = parse_parameter(Lexicon.INVERT, kw, False, EnumConvertType.BOOLEAN)
        params = [tuple(x) for x in zip_longest_fill(pA, scheme, user, invert)]
        images = []
        pbar = ProgressBar(len(params))
        for idx, (img, target, user, invert) in enumerate(params):
            img = tensor2cv(img)
            target = EnumColorTheory[target]
            img = color_theory(img, user, target)
            if invert:
                img = (image_invert(s, 1) for s in img)
            images.append([cv2tensor(a) for a in img])
            pbar.update_absolute(idx)
        return [torch.stack(i, dim=0).squeeze(1) for i in list(zip(*images))]

"""
class HistogramNode(JOVImageSimple):
    NAME = "HISTOGRAM (JOV) 👁‍🗨"
    NAME_URL = NAME.split(" (JOV)")[0].replace(" ", "%20")
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    DESCRIPTION = f"{JOV_WEB_RES_ROOT}/node/{NAME_URL}/{NAME_URL}.md"
    HELP_URL = f"{JOV_CATEGORY}#-{NAME_URL}"
        RETURN_TYPES = ("IMAGE", )
    RETURN_NAMES = (Lexicon.IMAGE,)
    OUTPUT_IS_LIST = (True,)
    SORT = 40

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {}),
        }}
        return Lexicon._parse(d, cls.HELP_URL)

    def run(self, **kw) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        pA = parse_parameter(Lexicon.PIXEL, kw, None, EnumConvertType.IMAGE)
        params = [tuple(x) for x in zip_longest_fill(pA,)]
        images = []
        pbar = ProgressBar(len(params))
        for idx, (pA, ) in enumerate(params):
            pA = image_histogram(pA)
            pA = image_histogram_normalize(pA)
            images.append(cv2tensor(pA))
            pbar.update_absolute(idx)
        return list(zip(*images))
"""
