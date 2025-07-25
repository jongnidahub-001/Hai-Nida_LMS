import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
from typing import List,Literal
import json
from uuid import uuid4

load_dotenv()

def generate_uuid_string():
    return str(uuid4())


class Grader(BaseModel):
    result: Literal[True,False]


GEMINI_API_KEY=os.getenv("GOOGLE_API_KEY")

# Create an OpenAI model client.
model_client = OpenAIChatCompletionClient(
    model="gemini-2.5-flash",
    model_info=ModelInfo(vision=True, function_calling=True, json_output=True, family="unknown", structured_output=True),
    api_key="AIzaSyCNd1tfREAZbBnhyGuusjcjz7OdexdazCY",
)

prompt = """
    ### ROLE ###
    You are a strict and precise AI System Evaluator.

    ### TASK ###
    Evaluate if the [User's Answer] is semantically and factually correct based on the provided [Model Answer]. Your goal is to output a single word: "True" if the user is correct, and "False" if they are not.

    ### EVALUATION RULES ###
    1.  **Semantic Match:** The user's answer does not need to be a word-for-word match, but it must have the same meaning as the model answer.
    2.  **Key Concepts:** For subjective questions, the user's answer is "True" if it contains the essential key concepts or ideas from the model answer.
    3.  **Leniency:** Be lenient with minor spelling mistakes, typos, or grammatical errors as long as the core meaning is clear.
    4.  **Completeness:** If the model answer requires multiple points, the user's answer must address all of them to be "True".

    ### OUTPUT FORMAT ###
    Your entire response MUST be a single word: "True" or "False". Do not provide any explanation, context, or any other text.

    ### EVALUATION DATA ###
    - **Question:** {question}
    - **Model Answer:** {model_answer}
    - **User's Answer:** {user_answer}

"""
class Evaluation:
    def __init__(self):
        pass
    
    async def evaluate(self, question: str, model_answer: str, user_answer: str):
        formatted_prompt = prompt.format(question=question, model_answer=model_answer, user_answer=user_answer)
        result = await team.run(task=formatted_prompt)
        return result


# test = CreateCourse()
# asyncio.run(test.create_quiz(number_of_questions=10,number_of_choices=4,number_of_subjective_questions=2,number_of_fill_in_the_blank_questions=2))



