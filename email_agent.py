import logging
from dotenv import load_dotenv
import os
import email
import imaplib
import smtplib
import google.generativeai as genai

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# Load environment variables from .env
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
gmailPassword = os.getenv("GMAIL_PASSWORD")
myEmail = os.getenv("GMAIL")

# Gemini config
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# Recipients emails for each category
recipients = {
    "Sales": "sales@gmail.com",
    "Partnership": "partnership@gmail.com",
    "Personal": "personal@gmail.com",
    "Inquiry": "inquiry@gmail.com",
}

# Function to connect email to server and fetch unread emails
def getEmails():
    try:
        logging.info("Connecting to Gmail to fetch emails.")
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(myEmail, gmailPassword)
        mail.select('inbox')

        # Search for unread emails
        status, messages = mail.search(None, 'UNSEEN')
        emailIds = messages[0].split()

        emails = []
        for e_id in emailIds:
            status, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg['subject']
                    from_email = msg['from']
                    body = extract_email_body(msg)
                    emails.append({"from": from_email, "subject": subject, "body": body})

        mail.logout()
        logging.info(f"Fetched {len(emails)} unread emails.")
        return emails
    except Exception as e:
        logging.error(f"Error while fetching emails: {e}")
        return []

# Function to extract body from the email
def extract_email_body(msg):
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        return payload.decode(charset)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                return payload.decode(charset)
        return "Email body is empty or could not be decoded."
    except Exception as e:
        logging.error(f"Error decoding email: {e}")
        return f"Error decoding email: {e}"

# Function to categorize the email body
def categorizeEmail(body):
    try:
        prompt = (
            "Your job is to categorize emails into one of these categories: Sales, Partnership, Personal, Inquiry.\n"
            f"Email: {body}\n"
            "Categorized as:"
        )
        logging.info("Categorizing email.")
        response = model.generate_content(prompt)
        category = response.text.strip()
        logging.info(f"Email categorized as: {category}")
        return category
    except Exception as e:
        logging.error(f"Error categorizing email: {e}")
        return "Categorize unavailable."

# Function to summarize the email body
def summarizeEmail(body):
    try:
        prompt = (
            "Your job is to summarize emails. Provide a summary of the email including the following:\n"
            "- Type: The category (Sales, Partnership, Personal, Inquiry).\n"
            "- Content Overview: A brief summary of the email's main points.\n"
            "- Recommended Action: Suggested next steps (e.g., Schedule a demo, Review partnership proposal).\n"
            f"Email: {body}\n"
            "Summary:"
        )
        logging.info("Summarizing email.")
        response = model.generate_content(prompt)
        summary = response.text.strip()
        logging.info(f"Summary: {summary}")
        return summary
    except Exception as e:
        logging.error(f"Error summarizing email: {e}")
        return "Summary unavailable."

# Function to send the email with the summary
def sendEmail(receiver_email, subject, body, summary):
    try:
        logging.info(f"Sending summarized email to {receiver_email}.")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(myEmail, gmailPassword)
        message = f"Subject:[AI-Agent] Forwarded Email: {subject}\n\nAI Summary:\n{summary}\n\nOriginal Email:\n{body}"
        server.sendmail(myEmail, receiver_email, message.encode('utf-8'))
        logging.info("Email sent successfully!")
    except Exception as e:
        logging.error(f"Error sending email: {e}")
    finally:
        server.quit()

# Main function
def main():
    logging.info("Starting email processing.")
    emails = getEmails()
    if not emails:
        logging.info("No new emails to process.")
    else:
        for email_data in emails:
            category = categorizeEmail(email_data["body"])
            summary = summarizeEmail(email_data["body"])
            recipient = recipients.get(category, "admin@gmail.com")
            sendEmail(recipient, email_data["subject"], email_data["body"], summary)

if __name__ == "__main__":
    main()
