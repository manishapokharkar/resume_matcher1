from outlook_mail import get_messages, is_job_related

print("\nReading Outlook emails...\n")

messages = get_messages()

print(f"Total emails found: {len(messages)}")

for message in messages:

    subject = message.get("subject", "")

    if is_job_related(message):

        print("\nJob Email Found")
        print("Subject:", subject)