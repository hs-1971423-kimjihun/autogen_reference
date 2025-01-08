import os
import autogen
import asyncio
import nest_asyncio
from playwright.async_api import async_playwright
from typing import Tuple

# Enable nested asyncio for Jupyter compatibility
nest_asyncio.apply()

# Existing llm_config configuration
llm_config = {
    "config_list": [
        {
            "model": "llama3",
            "api_key": "NotRequired",
            "base_url": "http://0.0.0.0:4000",
            "price": [0, 0],
        }
    ],
    "cache_seed": None,
}

engineer = autogen.AssistantAgent(
    name="Engineer",
    llm_config=llm_config,
    system_message="""
    I'm Engineer. I help with Firefox browser control tasks using Playwright.
    - Always wait for user input before taking any action
    - Only respond to explicit user commands
    - Available commands:
      * take screenshot [url]
      * get title [url]
      * navigate [url]
    - Do not suggest or execute actions without user input
    """,
)

user_proxy = autogen.UserProxyAgent(
    name="Admin",
    human_input_mode="ALWAYS",
    code_execution_config=False,
)

@user_proxy.register_for_execution()
@engineer.register_for_llm(description="Navigate to a specified URL")
async def navigate_to_url(url: str) -> Tuple[int, str]:
    try:
        async with async_playwright() as p:
            # Firefox 브라우저 실행
            browser = await p.firefox.launch_persistent_context(
                user_data_dir="./browser-data",
                headless=False  # GUI 모드로 실행
            )
            page = await browser.new_page()
            await page.goto(url)
            await browser.close()
        return 0, f"Successfully navigated to {url}"
    except Exception as e:
        return 1, f"Error navigating to URL: {str(e)}"

@user_proxy.register_for_execution()
@engineer.register_for_llm(description="Get page title from specified URL")
async def get_page_title(url: str) -> Tuple[int, str]:
    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch_persistent_context(
                user_data_dir="./browser-data",
                headless=False
            )
            page = await browser.new_page()
            await page.goto(url)
            title = await page.title()
            await browser.close()
        return 0, f"Page title: {title}"
    except Exception as e:
        return 1, f"Error getting page title: {str(e)}"

@user_proxy.register_for_execution()
@engineer.register_for_llm(description="Take screenshot of specified URL")
async def take_screenshot(url: str, filename: str = "screenshot.png") -> Tuple[int, str]:
    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch_persistent_context(
                user_data_dir="./browser-data",
                headless=False
            )
            page = await browser.new_page()
            await page.goto(url)
            await page.screenshot(path=filename)
            await browser.close()
        return 0, f"Screenshot saved as {filename}"
    except Exception as e:
        return 1, f"Error taking screenshot: {str(e)}"

groupchat = autogen.GroupChat(
    agents=[engineer, user_proxy],
    messages=[],
    max_round=500,
    speaker_selection_method="round_robin",
    enable_clear_history=True,
)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# Start conversation
chat_result = user_proxy.initiate_chat(
    manager,
    message="""
Hello! I can help you control the Firefox browser using Playwright.
What would you like to do? (navigate/get title/take screenshot)
"""
)