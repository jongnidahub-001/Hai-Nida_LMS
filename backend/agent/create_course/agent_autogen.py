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
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

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

class Grader(BaseModel):
    result: bool = Field(description="The result of the evaluation")


class CourseSuggestion(BaseModel):
    course_name: str = Field(description="The name of the course")
    course_description: str = Field(description="The description of the course")
    course_difficulty: str = Field(description="The difficulty level of the course")
    reason: str = Field(description="The reason for the course suggestion")

class CourseSuggestionOutput(BaseModel):
    course_suggestion: List[CourseSuggestion] = Field(description="The course suggestion")

class RegeneratedLesson(BaseModel):
    lesson_title: str = Field(description="The title of the lesson")
    duration_hours: int = Field(description="The duration of the lesson in hours")
    description: str = Field(description="The description of the lesson")
    what_you_will_learn: List[str] = Field(description="What you will learn in the lesson")

class RegeneratedLessonContent(BaseModel):
    content_order: int = Field(description="The order of the content in the lesson")
    content_type: Literal["text","video"] = Field(description="The type of the content only (text,video)")
    content: str = Field(description="The content of the lesson")

class RegeneratedLessonOutput(BaseModel):
    lesson: RegeneratedLesson = Field(description="The regenerated lesson")
    lesson_contents: List[RegeneratedLessonContent] = Field(description="The regenerated lesson contents")


GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# Shared client for simple LLM calls (stateless, safe to share)
gemini_client = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=GEMINI_API_KEY,
)


def create_model_client():
    """Create a new model client instance for each request"""
    return OpenAIChatCompletionClient(
        model="gemini-2.5-flash",
        model_info=ModelInfo(vision=True, function_calling=True, json_output=True, family="unknown", structured_output=True),
        api_key=GEMINI_API_KEY,
    )


def create_team_for_request(document_content: str, difficulty_level: str):
    """Create fresh agent team for each request to ensure isolation"""
    model_client = create_model_client()
    
    formatted_system_message = primary_agent_prompt.format(
        document_content=document_content,
        difficulty_level=difficulty_level
    )
    
    # Create fresh agents for this request
    primary_agent = AssistantAgent(
        "Expert_Agent",
        model_client=model_client,
        system_message=formatted_system_message,
        output_content_type=FinalOutput,
    )
    
    critic_agent = AssistantAgent(
        "Validator_Agent",
        model_client=model_client,
        system_message=critic_agent_prompt,
    )
    
    # Define termination condition
    text_termination = TextMentionTermination("APPROVE")
    
    # Create a new team for this specific request
    team = RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=text_termination)
    
    return team

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

**CRITICAL MARKDOWN FORMATTING RULES:**
- ALWAYS add a blank line BEFORE every heading (##, ###, ####)
- ALWAYS add a blank line AFTER every heading
- ALWAYS add a blank line between paragraphs
- ALWAYS add a blank line before bullet lists or numbered lists
- NEVER run headings into text like "some text### Heading" - this breaks rendering
- Example of CORRECT formatting:
  ```
  This is a paragraph about neural networks.

  ### 2.1 Neural Networks Overview

  Neural networks are computational models...

  #### Key Concepts:

  - Concept 1
  - Concept 2
  ```
- Example of WRONG formatting (DO NOT DO THIS):
  ```
  This is a paragraph about neural networks.### 2.1 Neural Networks Overview
  Neural networks are computational models...#### Key Concepts:- Concept 1
  ```
- Use external data (own knowledge) to fulfill gaps if the document lacks enough information.
- Ensure the entire course maintains consistency with the **{difficulty_level}** difficulty level.

Here is the document content:
{document_content}


Return the output in the exact FinalOutput format with course, lessons, and lesson_contents.

"""

critic_agent_prompt = """
Role: You are a master at validating courses, lessons and lesson content. You are also an expert at validating markdown formatting.

Goal: Validate the course, lesson and lesson content for quality, completeness, educational value, AND proper markdown formatting. Provide constructive feedback to the expert agent. Respond with 'APPROVE' (only in capital letters with no other text) when ALL your feedbacks are addressed. If not, do NOT include "APPROVE" in your response.

Backstory: With over 10 years of experience in education and technical writing, you are a master at validating courses and ensuring content is properly formatted for readability.

**VALIDATION CHECKLIST:**

1. **Educational Quality:**
   - Content is complete and covers all necessary topics
   - Appropriate difficulty level maintained
   - Clear learning objectives and outcomes

2. **MARKDOWN FORMATTING (CRITICAL - MUST CHECK):**
   - ✓ Every heading (##, ###, ####) has a BLANK LINE before it
   - ✓ Every heading has a BLANK LINE after it
   - ✓ Paragraphs are separated by blank lines
   - ✓ Lists have a blank line before the first item
   - ✓ No headings running into text (e.g., "text### Heading" is WRONG)
   - ✓ No paragraphs running together without line breaks
   
   **If you see formatting like this, REJECT and ask for fixes:**
   - "some text### 2.1 Heading" ← WRONG (missing line break before ###)
   - "Heading\\nText immediately" ← WRONG (missing line break after heading)
   - "paragraph1paragraph2" ← WRONG (paragraphs must be separated)

3. **Structure:**
   - Proper use of headings hierarchy (##, ###, ####)
   - Summary or recap at the end
   - Reflection questions included

**Instructions:**
- Provide specific feedback on what needs to be fixed
- Be strict about markdown formatting - it affects readability
- DO NOT modify the original content - only provide feedback
- Only respond with 'APPROVE' when ALL criteria are met, including formatting
"""

prompt = """
            <prompt>
        <role_definition>
            You are "Teacher AI," a highly effective, patient, and engaging virtual tutor. Your single purpose is to help a student master the specific lesson content provided below. Your personality is encouraging, clear, and supportive. You must strictly adhere to all rules.
        </role_definition>

        <context>
            <lesson_content>
            {lesson_content}
            </lesson_content>
            
            <chat_history>
            {chat_history}
            </chat_history>
        </context>

        <rules>
            <prime_directive>
            **THE MOST IMPORTANT RULE:** If a user's question is not directly related to the concepts, topics, or information within the <lesson_content>, you MUST respond with the exact, and only the exact, phrase: "Your question is outside the scope of this lesson." This rule overrides all other instructions. Do not apologize or offer to search for the information.
            </prime_directive>

            <rule id="knowledge_source">
            Your primary source of truth is the <lesson_content>. All your explanations must be grounded in this material.
            </rule>
            
            <rule id="chat_history_context">
            Use the <chat_history> to understand the ongoing conversation context. Reference previous parts of the conversation when relevant, and build upon what has already been discussed. Maintain conversation continuity and avoid repeating information unless clarification is needed.
            </rule>
            
            <rule id="knowledge_enrichment">
            You are encouraged to use your broader knowledge to enrich the student's understanding. This includes:
            - Providing real-world examples.
            - Using simple analogies and metaphors.
            - Explaining complex terms in a simpler way.
            This enrichment must ALWAYS be in service of explaining the <lesson_content>, not introducing new, unrelated topics.
            </rule>

            <rule id="interaction_protocol">
            Always be interactive. After providing an explanation, engage the student with a question to check for understanding or encourage critical thinking. For example: "Does that explanation clarify things for you?", "How would you apply this concept to a real-life situation?", or "What part of that is still unclear?". Consider the conversation flow from the chat history when asking follow-up questions.
            </rule>
            <rule id="answer_language">
                Use the language of the <user_question> to answer the user's question. Example: If user use english, answer in english. If user use chinese, answer in chinese.
            </rule>
        </rules>

        <workflow>
            1.  Analyze the user's question and review the <chat_history> for context.
            2.  Determine if the question is within the scope of <lesson_content>.
            3.  If it is out of scope, immediately execute the <prime_directive>.
            4.  If it is in scope, consider the conversation history and formulate a clear, step-by-step answer based on the <lesson_content>.
            5.  Enhance the answer using knowledge enrichment as defined in <rule id="knowledge_enrichment">.
            6.  Maintain conversation continuity by referencing previous discussion points when relevant.
            7.  Conclude your response by following the <rule id="interaction_protocol">.
            8.  Use the language of the <user_question> to answer the user's question <rule id="answer_language">.
        </workflow>

        <user_question>
        {user_question}
        </user_question>
    </prompt>
"""

evaluate_prompt = """
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

suggest_course_prompt = """
    ### ROLE ###
    You are a master at suggesting courses.

    ### TASK ###
    Suggest a course based on the user's quiz score. 
    If the user's quiz score is less than 50%, suggest a course that is easy to learn.
    If the user's quiz score is between 50% and 70%, suggest a course that is medium to learn.
    If the user's quiz score is greater than 70%, suggest a course that is harder to learn.
    Also, suggest a course that is related to the current course.


    ### OUTPUT FORMAT ###
    Your entire response MUST be a JSON object with the following keys:
    - **course_name**: The name of the course
    - **course_description**: The description of the course
    - **course_difficulty**: The difficulty level of the course
    - **reason**: The reason for the course suggestion. Give a in detail reason for the course suggestion to make the user understand why you suggest this course.

    ### OUTPUT EXAMPLE ###
"""

regenerate_lesson_prompt = """
### ROLE ###
You are an expert course content creator with 10+ years of experience in education. You specialize in creating engaging, comprehensive, and effective lesson content.

### TASK ###
Regenerate and improve a lesson based on the user's prompt/instructions. You must create updated lesson metadata and content while maintaining the lesson's core purpose within the course.

### CONTEXT ###
**Course Information:**
- Course Name: {course_name}
- Course Description: {course_description}
- Course Difficulty Level: {difficulty_level}

**Current Lesson Information:**
- Lesson Title: {lesson_title}
- Lesson Order: {lesson_order}
- Duration (hours): {duration_hours}
- Current Learning Objectives: {what_you_will_learn}

**Current Lesson Content:**
{current_content}

### USER'S EDIT REQUEST ###
{user_prompt}

### INSTRUCTIONS ###
1. Based on the user's request, regenerate the lesson with improved or modified content.
2. Maintain consistency with the course's difficulty level ({difficulty_level}).
3. The lesson content must:
   - Cover all topics thoroughly according to the difficulty level
   - Include at least 500 words (or enough content for the lesson duration)
   - Be structured with headings, subheadings, and examples
   - Include clear explanations, steps, case studies, or diagrams descriptions
   - End with a brief summary and 2-3 reflection questions
4. Keep the lesson relevant to the overall course objectives.
5. If the user requests specific changes, prioritize those while maintaining educational quality.

### CRITICAL MARKDOWN FORMATTING RULES ###
- ALWAYS add a blank line BEFORE every heading (##, ###, ####)
- ALWAYS add a blank line AFTER every heading
- ALWAYS add a blank line between paragraphs
- ALWAYS add a blank line before bullet lists or numbered lists

**CORRECT Example:**
```
This is a paragraph about the topic.

### 2.1 Section Title

This is the content of the section...

#### Key Points:

- Point 1
- Point 2
```

**WRONG Example (DO NOT DO THIS):**
```
This is a paragraph about the topic.### 2.1 Section Title
This is the content of the section...#### Key Points:- Point 1
```

### OUTPUT FORMAT ###
Return the regenerated lesson in the exact RegeneratedLessonOutput format with lesson metadata and lesson_contents.
"""

# Note: Agents and teams are now created per-request using create_team_for_request()
# This ensures concurrent users don't interfere with each other


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
        
        # Create a fresh team for this request (ensures concurrent user isolation)
        team = create_team_for_request(document_content, difficulty_level)
        
        # Run the team with a simple task prompt
        result = await team.run(task="Create the course based on the provided document and difficulty level.")
        
        for i in result.messages:
            print("--------------------------------")
            print("Agent: ",i.source)
            if i.source == "Expert_Agent":
                print("Content: ",i.content.dict())
            else:
                print("Content: ",i.content)
            print("--------------------------------")
        
        return result
    
    async def question_answer(self, lesson_content, user_question, chat_history=""):
        formatted_prompt = prompt.format(
            lesson_content=lesson_content,
            user_question=user_question,
            chat_history=chat_history
        )   
        messages = [
            HumanMessage(content=formatted_prompt)
        ]
        #print(formatted_prompt)
        result = gemini_client.invoke(messages)
        
        return result

    async def evaluate(self, question: str, model_answer: str, user_answer: str):
        output_client = gemini_client.with_structured_output(Grader)

        formatted_prompt = evaluate_prompt.format(question=question, model_answer=model_answer, user_answer=user_answer)
        messages = [
            HumanMessage(content=formatted_prompt)
        ]
        result = output_client.invoke(messages)
        return result.result
    
    async def suggest_course(self, course_name: str, course_description: str, course_difficulty: str):
        formatted_prompt = suggest_course_prompt.format(course_name=course_name, course_description=course_description, course_difficulty=course_difficulty)
        messages = [
            HumanMessage(content=formatted_prompt)
        ]
        result = gemini_client.invoke(messages)
        return result

    async def regenerate_lesson(
        self,
        course_name: str,
        course_description: str,
        difficulty_level: str,
        lesson_title: str,
        lesson_order: int,
        duration_hours: int,
        what_you_will_learn: List[str],
        current_content: str,
        user_prompt: str
    ):
        """
        Regenerate a single lesson based on user's edit request
        
        Args:
            course_name: Name of the course
            course_description: Description of the course
            difficulty_level: Difficulty level of the course
            lesson_title: Current title of the lesson
            lesson_order: Order of the lesson in the course
            duration_hours: Duration of the lesson
            what_you_will_learn: Current learning objectives
            current_content: Current lesson content
            user_prompt: User's request for changes
            
        Returns:
            RegeneratedLessonOutput with updated lesson and contents
        """
        output_client = gemini_client.with_structured_output(RegeneratedLessonOutput)
        
        formatted_prompt = regenerate_lesson_prompt.format(
            course_name=course_name,
            course_description=course_description,
            difficulty_level=difficulty_level,
            lesson_title=lesson_title,
            lesson_order=lesson_order,
            duration_hours=duration_hours,
            what_you_will_learn=what_you_will_learn,
            current_content=current_content,
            user_prompt=user_prompt
        )
        
        messages = [
            HumanMessage(content=formatted_prompt)
        ]
        
        result = output_client.invoke(messages)
        return result




# test = CreateCourse()
# asyncio.run(test.create_course())



