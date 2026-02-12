import resend
from src.config import config

resend.api_key = config.RESEND_API_KEY

def send_ingestion_notification(user_email: str, status: str, document_count: int, chunk_count: int, job_id: str, error_message: str = None):
    """
    Send email notification after ingestion process completes
    
    Args:
        user_email: Email address of the user
        status: 'success' or 'failed'
        document_count: Number of documents processed
        chunk_count: Number of chunks created
        job_id: Ingestion job ID
        error_message: Error message if status is failed
    """
    if not config.RESEND_API_KEY or not user_email:
        print(f"Skipping email notification - RESEND_API_KEY or user_email not configured")
        return
    
    try:
        if status == "success":
            subject = "Document Ingestion Complete - Ready for Assessment"
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #0a0a0a; color: #ffffff; padding: 40px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #1a1a1a; border: 1px solid #333; padding: 30px; border-radius: 8px;">
                        <h1 style="color: #ccff00; font-size: 28px; margin-bottom: 20px;">
                            INGESTION COMPLETE
                        </h1>
                        <p style="font-size: 16px; line-height: 1.6; color: #cccccc;">
                            Your PYQ documents have been successfully processed and vectorized!
                        </p>
                        
                        <div style="background-color: #0a0a0a; border-left: 3px solid #ccff00; padding: 20px; margin: 25px 0;">
                            <h3 style="color: #ccff00; margin-top: 0;">Processing Summary</h3>
                            <p style="margin: 8px 0;"><strong>Job ID:</strong> <code style="background: #333; padding: 2px 6px; border-radius: 3px;">{job_id}</code></p>
                            <p style="margin: 8px 0;"><strong>Documents Processed:</strong> {document_count}</p>
                            <p style="margin: 8px 0;"><strong>Chunks Created:</strong> {chunk_count}</p>
                            <p style="margin: 8px 0;"><strong>Status:</strong> <span style="color: #4caf50;">SUCCESS</span></p>
                        </div>
                        
                        <p style="font-size: 16px; line-height: 1.6; color: #cccccc;">
                            Your ExamIntel system is now ready to analyze these documents and generate personalized recovery plans.
                        </p>
                        
                        <div style="margin-top: 30px; text-align: center;">
                            <a href="https://examintel.thebuildguild.dev/assessment" 
                               style="background-color: #ccff00; color: #0a0a0a; padding: 14px 32px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block; text-transform: uppercase; letter-spacing: 0.05em;">
                                START ASSESSMENT
                            </a>
                        </div>
                        
                        <p style="font-size: 14px; color: #888; margin-top: 30px; border-top: 1px solid #333; padding-top: 20px;">
                            ExamIntel - AI-powered academic recovery<br>
                            This is an automated notification from your ingestion pipeline.
                        </p>
                    </div>
                </body>
            </html>
            """
        else:
            subject = "Document Ingestion Failed"
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #0a0a0a; color: #ffffff; padding: 40px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #1a1a1a; border: 1px solid #333; padding: 30px; border-radius: 8px;">
                        <h1 style="color: #ff4444; font-size: 28px; margin-bottom: 20px;">
                            INGESTION FAILED
                        </h1>
                        <p style="font-size: 16px; line-height: 1.6; color: #cccccc;">
                            Unfortunately, there was an error processing your PYQ documents.
                        </p>
                        
                        <div style="background-color: #0a0a0a; border-left: 3px solid #ff4444; padding: 20px; margin: 25px 0;">
                            <h3 style="color: #ff4444; margin-top: 0;">Error Details</h3>
                            <p style="margin: 8px 0;"><strong>Job ID:</strong> <code style="background: #333; padding: 2px 6px; border-radius: 3px;">{job_id}</code></p>
                            <p style="margin: 8px 0;"><strong>Status:</strong> <span style="color: #ff4444;">FAILED</span></p>
                            {f'<p style="margin: 8px 0;"><strong>Error:</strong> {error_message}</p>' if error_message else ''}
                        </div>
                        
                        <p style="font-size: 16px; line-height: 1.6; color: #cccccc;">
                            Please check your document URLs and try again. If the problem persists, contact support.
                        </p>
                        
                        <div style="margin-top: 30px; text-align: center;">
                            <a href="https://examintel.thebuildguild.dev/upload-pyq" 
                               style="background-color: #ccff00; color: #0a0a0a; padding: 14px 32px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block; text-transform: uppercase; letter-spacing: 0.05em;">
                                TRY AGAIN
                            </a>
                        </div>
                        
                        <p style="font-size: 14px; color: #888; margin-top: 30px; border-top: 1px solid #333; padding-top: 20px;">
                            ExamIntel - AI-powered academic recovery<br>
                            This is an automated notification from your ingestion pipeline.
                        </p>
                    </div>
                </body>
            </html>
            """
        
        params = {
            "from": config.EMAIL_FROM,
            "to": [user_email],
            "subject": subject,
            "html": html_content,
        }
        
        email = resend.Emails.send(params)
        print(f"Email notification sent to {user_email}: {email}")
        return email
        
    except Exception as e:
        print(f"Failed to send email notification: {e}")
        return None
