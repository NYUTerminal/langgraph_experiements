import requests
from bs4 import BeautifulSoup
import openai
from langgraph.graph import StateGraph

from typing import Optional
from pydantic import BaseModel


# Define the state schema using Pydantic
class WebsiteProcessingState(BaseModel):
    url: str  # Input URL provided by the user
    content: Optional[str] = None  # Extracted content from the website
    short_description: Optional[str] = None  # Generated short description
    industry_code: Optional[str] = None  # Mapped industry code
    error: Optional[str] = None  # Error message, if any
    next_action: Optional[str] = "scrape"  # Next step in the workflow


# Step 1: Web Scraping Tool
def scrape_website(state):
    url = state["url"]
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        text = " ".join([p.get_text() for p in soup.find_all("p")])  # Extract all paragraphs
        return {"content": text, "next_action": "generate_description"}
    return {"error": "Failed to scrape website", "next_action": "handle_error"}


# Step 2: Generate Short Description
def generate_short_description(state):
    content = state.get("content", "")
    if not content:
        return {"error": "No content to summarize", "next_action": "handle_error"}

    # Using GPT to generate a short description
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "Summarize this content in a few sentences."},
                  {"role": "user", "content": content}]
    )

    short_description = response["choices"][0]["message"]["content"]
    return {"short_description": short_description, "next_action": "map_to_industry"}


# Step 3: Map to Industry Code using Custom RAG Tool
def map_to_industry(state):
    short_description = state.get("short_description", "")
    if not short_description:
        return {"error": "No short description to map", "next_action": "handle_error"}

    # Example Custom RAG Tool interaction
    # Assume we have a function `query_rag_tool` that takes a description and returns an industry code
    industry_code = query_rag_tool(short_description)

    return {"industry_code": industry_code, "next_action": "complete"}


# Step 4: Error Handling
def handle_error(state):
    return {"final_status": "Error encountered in workflow.", "next_action": "complete"}


# Example custom RAG function
def query_rag_tool(description):
    # This is where your RAG tool logic goes to map the description to industry codes
    # Example static mapping (replace with real RAG logic)
    return "INDUSTRY_CODE_123"  # Example return value


class WebsiteIndustryMapperAgent:
    def __init__(self):
        self.graph = StateGraph()

        # Add Nodes
        self.graph.add_node("scrape", scrape_website)
        self.graph.add_node("generate_description", generate_short_description)
        self.graph.add_node("map_to_industry", map_to_industry)
        self.graph.add_node("handle_error", handle_error)

        # Router to dynamically determine next step
        def router(state):
            next_action = state.get("next_action")
            if next_action == "generate_description":
                return "generate_description"
            elif next_action == "map_to_industry":
                return "map_to_industry"
            elif next_action == "handle_error":
                return "handle_error"
            else:
                return None  # End workflow

        self.graph.add_node("router", router)
        self.graph.set_entry_point("scrape")

        # Define Workflow Edges
        self.graph.add_edge("scrape", "router")
        self.graph.add_edge("generate_description", "router")
        self.graph.add_edge("map_to_industry", "router")
        self.graph.add_edge("handle_error", "router")

    def run(self, url):
        initial_state = WebsiteProcessingState(url=url)  # Initialize with user input
        return self.graph.run(initial_state)


# Example Usage
agent = WebsiteIndustryMapperAgent()
result = agent.run("https://example.com")
print("Industry Code:", result.industry_code if result.industry_code else "Not mapped")

# Run the agent
agent = WebsiteIndustryMapperAgent()
result = agent.run("https://example.com")
print("Industry Code:", result.get("industry_code", "Not mapped"))
