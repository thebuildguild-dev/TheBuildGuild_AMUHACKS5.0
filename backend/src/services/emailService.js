import { Resend } from 'resend';
import config from '../config/index.js';
import log from '../utils/logger.js';

const resend = config.resendApiKey ? new Resend(config.resendApiKey) : null;

export async function sendPlanGeneratedEmail(userEmail, planData, assessmentData, planId) {
    if (!resend || !config.emailFrom) {
        log.warn('Email service not configured - skipping plan notification email');
        return false;
    }

    if (!userEmail) {
        log.warn('User email not provided - skipping plan notification email');
        return false;
    }

    try {
        const { examDate, subject, stressLevel } = assessmentData;
        const { summary, prioritizedTopics } = planData;

        const topTopics = prioritizedTopics.slice(0, 5).map(t =>
            `<li style="margin: 8px 0;"><strong>${t.name}</strong> - Priority: ${t.priority.toFixed(1)}, ${t.hoursNeeded}h needed</li>`
        ).join('');

        const htmlContent = `
<html>
    <body style="font-family: Arial, sans-serif; background-color: #0a0a0a; color: #ffffff; padding: 40px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #1a1a1a; border: 1px solid #333; padding: 30px; border-radius: 8px;">
            <h1 style="color: #ccff00; font-size: 28px; margin-bottom: 20px;">
                RECOVERY PLAN READY
            </h1>
            <p style="font-size: 16px; line-height: 1.6; color: #cccccc;">
                Your AI-powered recovery plan has been generated and is ready to help you ace your ${subject} exam!
            </p>
            
            <div style="background-color: #0a0a0a; border-left: 3px solid #ccff00; padding: 20px; margin: 25px 0;">
                <h3 style="color: #ccff00; margin-top: 0;">Plan Summary</h3>
                <p style="margin: 8px 0;"><strong>Subject:</strong> ${subject}</p>
                <p style="margin: 8px 0;"><strong>Exam Date:</strong> ${new Date(examDate).toLocaleDateString()}</p>
                <p style="margin: 8px 0;"><strong>Days Remaining:</strong> ${summary.totalDays}</p>
                <p style="margin: 8px 0;"><strong>Study Hours/Day:</strong> ${summary.studyHoursPerDay}</p>
                <p style="margin: 8px 0;"><strong>Total Topics:</strong> ${summary.totalTopics}</p>
                <p style="margin: 8px 0;"><strong>Confidence Level:</strong> <span style="color: ${summary.confidence === 'High' ? '#4caf50' : summary.confidence === 'Medium' ? '#ff9800' : '#ff4444'};">${summary.confidence}</span></p>
            </div>

            <div style="background-color: #0a0a0a; padding: 20px; margin: 25px 0;">
                <h3 style="color: #ccff00; margin-top: 0;">Top Priority Topics</h3>
                <ul style="list-style: none; padding: 0; margin: 0;">
                    ${topTopics}
                </ul>
            </div>
            
            <p style="font-size: 16px; line-height: 1.6; color: #cccccc;">
                Your personalized plan includes:
            </p>
            <ul style="color: #cccccc; line-height: 1.8;">
                <li>Prioritized topics based on PYQ analysis</li>
                <li>Day-by-day study schedule</li>
                <li>Exam strategies and recommendations</li>
                <li>Time allocation per topic</li>
            </ul>
            
            <div style="margin-top: 30px; text-align: center;">
                <a href="https://examintel.thebuildguild.dev/plan/${planId}" 
                   style="background-color: #ccff00; color: #0a0a0a; padding: 14px 32px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block; text-transform: uppercase; letter-spacing: 0.05em;">
                    VIEW YOUR PLAN
                </a>
            </div>
            
            <p style="font-size: 14px; color: #888; margin-top: 30px; border-top: 1px solid #333; padding-top: 20px;">
                ExamIntel - AI-powered academic recovery<br>
                This plan was generated using 15 years of Past Year Questions analysis.
            </p>
        </div>
    </body>
</html>
        `;

        const { data, error } = await resend.emails.send({
            from: config.emailFrom,
            to: [userEmail],
            subject: `Your ${subject} Recovery Plan is Ready!`,
            html: htmlContent,
        });

        if (error) {
            log.error('Failed to send plan notification email:', error);
            return false;
        }

        log.success(`Plan notification email sent to ${userEmail}`);
        return true;
    } catch (error) {
        log.error('Error sending plan notification email:', error.message);
        return false;
    }
}

export default {
    sendPlanGeneratedEmail,
};
