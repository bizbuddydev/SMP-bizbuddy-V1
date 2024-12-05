import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import gsc_data_pull
from llm_integration import query_gpt
from gaw_camapignbuilder import *

# Page configuration
st.set_page_config(page_title="SEOhelper", layout="wide", page_icon = "🔎")

# Function to fetch the page copy for SEO
def fetch_page_copy(url):
    try:
        # Fetch the content of the page
        response = requests.get(url)
        response.raise_for_status()  # Check if request was successful

        # Parse the page content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the title tag
        title = soup.title.string if soup.title else "No title found"

        # Extract the meta description
        meta_description = ""
        description_tag = soup.find("meta", attrs={"name": "description"})
        if description_tag and description_tag.get("content"):
            meta_description = description_tag["content"]
        else:
            meta_description = "No meta description found"

        # Extract meta keywords
        meta_keywords = ""
        keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        if keywords_tag and keywords_tag.get("content"):
            meta_keywords = keywords_tag["content"]
        else:
            meta_keywords = "No meta keywords found"

        # Extract main text from <p> and heading tags
        paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3'])
        page_text = "\n\n".join([para.get_text(strip=True) for para in paragraphs])

        # Combine all extracted data into a dictionary
        seo_data = {
            "Title": title,
            "Meta Description": meta_description,
            "Meta Keywords": meta_keywords,
            "Page Copy": page_text if page_text else "No main content found on this page."
        }

        return seo_data
    except requests.RequestException as e:
        return {"Error": f"An error occurred while fetching the page: {e}"}

# Function to generate keywords based on business description
def generate_keywords(business_description):
    llm_response = query_gpt(
        prompt=(
            "Generate a list of exactly 15 paid search keywords grouped into 3 ad groups based on the following business description. "
            "Each ad group should contain 5 keywords. "
            "Return the response as a JSON-formatted list of dictionaries, where each dictionary has the following structure: "
            '{"Keyword": "Keyword 1", "Ad Group": "Ad Group 1"}. '
            "Ensure that the only output is the JSON list of dictionaries with no additional text before or after."
        ),
        data_summary=business_description
    )

    # Extract content inside brackets
    extracted_json = extract_json_like_content(llm_response)
    if extracted_json:
        try:
            keyword_list = json.loads(extracted_json)  # Parse JSON
            st.session_state["keywords_df"] = pd.DataFrame(keyword_list)  # Save DataFrame in session state
            st.session_state["keyword_checkboxes"] = {
                f"{kw} ({ad})": True for kw, ad in zip(
                    st.session_state["keywords_df"]["Keyword"],
                    st.session_state["keywords_df"]["Ad Group"]
                )
            }  # Initialize checkbox states
            
            # Extract only the "Keyword" part
            keywords = [kw["Keyword"] for kw in keyword_list]
            return keywords  # Return the list of keywords
        except json.JSONDecodeError:
            st.error("Failed to parse the extracted content as JSON. Please check the output.")
    else:
        st.error("Could not extract content inside brackets. Please check the LLM response.")

# Combine the SEO tool with keyword generation
def display_report_with_llm(llm_prompt, keywords):
    # Ensure keywords are passed as a formatted string for the LLM prompt
    keywords_str = ', '.join(keywords)  # Join keywords into a string

    # Query the LLM with the prompt
    final_response = query_gpt(llm_prompt)
    st.subheader("ChatGPT Analysis:")
    st.write(final_response)

def main():
         
    # Ensure session_summary is initialized in session state
    if "session_summary" not in st.session_state:
        st.session_state["session_summary"] = ""  # Initialize with an empty string or default value
    

    # Display SEO helper app
    st.title("SEO Helper")
    st.write("This is the SEO helper app.")

    # Input field for the business description
    business_description = st.text_area(
        "Business Description", 
        placeholder="E.g., 'A sports psychologist in Boise, Idaho, specializing in 1-on-1 coaching, team workshops, and mental performance plans. Customers might search for terms like 'sports psychologist,' 'sports mental coach,' or 'mental fatigue in athletes.'"
    )

    # Input field for the URL to scrape
    url = st.text_input("Enter a URL to scrape", placeholder="https://example.com")

    # Initialize keyword_list variable
    keyword_list = []

    # Step 2: Keyword Generation
    if st.button("Generate Keywords") and business_description.strip():
        keyword_list = generate_keywords(business_description)

    # Now generate the SEO analysis based on the business description and keywords
    if url and keyword_list:
        st.write("Fetching content...")
        seo_data = fetch_page_copy(url)

        with st.expander("See Website Copy"):
            st.subheader("SEO Information")
            st.write(f"**Title:** {seo_data['Title']}")
            st.write(f"**Meta Description:** {seo_data['Meta Description']}")
            st.write(f"**Meta Keywords:** {seo_data['Meta Keywords']}")
            st.subheader("Page Copy")
            st.write(seo_data["Page Copy"])

        # Generate the prompt for LLM analysis
        llm_prompt_final = (
            f"Here is the SEO information and page copy from a webpage:\n\n"
            f"Title: {seo_data['Title']}\n"
            f"Meta Description: {seo_data['Meta Description']}\n"
            f"Meta Keywords: {seo_data['Meta Keywords']}\n"
            f"Page Copy: {seo_data['Page Copy']}\n\n"
            f"Based on this SEO information, please suggest possible improvements. Have one section that talks about overall SEO strategy. Below that, identify actual pieces of text that could be tweaked."
            f"Use the following context to guide your suggestions: {', '.join(keyword_list)}. "
            f"This is an analysis from an initial look at the search query report from this website."
        )

        st.session_state["session_summary"] = "" 
        
        # Display LLM analysis with the generated keywords included in the prompt
        display_report_with_llm(llm_prompt_final, keyword_list)
    else:
        if not keyword_list:
            st.warning("Please generate keywords by filling out the business description.")
        if not url:
            st.warning("Please enter a valid URL.")

if __name__ == "__main__":
     main()
