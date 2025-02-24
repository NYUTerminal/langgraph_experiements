import requests
from bs4 import BeautifulSoup
from langgraph.graph import StateGraph


class ScraperAgent:
    def __init__(self):
        state_schema = {
            "url": str,
            "scraped_data": dict,
            "mapped_data": dict
        }
        self.graph = StateGraph(state_schema=state_schema)
        self.graph.add_node("scrape", self.scrape)
        self.graph.add_node("map_data", self.map_data)
        self.graph.set_entry_point("scrape")
        self.graph._add_schema(state_schema)
        self.graph.add_edge("scrape", "map_data")

    def scrape(self, state):
        url = state.get("url")
        print(f"Scraping website: {url}")
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            data = {
                "title": soup.title.string if soup.title else "No Title",
                "headings": [h.get_text() for h in soup.find_all("h1")],
                "links": [a["href"] for a in soup.find_all("a", href=True)]
            }
            return {"scraped_data": data}
        else:
            return {"error": f"Failed to fetch website, status code: {response.status_code}"}

    def map_data(self, state):
        if "scraped_data" in state:
            print("Mapping data...")
            mapped_data = {
                "page_title": state["scraped_data"].get("title", "Unknown"),
                "main_headings": state["scraped_data"].get("headings", []),
                "external_links": [link for link in state["scraped_data"].get("links", []) if link.startswith("http")]
            }
            return {"mapped_data": mapped_data}
        return state

    def run(self, url):
        return self.graph.run({"url": url})


if __name__ == "__main__":
    agent = ScraperAgent()
    result = agent.run("https://example.com")
    print("Final Mapped Data:", result.get("mapped_data", "No Data"))
