prompt_template = """
Enrich the description of the disease trait '{disease_trait}' with relevant biological terms and concepts. Response with only a narrative paragraph.
"""

sanitize_disease_name_prompt_template = """
# Task:
Sanitize the disease name '{disease_name}' to a more readable format.
The disease name should be informative.
Convert to lowercase.
Remove unnessceray information. 
Don't use abbreviations.

# Response Instructions:
- Response with only the sanitized disease name.
- The disease name should be a single word.
"""