import asyncio
from app.services.llm import extract_email_info, summarize_application_status


async def test_extraction():
    sample_email = """
    Hi John,
    Thank you for applying to the Senior Python Engineer position at Acme Corp.
    Your application ID is ACME-9912. Please log into your portal to complete
    a short code assessment by Friday.
    """

    print("--- Testing Email Extraction ---")
    result = await extract_email_info(sample_email)
    print(result.model_dump_json(indent=2))


async def test_summarization():
    sample_timeline = [
        {"event_type": "APPLICATION_SUBMITTED", "date": "2026-07-20"},
        {"event_type": "ONLINE_ASSESSMENT_INVITE", "date": "2026-07-22"},
        {"event_type": "REJECTED", "date": "2026-07-24"},
    ]

    print("\n--- Testing Application Summarization ---")
    result = await summarize_application_status(sample_timeline)
    print(result.model_dump_json(indent=2))


async def main():
    await test_extraction()
    await test_summarization()


if __name__ == "__main__":
    asyncio.run(main())