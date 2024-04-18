import io
import json
from PIL import Image
import asyncio
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional
import pydantic
import os

def p(s=""):
    print(s, end=None if s == "" else "", flush=True)

def pause(secs=0.01):
    pass

async def set_window_size_for_screenshot(page, target_width, target_height):
    device_pixel_ratio = await page.evaluate("window.devicePixelRatio") 
    adjusted_width = int(target_width / device_pixel_ratio)
    adjusted_height = int(target_height / device_pixel_ratio)
    p(f" W: {adjusted_width} ")
    await page.set_viewport_size({"width": adjusted_width, "height": adjusted_height})


# Desktop and mobile window sizes
DW = 1024  
DH = 800

MW = 512
MH = 800

class ImageSize(pydantic.BaseModel):
    DW:int = 1024
    DH:int = 800
    MW:int = 512
    MH:int = 800

RS = Image.LANCZOS

async def async_gen_screenshots(url,image_dir:Optional[str]=None,image_size:ImageSize=ImageSize()):
    from playwright.async_api import async_playwright, TimeoutError
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

        target_url = url
        if os.path.exists(url):
            target_url = f"file://{url}"
            parsed_url = os.path.splitext(os.path.basename(target_url))[0]
            root_name = parsed_url.replace(".", "_")
        else:
            parsed_url = urlparse(url)
            root_name = parsed_url.netloc.replace(".", "_")

        await page.goto(target_url)
        

        img_dir = Path(image_dir) if image_dir else Path("screenshots")
        img_dir.mkdir(exist_ok=True)
        
        combined_img = img_dir / f"{root_name}"
        p(f"Capturing {root_name}")

        try:
            await page.wait_for_load_state("networkidle") 
            p(".")
            # await page.wait_for_function(
            #     "() => Array.from(document.images).every((img) => img.complete && (typeof img.naturalWidth != 'undefined'))"
            # )
        except TimeoutError:
            print("Timed out waiting for page to load")
            await browser.close()
            return None

        # Mobile
        await set_window_size_for_screenshot(page, MW, MH)
        pause() 
        light_mobile_img = Image.open(io.BytesIO(await page.screenshot()))
        w_percent = MW / float(light_mobile_img.size[0])
        mobile_size = (MW, int((float(light_mobile_img.size[1]) * float(w_percent))))
        p(f"M {mobile_size}")
        light_mobile_img = light_mobile_img.resize(mobile_size, RS)
        p(".")

        # Desktop  
        await set_window_size_for_screenshot(page, DW, DH)
        pause()
        light_img = Image.open(io.BytesIO(await page.screenshot())) 
        w_percent = DW / float(light_img.size[0])
        desktop_size = (DW, int((float(light_img.size[1]) * float(w_percent))))
        p(f"D {desktop_size}")
        light_img = light_img.resize(desktop_size, RS)
        p(".")

        # Combined
        dh = desktop_size[1]  
        final_img = Image.new("RGB", (DW, dh))
        final_img.paste(light_img, (0, 0))
        final_img.save(f"{combined_img}.png")
        mh = mobile_size[1]
        final_img_mobile = Image.new("RGB", (MW, mh))  
        final_img_mobile.paste(light_mobile_img, (0, 0))
        final_img_mobile.save(f"{combined_img}.mobile.png")
        p()

        await browser.close()

def gen_screenshots(url,image_dir:Optional[str]=None,image_size:ImageSize=ImageSize()):
    return asyncio.run(async_gen_screenshots(url,image_dir,image_size))

# gen_screenshots("file:///Users/allwefantasy/projects/auto-coder/screenshots/www_elmo_chat_combined.html")
