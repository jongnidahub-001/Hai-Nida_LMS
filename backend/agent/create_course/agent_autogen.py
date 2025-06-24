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

class Course(BaseModel):
    course_id: str = Field(description="The id of the course", default_factory=generate_uuid_string)
    course_name: str = Field(description="The name of the course")
    description: str = Field(description="The description of the course")
    total_hour: int = Field(description="The total hour of the course")
    status : Literal["Active","Inactive"] = Field(description="The status of the course")
    difficulty_level : Literal["Casual","Regular","Intense"]
    learning_objectives : List[str]
    prerequisites : List[str]

class Lesson(BaseModel):
    course_id: str = Field(description="The id of the course", default_factory=generate_uuid_string)
    lesson_id: str = Field(description="The id of the lesson", default_factory=generate_uuid_string)
    lesson_title: str = Field(description="The title of the lesson")
    duration_hours: int = Field(description="The duration of the lesson in hours")
    lesson_order: int = Field(description="The order of the lesson in the course")
    description: str = Field(description="The description of the lesson")
    what_you_will_learn : List[str] = Field(description="The what you will learn in the lesson")

class LessonContent(BaseModel):
    lesson_id: str = Field(description="The id of the lesson", default_factory=generate_uuid_string)
    content_order: int = Field(description="The order of the content in the lesson")
    content_type: Literal["text","video"] = Field(description="The type of the content only (text,video)")
    content: str = Field(description="The content of the lesson")

class FinalOutput(BaseModel):
    course: Course = Field(description="The course of the course")
    lessons: List[Lesson] = Field(description="The lessons of the course")
    lesson_contents: List[LessonContent] = Field(description="The lesson contents of the course")

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

Role: You are a master at creating engaging and effective courses. You are also a master at creating lessons and lesson content that are engaging and effective. You are also a master at creating course outlines that are engaging and effective.

Goal: Create a detailed course outline, lessons, and lesson content for a given document with the specified difficulty level: {difficulty_level}.

Backstory: With over 10 years of experience in the field of education, you are a master at designing content-rich, time-appropriate, and highly engaging instructional materials for different skill levels.

Instructions:
- Use the document to create a course, lessons, and detailed lesson content.
- Create the course with the specified difficulty level: **{difficulty_level}**
- Each lesson must be directly related to the course and match the specified difficulty level.

**Difficulty Level Guidelines:**

**CASUAL:**
- Focus on basic concepts and fundamental understanding
- Use simple language and clear, straightforward explanations
- Include more practical examples and real-world applications
- Shorter lesson durations (1-2 hours per lesson)
- Minimal prerequisites required
- Step-by-step guidance with plenty of support materials

**REGULAR:**
- Cover intermediate concepts with moderate depth
- Balance theory with practical applications
- Include case studies and moderate complexity examples
- Standard lesson durations (2-3 hours per lesson)
- Some foundational knowledge expected as prerequisites
- Mix of guided instruction and independent learning

**INTENSE:**
- Deep dive into advanced concepts and complex topics
- Assume strong foundational knowledge
- Include challenging case studies, complex problem-solving scenarios
- Longer lesson durations (3-4 hours per lesson)
- Multiple prerequisites and advanced preparation required
- Emphasis on critical thinking, analysis, and independent research

- Each lesson content must:
  - Cover all topics in the lesson thoroughly according to the **{difficulty_level}** difficulty level.
  - Include **at least 500 words** (or **enough content for a lesson duration**).
  - Be structured with **headings, subheadings**, and **examples** appropriate to the **{difficulty_level}** difficulty.
  - Include **clear explanations**, **steps**, **case studies**, or **diagrams** (if appropriate).
  - End with a brief **summary or recap** and 2-3 **reflection questions** or a quiz matching the **{difficulty_level}** difficulty level.
- Use external data (own knowledge) to fulfill gaps if the document lacks enough information.
- Ensure the entire course maintains consistency with the **{difficulty_level}** difficulty level.

Here is the document content:
{document_content}


Return the output in the exact FinalOutput format with course, lessons, and lesson_contents.

"""

critic_agent_prompt = """
    Role : You are a master at validating courses, lessons and lesson content. You are also a master at validating course outline that are engaging and effective.
    Goal : Validate the course, lesson and lesson content for a given document and provide feedback to the expert agent Provide constructive feedback. Respond with 'APPROVE'(only in capital letters with no other text) to when your feedbacks are addressed, if not, do not include "APPROVE" in your response. only include "APPROVE" if the course, lesson and lesson content is approved.
    Backstory : With over 10 years of experience in the field of education, you are a master at validating courses, lessons and lesson content. You are also a master at validating course outline that are engaging and effective.

    Additional Instructions :
    - Provide feedback on the quality, completeness, and educational value.
    - DO NOT modify the original course structure - only provide feedback.
    
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
    
    async def create_course(self, document_content: str = '', difficulty_level: str = 'Regular'):
        """
        Create a course with specified difficulty level
        
        Args:
            document_content (str): The content of the document to create course from
            difficulty_level (str): The difficulty level - must be one of: 'Casual', 'Regular', 'Intense'
        """
        # Validate difficulty level
        valid_difficulties = ['Casual', 'Regular', 'Intense']
        if difficulty_level not in valid_difficulties:
            raise ValueError(f"Invalid difficulty level. Must be one of: {valid_difficulties}")
        
        formatted_prompt = primary_agent_prompt.format(
            document_content=document_content,
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
# asyncio.run(test.create_course())



