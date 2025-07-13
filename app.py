# --- Imports ---
import os
import base64
import csv
from io import BytesIO
from datetime import date
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr

# --- Load API Key from Environment (batch mode only) ---
load_dotenv(override=True)
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    openai = OpenAI()
else:
    openai = None
    print("⚠️ No API key found for batch mode.")

# --- Settings ---
MODEL = "gpt-4o-mini"
MOCKUP_TEMPLATE = "frame_template_Wall.png"
DEFAULT_WATERMARK = "The Real Doctor"

# --- Anatomy List (for batch use) ---
medical_anatomy = [
    "Heart", "Lung", "Kidney", "Eye", "Brain", "Bladder", "Abdomen", "Uterus",
    "Skeleton", "Muscles", "Nervous system", "Venous system", "Arterial system", "Ear", "Nose",
    "Throat", "Knee", "Ankle", "Shoulder", "Vertebrae", "Elbow", "Hand", "Foot",
    "Male genitalia", "Female genitalia", "Oral cavity", "Skin", "Head"
]

# --- Artist Style Options ---
artist_styles = [
    "None", "Van Gogh", "Hokusai", "Ghibli", "Basquiat", "Cubist",
    "Minimalist", "Impressionist", "Futurist", "Mondrian",
    "Andy Warhol", "Art Nouveau", "Street Art", "Surrealist",
    "Medical Illustration"
]

# --- CSV Logger (optional for batch) ---
def log_anatomy_to_csv(anatomy, filename, folder="anatomy_posters_wall", csv_path="anatomy_poster_wall_log.csv"):
    today = date.today().isoformat()
    filepath = os.path.join(folder, filename)
    row = {"anatomy": anatomy, "filename": filename, "date": today, "path": filepath}
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    print(f"📝 CSV updated for {anatomy}")

# --- Generate Anatomy Poster ---
def generate_anatomy_image(anatomy, artist_style=None, user_openai=None):
    anatomy_clean = anatomy.lower().replace(" ", "_")
    today = date.today().isoformat()
    filename = f"popart_{anatomy_clean}_{today}.png"

    style_clause = f", in {artist_style} style" if artist_style and artist_style != "None" else ""
    prompt = f"Vibrant pop-art style human anatomy of {anatomy}{style_clause}, with anatomical landmarks, suitable for wall art, highly detailed, colorful, 1024x1024 resolution"

    response = user_openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        n=1,
        response_format="b64_json"
    )

    image_data = base64.b64decode(response.data[0].b64_json)
    image = Image.open(BytesIO(image_data))
    return image

# --- Generate Mockup and Save to Temp File ---
def create_mockup(image, watermark_text=DEFAULT_WATERMARK):
    try:
        mockup = Image.open(MOCKUP_TEMPLATE).convert("RGBA")
    except Exception as e:
        raise FileNotFoundError(f"❌ Could not load mockup template: {e}")

    art = image.convert("RGBA").resize((500, 500))
    mockup_copy = mockup.copy()
    x = (mockup_copy.width - art.width) // 2
    y = (mockup_copy.height - art.height) // 2
    mockup_copy.paste(art, (x, y), art)

    if watermark_text:
        draw = ImageDraw.Draw(mockup_copy)
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        draw.text((20, 20), watermark_text, fill=(255, 255, 255, 180), font=font)

    temp_path = gr.make_tempfile(suffix=".png")
    mockup_copy.save(temp_path)
    print(f"🖼️ Mockup saved: {temp_path}")
    return temp_path

# --- Gradio Interface Function ---
def generate_single_mockup(api_key, anatomy_input, artist_style, watermark_text):
    try:
        user_openai = OpenAI(api_key=api_key)

        # Generate anatomy image
        image = generate_anatomy_image(anatomy_input, artist_style, user_openai=user_openai)

        # Create mockup and save to temp file
        output_path = create_mockup(image, watermark_text)

        return output_path  # Must be a file path

    except Exception as e:
        print(f"❌ Error: {e}")
        if "billing_hard_limit" in str(e):
            print("⚠️ OpenAI billing limit reached.")
        return None  # Gradio will show nothing if there's no image

# --- Gradio UI ---
demo = gr.Interface(
    fn=generate_single_mockup,
    inputs=[
        gr.Textbox(label="Your OpenAI API Key", type="password"),
        gr.Textbox(label="Anatomy Term (e.g. Heart)"),
        gr.Dropdown(label="Art Style", choices=artist_styles, value="None"),
        gr.Textbox(label="Watermark Text (optional)", value=DEFAULT_WATERMARK),
    ],
    outputs=gr.Image(type="filepath", label="Generated Mockup"),
    title="Anatomy Poster Generator",
    description="Generate vibrant anatomy mockups inspired by classic and modern art styles. Secure, local, and watermark-protected."
)

# --- Run ---
if __name__ == "__main__":
    demo.launch()
