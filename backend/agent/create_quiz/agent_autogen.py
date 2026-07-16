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

class RegeneratedQuestion(BaseModel):
    question_text: str = Field(description="The text of the question")
    question_type: Literal["Multiple Choice","Subjective","Fill in the Blank"] = Field(description="The type of the question")
    points: int = Field(description="The points of the question")

class RegeneratedChoice(BaseModel):
    choice_text: str = Field(description="The text of the choice")
    is_correct: bool = Field(description="Whether the choice is correct")

class RegeneratedAnswer(BaseModel):
    answer_text: str = Field(description="The text of the answer")

class RegeneratedQuestionOutput(BaseModel):
    question: RegeneratedQuestion = Field(description="The regenerated question")
    choices: List[RegeneratedChoice] = Field(description="The regenerated choices (for Multiple Choice questions)")
    answers: List[RegeneratedAnswer] = Field(description="The regenerated answers")


GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
from gemini_config import get_gemini_model

# Create an OpenAI model client.
def _create_model_client():
    return OpenAIChatCompletionClient(
        model=get_gemini_model(),
        model_info=ModelInfo(vision=True, function_calling=True, json_output=True, family="unknown", structured_output=True),
        api_key=GEMINI_API_KEY,
    )

def _get_gemini_client():
    return ChatGoogleGenerativeAI(
        model=get_gemini_model(),
        api_key=GEMINI_API_KEY,
    )

# Module-level clients - use get_gemini_model() so config changes take effect on next request
model_client = _create_model_client()

primary_agent_prompt = """

Role: You are a master at creating engaging and effective quizzes. You are also a master at creating questions with appropriate choices and answers that are educational and challenging at different difficulty levels.

Goal: Create a comprehensive quiz with questions, choices, and answers based on a given document with the specified difficulty level: {difficulty_level}.

Backstory: With over 10 years of experience in the field of education and assessment, you are a master at designing comprehensive, well-structured quizzes that effectively test knowledge and understanding at various difficulty levels.

Instructions:
- Use the document to create a quiz with multiple questions covering the key topics.
- Create the quiz with the specified difficulty level: **{difficulty_level}**
- Create questions of different types: Multiple Choice, Subjective, and Fill in the Blank.
- Each question must be directly related to the content in the document and match the specified difficulty level.

**Difficulty Level Guidelines (STRICT – Must Be Visibly Harder Each Level):**

**CASUAL (Recall & Basic Understanding):**
- Bloom's: Remember + Understand only.
- Multiple Choice: Question 10-20 words. Correct answer is direct from document. Wrong answers are obviously wrong (definitions of unrelated terms).
- Subjective: "What is X?" or "Define X." Answer in 1-2 sentences. 1-2 points.
- Fill in the Blank: Single keyword from document. Strong context clues in sentence.
- Points: 1-3 per question. 70% of questions = recall.
- AVOID: Scenario-based questions, comparing options, multi-step reasoning.

**REGULAR (Application & Analysis):**
- Bloom's: Apply + Analyze.
- Multiple Choice: Question 25-40 words with a scenario. Correct answer requires understanding "how/when to use." Distractors are plausible but wrong for this scenario.
- Subjective: "In scenario Y, how would you apply X? Explain." Answer 2-4 sentences with reasoning. 2-4 points.
- Fill in the Blank: Term that requires understanding sentence context, not just keyword match.
- Points: 2-5 per question. Balance recall and application.
- AVOID: Trivial recall (Casual). Deep trade-off analysis (Intense).

**INTENSE (Evaluation & Synthesis):**
- Bloom's: Evaluate + Create.
- Multiple Choice: Question 40-70 words, complex scenario. Correct answer requires comparing options, eliminating wrong ones. All distractors are plausible; must reason to choose.
- Subjective: "Compare X and Z. What are trade-offs? When would you choose which? justify." Answer 4+ sentences, multiple factors. 4-6 points.
- Fill in the Blank: Phrase or term requiring synthesis of multiple concepts from context.
- Points: 5-10 per question. 50%+ questions = analysis/synthesis.
- AVOID: Definition-only questions. Simple scenario with obvious answer.

**CRITICAL:** Casual = answer in seconds. Regular = think 30+ seconds. Intense = think 1+ minute. If a Casual learner can answer an Intense question easily, it's not Intense.

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

**SOURCE PRIORITY (CRITICAL):**
- The document is the PRIMARY source. Questions, answers, and key terms MUST be grounded in the document content.
- Use external knowledge ONLY to enhance question quality when the document lacks sufficient detail - never replace or contradict document content.

Here is the number of questions you need to create: {number_of_questions}
here is the number of choices you need to create: {number_of_choices}
here is the number of Subjective questions you need to create: {number_of_subjective_questions}
here is the number of Fill in the Blank questions you need to create: {number_of_fill_in_the_blank_questions}

Here is the document content (PRIMARY SOURCE):
{document_content} 


Return the output in the exact FinalOutput format with quiz, questions, choices, and answers.

"""

critic_agent_prompt = """
    Role : You are a master at validating quizzes, questions, choices, and answers. You are an expert at ensuring quiz quality and correctness.
    Goal : Validate the quiz, questions, choices, and answers for accuracy and quality. Provide constructive feedback to the expert agent. Respond with 'APPROVE' (only in capital letters with no other text) when all questions and answers are correct and the quiz meets quality standards. If not, do not include "APPROVE" in your response. Only include "APPROVE" if the quiz, questions, and answers are all correct and approved.
    Backstory : With over 10 years of experience in educational assessment and quiz validation, you are a master at ensuring quiz accuracy, question clarity, and answer correctness.

    **Difficulty Level Validation (Check before APPROVE):**

    The quiz being validated has difficulty level: **{difficulty_level}**. Apply the appropriate checklist:

    For CASUAL quiz:
    - [ ] MC questions: short (10-20 words), direct from document
    - [ ] MC distractors: obviously wrong, not plausible
    - [ ] Subjective: "what is" or "define" only, short answer
    - [ ] Fill in the blank: single keyword with strong clues
    - [ ] Points: 1-3 per question
    - [ ] No scenario-based or comparison questions

    For REGULAR quiz:
    - [ ] MC questions: 25-40 words, scenario included
    - [ ] MC distractors: plausible but wrong for the scenario
    - [ ] Subjective: "how would you apply" with scenario, 2-4 sentences
    - [ ] Points: 2-5 per question
    - [ ] Mix of recall and application questions

    For INTENSE quiz:
    - [ ] MC questions: 40-70 words, complex multi-factor scenario
    - [ ] MC distractors: all plausible, requires elimination/reasoning
    - [ ] Subjective: "compare", "evaluate", "trade-offs", 4+ sentences
    - [ ] Points: 5-10 per question
    - [ ] Majority of questions require analysis/synthesis

    If any question could fit a lower difficulty (e.g., Intense question is answerable by recall), REJECT: "Question X does not match {difficulty_level}. Reason: [specific feedback]."

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

regenerate_question_prompt = """
### ROLE ###
You are an expert quiz creator with 10+ years of experience in educational assessment. You specialize in creating clear, effective, and appropriately challenging quiz questions.

### TASK ###
Regenerate and improve a quiz question based on the user's prompt/instructions. You must create an updated question with appropriate choices (for Multiple Choice) and answers.

### SOURCE DOCUMENT ###
Use this document content as the primary source of information for creating accurate questions and answers:

{document_content}

### CONTEXT ###
**Quiz Information:**
- Quiz Title: {quiz_title}
- Quiz Description: {quiz_description}
- Difficulty Level: {difficulty_level}

**Current Question Information:**
- Question Type: {question_type}
- Question Text: {question_text}
- Points: {points}
- Current Choices: {current_choices}
- Current Answer: {current_answer}

### USER'S EDIT REQUEST ###
{user_prompt}

### DIFFICULTY LEVEL GUIDELINES ({difficulty_level}) ###
- CASUAL: MC 10-20 words, answer from document, distractors obviously wrong. Subjective: "What is X?" 1-2 points. Fill: single keyword.
- REGULAR: MC 25-40 words with scenario, plausible distractors. Subjective: "How would you apply X?" 2-4 points.
- INTENSE: MC 40-70 words, complex scenario, all distractors plausible. Subjective: "Compare X and Z" 4-6 points.

### INSTRUCTIONS ###
1. Based on the user's request and the SOURCE DOCUMENT, regenerate the question with improved or modified content.
2. Ensure the question and answer are accurate based on the SOURCE DOCUMENT content.
3. Maintain consistency with the quiz's difficulty level ({difficulty_level}) per guidelines above.
4. Keep the same question type ({question_type}) unless user explicitly requests a change.
5. For Multiple Choice questions:
   - Provide exactly 4 choices with only one correct answer
   - Make distractors plausible but clearly incorrect based on the document
   - Ensure the correct answer is accurate according to the document
6. For Subjective questions:
   - Create a clear, unambiguous question
   - Provide a comprehensive expected answer based on the document
7. For Fill in the Blank questions:
   - Create a clear sentence with a blank
   - Provide the exact correct answer from the document
8. Assign appropriate point values based on difficulty and complexity.
9. If the user requests specific changes, prioritize those while maintaining question quality and accuracy.

### OUTPUT FORMAT ###
Return the regenerated question in the exact RegeneratedQuestionOutput format with question, choices (if applicable), and answers.
"""

# Define a termination condition that stops the task if the critic approves.
text_termination = TextMentionTermination("APPROVE")


def create_team_for_quiz_request(document_content: str, number_of_questions: int, number_of_choices: int, number_of_subjective_questions: int, number_of_fill_in_the_blank_questions: int, difficulty_level: str):
    """Create fresh agent team for each quiz request to ensure difficulty_level is passed to critic."""
    formatted_primary = primary_agent_prompt.format(
        document_content=document_content,
        number_of_questions=number_of_questions,
        number_of_choices=number_of_choices,
        number_of_subjective_questions=number_of_subjective_questions,
        number_of_fill_in_the_blank_questions=number_of_fill_in_the_blank_questions,
        difficulty_level=difficulty_level
    )
    formatted_critic = critic_agent_prompt.format(difficulty_level=difficulty_level)

    primary_agent = AssistantAgent(
        "Expert_Agent",
        model_client=model_client,
        system_message=formatted_primary,
        output_content_type=FinalOutput,
    )
    critic_agent = AssistantAgent(
        "Validator_Agent",
        model_client=model_client,
        system_message=formatted_critic,
    )
    team = RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=text_termination)
    return team


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

        team = create_team_for_quiz_request(
            document_content=document_content,
            number_of_questions=number_of_questions,
            number_of_choices=number_of_choices,
            number_of_subjective_questions=number_of_subjective_questions,
            number_of_fill_in_the_blank_questions=number_of_fill_in_the_blank_questions,
            difficulty_level=difficulty_level
        )

        result = await team.run(task="Create the quiz based on the provided document and difficulty level.")
        for i in result.messages:
            print("--------------------------------")
            print("Agent: ",i.source)
            if i.source == "Expert_Agent":
                print("Content: ",i.content.dict())
            else:
                print("Content: ",i.content)
            print("--------------------------------")
        
        return result

    async def regenerate_question(
        self,
        document_content: str,
        quiz_title: str,
        quiz_description: str,
        difficulty_level: str,
        question_type: str,
        question_text: str,
        points: int,
        current_choices: str,
        current_answer: str,
        user_prompt: str
    ):
        """
        Regenerate a single quiz question based on user's edit request
        
        Args:
            document_content: The original document content used to create the quiz
            quiz_title: Title of the quiz
            quiz_description: Description of the quiz
            difficulty_level: Difficulty level of the quiz
            question_type: Type of question (Multiple Choice, Subjective, Fill in the Blank)
            question_text: Current question text
            points: Current point value
            current_choices: Current choices as string (for Multiple Choice)
            current_answer: Current answer as string
            user_prompt: User's request for changes
            
        Returns:
            RegeneratedQuestionOutput with updated question, choices, and answers
        """
        output_client = _get_gemini_client().with_structured_output(RegeneratedQuestionOutput)
        
        formatted_prompt = regenerate_question_prompt.format(
            document_content=document_content,
            quiz_title=quiz_title,
            quiz_description=quiz_description,
            difficulty_level=difficulty_level,
            question_type=question_type,
            question_text=question_text,
            points=points,
            current_choices=current_choices,
            current_answer=current_answer,
            user_prompt=user_prompt
        )
        
        messages = [
            HumanMessage(content=formatted_prompt)
        ]
        
        result = output_client.invoke(messages)
        return result


# test = CreateCourse()
# asyncio.run(test.create_quiz(number_of_questions=10,number_of_choices=4,number_of_subjective_questions=2,number_of_fill_in_the_blank_questions=2))



