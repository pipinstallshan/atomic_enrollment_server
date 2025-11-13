from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import google.generativeai as genai
import os
from dotenv import load_dotenv

from utils.ai_prompts import create_prompt_for_popup_detection

load_dotenv()
import time

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_screenshot(url: str, output_path: str, ai_check: bool = False):
    """
    Takes a screenshot of a webpage and optionally checks for pop-ups using AI.

    Args:
        url: The URL of the webpage.
        output_path: The path to save the screenshot.
        ai_check: Whether to use AI to check for pop-ups.
    """
    driver = None
    try:

        # Set up Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--headless")

        # Initialize the WebDriver with the specified options
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.set_window_size(1920, 1080)

        # Navigate to the URL
        driver.get(url)

        # Wait for the page to load (adjust the timeout as needed)
        driver.implicitly_wait(10)  # Wait for 10 seconds

        # Optional: Add extra time for dynamic content to load
        time.sleep(5)  # Wait for an additional 5 seconds

        if ai_check:
            # Take a screenshot and save it temporarily
            temp_screenshot_path = "temp_screenshot.png"
            driver.save_screenshot(temp_screenshot_path)

            with open(temp_screenshot_path, "rb") as image_file:
                image_data = image_file.read()

            # Then, I need to create a gemini model instance.
            # I will use the model 'gemini-flash-1.5'.
            model = genai.GenerativeModel('gemini-2.0-flash')

            prompt = create_prompt_for_popup_detection()

            # Then, I need to send the prompt and the image to the model.
            response = model.generate_content(
                [
                    prompt,
                    {"mime_type": "image/png", "data": image_data},
                ],
                stream=False
            )

            # Then, I need to process the response.
            print(response.text)

            if "UNUSABLE" in response.text:
                import random
                driver.save_screenshot("output/error_image" + str(random.randint(0, 1000000)) + ".png")
                return {"success": False}

        # Take a screenshot and save it
        driver.save_screenshot(output_path)
        return {"success": True}

    finally:
        if driver is not None:
            driver.quit()
