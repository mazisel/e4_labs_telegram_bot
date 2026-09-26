from psd_tools import PSDImage
from psd_tools.constants import BlendMode

def emphasize_footer_text(tmpl):
    """
    Makes the white footer texts/icons (social handle, website, phone) on the
    orange strip more prominent: slightly bolder plus a soft dark drop shadow.
    Modifies tmpl (RGBA) in place.
    """
    from PIL import Image, ImageChops, ImageFilter

    # Social handle, website, phone - all on the solid orange footer
    FOOTER_BOXES = [(18, 1274, 403, 1317), (732, 1275, 1063, 1317), (447, 1313, 630, 1343)]
    BANNER_GREEN = 109  # green channel of the orange (222, 109, 33); white is 255
    SHADOW_COLOR = (60, 25, 5, 255)
    SHADOW_ALPHA = 140

    # White-ness mask of the footer text (keeps anti-aliased edges)
    text_mask = Image.new("L", tmpl.size, 0)
    for box in FOOTER_BOXES:
        green = tmpl.crop(box).split()[1]
        text_mask.paste(green.point(lambda v: max(0, min(255, (v - BANNER_GREEN) * 255 // (255 - BANNER_GREEN)))), box[:2])

    # Slightly bolder: dilate at 4x resolution so strokes grow by ~1/4 px per side
    big = text_mask.resize((tmpl.width * 4, tmpl.height * 4), Image.LANCZOS).filter(ImageFilter.MaxFilter(3))
    bold_mask = ImageChops.lighter(text_mask, big.resize(tmpl.size, Image.LANCZOS))

    shadow = ImageChops.offset(bold_mask, 1, 2).filter(ImageFilter.GaussianBlur(1.5))
    tmpl.paste(SHADOW_COLOR, (0, 0), shadow.point(lambda v: v * SHADOW_ALPHA // 255))
    tmpl.paste((255, 255, 255, 255), (0, 0), bold_mask)

def generate_template():
    print("Loading PSD...")
    psd = PSDImage.open("assets/Hosgeldiniz.psd")
    
    layers_to_hide = [
        "T.C. Suşehri Belediyesi",
        "SİVAS",
        "FOTOĞRAF",
        # Hiding the sample photo main layer
        "Vector Smart Object", 
        # Hiding other possible artifact layers
        "img-signin.8188da91"
    ]
    
    
    # Target BBox for the sample photo (from analysis)
    PHOTO_BBOX = (223, 185, 858, 1044)
    
    for layer in psd.descendants():
        # Hide dynamic text placeholders
        if layer.name in ["T.C. Suşehri Belediyesi", "SİVAS", "FOTOĞRAF", "BAĞIMSIZ YEREL HAK-SEN", "Ailemize Hoşgeldiniz"]:
            # Actually, "BAĞIMSIZ..." and "Ailemize..." are static? 
            # User screenshot shows them. We should KEEP them visible.
            # Only hide the variable ones.
            pass
            
        if layer.name in ["T.C. Suşehri Belediyesi", "SİVAS", "FOTOĞRAF"]:
            layer.visible = False
            print(f"Hiding Text Layer: {layer.name}")

        # Hide the sample photo layer(s)
        # NOTE: img-signin.8188da91 is the LOGO - DO NOT HIDE IT
             
        if layer.name == "Vector Smart Object":
            # Check if this is the big photo layer
            # Comparison with tolerance
            box = layer.bbox
            if box[0] >= 220 and box[1] >= 180 and box[2] <= 860 and box[3] <= 1050:
                layer.visible = False
                print(f"Hiding Sample Photo Layer (Matched BBox): {layer.name} {box}")
                
            # Also check the other large background object just in case
            if box == (0, 0, 1080, 1350):
                 # This might be 'Layer 0' or similar. 
                 # We assume background is separate.
                 # Analyze output showed 'Layer 0' is smart object at full size.
                 pass
            
    print("Composing template...")
    image = psd.composite()
    image.save("assets/generated_template.png")
    
    # POST-PROCESSING: FORCE CLEAR THE PHOTO AREA
    # This ensures no white background layer blocks the user's photo
    print("Post-processing: Cutting hole for photo...")
    from PIL import Image, ImageDraw, ImageChops
    
    start_x, start_y, end_x, end_y = PHOTO_BBOX
    # We might want to keep the inner shadow/borders if they exist?
    # If we cut perfectly, we might lose inner shadow.
    # But user complained of "White box".
    # Let's cut slightly INSIDE if we want to keep borders, or EXACTLY if we trust the borders are outside.
    # The BBOX (223, 185, 858, 1044) is likely the content area.
    # Let's cut it exactly.
    
    tmpl = Image.open("assets/generated_template.png").convert("RGBA")
    draw = ImageDraw.Draw(tmpl)
    
    # Draw a clear rectangle (Eraser)
    draw.rectangle(PHOTO_BBOX, fill=(0,0,0,0), outline=None)

    # Shift the bottom-left slogan ("Türkiye gerçek sendikacılık...") right,
    # it touches the left edge in the PSD. The banner is solid orange, so only
    # the non-orange (text) pixels are moved.
    BANNER_COLOR = (222, 109, 33, 255)
    SLOGAN_BOX = (0, 1164, 366, 1212)
    SLOGAN_SHIFT_X = 24
    slogan = tmpl.crop(SLOGAN_BOX)
    banner = Image.new("RGBA", slogan.size, BANNER_COLOR)
    r, g, b, a = ImageChops.difference(slogan, banner).split()
    text_mask = ImageChops.lighter(ImageChops.lighter(r, g), ImageChops.lighter(b, a)).point(lambda v: 255 if v else 0)
    draw.rectangle((SLOGAN_BOX[0], SLOGAN_BOX[1], SLOGAN_BOX[2] - 1, SLOGAN_BOX[3] - 1), fill=BANNER_COLOR)
    tmpl.paste(slogan, (SLOGAN_BOX[0] + SLOGAN_SHIFT_X, SLOGAN_BOX[1]), text_mask)

    emphasize_footer_text(tmpl)

    tmpl.save("assets/generated_template.png")
    print("Template saved to assets/generated_template.png (Hole Cut)")

def generate_ziyaret_template():
    import os
    from PIL import Image, ImageDraw
    psd_path = "assets/ziyaret.psd"
    if not os.path.exists(psd_path):
        print(f"{psd_path} not found, skipping...")
        return
    
    print("Loading Ziyaret PSD...")
    psd = PSDImage.open(psd_path)
    
    # Save solid rounded photo mask
    mask = Image.new("L", (1007, 676), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, 1007, 676), radius=44, fill=255)
    mask.save("assets/ziyaret_photo_mask.png")
    print("Photo mask saved to assets/ziyaret_photo_mask.png")

    for layer in psd:
        if layer.name in ['görsel', 'metin']:
            layer.visible = False
            
    bg = psd.composite()
    bg.save("assets/ziyaret_template.png")
    print("Template saved to assets/ziyaret_template.png")


if __name__ == "__main__":
    generate_template()
    generate_ziyaret_template()
