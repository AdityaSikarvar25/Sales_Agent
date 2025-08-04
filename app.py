from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, Runner, trace, function_tool, OpenAIChatCompletionsModel, input_guardrail, GuardrailFunctionOutput
from typing import Dict
import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content
from pydantic import BaseModel
import certifi
import os
import asyncio
os.environ['SSL_CERT_FILE'] = certifi.where()
load_dotenv(override=True)

class Me:
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.name = "Aditya Sikarvar"
        self.instructions1 = (
            "You are a sales agent working for ComplAI, a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. "
            "You write professional, serious cold emails."
        )
        self.instructions2 = (
            "You are a humorous, engaging sales agent working for ComplAI, "
            "a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. "
            "You write witty, engaging cold emails that are likely to get a response."
        )
        self.instructions3 = (
            "You are a busy sales agent working for ComplAI, "
            "a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. "
            "You write concise, to the point cold emails."
        )
        self.instructions4 = (
            "You are a sales agent working for ComplAI, "
            "a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. "
            "You write cold emails that are likely to get a response."
        )
        self.subject_instructions = (
            "You can write a subject for a cold sales email. "
            "You are given a message and you need to write a subject for an email that is likely to get a response."
        )
        self.html_instructions = (
            "You can convert a text email body to an HTML email body. "
            "You are given a text email body which might have some markdown or formatting, "
            "and you need to convert it to an HTML email body with simple, clear, compelling layout and design."
        )
        self.sender_email = "adityasikarvar25@gmail.com"
        self.recipient_email = "aditya.s@crestskillserve.com"
        self.GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
        self.gemini_client = AsyncOpenAI(base_url=self.GEMINI_BASE_URL, api_key=self.google_api_key)
        self.gemini_model = OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=self.gemini_client)
    def parse_email(self, email: str) -> (str, str):
        parts = email.split('@')
        username = parts[0]
        domain = parts[1]
        if '.' in username:
            first_name = username.split('.')[0].capitalize()
        else:
            first_name = username.capitalize()
        return first_name, domain
    
    def Sales_Agent(self):
        sales_agent1 =  Agent(name="Sales Agent 1", instructions=self.instructions1, model=self.gemini_model)
        sales_agent2 =  Agent(name="Sales Agent 2", instructions=self.instructions2, model=self.gemini_model)
        sales_agent3 =  Agent(name="Sales Agent 3", instructions=self.instructions3, model=self.gemini_model)
        return sales_agent1, sales_agent2, sales_agent3
    def Sales_tools(self):
        sales_agent1, sales_agent2, sales_agent3 = self.Sales_Agent()
        tool1 = sales_agent1.as_tool(tool_name="sales_agent1", tool_description=self.instructions1)
        tool2 = sales_agent2.as_tool(tool_name="sales_agent2", tool_description=self.instructions2)
        tool3 = sales_agent3.as_tool(tool_name="sales_agent3", tool_description=self.instructions3)
        return tool1, tool2, tool3
    def Email_Sender_Tools(self):
        @function_tool
        def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
            """ Send out an email with the given subject and HTML body to all sales prospects """
            sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
            from_email = Email(self.sender_email)  # Change to your verified sender
            to_email = To(self.recipient_email)  # Change to your recipient
            content = Content("text/html", html_body)
            mail = Mail(from_email, to_email, subject, content).get()
            print("Sending request to mail")
            sg.client.mail.send.post(request_body=mail)
            print("Mail Sent")
            return {"status": "success"}
        subject_writer = Agent(name="Email subject writer", instructions=self.subject_instructions, model=self.gemini_model)
        subject_tool = subject_writer.as_tool(tool_name="subject_writer", tool_description="Write a subject for a cold sales email")
        html_converter = Agent(name="HTML email body converter", instructions=self.html_instructions, model=self.gemini_model)
        html_tool = html_converter.as_tool(tool_name="html_converter",tool_description="Convert a text email body to an HTML email body")
        return subject_tool, html_tool, send_html_email
    def Emailer_Agent(self):
        instructions ="You are an email formatter and sender. You receive the body of an email to be sent. \
        You first use the subject_writer tool to write a subject for the email, then use the html_converter tool to convert the body to HTML. \
        Finally, you use the send_html_email tool to send the email with the subject and HTML body."
        email_tools = self.Email_Sender_Tools()
        email_agent= Agent(name="Email Manager",instructions=instructions,tools=email_tools,model=self.gemini_model,handoff_description="Convert an email to HTML and send it")
        return email_agent
    def Sales_Manager(self):
        sales_tools = self.Sales_tools()
        handoffs=[self.Emailer_Agent()]
        sales_manager_instructions = """
        You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email using the sales_agent tools.
        
        Follow these steps carefully:
        1. Generate Drafts: Use all three sales_agent tools to generate three different email drafts. Do not proceed until all three drafts are ready.
        
        2. Evaluate and Select: Review the drafts and choose the single best email using your judgment of which one is most effective.
        You can use the tools multiple times if you're not satisfied with the results from the first try.
        
        3. Handoff for Sending: Pass ONLY the winning email draft to the 'Email Manager' agent. The Email Manager will take care of formatting and sending.
        
        Crucial Rules:
        - You must use the sales agent tools to generate the drafts — do not write them yourself.
        - You must hand off exactly ONE email to the Email Manager — never more than one.
        """
        sales_manager = Agent(name="Sales Manager",instructions=sales_manager_instructions,tools=sales_tools,handoffs=handoffs,model=self.gemini_model)
        return sales_manager
    async def run(self):
        sales_manager = self.Sales_Manager()
        first_name, domain = self.parse_email(self.recipient_email)
        message = f"Write a cold sales email to {first_name} at {domain}. The email should be from Aditya Sikarvar."
        with trace("Automated SDR"):
            result = await Runner.run(sales_manager,message)
        return result

if __name__ == "__main__":
    async def main():
        me = Me()
        print("Starting the Sales Agent...")
        result = await me.run()
        print("Result:", result)
    asyncio.run(main())