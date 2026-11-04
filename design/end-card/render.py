"""Render design/end-card/end-card.html to still PNGs (1x and 2x) and an MP4.

Usage: python design/end-card/render.py [seconds] [fps]
Needs: playwright (chromium installed), imageio_ffmpeg.
"""
import pathlib
import subprocess
import sys

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
URL = HERE.joinpath("end-card.html").as_uri() + "?frame=1"
SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
FPS = int(sys.argv[2]) if len(sys.argv) > 2 else 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CLIP = {"x": 0, "y": 0, "width": 1920, "height": 1080}


def open_page(pw, scale):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=scale)
    page.goto(URL)
    page.wait_for_function("document.fonts.status === 'loaded'")
    page.wait_for_timeout(300)
    return browser, page


with sync_playwright() as pw:
    # stills: settled frame, embers kept off the text lines (video keeps them everywhere)
    for scale, name in ((1, "end-card-1920.png"), (2, "end-card-3840.png")):
        browser, page = open_page(pw, scale)
        page.evaluate("render(6.0, true)")
        page.screenshot(path=str(HERE / name), clip=CLIP)
        browser.close()
        print("wrote", name)

    browser, page = open_page(pw, 1)
    out = HERE / "end-card.mp4"
    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-f", "image2pipe", "-vcodec", "png", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "slow",
           "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(SECS * FPS)
    for i in range(n):
        page.evaluate(f"render({i / FPS:.5f})")
        proc.stdin.write(page.screenshot(type="png", clip=CLIP))
        if i % FPS == 0:
            print(f"  {i // FPS}s / {SECS:.0f}s", flush=True)
    proc.stdin.close()
    proc.wait()
    browser.close()
    print("wrote", out.name, "ffmpeg exit", proc.returncode)
