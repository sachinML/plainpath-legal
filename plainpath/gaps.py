"""Gap Watch: topics a document type usually covers that this text does not mention."""

from __future__ import annotations

from dataclasses import dataclass

from plainpath.types import Gap, PersonaId


@dataclass(frozen=True)
class ExpectedTopic:
    """A topic we look for; absence is a gap, not a legal conclusion."""

    topic: str
    phrases: tuple[str, ...]
    why_it_matters: str
    suggested_question: str
    doc_types: tuple[str, ...]
    personas: tuple[PersonaId, ...] | None = None


EXPECTED_TOPICS: tuple[ExpectedTopic, ...] = (
    ExpectedTopic(
        topic="How the security deposit is returned",
        phrases=(
            "deposit shall be returned",
            "return of the security deposit",
            "return the security deposit",
            "deposit refund",
        ),
        why_it_matters="Without a return rule, it is harder to know when held money should come back.",
        suggested_question="What is the deadline and process for returning my deposit, and what deductions are allowed?",
        doc_types=("lease",),
    ),
    ExpectedTopic(
        topic="Repair or habitability timeline",
        phrases=("habitable", "make necessary repairs", "maintenance request", "repair within"),
        why_it_matters="A lease that is silent on repairs leaves a common housing issue unaddressed on the page.",
        suggested_question="If something breaks, how soon must it be fixed, and how do I give notice?",
        doc_types=("lease",),
    ),
    ExpectedTopic(
        topic="Advance notice before entry",
        phrases=("hours notice", "notice before enter", "prior notice", "24-hour", "24 hour"),
        why_it_matters="Entry without a stated notice period can catch a renter off guard.",
        suggested_question="How much notice will I get before anyone enters, except in a true emergency?",
        doc_types=("lease",),
        personas=("tenant", "caregiver", "community_navigator"),
    ),
    ExpectedTopic(
        topic="Pay frequency and method",
        phrases=("paid biweekly", "paid weekly", "direct deposit", "payday", "pay period"),
        why_it_matters="If pay timing is missing, a core job term is not on the page.",
        suggested_question="When will I be paid, and by what method?",
        doc_types=("employment",),
    ),
    ExpectedTopic(
        topic="How to cancel",
        phrases=("how to cancel", "cancellation", "cancel your subscription", "opt out"),
        why_it_matters="A contract that bills you but does not say how to stop is a common trap.",
        suggested_question="Exactly how do I cancel, and what is the last day I can do it?",
        doc_types=("terms_of_service", "service_agreement"),
        personas=("consumer", "small_business"),
    ),
    ExpectedTopic(
        topic="Data deletion or access request",
        phrases=("delete your data", "access your data", "right to delete", "data subject"),
        why_it_matters="Privacy terms often omit how you ask to see or erase information.",
        suggested_question="How do I ask to see or delete information about me?",
        doc_types=("privacy_policy", "terms_of_service"),
    ),
    ExpectedTopic(
        topic="Fee cap or estimate",
        phrases=("not to exceed", "fee cap", "estimate", "maximum fee"),
        why_it_matters="Service work without a cap can grow in cost without a written ceiling.",
        suggested_question="Is there a maximum I will be charged, and what happens if work goes over?",
        doc_types=("service_agreement",),
        personas=("small_business", "consumer", "caregiver"),
    ),
    ExpectedTopic(
        topic="Interpreter or accessible format",
        phrases=("interpreter", "large print", "accessible format", "reasonable accommodation", "plain language copy"),
        why_it_matters="People who need language or format support rarely see that support written down.",
        suggested_question="Can we get this in another language, large print, or with an interpreter?",
        doc_types=("lease", "employment", "terms_of_service", "service_agreement", "privacy_policy", "other"),
        personas=("community_navigator", "caregiver"),
    ),
)


def find_gaps(text: str, document_type: str, persona_id: str) -> tuple[Gap, ...]:
    """Return expected topics that do not appear in the document text."""
    lowered = text.lower()
    gaps: list[Gap] = []
    for topic in EXPECTED_TOPICS:
        if document_type not in topic.doc_types and "other" not in topic.doc_types:
            continue
        if topic.personas is not None and persona_id not in topic.personas:
            continue
        if any(phrase in lowered for phrase in topic.phrases):
            continue
        gaps.append(
            Gap(
                topic=topic.topic,
                why_it_matters=topic.why_it_matters,
                suggested_question=topic.suggested_question,
            )
        )
    return tuple(gaps)
