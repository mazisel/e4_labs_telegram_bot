from PIL import Image, ImageDraw, ImageFont
import os
import os

class ImageComposer:
    def __init__(self, assets_dir="assets"):
        self.assets_dir = assets_dir
        # Use the generated template from PSD
        self.template_path = os.path.join(assets_dir, "generated_template.png")
        self.font_bold_path = os.path.join(assets_dir, "Poppins-Bold.ttf")
        self.font_light_path = os.path.join(assets_dir, "Poppins-Light.ttf")
        
        self.debug = False
        
        # Dimensions will be read from template
        self.width = 1080
        self.height = 1350

    def enable_debug(self):
        self.debug = True

    def _load_font(self, path, size):
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            print(f"Font not found: {path}")
            return ImageFont.load_default()

    def compose(self, user_photo_path, city_text, municipality_text, output_path):
        """
        Composes using PSD-derived coordinates and Auto-Fit text.
        """
        
        # PSD Constants
        # Photo Area: (223, 185, 858, 1044) -> W=635, H=859
        PHOTO_BOX = (223, 185, 858, 1044)
        PHOTO_W = 858 - 223
        PHOTO_H = 1044 - 185
        
        # Text Baseline - In the white strip below photo, above the bottom hook
        TEXT_Y = 1079
        
        # Text Anchors - Photo frame is 223-858
        # Municipality: Left aligned at left edge of photo frame
        MUNICIPALITY_X = 225
        # City: Right aligned, but avoid the hook/notch at bottom right (before X=720)
        CITY_X = 700
        
        # Max Widths - Keep texts from overlapping
        # Municipality can extend to ~500, City stays small
        MUNICIPALITY_MAX_W = 350
        CITY_MAX_W = 150 

        # 1. Canvas & Template
        if os.path.exists(self.template_path):
            template = Image.open(self.template_path).convert("RGBA")
            self.width, self.height = template.size
        else:
            print("Template not found! Run generate_template.py first.")
            return None
            
        canvas = Image.new("RGBA", (self.width, self.height), (255, 255, 255, 255))
        
        # 2. Photo (Paste First)
        try:
            photo = Image.open(user_photo_path).convert("RGBA")
            
            # Target size: PHOTO_W x PHOTO_H
            target_ratio = PHOTO_W / PHOTO_H
            photo_ratio = photo.width / photo.height
            
            if photo_ratio > target_ratio:
                # Wider -> Fit height
                new_height = PHOTO_H
                new_width = int(new_height * photo_ratio)
            else:
                # Taller -> Fit width
                new_width = PHOTO_W
                new_height = int(new_width / photo_ratio)
                
            photo = photo.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Crop to fit exactly
            left = (new_width - PHOTO_W) // 2
            top = (new_height - PHOTO_H) // 2
            photo = photo.crop((left, top, left + PHOTO_W, top + PHOTO_H))
            
            # Paste at specific coordinate
            canvas.paste(photo, (PHOTO_BOX[0], PHOTO_BOX[1]))
            
        except Exception as e:
            print(f"Error loading photo: {e}")

        # 3. Overlay Template
        canvas.alpha_composite(template)

        # 4. Text with Balanced Auto-Fit
        draw = ImageDraw.Draw(canvas)
        text_color = (0, 0, 0, 255)
        
        def calculate_max_font_size(text, font_path, max_width, start_size=32):
            font_size = start_size
            min_font_size = 14
            
            while font_size > min_font_size:
                font = self._load_font(font_path, font_size)
                # Check width
                length = draw.textlength(text, font=font)
                
                if length <= max_width:
                    return font_size
                
                font_size -= 2
            return min_font_size

        # Calculate optimal sizes independently (not balanced)
        # This allows short city names to be larger while long municipality names shrink
        mun_size = calculate_max_font_size(municipality_text, self.font_bold_path, MUNICIPALITY_MAX_W)
        city_size = calculate_max_font_size(city_text, self.font_light_path, CITY_MAX_W)
        
        # Helper to draw text with specified anchor
        def draw_text_final(x, y, text, font_path, size, anchor="ls"):
            font = self._load_font(font_path, size)
            draw.text((x, y), text, font=font, fill=text_color, anchor=anchor)

        # Draw Municipality: LEFT aligned at baseline
        draw_text_final(MUNICIPALITY_X, TEXT_Y, municipality_text, self.font_bold_path, mun_size, anchor="ls")
        
        # Draw City: RIGHT aligned at baseline
        draw_text_final(CITY_X, TEXT_Y, city_text, self.font_light_path, city_size, anchor="rs")

        # Debug overlay (optional)
        if self.debug:
            draw.rectangle(PHOTO_BOX, outline="red", width=5)
            draw.line([(0, TEXT_Y), (self.width, TEXT_Y)], fill="blue", width=1)
            draw.rectangle([MUNICIPALITY_X, TEXT_Y-20, MUNICIPALITY_X+MUNICIPALITY_MAX_W, TEXT_Y+20], outline="green")
            draw.rectangle([CITY_X, TEXT_Y-20, CITY_X+CITY_MAX_W, TEXT_Y+20], outline="orange")
            
        canvas.convert("RGB").save(output_path)
        return output_path

if __name__ == "__main__":
    # Test block
    composer = ImageComposer()
    # Create a dummy photo for testing if not exists
    if not os.path.exists("test_photo.jpg"):
        img = Image.new("RGB", (500, 500), color = "red")
        img.save("test_photo.jpg")
    
    composer.compose("test_photo.jpg", "İzmir", "Konak Belediyesi", "output_test.jpg")
    print("Test image created: output_test.jpg")
