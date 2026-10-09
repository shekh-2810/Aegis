from datetime import datetime, timezone
from database import articles_collection, alerts_collection


articles = [
    {
        "title": "New phishing campaign targets online banking users",
        "category": "Phishing",
        "description": "Security researchers have identified a new phishing campaign designed to steal banking credentials.",
        "author": "Aiges Security Desk",
        "date": "2026-08-25T10:00:00Z",
        "featured": True,
        "trending": True,
    },
    {
        "title": "Fake payment websites impersonate trusted brands",
        "category": "Fraud",
        "description": "Fraudulent domains are using brand lookalikes to trick users into entering payment information.",
        "author": "Aiges Security Desk",
        "date": "2026-08-24T15:30:00Z",
        "featured": False,
        "trending": True,
    },
    {
        "title": "How typosquatting attacks trick users",
        "category": "Phishing",
        "description": "Small changes in a domain name can lead users to malicious lookalike websites.",
        "author": "Aiges Security Desk",
        "date": "2026-08-24T09:00:00Z",
        "featured": False,
        "trending": True,
    },
    {
        "title": "Rising alerts around fake login portals",
        "category": "Fraud",
        "description": "Security teams are monitoring an increase in fake authentication pages.",
        "author": "Aiges Security Desk",
        "date": "2026-08-23T18:00:00Z",
        "featured": False,
        "trending": False,
    },
    {
        "title": "Understanding suspicious domains",
        "category": "Cyber Safety",
        "description": "Learn the basic warning signs that can help identify suspicious websites.",
        "author": "Aiges Security Desk",
        "date": "2026-08-22T12:00:00Z",
        "featured": False,
        "trending": False,
    },
    {
        "title": "Security checklist for safer browsing",
        "category": "Cyber Safety",
        "description": "Simple practices that can reduce the risk of falling for online scams.",
        "author": "Aiges Security Desk",
        "date": "2026-08-21T11:00:00Z",
        "featured": False,
        "trending": False,
    },
]

alerts = [
    {
        "title": "High-risk phishing domains detected",
        "severity": "High",
        "description": "Multiple suspicious domains have been flagged for phishing-related activity.",
        "date": "2026-08-25T11:00:00Z",
    },
    {
        "title": "Fake payment pages under monitoring",
        "severity": "Medium",
        "description": "Several lookalike payment pages are being monitored.",
        "date": "2026-08-24T16:00:00Z",
    },
    {
        "title": "Typosquatting activity observed",
        "severity": "Medium",
        "description": "New domains resembling well-known brands have been identified.",
        "date": "2026-08-24T10:00:00Z",
    },
]


def seed():
    # Clear only the sample collections so this script can be safely rerun.
    articles_collection.delete_many({})
    alerts_collection.delete_many({})

    articles_collection.insert_many(articles)
    alerts_collection.insert_many(alerts)

    print(f"Inserted {len(articles)} sample articles.")
    print(f"Inserted {len(alerts)} sample alerts.")
    print("Aiges sample data is ready.")


if __name__ == "__main__":
    seed()
