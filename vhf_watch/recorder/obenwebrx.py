import subprocess

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# http://mayzus.ddns.net:8073/#freq=156800000,mod=nfm,sql=-120
# First - chose the channel RSP1 Marine VHF
# Chose the rigth frequency

# TODO: reverse-engineer the websocket?

def tune_openwebrx_with_profile(
    url="http://mayzus.ddns.net:8073", 
    profile_name="RSP1 [1] Marine VHF", 
    freq=156800000, 
    mod="nfm"
):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
            context = browser.new_context()
            page = context.new_page()

            page.goto(url)
            print("Opened URL")

            # Wait for profile dropdown
            page.wait_for_selector("#openwebrx-sdr-profiles-listbox", timeout=10000)
            page.select_option("#openwebrx-sdr-profiles-listbox", label=profile_name)
            print(f"Selected SDR profile: {profile_name}")

            # Wait for the receiver to be ready
            page.wait_for_function("window.openwebrx_ready === true", timeout=10000)

            # Tune frequency and modulation
            js_code = f"""
                if (typeof tune === 'function') {{
                    tune({freq}, '{mod}');
                }}
            """
            page.evaluate(js_code)
            print(f"Tuned to {freq/1e6} MHz in {mod} mode.")

            return page, browser
    except PlaywrightTimeoutError as e:
        print("Playwright timed out:", e)
    except Exception as e:
        print("Something went wrong:", e)

    return None, None


def record_audio_to_file(duration=60, output="radio.wav"):
    ffmpeg_cmd = [
        "ffmpeg",
        "-f", "avfoundation",  # Use 'pulse', or 'avfoundation' on macOS
        "-i", ":0",  # Laptop's Microphone
        "-t", str(duration),
        output
    ]
    print("Recording audio...")
    subprocess.run(ffmpeg_cmd)
    print("Recording complete.")


if __name__ == "__main__":
    page, browser = tune_openwebrx_with_profile(freq=156800000, mod="nfm")
    record_audio_to_file(duration=30, output="vhf_mayzus.wav")
    if browser:
        browser.close()