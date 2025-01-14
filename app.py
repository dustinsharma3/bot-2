import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from pyppeteer import launch

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Bot token not set. Please define TELEGRAM_BOT_TOKEN in environment variables.")

# Custom headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://sarathi.parivahan.gov.in/sarathiservice/relApplnSearch.do",
}

# Start command to welcome users
async def start(update: Update, context):
    await update.message.reply_text("Welcome! Please send your DL number to get the DL info.")

# Function to open the page, click the button, and download the page as a PDF
async def download_pdf(dl_number: str, output_filename: str):
    browser = None
    try:
        # Launch Chromium browser in headless mode
        browser = await launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = await browser.newPage()

        # Set custom headers
        await page.setExtraHTTPHeaders(HEADERS)

        # Construct the URL for the given DL number
        url = f"https://sarathi.parivahan.gov.in/sarathiservice/dlDetailsResult.do?reqDlNumber={dl_number}"

        # Open the URL with custom headers
        await page.goto(url)

        # Wait for the page to load and the button to be available
        await page.waitForSelector('input.btn.top-space', {'timeout': 2000, 'visible': True})

        # Click the "Print" button
        await page.evaluate('document.querySelector("input[name=\'Print\']").click();')

        # Wait for a short time to ensure the print window or result is handled
        await page.waitForTimeout(5000)

        # Save the page as a PDF
        await page.pdf({'path': output_filename, 'format': 'A4'})

        logger.info(f"PDF downloaded and saved at: {output_filename}")
        return output_filename
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        return None
    finally:
        if browser:
            await browser.close()

# Message handler for DL number input
async def handle_dl_number(update: Update, context):
    dl_number = update.message.text.strip()

    if not dl_number:
        await update.message.reply_text("❌ Please provide a valid DL number.")
        return

    # Define the output file path (for saving the PDF)
    output_filename = os.path.join("/tmp", f"{dl_number}_details.pdf")

    try:
        # Send processing message
        await update.message.reply_text(f"⏳ Fetching DL details for {dl_number}. Please wait...")

        # Download the PDF
        downloaded_file_path = await download_pdf(dl_number, output_filename)

        if downloaded_file_path:
            # Send the downloaded file to the user (PDF)
            with open(downloaded_file_path, "rb") as file:
                await update.message.reply_document(
                    document=file,
                    filename=os.path.basename(downloaded_file_path),
                    caption="Here is your DL INFO PDF."
                )
        else:
            await update.message.reply_text("❌ Error downloading the PDF. Please try again.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ An error occurred: {str(e)}")

# Main function to start the bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))

    # Add message handler for DL number
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dl_number))

    # Start the bot
    application.run_polling()

# Start the bot
if __name__ == "__main__":
    main()
