#   jev_api.py: cheap first pass trigger, sends one transcript chunk to the model (Jev)
#   returns {"keep": bool, "confidence": float 0-1, "reason": str | None}, placeholder shape until SCRUM-48 sets the shared schema
#   requires TYPESAFE_API_KEY in ai/.env, run with: uv run --env-file .env ...
#   timeouts, rate limits and API errors are raised as TypeSafe exceptions, not caught here, so the fallback can handle them
#
#   known limitation: background media (TV ads, radio) can't be told apart from real speech using text alone, 
#   so it passes on to the expensive classifier
    
from typesafe_sdk import Choice, Noul, NoulCriteria, TypeSafeClient, RetryPolicy, TypeSafeNotFoundError, TypeSafeInternalServerError, TypeSafeRateLimitError, TypeSafeAuthenticationError, TypeSafePermissionDeniedError, TypeSafeUnprocessableEntityError, TypeSafeAPIResponseValidationError, TypeSafeBadRequestError, TypeSafeAPIConnectionError, TypeSafeAPITimeoutError, TypeSafeError #jev API imports: use Noul for 0-1 if a moment is memorable or not, Choice for the reason
import os
from transformers import pipeline

KEEP_THRESHOLD = 0.35 # low cutoff on purpose, only drop the definite no's, can be finetuned down the line
API_KEY = os.environ.get("TYPESAFE_API_KEY", "XAXAXAXAXAXAXAXAXAXAX") # Load the API Key for Typesafe's JEV (default is set to a nonsense string)
RetryPolicyObj = RetryPolicy(max_retries=3, backoff_max=0.2, timeout=1.0) # typesafe's recommended RetryPolicy parameters

temp_bool_str = os.environ.get("TRY_API_THEN_LOCAL", 'True')
if temp_bool_str == 'True' or temp_bool_str == 'False':
    TRY_API_THEN_LOCAL = True if temp_bool_str == 'True' else False
else:
    print(f'The .env value for TRY_API_THEN_LOCAL was entered incorrectly; Accepted values are "True" or "False"; True will be used until the server is launched with a valid .env value; The entered value was: {temp_bool_str}')
    TRY_API_THEN_LOCAL:bool = True

# routes between Local Trigger Model and API Trigger Model
def is_memorable_transcription(transcription):
    if TRY_API_THEN_LOCAL:
        api_response = is_memorable_transcription_api(transcription)
        if api_response.get('status') != 1:
            return is_memorable_transcription_local(transcription)
        return api_response
    else:
        return is_memorable_transcription_local(transcription)

#function to call Local Trigger Model and handle if a moment is memorable or not.
#returns keep/discard decision, confidence and reason, placeholder shape until the shared output schema (SCRUM-48) is set
def is_memorable_transcription_local(transcription):
    # NOTE: Is it good, not a clue. This is just the first model I found that could use the decision pipeline, didn't require external dependencies, and wasn't monstrously large (it's still big)
    model_pipeline = pipeline("decision", model="carrtesy/EXAONE-4.0-1.2B-JEV")
    response = model_pipeline(
        {
            "state": transcription, # what we want evaluated by the decision model, assumption: this is a string, though this could change
            "questions": {
                "is_memorable": {
                    "type": "noul", #stores a probability value between 0-1
                    "instructions": "The transcript contains something the speaker or listener may want to recall later.",
                    "criteria": { #why it leans closer to 0 or 1
                        "true": "The transcript contains specific, recallable information such as a plan, appointment, deadline, task, promise, instruction, decision, name, number, where an object was put, or something described as important (for example, 'this will be on the exam;').",
                        "false": "The transcript contains only small talk, greetings, filler, background TV or music, or unclear fragments with nothing specific to recall."
                    }
                },
                "reason": {
                    "type": "choice", #which kind of memorable info it is, only read when the Noul says keep
                    "instructions": "The kind of information in the transcript the speaker or listener may want to recall later.",
                    "criteria": { #structured options so neighbouring labels don't blur together
                        "event_or_deadline": {"covers": "appointments, exams, due dates, scheduled times", "excludes": "tasks with no set time"},
                        "task_or_commitment": {"covers": "something someone has to do or promised to do", "excludes": "general directions on how to do something"},
                        "instruction": {"covers": "directions, steps, rules or how to do something", "excludes": "a specific task assigned to someone"},
                        "object_location": {"covers": "where an object was put or can be found", "excludes": "where an event takes place"},
                        "fact_or_detail": {"covers": "names, numbers, decisions or other specific facts", "excludes": "dates and times of events"},
                        "flagged_important": {"covers": "someone explicitly says this matters, e.g. 'this will be on the exam'", "excludes": "anything not called out as important"},
                    }
                }
            }
        }
    )
        
    confidence = response.get("is_memorable").get('noul') # grabs probability value
    keep = confidence >= KEEP_THRESHOLD 
    return {
        "transcription_chunk": transcription,
        "keep": keep,
        "confidence": confidence,
        "reason": response.get("reason").get("choice") if keep else None,
        "status": 1,
        "error": "",
    }

#function to call Jev API and handle if a moment is memorable or not.
#returns keep/discard decision, confidence and reason, placeholder shape until the shared output schema (SCRUM-48) is set
def is_memorable_transcription_api(transcription):
    try:
        with TypeSafeClient(api_key=API_KEY) as client:
            try:
                response = client.system_one(
                    model = "jev-latest",
                    state = transcription, # what we want evaluated by JEV, assumption: this is a string, though this could change
                    questions = {
                        "is_memorable": Noul( #stores a probability value between 0-1
                            instructions= "The transcript contains something the speaker or listener may want to recall later.",
                            criteria= NoulCriteria( #why it leans closer to 0 or 1
                                true= "The transcript contains specific, recallable information such as a plan, appointment, deadline, task, promise, instruction, decision, name, number, where an object was put, or something described as important (for example, 'this will be on the exam;').",
                                false= "The transcript contains only small talk, greetings, filler, background TV or music, or unclear fragments with nothing specific to recall.",
                            ),
                        ),
                        "reason": Choice( #which kind of memorable info it is, only read when the Noul says keep
                            instructions= "The kind of information in the transcript the speaker or listener may want to recall later.",
                            criteria= { #structured options so neighbouring labels don't blur together
                                "event_or_deadline": {"covers": "appointments, exams, due dates, scheduled times", "excludes": "tasks with no set time"},
                                "task_or_commitment": {"covers": "something someone has to do or promised to do", "excludes": "general directions on how to do something"},
                                "instruction": {"covers": "directions, steps, rules or how to do something", "excludes": "a specific task assigned to someone"},
                                "object_location": {"covers": "where an object was put or can be found", "excludes": "where an event takes place"},
                                "fact_or_detail": {"covers": "names, numbers, decisions or other specific facts", "excludes": "dates and times of events"},
                                "flagged_important": {"covers": "someone explicitly says this matters, e.g. 'this will be on the exam'", "excludes": "anything not called out as important"},
                            },
                        ),
                    },
                    retry=RetryPolicyObj,
                )
            # All Typesafe Exceptions inherit TypeSafeAPIError so this will catch them all
            except TypeSafeError as exception:
                status_val = -1
                
                # 404 (TypeSafeNotFoundError), 5XX (TypeSafeInternalServerError): tell pipeline trigger model is unavailable, retry later (Server Down/not reachable):
                if isinstance(exception, TypeSafeNotFoundError): status_val = 2
                elif isinstance(exception, TypeSafeInternalServerError): status_val = 2
                # 429 (TypeSafeRateLimitError): Wait and try again (Too many requests at once, slow down)
                elif isinstance(exception, TypeSafeRateLimitError): status_val = 3
                # 401 (TypeSafeAuthenticationError), 403 (TypeSafePermissionDeniedError), 422 (TypeSafeUnprocessableEntityError): tell pipeline trigger model is unavailable (Permissions Issue)
                elif isinstance(exception, TypeSafeAuthenticationError):  status_val = 4
                elif isinstance(exception, TypeSafePermissionDeniedError): status_val = 4
                elif isinstance(exception, TypeSafeUnprocessableEntityError): status_val = 4
                # TypeSafeAPIResponseValidationError: retry (Typespace goofed up)
                elif isinstance(exception, TypeSafeAPIResponseValidationError): status_val = 5
                # 400 (TypeSafeBadRequestError): tell pipeline trigger model is unavailable and store the last request (we messed up the input)
                elif isinstance(exception, TypeSafeBadRequestError): status_val = 6
                # TypeSafeAPIConnectionError, TypeSafeAPITimeoutError: retry (typesafe took too long to respond)
                elif isinstance(exception, TypeSafeAPIConnectionError): status_val = 7
                elif isinstance(exception, TypeSafeAPITimeoutError): status_val = 7
                # Unknown TypeSafeError Exception type
                else: raise Exception(f"We haven't accounted for the following TypeSafeError error: ({type(exception)}): {exception}")
                
                return {"transcription_chunk": transcription, "keep": None, "confidence": None, "reason": None, "status": status_val, "error": exception}
            
    except TypeSafeError as exception:
        # API authentification error gets raised immediantly so the catches within client wouldn't catch it
        if type(exception) is TypeSafeError and "No API key was provided" in str(exception):
            return {"transcription_chunk": transcription, "keep": None, "confidence": None, "reason": None, "status": 4, "error": exception}
        else:
            print(f'Unknown Exception raised during TypeSafe client instantiation/running: {exception}')
            return None
    confidence = response.answers["is_memorable"].noul # grabs probability value
    keep = confidence >= KEEP_THRESHOLD 
    return {
        "transcription_chunk": transcription,
        "keep": keep,
        "confidence": confidence,
        "reason": response.answers["reason"].choice if keep else None,
        "status": 1,
        "error": "",
    }

# TODO: update placeholder shape when shema is set
