from datetime import datetime, timedelta
from jose import jwt
import boto3
from botocore.exceptions import ClientError
import sys

from config import (
    JWT_SECRET_KEY,
    JWT_EXPIRATION_DAYS,
    EMAIL_LOGIN_JWT_EXPIRATION_DAYS,
    FRONTEND_URL,
    EMAIL_FROM,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
)


def send_login_link(email: str) -> None:
    """Send a login link to the user's email."""
    # Generate a JWT token
    token = jwt.encode(
        {
            "email": email,
            "exp": datetime.now() + timedelta(days=EMAIL_LOGIN_JWT_EXPIRATION_DAYS),
        },
        JWT_SECRET_KEY,
        algorithm="HS256",
    )

    login_link = f"{FRONTEND_URL}/email-login?token={token}"

    html_content = f"""
    <html>
        <head></head>
        <body>
            <h1>Hello!</h1>
            <p>Here's your link: <a href="{login_link}">Login Link</a></p>
        </body>
    </html>
    """

    text_content = f"Hello!\n\nHere's your link: {login_link}"
    _send_email(email, "Spark Stack Login Link", html_content, text_content)


def _send_email(
    recipient_email: str, subject: str, html_content: str, text_content: str
):
    # Create a new SES resource
    client = boto3.client(
        "ses",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    try:
        response = client.send_email(
            Source=EMAIL_FROM,
            Destination={"ToAddresses": [recipient_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_content, "Charset": "UTF-8"},
                    "Html": {"Data": html_content, "Charset": "UTF-8"},
                },
            },
        )
        print(f"Email sent! Message ID: {response['MessageId']}")
    except ClientError as e:
        print(f"Error sending email: {e.response['Error']['Message']}")
        sys.exit(1)
