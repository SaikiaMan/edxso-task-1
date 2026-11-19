from signalstack.research import RESEARCH_FIELDS, build_research_graph


def fake_researcher(prompt):
    assert "MeetUniversity" in prompt

    profile = {
        field: {
            "findings": [],
            "unknowns": ["No public evidence was collected in this smoke test."],
        }
        for field in RESEARCH_FIELDS
    }

    profile["interview_gaps"]["questions"] = [
    "Which student segment generates the most revenue?",
]
    

    return profile


graph = build_research_graph(fake_researcher)

result = graph.invoke({
    "company_name": "MeetUniversity",
    "website": "https://www.meetuniversity.com",
})

assert result["validated"] is True
print("Smoke test passed")