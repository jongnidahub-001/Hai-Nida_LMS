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

class Course(BaseModel):
    course_id: str = Field(description="The id of the course", default_factory=generate_uuid_string)
    course_name: str = Field(description="The name of the course")
    description: str = Field(description="The description of the course")
    total_hour: int = Field(description="The total hour of the course")
    status: Literal["Active", "Inactive"] = Field(description="The status of the course")
    difficulty_level: Literal["Casual", "Regular", "Intense"]
    learning_objectives: List[str]
    prerequisites: List[str]

class Lesson(BaseModel):
    course_id: str = Field(description="The id of the course", default_factory=generate_uuid_string)
    lesson_id: str = Field(description="The id of the lesson", default_factory=generate_uuid_string)
    lesson_title: str = Field(description="The title of the lesson")
    duration_hours: int = Field(description="The duration of the lesson in hours")
    lesson_order: int = Field(description="The order of the lesson in the course")
    description: str = Field(description="The description of the lesson")
    what_you_will_learn: List[str] = Field(description="The what you will learn in the lesson")

class LessonContent(BaseModel):
    lesson_id: str = Field(description="The id of the lesson", default_factory=generate_uuid_string)
    content_order: int = Field(description="The order of the content in the lesson")
    content_type: Literal["text", "video"] = Field(description="The type of the content only (text,video)")
    content: str = Field(description="The content of the lesson")

class FinalOutput(BaseModel):
    course: Course = Field(description="The course of the course")
    lessons: List[Lesson] = Field(description="The lessons of the course")
    lesson_contents: List[LessonContent] = Field(description="The lesson contents of the course")


# ============== NEW: Planner output models (P1-4) ==============

class LessonStub(BaseModel):
    lesson_title: str = Field(description="The title of the lesson")
    duration_hours: int = Field(description="The planned duration in hours")
    lesson_order: int = Field(description="The order of the lesson in the course")
    description: str = Field(description="Brief description of what this lesson covers")
    what_you_will_learn: List[str] = Field(description="Learning objectives for this lesson")
    relevant_doc_sections: str = Field(description="Description of which document sections/topics this lesson draws from")

class CourseOutline(BaseModel):
    course: Course = Field(description="The course metadata")
    lesson_stubs: List[LessonStub] = Field(description="Planned lessons with structure but no content yet")

# Writer output for a single lesson
class LessonWithContent(BaseModel):
    lesson_title: str = Field(description="The title of the lesson")
    duration_hours: int = Field(description="The duration in hours")
    lesson_order: int = Field(description="The order of the lesson")
    description: str = Field(description="Description of the lesson")
    what_you_will_learn: List[str] = Field(description="Learning objectives")
    contents: List[LessonContent] = Field(description="The full lesson content sections")


# ============== Other models (unchanged) ==============

class ValidationOutput(BaseModel):
    feedback: str = Field(description="The feedback on the course, lesson and lesson content")
    approved: Literal["APPROVE", "REJECT"] = Field(description="Whether the course, lesson and lesson content is approved")

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
    content_type: Literal["text", "video"] = Field(description="The type of the content only (text,video)")
    content: str = Field(description="The content of the lesson")

class RegeneratedLessonOutput(BaseModel):
    lesson: RegeneratedLesson = Field(description="The regenerated lesson")
    lesson_contents: List[RegeneratedLessonContent] = Field(description="The regenerated lesson contents")


# ============== Model client factories (P1-6: per-role) ==============

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

from gemini_config import get_model_for_role, get_gemini_api_key, get_gemini_model


def create_model_client(role: str = "writer"):
    """Create a new model client instance for a specific role.
    
    Args:
        role: One of 'planner', 'writer', 'grader'
    """
    return OpenAIChatCompletionClient(
        model=get_model_for_role(role),
        model_info=ModelInfo(vision=True, function_calling=True, json_output=True, family="unknown", structured_output=True),
        api_key=get_gemini_api_key(),
    )


def create_planner_client():
    """Create model client configured for the planner role (fast, cheap)."""
    return create_model_client("planner")


def create_writer_client():
    """Create model client configured for the writer role (creative, detailed)."""
    return create_model_client("writer")


def create_grader_client():
    """Create model client configured for the grader role."""
    return create_model_client("grader")


def _get_gemini_client(role: str = "writer"):
    """Get a LangChain Gemini client for a specific role."""
    return ChatGoogleGenerativeAI(
        model=get_model_for_role(role),
        api_key=get_gemini_api_key(),
    )


# ============== Stage 1: Planner Prompts (P1-5) ==============

planner_prompt = """
Role: You are a Course Structure Architect — an expert at designing well-organized course outlines.

Goal: Create a detailed course outline (structure only, NO full lesson content) based on the provided document. The outline should map document topics to lessons with appropriate time allocation.

Difficulty Level: **{difficulty_level}**

**Structure Guidelines by Difficulty:**
- CASUAL: 4-6 lessons, 1-2 hours each. Total 6-12 hours. 0-2 prerequisites. 3-5 learning objectives.
- REGULAR: 5-8 lessons, 2-3 hours each. Total 12-24 hours. 2-3 prerequisites. 5-8 learning objectives.
- INTENSE: 6-10 lessons, 3-4 hours each. Total 18-40 hours. 4+ prerequisites. 7-12 learning objectives.

**Instructions:**
1. Analyze the document structure and identify key topics/sections.
2. Group related topics into lessons with logical progression.
3. For each lesson, specify:
   - A clear title
   - Duration in hours (appropriate for difficulty)
   - Order number
   - Brief description (1-2 sentences)
   - 2-4 learning objectives
   - Which document sections/topics it draws from (relevant_doc_sections)
4. Ensure complete document coverage — no important topics left out.
5. Balance lesson sizes — avoid one lesson being 5x longer than another.
6. Set course-level metadata: name, description, total hours, objectives, prerequisites.

**Document Content (PRIMARY SOURCE):**
{document_content}

**SOURCE PRIORITY (CRITICAL):**
- The document above is the PRIMARY source. The course structure, topics, and lesson breakdown MUST be derived from the document's actual content and structure.
- Do NOT invent topics that are not present in the document.
- External knowledge may be used only to organize or label topics, not to add new subject matter.

Return the output in the exact CourseOutline format with course metadata and lesson_stubs.
"""

outline_reviewer_prompt = """
Role: You are a Course Outline Quality Reviewer.

Goal: Validate the course outline for completeness, balance, and educational soundness. Respond with 'APPROVE' when the outline is satisfactory. If not, provide specific feedback without including "APPROVE".

Difficulty Level: **{difficulty_level}**

**Validation Checklist:**
1. Coverage: Does the outline cover all major topics from the document?
2. Balance: Are lessons roughly balanced in scope (no single lesson >2x others)?
3. Progression: Do lessons flow logically (foundational → advanced)?
4. Time: Does total hours match difficulty guidelines?
   - CASUAL: 6-12 hours | REGULAR: 12-24 hours | INTENSE: 18-40 hours
5. Objectives: Are learning objectives specific and measurable?
6. Prerequisites: Appropriate for difficulty level?

If the outline passes all checks, respond with exactly: APPROVE
If not, explain what needs fixing (be concise).
"""


# ============== Stage 2: Writer Prompts (P2-1) ==============

lesson_writer_prompt = """
Role: You are a Lesson Content Writer — an expert at creating rich, engaging educational content.

Goal: Write the FULL content for ONE lesson based on the provided lesson plan and document section.

**Course Context:**
- Course: {course_name}
- Description: {course_description}
- Difficulty Level: **{difficulty_level}**

**Your Lesson Assignment:**
- Title: {lesson_title}
- Order: {lesson_order}
- Duration: {duration_hours} hours
- Description: {lesson_description}
- Learning Objectives: {what_you_will_learn}
- Relevant Document Sections: {relevant_doc_sections}

**Difficulty Level Content Guidelines:**
- CASUAL: Short sentences (10-15 words), simple vocabulary, analogies, 1-2 topics per content section. Target 300-400 words total. Focus on clarity over completeness. End with "What did you understand about X?"
- REGULAR: Medium sentences (15-25 words), case studies, 2-3 topics + connections. Target 500-700 words total. End with "How would you apply X in scenario Y?"
- INTENSE: Complex sentences (20-35 words), trade-offs, deep analysis, 3-4 topics. Target 700-1000 words total. End with "Compare X and Z. What are trade-offs?"

**Content Requirements:**
- Cover all topics listed in the lesson plan thoroughly
- Include at least the minimum word count for the difficulty level (CASUAL: 300, REGULAR: 500, INTENSE: 700)
- Structure with headings (##, ###), subheadings, and examples
- Include clear explanations, steps, case studies as appropriate
- End with a brief summary and 2-3 reflection questions

**CRITICAL MARKDOWN FORMATTING:**
- ALWAYS add a blank line BEFORE and AFTER every heading
- ALWAYS add a blank line between paragraphs and before lists
- Use ## and ### for section headings (NEVER use **bold** as a heading substitute)
- Use **bold** ONLY for emphasis within paragraphs (NOT for section titles)
- Reserve backticks only for actual code snippets or file paths
- WRONG: **Introduction to Topic** (this is NOT a heading)
- CORRECT: ## Introduction to Topic (this IS a heading)

**Document Content (PRIMARY SOURCE — use this for facts and key terms):**
{document_section}

**SOURCE PRIORITY (CRITICAL):**
- The document above is the PRIMARY source. All key terms, definitions, concepts, structure, and facts from the document MUST appear in the lesson content.
- Use external knowledge ONLY to: (1) fill gaps where the document lacks detail, (2) add examples or explanations that SUPPORT the document's content, (3) enrich lessons without replacing or omitting document content.
- Never replace or omit key content from the document with external information.

Return the output in the exact LessonWithContent format.
"""

lesson_reviewer_prompt = """
Role: You are a Lesson Content Quality Reviewer.

Goal: Validate the lesson content for quality, completeness, and formatting. Respond with 'APPROVE' when satisfactory. If not, provide specific feedback without including "APPROVE".

Difficulty Level: **{difficulty_level}**
Expected Lesson: {lesson_title} (Order: {lesson_order}, Duration: {duration_hours}h)

**Validation Checklist:**
1. Content covers all learning objectives specified
2. Depth matches difficulty level (CASUAL=simple, REGULAR=applied, INTENSE=analytical)
3. Meets minimum word count for difficulty (CASUAL: 300, REGULAR: 500, INTENSE: 700)
4. Proper markdown formatting (blank lines around headings, no backtick emphasis)
5. Ends with summary + reflection questions
6. Content is factually grounded in the document

If the content passes all checks, respond with exactly: APPROVE
If not, list specific issues to fix (be concise, max 3 points).
"""


# ============== Existing prompts (unchanged interfaces) ==============

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
            Always be interactive. After providing an explanation, engage the student with a question to check for understanding or encourage critical thinking.
            </rule>
            <rule id="answer_language">
                Use the language of the <user_question> to answer the user's question.
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
    Evaluate if the [User's Answer] is semantically and factually correct based on the provided [Model Answer]. Output "True" if correct, "False" if not.

    ### EVALUATION RULES ###
    1. Semantic Match: same meaning, not word-for-word.
    2. Key Concepts: must contain essential ideas from model answer.
    3. Leniency: minor spelling/grammar errors are OK.
    4. Completeness: must address all points if model answer has multiple.

    ### OUTPUT FORMAT ###
    Single word: "True" or "False". No explanation.

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
    If the user's quiz score is less than 50%, suggest an easy course.
    If between 50% and 70%, suggest a medium course.
    If greater than 70%, suggest a harder course.
    Also, suggest a course related to the current course.

    ### OUTPUT FORMAT ###
    JSON object with: course_name, course_description, course_difficulty, reason.
"""


regenerate_lesson_prompt = """
### ROLE ###
You are an expert course content creator with 10+ years of experience in education.

### TASK ###
Regenerate and improve a lesson based on the user's prompt/instructions.

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

### DIFFICULTY LEVEL GUIDELINES ({difficulty_level}) ###
- CASUAL: Short sentences (10-15 words), simple vocabulary, analogies, 1-2 topics.
- REGULAR: Medium sentences (15-25 words), case studies, "How would you apply X?"
- INTENSE: Complex sentences (20-35 words), trade-offs, deep analysis, "Compare X and Z."

### INSTRUCTIONS ###
1. Regenerate the lesson based on user's request.
2. Maintain difficulty level consistency.
3. Content must: cover topics thoroughly (500+ words), use proper headings, end with summary + reflection questions.
4. Use **bold** for emphasis, NOT backticks for key terms.
5. Proper markdown: blank lines around headings and before lists.

### OUTPUT FORMAT ###
Return in RegeneratedLessonOutput format with lesson metadata and lesson_contents.
"""


# ============== Pipeline Implementation ==============

@dataclass
class PipelineLog:
    """Represents a log entry from the pipeline for frontend display."""
    agent: str
    content: str
    stage: str  # "planning", "writing", "assembly"
    token_usage: Optional[dict] = None  # {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}


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


async def _run_planner(document_content: str, difficulty_level: str) -> tuple:
    """Stage 1: Plan the course outline.
    
    Returns:
        (CourseOutline, list of PipelineLog entries)
    """
    client = create_planner_client()
    
    formatted_planner = planner_prompt.format(
        document_content=document_content,
        difficulty_level=difficulty_level
    )
    formatted_reviewer = outline_reviewer_prompt.format(
        difficulty_level=difficulty_level
    )
    
    planner_agent = AssistantAgent(
        "planner_agent",
        model_client=client,
        system_message=formatted_planner,
        output_content_type=CourseOutline,
    )
    reviewer_agent = AssistantAgent(
        "outline_reviewer",
        model_client=client,
        system_message=formatted_reviewer,
    )
    
    text_termination = TextMentionTermination("APPROVE")
    max_msg_termination = MaxMessageTermination(max_messages=4)  # 2 rounds max
    
    team = RoundRobinGroupChat(
        [planner_agent, reviewer_agent],
        termination_condition=text_termination | max_msg_termination
    )
    
    result = await team.run(task="Create the course outline based on the provided document and difficulty level.")
    
    # Extract the outline from last planner output
    outline = None
    logs = []
    for msg in result.messages:
        usage = _extract_token_usage(msg)
        if msg.source == "planner_agent" and hasattr(msg.content, 'course'):
            outline = msg.content
            logs.append(PipelineLog(agent=msg.source, content=json.dumps(msg.content.dict(), ensure_ascii=False), stage="planning", token_usage=usage))
        else:
            content_str = msg.content if isinstance(msg.content, str) else json.dumps(msg.content.dict(), ensure_ascii=False)
            logs.append(PipelineLog(agent=msg.source, content=content_str, stage="planning", token_usage=usage))
    
    return outline, logs


async def _write_single_lesson(
    stub: LessonStub,
    course: Course,
    document_content: str,
    difficulty_level: str,
) -> tuple:
    """Write content for a single lesson (writer + reviewer pair).
    
    Returns:
        (LessonWithContent or None, list of PipelineLog entries)
    """
    client = create_writer_client()
    
    formatted_writer = lesson_writer_prompt.format(
        course_name=course.course_name,
        course_description=course.description,
        difficulty_level=difficulty_level,
        lesson_title=stub.lesson_title,
        lesson_order=stub.lesson_order,
        duration_hours=stub.duration_hours,
        lesson_description=stub.description,
        what_you_will_learn=", ".join(stub.what_you_will_learn),
        relevant_doc_sections=stub.relevant_doc_sections,
        document_section=document_content,  # full doc or routed section
    )
    formatted_reviewer = lesson_reviewer_prompt.format(
        difficulty_level=difficulty_level,
        lesson_title=stub.lesson_title,
        lesson_order=stub.lesson_order,
        duration_hours=stub.duration_hours,
    )
    
    writer_agent = AssistantAgent(
        f"lesson_writer_L{stub.lesson_order}",
        model_client=client,
        system_message=formatted_writer,
        output_content_type=LessonWithContent,
    )
    reviewer_agent = AssistantAgent(
        f"lesson_reviewer_L{stub.lesson_order}",
        model_client=client,
        system_message=formatted_reviewer,
    )
    
    text_termination = TextMentionTermination("APPROVE")
    max_msg_termination = MaxMessageTermination(max_messages=4)  # 2 rounds max
    
    team = RoundRobinGroupChat(
        [writer_agent, reviewer_agent],
        termination_condition=text_termination | max_msg_termination
    )
    
    result = await team.run(task=f"Write the full content for lesson {stub.lesson_order}: '{stub.lesson_title}'.")
    
    # Extract the lesson content from writer output
    lesson_content = None
    logs = []
    for msg in result.messages:
        usage = _extract_token_usage(msg)
        if msg.source.startswith("lesson_writer") and hasattr(msg.content, 'lesson_title'):
            lesson_content = msg.content
            logs.append(PipelineLog(
                agent=msg.source,
                content=f"Wrote lesson: {stub.lesson_title} ({len(msg.content.contents)} content sections)",
                stage="writing",
                token_usage=usage,
            ))
        else:
            content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
            logs.append(PipelineLog(agent=msg.source, content=content_str, stage="writing", token_usage=usage))
    
    return lesson_content, logs


async def _write_lessons_parallel(
    outline: CourseOutline,
    document_content: str,
    difficulty_level: str,
    progress_callback: Optional[Callable] = None,
) -> tuple:
    """Stage 2: Write all lessons in parallel.
    
    Uses document routing to send only relevant sections to each writer
    instead of the full document, reducing prompt tokens significantly.
    
    Returns:
        (list of LessonWithContent, list of PipelineLog entries)
    """
    from document_chunking import split_document_by_topics
    
    stubs = outline.lesson_stubs
    total = len(stubs)
    
    # Route document sections to individual writers (cost optimization)
    lesson_stubs_dicts = [{'relevant_doc_sections': s.relevant_doc_sections} for s in stubs]
    routed_sections = split_document_by_topics(document_content, lesson_stubs_dicts)
    
    async def write_with_retry(stub, doc_section):
        """Write a lesson with up to 2 retries on failure."""
        for attempt in range(3):
            try:
                result = await _write_single_lesson(stub, outline.course, doc_section, difficulty_level)
                if result[0] is not None:
                    return result
            except Exception as e:
                if attempt == 2:
                    # Final attempt failed — return None with error log
                    return None, [PipelineLog(
                        agent=f"lesson_writer_L{stub.lesson_order}",
                        content=f"Failed after 3 attempts: {str(e)[:200]}",
                        stage="writing"
                    )]
        return None, []
    
    # Run all lessons in parallel with routed document sections
    tasks = [write_with_retry(stub, routed_sections[i]) for i, stub in enumerate(stubs)]
    results = await asyncio.gather(*tasks)
    
    lessons = []
    all_logs = []
    for i, (lesson, logs) in enumerate(results):
        all_logs.extend(logs)
        if lesson is not None:
            lessons.append(lesson)
        if progress_callback:
            pct = 35 + int(40 * (i + 1) / total)
            progress_callback(f"Writing Lesson {i+1}/{total}: {stubs[i].lesson_title}", pct)
    
    return lessons, all_logs


def _assemble_final_output(outline: CourseOutline, lessons: List[LessonWithContent]) -> FinalOutput:
    """Stage 3: Assemble final output from outline + written lessons (deterministic, no LLM).
    
    Merges parallel writer outputs into a single FinalOutput matching the original schema.
    """
    course = outline.course
    course_id = course.course_id
    
    assembled_lessons = []
    assembled_contents = []
    
    # Sort lessons by order
    lessons_sorted = sorted(lessons, key=lambda l: l.lesson_order)
    
    for lesson_data in lessons_sorted:
        lesson_id = generate_uuid_string()
        
        assembled_lessons.append(Lesson(
            course_id=course_id,
            lesson_id=lesson_id,
            lesson_title=lesson_data.lesson_title,
            duration_hours=lesson_data.duration_hours,
            lesson_order=lesson_data.lesson_order,
            description=lesson_data.description,
            what_you_will_learn=lesson_data.what_you_will_learn,
        ))
        
        for content in lesson_data.contents:
            assembled_contents.append(LessonContent(
                lesson_id=lesson_id,
                content_order=content.content_order,
                content_type=content.content_type,
                content=content.content,
            ))
    
    return FinalOutput(
        course=course,
        lessons=assembled_lessons,
        lesson_contents=assembled_contents,
    )


# ============== Compatibility layer ==============
# The app.py expects result.messages with .source and .content attributes.
# We create a simple wrapper to maintain this interface.

@dataclass
class PipelineMessage:
    """Mimics autogen message interface for backward compatibility with app.py."""
    source: str
    content: object  # FinalOutput or str
    stage: str = ""  # "planning", "writing", "assembly"
    token_usage: Optional[dict] = None


@dataclass 
class PipelineResult:
    """Mimics TaskResult interface for backward compatibility with app.py."""
    messages: List[PipelineMessage]


class CreateCourse:
    def __init__(self):
        pass
    
    async def create_course(
        self,
        document_content: str = '',
        difficulty_level: str = 'Regular',
        progress_callback: Optional[Callable] = None,
    ):
        """
        Create a course using the multi-agent hierarchical pipeline.
        
        Pipeline: Planner → Parallel Writers → Assembler
        
        Args:
            document_content: The content of the document to create course from
            difficulty_level: 'Casual', 'Regular', or 'Intense'
            progress_callback: Optional (message, percent) callback for UI updates
            
        Returns:
            PipelineResult with .messages compatible with existing app.py processing
        """
        valid_difficulties = ['Casual', 'Regular', 'Intense']
        if difficulty_level not in valid_difficulties:
            raise ValueError(f"Invalid difficulty level. Must be one of: {valid_difficulties}")
        
        all_logs = []
        
        # Stage 1: Planning
        if progress_callback:
            progress_callback("Planning course outline...", 25)
        
        outline, planning_logs = await _run_planner(document_content, difficulty_level)
        all_logs.extend(planning_logs)
        
        if outline is None:
            raise RuntimeError("Planner failed to generate a valid course outline")
        
        if progress_callback:
            progress_callback("Outline approved", 30)
        
        # Stage 2: Parallel lesson writing
        if progress_callback:
            progress_callback(f"Writing {len(outline.lesson_stubs)} lessons in parallel...", 35)
        
        lessons, writing_logs = await _write_lessons_parallel(
            outline, document_content, difficulty_level, progress_callback
        )
        all_logs.extend(writing_logs)
        
        if not lessons:
            raise RuntimeError("All lesson writers failed to produce content")
        
        # Stage 3: Assembly
        if progress_callback:
            progress_callback("Assembling final output...", 80)
        
        final_output = _assemble_final_output(outline, lessons)
        
        all_logs.append(PipelineLog(
            agent="assembler",
            content=f"Final output assembled ({len(final_output.lessons)} lessons, {len(final_output.lesson_contents)} contents)",
            stage="assembly"
        ))
        
        if progress_callback:
            progress_callback("Validating...", 90)
        
        # Build backward-compatible result
        # app.py iterates messages looking for source=="Expert_Agent" with .content.dict()
        messages = []
        for log in all_logs:
            messages.append(PipelineMessage(source=log.agent, content=log.content, stage=log.stage, token_usage=log.token_usage))
        
        # Add the final output as "Expert_Agent" for backward compatibility
        messages.append(PipelineMessage(source="Expert_Agent", content=final_output, stage="assembly"))
        
        if progress_callback:
            progress_callback("Done", 100)
        
        return PipelineResult(messages=messages)


    async def question_answer(self, lesson_content, user_question, chat_history=""):
        formatted_prompt = prompt.format(
            lesson_content=lesson_content,
            user_question=user_question,
            chat_history=chat_history
        )
        messages = [HumanMessage(content=formatted_prompt)]
        result = _get_gemini_client("writer").invoke(messages)
        return result

    async def evaluate(self, question: str, model_answer: str, user_answer: str):
        output_client = _get_gemini_client("grader").with_structured_output(Grader)
        formatted_prompt = evaluate_prompt.format(
            question=question, model_answer=model_answer, user_answer=user_answer
        )
        messages = [HumanMessage(content=formatted_prompt)]
        result = output_client.invoke(messages)
        return result.result
    
    async def suggest_course(self, course_name: str, course_description: str, course_difficulty: str):
        formatted_prompt = suggest_course_prompt.format(
            course_name=course_name,
            course_description=course_description,
            course_difficulty=course_difficulty
        )
        messages = [HumanMessage(content=formatted_prompt)]
        result = _get_gemini_client("writer").invoke(messages)
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
        """Regenerate a single lesson based on user's edit request (interface unchanged)."""
        output_client = _get_gemini_client("writer").with_structured_output(RegeneratedLessonOutput)
        
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
        
        messages = [HumanMessage(content=formatted_prompt)]
        result = output_client.invoke(messages)
        return result
