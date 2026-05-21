import sys, time, os, torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText

MODEL = "zai-org/GLM-OCR"
IMG = sys.argv[1] if len(sys.argv) > 1 else "examples/source/code.png"
PROMPT = sys.argv[2] if len(sys.argv) > 2 else "Text Recognition:"

# Resize cap: keeps MPS GPU happy on 16GB Macs. ~1300px on the long edge ≈ ~1700 image tokens.
MAX_LONG_EDGE = int(os.environ.get("OCR_MAX_LONG_EDGE", "1280"))

device = os.environ.get("OCR_DEVICE") or ("mps" if torch.backends.mps.is_available() else "cpu")
dtype = torch.float16 if device == "mps" else torch.float32
print(f"device={device} dtype={dtype} max_long_edge={MAX_LONG_EDGE}")

t0 = time.time()
processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
model = AutoModelForImageTextToText.from_pretrained(
    MODEL, torch_dtype=dtype, trust_remote_code=True
).to(device).eval()
print(f"model loaded in {time.time()-t0:.1f}s")

image = Image.open(IMG).convert("RGB")
if max(image.size) > MAX_LONG_EDGE:
    w, h = image.size
    scale = MAX_LONG_EDGE / max(w, h)
    image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    print(f"resized image to {image.size}")
messages = [{
    "role": "user",
    "content": [
        {"type": "image", "image": image},
        {"type": "text", "text": PROMPT},
    ],
}]

inputs = processor.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to(device)

print(f"input_ids shape: {inputs['input_ids'].shape}")

t1 = time.time()
with torch.inference_mode():
    out = model.generate(
        **inputs,
        max_new_tokens=2048,
        do_sample=False,
        temperature=0.0,
    )
gen = out[:, inputs["input_ids"].shape[1]:]
text = processor.batch_decode(gen, skip_special_tokens=True)[0]
print(f"generated in {time.time()-t1:.1f}s")
print("=" * 60)
print(text)
print("=" * 60)
