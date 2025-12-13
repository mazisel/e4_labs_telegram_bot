from PIL import Image

def analyze_template():
    try:
        img = Image.open("assets/template_frame.png")
        print(f"Format: {img.format}")
        print(f"Mode: {img.mode}")
        print(f"Size: {img.size}")
        
        # Check center pixel for transparency
        center_pixel = img.getpixel((img.width // 2, img.height // 2))
        print(f"Center pixel: {center_pixel}")
        
        if len(center_pixel) == 4 and center_pixel[3] == 0:
            print("Center is transparent.")
        else:
            print("Center is NOT transparent (likely white).")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_template()
