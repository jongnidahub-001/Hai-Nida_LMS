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


class Quiz(BaseModel):
    quiz_id: str = Field(description="The id of the quiz", default_factory=generate_uuid_string)
    course_id: str = Field(description="The id of the course")
    quiz_title: str = Field(description="The title of the quiz")
    status : Literal["Active","Inactive"] = Field(description="The status of the quiz")
    description: str = Field(description="The description of the quiz")
    difficulty_level : Literal["Casual","Regular","Intense"] = Field(description="The difficulty level of the quiz")

class Question(BaseModel):
    question_id: str = Field(description="The id of the question", default_factory=generate_uuid_string)
    quiz_id: str = Field(description="The id of the quiz")
    question_text: str = Field(description="The text of the question")
    question_type: Literal["Multiple Choice","Subjective","Fill in the Blank"] = Field(description="The type of the question")
    points: int = Field(description="The points of the question")

class Choice(BaseModel):
    choice_id: str = Field(description="The id of the choice", default_factory=generate_uuid_string)
    question_id: str = Field(description="The id of the question")
    choice_text: str = Field(description="The text of the choice")
    is_correct: bool = Field(description="Whether the choice is correct")

class Answer(BaseModel):
    answer_id: str = Field(description="The id of the answer", default_factory=generate_uuid_string)
    question_id: str = Field(description="The id of the question")
    answer_text: str = Field(description="The text of the answer")

class FinalOutput(BaseModel):
    quiz: Quiz = Field(description="The quiz of the quiz")
    questions: List[Question] = Field(description="The questions of the quiz")
    choices: List[Choice] = Field(description="The choices of the quiz")
    answers: List[Answer] = Field(description="The answers of the quiz")

class ValidationOutput(BaseModel):
    feedback: str = Field(description="The feedback on the course, lesson and lesson content")
    approved: Literal["APPROVE","REJECT"] = Field(description="Whether the course, lesson and lesson content is approved")


GEMINI_API_KEY=os.getenv("GOOGLE_API_KEY")

# Create an OpenAI model client.
model_client = OpenAIChatCompletionClient(
    model="gemini-2.5-flash",
    model_info=ModelInfo(vision=True, function_calling=True, json_output=True, family="unknown", structured_output=True),
    api_key="AIzaSyCNd1tfREAZbBnhyGuusjcjz7OdexdazCY",
)

primary_agent_prompt = """

Role: You are a master at creating engaging and effective quizzes. You are also a master at creating questions with appropriate choices and answers that are educational and challenging at different difficulty levels.

Goal: Create a comprehensive quiz with questions, choices, and answers based on a given document with the specified difficulty level: {difficulty_level}.

Backstory: With over 10 years of experience in the field of education and assessment, you are a master at designing comprehensive, well-structured quizzes that effectively test knowledge and understanding at various difficulty levels.

Instructions:
- Use the document to create a quiz with multiple questions covering the key topics.
- Create the quiz with the specified difficulty level: **{difficulty_level}**
- Create questions of different types: Multiple Choice, Subjective, and Fill in the Blank.
- Each question must be directly related to the content in the document and match the specified difficulty level.

**Difficulty Level Guidelines:**

**CASUAL:**
- Focus on basic recall and fundamental understanding
- Use straightforward language and simple concepts
- Multiple Choice: Clear distinctions between correct and incorrect answers
- Questions test basic facts, definitions, and simple applications
- Point values: 1-3 points per question
- Avoid complex reasoning or multi-step problems

**REGULAR:**
- Test intermediate understanding and application
- Include some analysis and interpretation questions
- Multiple Choice: Include plausible distractors that require moderate knowledge
- Questions test comprehension, application, and basic analysis
- Point values: 2-5 points per question
- Mix of recall and application-based questions

**INTENSE:**
- Test deep understanding, critical thinking, and complex application
- Require synthesis of multiple concepts and advanced reasoning
- Multiple Choice: Complex scenarios with sophisticated distractors
- Questions test analysis, synthesis, evaluation, and problem-solving
- Point values: 5-10 points per question
- Focus on higher-order thinking skills and complex applications

- For Multiple Choice questions:
  - Provide 4 choices with only one correct answer.
  - Make distractors (incorrect choices) appropriate to the **{difficulty_level}** level.
  - **{difficulty_level}** difficulty should be reflected in question complexity and distractor sophistication.
- For Subjective questions:
  - Create questions that are clear and match the **{difficulty_level}** complexity level.
  - **{difficulty_level}** questions should require appropriate depth of response.
- For Fill in the Blank questions:
  - Create questions that test concepts appropriate to **{difficulty_level}** level.
  - Provide the correct answer in the answers section.
- Assign appropriate point values to questions based on **{difficulty_level}** complexity.
- Set the quiz difficulty_level to **{difficulty_level}** in the output.
- Ensure all questions maintain consistency with the **{difficulty_level}** difficulty level.
- Use external knowledge to enhance question quality if the document lacks sufficient detail.


Here is the number of questions you need to create: {number_of_questions}
here is the number of choices you need to create: {number_of_choices}
here is the number of Subjective questions you need to create: {number_of_subjective_questions}
here is the number of Fill in the Blank questions you need to create: {number_of_fill_in_the_blank_questions}

Here is the document content:
{document_content} 


Return the output in the exact FinalOutput format with quiz, questions, choices, and answers.

"""

critic_agent_prompt = """
    Role : You are a master at validating quizzes, questions, choices, and answers. You are an expert at ensuring quiz quality and correctness.
    Goal : Validate the quiz, questions, choices, and answers for accuracy and quality. Provide constructive feedback to the expert agent. Respond with 'APPROVE' (only in capital letters with no other text) when all questions and answers are correct and the quiz meets quality standards. If not, do not include "APPROVE" in your response. Only include "APPROVE" if the quiz, questions, and answers are all correct and approved.
    Backstory : With over 10 years of experience in educational assessment and quiz validation, you are a master at ensuring quiz accuracy, question clarity, and answer correctness.

    Additional Instructions :
    - Verify that all questions are clear and unambiguous.
    - Check that multiple choice questions have exactly one correct answer and plausible distractors.
    - Check that Subjective questions are clear and unambiguous.
    - Validate that Fill in the Blank answers are accurate and complete.
    - Confirm that point values are appropriate for question difficulty.
    - Check that the quiz difficulty level matches the question complexity.
    - Provide feedback on question quality, answer accuracy, and overall quiz effectiveness.
    - DO NOT modify the original quiz structure - only provide validation feedback.
    
"""

# Create the primary agent.
primary_agent = AssistantAgent(
    "Expert_Agent",
    model_client=model_client,
    system_message=primary_agent_prompt,
    output_content_type=FinalOutput,
)

# Create the critic agent.
critic_agent = AssistantAgent(
    "Validator_Agent",
    model_client=model_client,
    system_message=critic_agent_prompt,
)

# Define a termination condition that stops the task if the critic approves.
text_termination = TextMentionTermination("APPROVE")

# Create a team with the primary and critic agents.
team = RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=text_termination)


class CreateCourse:
    def __init__(self):
        pass
    
    async def create_quiz(self, document_content: str = '', number_of_questions: int = 0, number_of_choices: int = 0, number_of_subjective_questions: int = 0, number_of_fill_in_the_blank_questions: int = 0, difficulty_level: str = 'Regular'):
        """
        Create a quiz with specified difficulty level
        
        Args:
            document_content (str): The content of the document to create quiz from
            number_of_questions (int): Total number of questions to create
            number_of_choices (int): Number of multiple choice questions
            number_of_subjective_questions (int): Number of subjective questions
            number_of_fill_in_the_blank_questions (int): Number of fill in the blank questions
            difficulty_level (str): The difficulty level - must be one of: 'Casual', 'Regular', 'Intense'
        """
        # Validate difficulty level
        valid_difficulties = ['Casual', 'Regular', 'Intense']
        if difficulty_level not in valid_difficulties:
            raise ValueError(f"Invalid difficulty level. Must be one of: {valid_difficulties}")
        
        formatted_prompt = primary_agent_prompt.format(
            document_content=document_content,
            number_of_questions=number_of_questions,
            number_of_choices=number_of_choices,
            number_of_subjective_questions=number_of_subjective_questions,
            number_of_fill_in_the_blank_questions=number_of_fill_in_the_blank_questions,
            difficulty_level=difficulty_level
        )
        
        result = await team.run(task=formatted_prompt)
        for i in result.messages:
            print("--------------------------------")
            print("Agent: ",i.source)
            if i.source == "Expert_Agent":
                print("Content: ",i.content.dict())
            else:
                print("Content: ",i.content)
            print("--------------------------------")
        
        return result


# test = CreateCourse()
# asyncio.run(test.create_quiz(number_of_questions=10,number_of_choices=4,number_of_subjective_questions=2,number_of_fill_in_the_blank_questions=2))



