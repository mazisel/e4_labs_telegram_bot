from psd_tools import PSDImage
from psd_tools.constants import BlendMode

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
    from PIL import Image, ImageDraw
    
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
    
    tmpl.save("assets/generated_template.png")
    print("Template saved to assets/generated_template.png (Hole Cut)")

if __name__ == "__main__":
    generate_template()
