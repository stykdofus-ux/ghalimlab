import os
import pathlib
from PIL import Image, ImageDraw

def create_default_branding():
    branding_dir = pathlib.Path("uploads/branding")
    branding_dir.mkdir(parents=True, exist_ok=True)

    # 1. SVG Logo
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 80" width="320" height="80">
  <defs>
    <linearGradient id="gradLab" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284C7" />
      <stop offset="100%" stop-color="#0F766E" />
    </linearGradient>
  </defs>
  <rect x="8" y="10" width="60" height="60" rx="14" fill="url(#gradLab)" />
  <path d="M38 24 C30 24 26 30 26 38 C26 48 38 58 38 58 C38 58 50 48 50 38 C50 30 46 24 38 24 Z" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="38" cy="37" r="4" fill="#FFFFFF" />
  <text x="80" y="38" font-family="Arial, sans-serif" font-size="22" font-weight="bold" fill="#0F172A">GHALIM<tspan fill="#0284C7">LAB</tspan></text>
  <text x="82" y="53" font-family="Arial, sans-serif" font-size="8.5" font-weight="bold" fill="#64748B" letter-spacing="1.5">BIOLOGIE MEDICALE</text>
  <text x="82" y="65" font-family="Arial, sans-serif" font-size="7.5" fill="#0F766E">LIMS &amp; AUTOMATION CERTIFIE</text>
</svg>"""
    with open(branding_dir / "logo.svg", "w", encoding="utf-8") as f:
        f.write(svg_content)

    # 2. PNG Logo
    img_logo = Image.new("RGBA", (640, 160), (255, 255, 255, 0))
    d_logo = ImageDraw.Draw(img_logo)
    d_logo.rounded_rectangle([(16, 16), (144, 144)], radius=28, fill=(2, 132, 199, 255))
    d_logo.ellipse([(55, 45), (105, 95)], fill=(255, 255, 255, 255))
    d_logo.ellipse([(70, 60), (90, 80)], fill=(2, 132, 199, 255))
    d_logo.text((168, 42), "GHALIMLAB", fill=(15, 23, 42, 255))
    d_logo.text((170, 85), "LABORATOIRE DE BIOLOGIE MEDICALE", fill=(15, 118, 110, 255))
    img_logo.save(branding_dir / "logo.png", "PNG")

    # 3. Cachet du Laboratoire (Stamp with blue ink)
    img_cachet = Image.new("RGBA", (320, 320), (255, 255, 255, 0))
    d_cachet = ImageDraw.Draw(img_cachet)
    ink_blue = (26, 86, 179, 230)
    d_cachet.ellipse([(15, 15), (305, 305)], outline=ink_blue, width=4)
    d_cachet.ellipse([(25, 25), (295, 295)], outline=ink_blue, width=2)
    d_cachet.ellipse([(65, 65), (255, 255)], outline=ink_blue, width=2)
    d_cachet.text((60, 40), "* LABO D ANALYSES MEDICALES *", fill=ink_blue)
    d_cachet.text((105, 100), "GHALIMLAB", fill=ink_blue)
    d_cachet.text((95, 130), "DR. M. GHALIM", fill=ink_blue)
    d_cachet.text((80, 160), "BIOLOGISTE MEDICAL", fill=ink_blue)
    d_cachet.text((98, 190), "CASABLANCA", fill=ink_blue)
    d_cachet.text((108, 260), "* MAROC *", fill=ink_blue)
    img_cachet.save(branding_dir / "cachet.png", "PNG")

    # 4. Signature électronique (Cursive signature in blue ink)
    img_sign = Image.new("RGBA", (320, 140), (255, 255, 255, 0))
    d_sign = ImageDraw.Draw(img_sign)
    ink_sign = (18, 65, 145, 240)
    points = [
        (30, 80), (60, 40), (80, 95), (100, 30), (120, 85),
        (145, 75), (170, 70), (190, 82), (210, 65), (235, 75),
        (260, 50), (280, 90), (200, 110), (100, 115), (50, 110)
    ]
    for i in range(len(points) - 1):
        d_sign.line([points[i], points[i + 1]], fill=ink_sign, width=3)
    d_sign.text((50, 115), "Dr. M. Ghalim - Biologiste", fill=ink_sign)
    img_sign.save(branding_dir / "signature.png", "PNG")

    print("Default branding created in uploads/branding/")

if __name__ == "__main__":
    create_default_branding()
