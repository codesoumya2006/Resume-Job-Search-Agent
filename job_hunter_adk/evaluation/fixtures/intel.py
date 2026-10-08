"""
Deterministic company intel fixtures for evaluation scenarios.
"""
from schemas.company_intel import CompanyIntel, ReviewSummary

TECHNOVA_INTEL = CompanyIntel(
    company_name="TechNova",
    website="https://technova.io",
    recent_news=["TechNova raises Series B to expand distributed cloud infrastructure."],
    financial_snapshot="Series B funded, $40M ARR.",
    reviews=[
        ReviewSummary(
            source="glassdoor",
            summary="Strong engineering culture with cutting-edge microservices tech stack.",
            sentiment="positive"
        ),
        ReviewSummary(
            source="blind",
            summary="Competitive compensation and great work-life balance for remote teams.",
            sentiment="positive"
        )
    ]
)

COGNITIVEAI_INTEL = CompanyIntel(
    company_name="CognitiveAI",
    website="https://cognitiveai.io",
    recent_news=["CognitiveAI launches new generative models API."],
    financial_snapshot="Seed round $5M.",
    reviews=[
        ReviewSummary(
            source="glassdoor",
            summary="Rapidly growing AI startup, fast-paced environment.",
            sentiment="neutral"
        )
    ]
)
