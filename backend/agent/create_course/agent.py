from crewai import Agent,Task,Crew,LLM
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from pydantic import BaseModel, Field
from typing import List,Literal
import json
from uuid import uuid4
from crewai.agents.agent_builder.base_agent import BaseAgent

def generate_uuid_string():
    return str(uuid4())

class Course(BaseModel):
    course_id: str = Field(description="The id of the course", default_factory=generate_uuid_string)
    course_name: str = Field(description="The name of the course")
    description: str = Field(description="The description of the course")
    total_hour: int = Field(description="The total hour of the course")
    status : Literal["Active","Inactive"] = Field(description="The status of the course")
    difficulty_level : Literal["Casual","Intermediate","Advanced"]
    learning_objectives : List[str]
    prerequisites : List[str]

class Lesson(BaseModel):
    course_id: str = Field(description="The id of the course", default_factory=generate_uuid_string)
    lesson_id: str = Field(description="The id of the lesson", default_factory=generate_uuid_string)
    lesson_title: str = Field(description="The title of the lesson")
    duration_hours: int = Field(description="The duration of the lesson in hours")
    lesson_order: int = Field(description="The order of the lesson in the course")
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
    


load_dotenv()
GEMINI_API_KEY=os.getenv("GOOGLE_API_KEY")
gemini_llm = LLM(
    model='gemini/gemini-2.0-flash',
    temperature=0.0
)
class CreateCourse(Crew):

    def __init__(self):
        pass
    
    def create_course(self,document_content:str=''):
        #Agent
        expert_agent = Agent(
            role="Create Course Agent",
            goal="Create a Coures , Lesson and Lesson Content for a given document",
            backstory="With over 10 years of experience in the field of education, you are a master at creating engaging and effective courses. You are also a master at creating lessons and lesson content that are engaging and effective. You are also a master at creating course outline that are engaging and effective.",
            tools=[],
            llm=gemini_llm
        )

        validator_agent = Agent(
            role="Validator Agent",
            goal="Validate the course, lesson and lesson content for a given document and provide feedback to the expert agent",
            backstory="With over 10 years of experience in the field of education, you are a master at validating courses, lessons and lesson content. You are also a master at validating course outline that are engaging and effective.",
            tools=[],
            llm=gemini_llm
        )




        #TASK
        expert_task = Task(
            description="""Create a course, lesson and lesson content for a given document
                The document is a pdf file that contains the course outline.
                use the document to create a course, lesson and lesson content.
                use external data(own knowledge) to fulfill the course, lesson and lesson content in case of data is not enough in the document.
                Here is the document content:
                {document_content}


                Return the output in the exact FinalOutput format with course, lessons, and lesson_contents.
            """,
            expected_output="""
            A structured course with lessons and lesson content in FinalOutput format, Output must be in json format not text.
            Every course must have at least 1 lesson and 1 lesson content.
            """,
            agent=expert_agent,
            output_pydantic=FinalOutput,
        )

        validator_task = Task(
            description="""from the course, lesson and lesson content created by the expert agent,
                Provide feedback on the quality, completeness, and educational value.
                Also check if the course, lesson and lesson content is in the FinalOutput format and every course must have at least 1 lesson and 1 lesson content.
            """,
            expected_output="Feedback and validation comments on the course structure and lesson content",
            agent=validator_agent,
            context=[expert_task]  # This task depends on expert_task output
        )



        crew = Crew(
            agents=[expert_agent, validator_agent],
            tasks=[expert_task, validator_task],
            verbose=True,
            max_rpm=15,
            output_log_file = 'crew_output.json'
            
        )

        crew_output = crew.kickoff()

        # Debug: Check what we actually got
        print("=== DEBUGGING CREW OUTPUT ===")
        print(f"crew_output type: {type(crew_output)}")
        print(f"json_dict: {crew_output.json_dict}")
        print(f"pydantic: {crew_output.pydantic}")
        print(f"raw type: {type(crew_output.raw)}")

        # Method 1: Get structured output from expert task specifically
        expert_task_output = None
        for task_output in crew_output.tasks_output:
            if hasattr(task_output, 'pydantic') and task_output.pydantic is not None:
                expert_task_output = task_output
                break

        if expert_task_output and expert_task_output.pydantic:
            # Convert the expert task's Pydantic output to dict
            result_dict = expert_task_output.pydantic.model_dump()
            print("\n=== SUCCESS: Dictionary from Expert Task Pydantic ===")
            print(f"Type: {type(result_dict)}")
            print(f"Course Name: {result_dict['course']['course_name']}")
            print(f"Number of Lessons: {len(result_dict['lessons'])}")
            print(f"Number of Lesson Contents: {len(result_dict['lesson_contents'])}")
            
            # You can now use result_dict as your main dictionary
            course_data = result_dict
            
        elif crew_output.json_dict:
            # Fallback to crew json_dict
            result_dict = crew_output.json_dict
            print("\n=== Dictionary from crew json_dict ===")
            print(f"Type: {type(result_dict)}")
            course_data = result_dict
            
        else:
            # Fallback to parsing raw output
            try:
                result_dict = json.loads(crew_output.raw)
                print("\n=== Dictionary from raw JSON ===")
                print(f"Type: {type(result_dict)}")
                course_data = result_dict
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error: Could not parse any structured output: {e}")
                course_data = None

        # Example usage of the dictionary
        if course_data:
            print(f"\n=== USING THE DICTIONARY ===")
            print(f"Course ID: {course_data['course']['course_id']}")
            print(f"Course Name: {course_data['course']['course_name']}")
            print(f"Total Hours: {course_data['course']['total_hour']}")
            print(f"Number of Lessons: {len(course_data['lessons'])}")
            

        return course_data