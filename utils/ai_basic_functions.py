import aisuite
import google.generativeai as genai
import os
import asyncio
from google import genai as new_genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def ask_question_and_get_boolean_answer(question: str, provider_model: str="openai:gpt-4o") -> bool:
    """
    Asks a question and returns a boolean answer based on the LLM's response.

    Args:
        question: The question to ask.
        model: The LLM model to use.

    Returns:
        True if the answer is 'yes', False if the answer is 'no'.
    """
    prompt = f"""
        Answer the following question with either 'yes' or 'no', no other output allowed:

        {question}
        """
    response = aisuite.Client().chat.completions.create(model=provider_model, messages=[{"role": "user", "content": prompt}])

    content = response.choices[0].message.content.lower()

    if "yes" in content:
        return True
    elif "no" in content:
        return False
    else:
        raise ValueError(f"Could not parse 'yes' or 'no' from response: {content}")



def categorize(string_to_categorize: str, categories: list[str], context: str="", provider_model: str="openai:gpt-4o") -> str:
    """
    Categorizes the `string_to_categorize` into one of the `categories` and returns only that string using the LLM's response.

    Args:
        string_to_categorize: the thing we want to find the category for
        categories: List of valid categories
        context: useful for explaining context or examples required for best possible classification performance
        provider_model: the LLM to use

    Returns:
        A category. Garanteed to be a string from the categories list.
    """
    if len(categories) == 0:
        raise "no categories to predit"

    prompt_to_find_category = f"""Your job is to find the best fitting category for the given name/description. You have to pick one of the categories and output the full category name.

Here are the possible categories:
{str(categories)}

And here is what we want to categorize:
{string_to_categorize}

{("Here is some potentially helpful context/examples about this:\n" + context+"\n") if context else ""}

So basically you will now decide to which category '{string_to_categorize}' fits best. 
{", ".join(categories[:-1]) + ", or " + categories[-1]}

Only output the one most fitting category name from the list:
"""
    
    response = aisuite.Client().chat.completions.create(model=provider_model, messages=[{"role": "user", "content": prompt_to_find_category}])

    content = response.choices[0].message.content.lower()

    prompt_to_find_index = f"""Your job is to just output the index of the category '{content}' from the list. You may only output the integer. No other output allowed.
You do not comment on your decision of use any words at all. the category doesn't need to match '{content}' exactly. 

{[{"id": x, "category": category} for x, category in enumerate(categories)]}

Now output the id of '{content}' without any words. Just the integer now:"""
    
    response = aisuite.Client().chat.completions.create(model=provider_model, messages=[{"role": "user", "content": prompt_to_find_index}])

    content = response.choices[0].message.content

    try:
        id = int(content)
        return categories[id]
    except Exception as e:
        # TODO error handling
        pass


def run_prompt_with_gemini(prompt, model="gemini-2.0-flash"):
    """
    Runs a prompt using the Gemini API and returns the result.
    Retries up to 3 times if the API call fails.

    Args:
        prompt (str): The prompt to run.
        model (str, optional): The Gemini model to use. Defaults to "gemini-pro".

    Returns:
        str: The content of the response from the Gemini API.
             Returns None if all retries fail.
    """
    model = genai.GenerativeModel(model)
    max_retries = 7
    initial_delay = 1  # initial delay in seconds
    import time
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=0))
            return response.text
        except Exception as e:
            print(f"Gemini API call failed on attempt {attempt + 1}/{max_retries}: {e}")
            time.sleep(initial_delay * (2 ** attempt))
            if attempt == max_retries - 1:
                try:
                    return run_prompt_with_openai(prompt)
                except Exception as e:
                    raise  # Re-raise the last exception after all retries fail

    return None  # Should not reach here as exception is re-raised, but for clarity


def run_prompt_with_openai(prompt, model="gpt-4o"):
    """
    Runs a prompt using the OpenAI API and returns the result.
    Retries up to 3 times if the API call fails.

    Args:
        prompt (str): The prompt to run.
        model (str, optional): The OpenAI model to use. Defaults to "gpt-4-0125-preview".

    Returns:
        str: The content of the response from the OpenAI API.
            Returns None if all retries fail.
    """
    
    max_retries = 7
    initial_delay = 1  # initial delay in seconds
    import time
    for attempt in range(max_retries):
        try:
            response = aisuite.Client().chat.completions.create(model="openai:"+model, messages=[{"role": "user", "content": prompt}])
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API call failed on attempt {attempt + 1}/{max_retries}: {e}")
            time.sleep(initial_delay * (2 ** attempt))
            if attempt == max_retries - 1:
                raise  # Re-raise the last exception after all retries fail

    return None

async def run_prompt_with_gemini_async(prompt, model="gemini-2.0-flash"):
    """
    Runs a prompt using the Gemini API asynchronously and returns the result.
    Retries up to 7 times if the API call fails.

    Args:
        prompt (str): The prompt to run.
        model (str, optional): The Gemini model to use. Defaults to "gemini-2.0-flash".

    Returns:
        str: The content of the response from the Gemini API.
             Returns None if all retries fail.
    """
    client = new_genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    max_retries = 7
    initial_delay = 1  # initial delay in seconds
    import time
    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Gemini API async call failed on attempt {attempt + 1}/{max_retries}: {e}")
            time.sleep(initial_delay * (2 ** attempt))
            if attempt == max_retries - 1:
                try:
                    return run_prompt_with_openai(prompt)
                except Exception as e:
                    raise  # Re-raise the last exception after all retries fail

    return None  # Should not reach here as exception is re-raised, but for clarity
