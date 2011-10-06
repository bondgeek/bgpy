#!/usr/bin/env python
'''
Color handling

Uses python colorsys module and code from:

http://code.activestate.com/recipes/266466/
'''

import re
import numpy as np
import colorsys

reg_html = re.compile(r"""^#?([0-9a-fA-F]|[0-9a-fA-F]{2})([0-9a-fA-F]|[0-9a-fA-F]{2})([0-9a-fA-F]|[0-9a-fA-F]{2})?$""")

def color_rgb_html(r, g, b):
    """
    R, G, B values to #RRGGBB hex string. 
    Returns None on invalid input
    """
    rgb = (r, g, b)

    if max(rgb) <= 255 and min(rgb) >= 0:
        htmlcolor = '#%02x%02x%02x' % rgb
        return htmlcolor

    return None

        
def color_html_rgb(colorstring):
    """#RRGGBB or #RGB hex string to (R,G,B)"""
    
    colorstring = colorstring.strip()

    if (len(colorstring) == 6 or len(colorstring) == 3):
        reg_m = reg_html.match(colorstring)
        if reg_m:
            return tuple([int(n, 16) for n in reg_m.groups()])
    
    return None

def color_rgb_hsv(r, g, b):
    '''R, G, B [0-255] to HSV [angle, %, %]'''
  
    rgb = (r, g, b)

    if max(rgb) <= 255 and min(rgb) >= 0:
        r, g, b = [float(x) / 255. for x in rgb]

        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return (h * 360., s, v)
    return None

def color_hsv_rgb(h, s, v):
    '''HSV [angle, %, %] to r, g, b [0-255]'''

    if ((h >= 0. and h <= 360.) and
        (min((s, v)) >= 0. and max((s, v)) <= 1.0)):

        rgb = colorsys.hsv_to_rgb(h / 360., s, v)

        return tuple([int(x * 255.) for x in rgb])
    
    return None

if __name__ == "__main__":
    
    tests_good = ["#FFF", "#FFFFFF", "FFF", "FFFFFF", "#003333"]
    tests_bad = ["#GGG", "00H", "A", "FFF0", "GFGFGF", "FFFFFF00"]
    
    print("test valid codes:")
    for tst in tests_good:
        print tst, color_html_rgb(tst)
    
    print("\ntest invalid codes:")
    for tst in tests_bad:
        print tst, color_html_rgb(tst)
        