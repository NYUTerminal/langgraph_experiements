import json
from typing import Optional, Annotated
from operator import add

from langgraph.graph import StateGraph, START, END
from langfuse.decorators import observe
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.llm.genos import GenOsLLM


class OnboardingState:
    url: str  # Input URL provided by the user
    content: Optional[str]  # Extracted content from the website
    short_description: Optional[str]  # Generated short description
    industry_code: Optional[str]  # Mapped industry code
    error: Optional[str]  # Error message, if any
    next_action: Annotated[list[str], add]


class LangGraphWorkflowOnboarding:
    def __init__(self, website, name, ticket, user_id, realm_id, settings):
        self.website = website
        self.name = name
        self.ticket = ticket
        self.user_id = user_id
        self.realm_id = realm_id
        self.settings = settings
        self.llm = GenOsLLM(ticket, user_id, realm_id, settings)

    @observe
    def validation_node(self, state: OnboardingState):
        if not state.url:
            return {"error": "Website URL is required."}
        return {"next_action": ["webscrape_tool_node"]}

    @observe
    def web_scraper_node(self, state: OnboardingState):
        try:
            # Simulating scraping operation
            scraped_content = f"Scraped content from {state.url}"
            return {"content": scraped_content, "next_action": ["short_description_tool"]}
        except Exception as e:
            return {"error": str(e)}

    @observe
    def short_description_tool(self, state: OnboardingState):
        if not state.content:
            return {"error": "Failed to extract website content."}
        short_desc = f"Short summary of {state.content}"
        return {"short_description": short_desc, "next_action": ["industry_mapping_tool", "offline_info_tool"]}

    @observe
    def industry_mapping_tool(self, state: OnboardingState):
        try:
            industry_code = "541512"  # Simulated industry mapping
            return {"industry_code": industry_code}
        except Exception as e:
            return {"error": str(e)}

    @observe
    def offline_info_tool(self, state: OnboardingState):
        try:
            offline_info = "Offline business info retrieved"
            return {"offline_info": offline_info}
        except Exception as e:
            return {"error": str(e)}

    @observe
    def error_handler_tool(self, state: OnboardingState):
        return {"final_response": f"An error occurred: {state.error}"}

    @observe
    def respond(self, state: OnboardingState):
        return {"final_response": {
            "content": state.content,
            "short_description": state.short_description,
            "industry_code": state.industry_code,
        }}

    def kickoff(self):
        onboarding_workflow = StateGraph(OnboardingState)

        # Adding nodes
        onboarding_workflow.add_node("validation_node", self.validation_node)
        onboarding_workflow.add_node("webscrape_tool_node", self.web_scraper_node)
        onboarding_workflow.add_node("short_description_tool", self.short_description_tool)
        onboarding_workflow.add_node("industry_mapping_tool", self.industry_mapping_tool)
        onboarding_workflow.add_node("offline_info_tool", self.offline_info_tool)
        onboarding_workflow.add_node("error_handler_tool", self.error_handler_tool)
        onboarding_workflow.add_node("respond", self.respond)

        # Connecting edges
        onboarding_workflow.add_edge(START, "validation_node")
        onboarding_workflow.add_conditional_edges(
            "validation_node", lambda state: "error" if state.get("error") else "webscrape_tool_node",
            {"error": "error_handler_tool", "webscrape_tool_node": "webscrape_tool_node"},
        )
        onboarding_workflow.add_conditional_edges(
            "webscrape_tool_node", lambda state: "error" if state.get("error") else "short_description_tool",
            {"error": "error_handler_tool", "short_description_tool": "short_description_tool"},
        )
        onboarding_workflow.add_conditional_edges(
            "short_description_tool",
            lambda state: "error" if state.get("error") else "parallel_processing",
            {"error": "error_handler_tool", "parallel_processing": "parallel_tools"}
        )

        onboarding_workflow.add_node("parallel_tools", lambda state: tuple(state["next_action"]))

        onboarding_workflow.add_parallel_edges(
            "parallel_tools",
            ["industry_mapping_tool", "offline_info_tool"]
        )

        onboarding_workflow.add_edge("industry_mapping_tool", "respond")
        onboarding_workflow.add_edge("offline_info_tool", "respond")
        onboarding_workflow.add_edge("respond", END)
        onboarding_workflow.add_edge("error_handler_tool", END)

        graph = onboarding_workflow.compile()

        messages = graph.invoke({"url": self.website})
        return messages["final_response"]
