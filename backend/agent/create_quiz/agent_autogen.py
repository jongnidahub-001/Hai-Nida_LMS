import asyncio
from dataclasses import dataclass
from typing import List, Literal, Optional, Callable

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import ExternalTermination, MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
import json
from uuid import uuid4
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

def generate_uuid_string():
    return str(uuid4())


# ============== Pydantic Models (backward compatible output) ==============

class Quiz(BaseModel):
    quiz_id: str = Field(description="The id of the quiz", default_factory=generate_uuid_string)
    course_id: str = Field(description="The id of the course")
    quiz_title: str = Field(description="The title of the quiz")
    status: Literal["Active", "Inactive"] = Field(description="The status of the quiz")
    description: str = Field(description="The description of the quiz")
    difficulty_level: Literal["Casual", "Regular", "Intense"] = Field(description="The difficulty level of the quiz")

class Question(BaseModel):
    question_id: str = Field(description="The id of the question", default_factory=generate_uuid_string)
    quiz_id: str = Field(description="The id of the quiz")
    question_text: str = Field(description="The text of the question")
    question_type: Literal["Multiple Choice", "Subjective", "Fill in the Blank"] = Field(description="The type of the question")
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


# ============== NEW: Planner output models (P3-1) ==============

class TopicAllocation(BaseModel):
    topic_name: str = Field(description="Name of the topic")
    num_multiple_choice: int = Field(description="Number of MC questions for this topic")
    num_subjective: int = Field(description="Number of subjective questions for this topic")
    num_fill_in_blank: int = Field(description="Number of fill-in-blank questions for this topic")
    relevant_content: str = Field(description="Key content from the document relevant to this topic")

class QuizBlueprint(BaseModel):
    quiz: Quiz = Field(description="The quiz metadata")
    topic_allocations: List[TopicAllocation] = Field(description="Topic-based question allocation plan")

# Writer output for a batch of questions per topic
class QuestionBatch(BaseModel):
    questions: List[Question] = Field(description="Questions generated for this topic")
    choices: List[Choice] = Field(description="Choices for MC questions")
    answers: List[Answer] = Field(description="Answers for all questions")


# ============== Other models (unchanged) ==============

class ValidationOutput(BaseModel):
    feedback: str = Field(description="Feedback on quiz quality")
    approved: Literal["APPROVE", "REJECT"] = Field(description="Whether the quiz is approved")

class RegeneratedQuestion(BaseModel):
    question_text: str = Field(description="The text of the question")
    question_type: Literal["Multiple Choice", "Subjective", "Fill in the Blank"] = Field(description="The type of the question")
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


# ============== Model client factories ==============

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
from gemini_config import get_model_for_role, get_gemini_api_key


def _create_model_client(role: str = "writer"):
    """Create a fresh model client for a specific role."""
    return OpenAIChatCompletionClient(
        model=get_model_for_role(role),
        model_info=ModelInfo(vision=True, function_calling=True, json_output=True, family="unknown", structured_output=True),
        api_key=get_gemini_api_key(),
    )


def _get_gemini_client(role: str = "writer"):
    """Get a LangChain Gemini client for a specific role."""
    return ChatGoogleGenerativeAI(
        model=get_model_for_role(role),
        api_key=get_gemini_api_key(),
    )


# ============== Quiz Planner Prompts (P3-1) ==============

quiz_planner_prompt = """
Role: You are a Quiz Architecture Planner — expert at designing comprehensive assessments.

Goal: Create a quiz blueprint that maps document topics to question allocations.

Difficulty Level: **{difficulty_level}**
Total Questions Required: {number_of_questions}
- Multiple Choice: {number_of_choices}
- Subjective: {number_of_subjective_questions}
- Fill in the Blank: {number_of_fill_in_the_blank_questions}

**Instructions:**
1. Analyze the document and identify 2-4 key topics/sections.
2. Allocate questions across topics proportionally to content importance.
3. Ensure total questions match the requested counts exactly.
4. For each topic, extract the relevant content that questions should be based on.
5. Set quiz metadata: title, description, difficulty_level, status="Active".
6. The quiz course_id should be set to a placeholder (will be assigned later).

**Document Content:**
{document_content}

Return the output in the exact QuizBlueprint format.
"""

quiz_planner_reviewer_prompt = """
Role: You are a Quiz Blueprint Reviewer.

Goal: Validate the quiz blueprint for completeness and balance. Respond with 'APPROVE' when satisfactory.

Difficulty Level: **{difficulty_level}**
Expected: {number_of_questions} total questions ({number_of_choices} MC, {number_of_subjective_questions} Subjective, {number_of_fill_in_the_blank_questions} Fill-in-Blank)

**Checklist:**
1. Total question counts match requirements exactly
2. Topics are distinct and cover major document sections
3. Question distribution is balanced (no single topic gets >60% of questions)
4. Relevant content is specific enough for question generation

If valid, respond: APPROVE
"""


# ============== Question Writer Prompts (P3-2) ==============

question_writer_prompt = """
Role: You are a Question Writer — expert at creating effective quiz questions.

Goal: Create questions for topic "{topic_name}" based on the provided content.

Difficulty Level: **{difficulty_level}**
Questions to create:
- Multiple Choice: {num_mc}
- Subjective: {num_subjective}
- Fill in the Blank: {num_fill}

**Difficulty Guidelines:**
- CASUAL: MC 10-20 words, direct from doc. Subjective: "What is X?" Fill: single keyword. Points 1-3.
- REGULAR: MC 25-40 words with scenario. Subjective: "How would you apply X?" Points 2-5.
- INTENSE: MC 40-70 words, complex scenario. Subjective: "Compare X and Z. Trade-offs?" Points 5-10.

**Rules:**
- For MC: exactly 4 choices, one correct answer
- All questions must be grounded in the provided content
- quiz_id will be assigned later (use placeholder)
- Each question needs appropriate point values for difficulty

**Topic Content (PRIMARY SOURCE):**
{topic_content}

Return the output in the exact QuestionBatch format with questions, choices, and answers.
"""

question_reviewer_prompt = """
Role: You are a Question Quality Reviewer.

Goal: Validate questions for accuracy, clarity, and difficulty-level match. Respond with 'APPROVE' when satisfactory.

Difficulty Level: **{difficulty_level}**
Topic: {topic_name}

**Checklist:**
1. All questions are clear and unambiguous
2. MC questions have exactly one correct answer and plausible distractors
3. Question complexity matches {difficulty_level} level
4. Point values are appropriate
5. Answers are factually correct based on source content

If all checks pass, respond: APPROVE
If not, list specific issues (max 3 points).
"""


regenerate_question_prompt = """
### ROLE ###
You are an expert quiz creator with 10+ years of experience in educational assessment.

### TASK ###
Regenerate and improve a quiz question based on the user's prompt/instructions.

### SOURCE DOCUMENT ###
{document_content}

### CONTEXT ###
- Quiz Title: {quiz_title}
- Quiz Description: {quiz_description}
- Difficulty Level: {difficulty_level}
- Question Type: {question_type}
- Question Text: {question_text}
- Points: {points}
- Current Choices: {current_choices}
- Current Answer: {current_answer}

### USER'S EDIT REQUEST ###
{user_prompt}

### INSTRUCTIONS ###
1. Regenerate based on user's request and SOURCE DOCUMENT.
2. Maintain difficulty level ({difficulty_level}) consistency.
3. Keep same question type ({question_type}) unless user requests change.
4. MC: exactly 4 choices, one correct. Subjective: clear question + answer. Fill: clear sentence with blank.

Return in RegeneratedQuestionOutput format.
"""


# ============== Pipeline Implementation (P3-1 through P3-4) ==============

@dataclass
class PipelineLog:
    """A log entry from the pipeline."""
    agent: str
    content: str
    stage: str  # "planning", "writing", "assembly"
    token_usage: Optional[dict] = None


def _extract_token_usage(msg) -> Optional[dict]:
    """Extract token usage from an autogen message if available."""
    usage = getattr(msg, 'models_usage', None)
    if usage is not None:
        prompt_t = getattr(usage, 'prompt_tokens', 0) or 0
        completion_t = getattr(usage, 'completion_tokens', 0) or 0
        return {
            'prompt_tokens': prompt_t,
            'completion_tokens': completion_t,
            'total_tokens': prompt_t + completion_t,
        }
    return None


@dataclass
class PipelineMessage:
    """Mimics autogen message interface for backward compatibility."""
    source: str
    content: object
    stage: str = ""
    token_usage: Optional[dict] = None


@dataclass
class PipelineResult:
    """Mimics TaskResult interface for backward compatibility."""
    messages: List[PipelineMessage]


async def _run_quiz_planner(
    document_content: str,
    difficulty_level: str,
    number_of_questions: int,
    number_of_choices: int,
    number_of_subjective_questions: int,
    number_of_fill_in_the_blank_questions: int,
) -> tuple:
    """Stage 1: Plan the quiz blueprint."""
    client = _create_model_client("planner")
    
    formatted_planner = quiz_planner_prompt.format(
        document_content=document_content,
        difficulty_level=difficulty_level,
        number_of_questions=number_of_questions,
        number_of_choices=number_of_choices,
        number_of_subjective_questions=number_of_subjective_questions,
        number_of_fill_in_the_blank_questions=number_of_fill_in_the_blank_questions,
    )
    formatted_reviewer = quiz_planner_reviewer_prompt.format(
        difficulty_level=difficulty_level,
        number_of_questions=number_of_questions,
        number_of_choices=number_of_choices,
        number_of_subjective_questions=number_of_subjective_questions,
        number_of_fill_in_the_blank_questions=number_of_fill_in_the_blank_questions,
    )
    
    planner_agent = AssistantAgent(
        "quiz_planner",
        model_client=client,
        system_message=formatted_planner,
        output_content_type=QuizBlueprint,
    )
    reviewer_agent = AssistantAgent(
        "quiz_planner_reviewer",
        model_client=client,
        system_message=formatted_reviewer,
    )
    
    text_term = TextMentionTermination("APPROVE")
    max_term = MaxMessageTermination(max_messages=4)
    
    team = RoundRobinGroupChat(
        [planner_agent, reviewer_agent],
        termination_condition=text_term | max_term
    )
    
    result = await team.run(task="Create the quiz blueprint based on the document.")
    
    blueprint = None
    logs = []
    for msg in result.messages:
        usage = _extract_token_usage(msg)
        if msg.source == "quiz_planner" and hasattr(msg.content, 'quiz'):
            blueprint = msg.content
            logs.append(PipelineLog(agent=msg.source, content="Quiz blueprint generated", stage="planning", token_usage=usage))
        else:
            content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
            logs.append(PipelineLog(agent=msg.source, content=content_str, stage="planning", token_usage=usage))
    
    return blueprint, logs


async def _write_questions_for_topic(
    topic: TopicAllocation,
    difficulty_level: str,
    topic_index: int,
) -> tuple:
    """Write questions for a single topic (writer + reviewer pair)."""
    client = _create_model_client("writer")
    
    formatted_writer = question_writer_prompt.format(
        topic_name=topic.topic_name,
        difficulty_level=difficulty_level,
        num_mc=topic.num_multiple_choice,
        num_subjective=topic.num_subjective,
        num_fill=topic.num_fill_in_blank,
        topic_content=topic.relevant_content,
    )
    formatted_reviewer = question_reviewer_prompt.format(
        difficulty_level=difficulty_level,
        topic_name=topic.topic_name,
    )
    
    writer_agent = AssistantAgent(
        f"question_writer_T{topic_index}",
        model_client=client,
        system_message=formatted_writer,
        output_content_type=QuestionBatch,
    )
    reviewer_agent = AssistantAgent(
        f"question_reviewer_T{topic_index}",
        model_client=client,
        system_message=formatted_reviewer,
    )
    
    text_term = TextMentionTermination("APPROVE")
    max_term = MaxMessageTermination(max_messages=4)
    
    team = RoundRobinGroupChat(
        [writer_agent, reviewer_agent],
        termination_condition=text_term | max_term
    )
    
    result = await team.run(task=f"Create questions for topic: '{topic.topic_name}'.")
    
    batch = None
    logs = []
    for msg in result.messages:
        usage = _extract_token_usage(msg)
        if msg.source.startswith("question_writer") and hasattr(msg.content, 'questions'):
            batch = msg.content
            logs.append(PipelineLog(
                agent=msg.source,
                content=f"Generated {len(msg.content.questions)} questions for '{topic.topic_name}'",
                stage="writing",
                token_usage=usage,
            ))
        else:
            content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
            logs.append(PipelineLog(agent=msg.source, content=content_str, stage="writing", token_usage=usage))
    
    return batch, logs


async def _write_questions_parallel(
    blueprint: QuizBlueprint,
    difficulty_level: str,
) -> tuple:
    """Stage 2: Write questions for all topics in parallel."""
    topics = blueprint.topic_allocations
    
    async def write_with_retry(topic, idx):
        for attempt in range(3):
            try:
                result = await _write_questions_for_topic(topic, difficulty_level, idx)
                if result[0] is not None:
                    return result
            except Exception as e:
                if attempt == 2:
                    return None, [PipelineLog(
                        agent=f"question_writer_T{idx}",
                        content=f"Failed after 3 attempts: {str(e)[:200]}",
                        stage="writing"
                    )]
        return None, []
    
    tasks = [write_with_retry(topic, i) for i, topic in enumerate(topics)]
    results = await asyncio.gather(*tasks)
    
    batches = []
    all_logs = []
    for batch, logs in results:
        all_logs.extend(logs)
        if batch is not None:
            batches.append(batch)
    
    return batches, all_logs


def _assemble_quiz_output(blueprint: QuizBlueprint, batches: List[QuestionBatch], target_counts: dict = None) -> FinalOutput:
    """Stage 3: Assemble final quiz output (deterministic, no LLM).
    
    Merges question batches, assigns consistent IDs, deduplicates,
    and enforces target question counts from user configuration.
    
    Args:
        blueprint: The quiz blueprint from planner
        batches: List of QuestionBatch from parallel writers
        target_counts: Optional dict with {number_of_questions, number_of_choices, 
                       number_of_subjective_questions, number_of_fill_in_the_blank_questions}
    """
    quiz = blueprint.quiz
    quiz_id = quiz.quiz_id
    
    all_questions = []
    all_choices = []
    all_answers = []
    
    seen_texts = set()  # For deduplication
    
    for batch in batches:
        for q in batch.questions:
            # Deduplicate by question text
            q_text_lower = q.question_text.lower().strip()
            if q_text_lower in seen_texts:
                continue
            seen_texts.add(q_text_lower)
            
            question_id = generate_uuid_string()
            all_questions.append(Question(
                question_id=question_id,
                quiz_id=quiz_id,
                question_text=q.question_text,
                question_type=q.question_type,
                points=q.points,
            ))
            
            # Find matching choices and answers by original question_id
            for choice in batch.choices:
                if choice.question_id == q.question_id:
                    all_choices.append(Choice(
                        choice_id=generate_uuid_string(),
                        question_id=question_id,
                        choice_text=choice.choice_text,
                        is_correct=choice.is_correct,
                    ))
            
            for answer in batch.answers:
                if answer.question_id == q.question_id:
                    all_answers.append(Answer(
                        answer_id=generate_uuid_string(),
                        question_id=question_id,
                        answer_text=answer.answer_text,
                    ))
    
    # Enforce target question counts if provided
    if target_counts:
        target_mc = target_counts.get('number_of_choices', 0)
        target_subj = target_counts.get('number_of_subjective_questions', 0)
        target_fill = target_counts.get('number_of_fill_in_the_blank_questions', 0)
        target_total = target_counts.get('number_of_questions', 0)
        
        # Separate questions by type
        mc_questions = [q for q in all_questions if q.question_type in ('choices', 'Multiple Choice')]
        subj_questions = [q for q in all_questions if q.question_type in ('subjective', 'Subjective')]
        fill_questions = [q for q in all_questions if q.question_type in ('fill', 'Fill in the Blank')]
        
        # Trim each type to target count
        if target_mc > 0:
            mc_questions = mc_questions[:target_mc]
        if target_subj > 0:
            subj_questions = subj_questions[:target_subj]
        if target_fill > 0:
            fill_questions = fill_questions[:target_fill]
        
        # Rebuild trimmed question list
        trimmed_questions = mc_questions + subj_questions + fill_questions
        
        # If still over total, trim from the end
        if target_total > 0 and len(trimmed_questions) > target_total:
            trimmed_questions = trimmed_questions[:target_total]
        
        # Filter choices and answers to only include kept questions
        kept_ids = {q.question_id for q in trimmed_questions}
        all_questions = trimmed_questions
        all_choices = [c for c in all_choices if c.question_id in kept_ids]
        all_answers = [a for a in all_answers if a.question_id in kept_ids]
    
    return FinalOutput(
        quiz=quiz,
        questions=all_questions,
        choices=all_choices,
        answers=all_answers,
    )


# ============== Main Class ==============

class CreateCourse:
    """Quiz creation class (named CreateCourse for backward compat with app.py import)."""
    
    def __init__(self):
        pass
    
    async def create_quiz(
        self,
        document_content: str = '',
        number_of_questions: int = 0,
        number_of_choices: int = 0,
        number_of_subjective_questions: int = 0,
        number_of_fill_in_the_blank_questions: int = 0,
        difficulty_level: str = 'Regular',
    ):
        """
        Create a quiz using the multi-agent hierarchical pipeline.
        
        Pipeline: QuizPlanner -> Parallel QuestionWriters -> QuizAssembler
        
        Returns:
            PipelineResult with .messages compatible with existing app.py processing
        """
        valid_difficulties = ['Casual', 'Regular', 'Intense']
        if difficulty_level not in valid_difficulties:
            raise ValueError(f"Invalid difficulty level. Must be one of: {valid_difficulties}")
        
        all_logs = []
        
        # Stage 1: Planning
        blueprint, planning_logs = await _run_quiz_planner(
            document_content=document_content,
            difficulty_level=difficulty_level,
            number_of_questions=number_of_questions,
            number_of_choices=number_of_choices,
            number_of_subjective_questions=number_of_subjective_questions,
            number_of_fill_in_the_blank_questions=number_of_fill_in_the_blank_questions,
        )
        all_logs.extend(planning_logs)
        
        if blueprint is None:
            raise RuntimeError("Quiz planner failed to generate a valid blueprint")
        
        # Stage 2: Parallel question writing
        batches, writing_logs = await _write_questions_parallel(blueprint, difficulty_level)
        all_logs.extend(writing_logs)
        
        if not batches:
            raise RuntimeError("All question writers failed to produce content")
        
        # Stage 3: Assembly (with target count enforcement)
        target_counts = {
            'number_of_questions': number_of_questions,
            'number_of_choices': number_of_choices,
            'number_of_subjective_questions': number_of_subjective_questions,
            'number_of_fill_in_the_blank_questions': number_of_fill_in_the_blank_questions,
        }
        final_output = _assemble_quiz_output(blueprint, batches, target_counts=target_counts)
        
        all_logs.append(PipelineLog(
            agent="assembler",
            content=f"Quiz assembled ({len(final_output.questions)} questions, {len(final_output.choices)} choices)",
            stage="assembly"
        ))
        
        # Build backward-compatible result
        messages = []
        for log in all_logs:
            messages.append(PipelineMessage(source=log.agent, content=log.content, stage=log.stage, token_usage=log.token_usage))
        
        # Add final output as "Expert_Agent" for backward compatibility
        messages.append(PipelineMessage(source="Expert_Agent", content=final_output, stage="assembly"))
        
        return PipelineResult(messages=messages)

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
        """Regenerate a single quiz question (interface unchanged)."""
        output_client = _get_gemini_client("writer").with_structured_output(RegeneratedQuestionOutput)
        
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
        
        messages = [HumanMessage(content=formatted_prompt)]
        result = output_client.invoke(messages)
        return result
