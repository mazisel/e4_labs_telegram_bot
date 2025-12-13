from psd_tools import PSDImage

def analyze_psd():
    psd = PSDImage.open("assets/Hosgeldiniz.psd")
    print(f"PSD Size: {psd.size}")
    
    print("\n--- Layers ---\n")
    for layer in psd.descendants():
        print(f"Name: {layer.name}, Visible: {layer.visible}, Kind: {layer.kind}, Box: {layer.bbox}")
        if layer.kind == "type":
             print(f"   -> Text: {layer.text}")

if __name__ == "__main__":
    analyze_psd()
