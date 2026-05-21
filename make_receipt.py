from PIL import Image, ImageDraw, ImageFont
import os

W, H = 520, 760
im = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(im)

def font(size):
    for path in [
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Courier.ttc",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

f_title = font(28)
f_body = font(20)
f_small = font(16)

y = 30
def line(text, fnt=f_body, dy=28, center=False):
    global y
    if center:
        w = draw.textlength(text, font=fnt)
        x = (W - w) // 2
    else:
        x = 40
    draw.text((x, y), text, fill="black", font=fnt)
    y += dy

line("WHOLE FOODS MARKET", f_title, 40, center=True)
line("123 Main Street, San Francisco CA", f_small, 22, center=True)
line("Tel: (415) 555-0199", f_small, 30, center=True)
line("-" * 42, f_small, 22)
line("Date: 2026-05-15      Time: 14:32", f_small, 30)
line("-" * 42, f_small, 22)

items = [
    ("Organic Bananas (1.2 lb)", "2.39"),
    ("Whole Milk 1 Gallon", "4.99"),
    ("Sourdough Bread", "5.49"),
    ("Avocado x 3", "4.50"),
    ("Greek Yogurt 32oz", "6.79"),
    ("Free Range Eggs (dozen)", "7.29"),
    ("Coffee Beans 12oz", "14.99"),
    ("Almond Butter Jar", "9.49"),
]
for name, price in items:
    dots = "." * (35 - len(name))
    line(f"{name} {dots} ${price}", f_body, 26)

line("-" * 42, f_small, 22)
line("Subtotal:                       $55.93", f_body, 26)
line("Tax (8.5%):                      $4.75", f_body, 26)
line("TOTAL:                          $60.68", f_body, 32)
line("-" * 42, f_small, 22)
line("Paid with VISA ****1234", f_small, 22)
line("Thank you for shopping with us!", f_small, 22, center=True)

out = "/Users/venkateshbonthala/Desktop/sample_receipt.png"
im.save(out)
print("saved:", out, im.size)
