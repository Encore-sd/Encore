#   jev_api.py: cheap first pass trigger, sends one transcript chunk to the model (Jev)
#   returns {"keep": bool, "confidence": float 0-1, "reason": str | None}, placeholder shape until SCRUM-48 sets the shared schema
#   requires TYPESAFE_API_KEY in ai/.env, run with: uv run --env-file .env ...
#   timeouts, rate limits and API errors are retried by the RetryPolicy, then caught here: keep is None and reason holds the error
#
#   known limitation: background media (TV ads, radio) can't be told apart from real speech using text alone, 
#   so it passes on to the expensive classifier

from typesafe_sdk import Choice, Noul, NoulCriteria, TypeSafeClient, RetryPolicy, TypeSafeError #jev API imports: use Noul for 0-1 if a moment is memorable or not, Choice for the reason

KEEP_THRESHOLD = 0.35 # low cutoff on purpose, only drop the definite no's, can be finetuned down the line
RetryPolicyObj = RetryPolicy(max_retries=3, backoff_max=0.2, timeout=1.0) # typesafe's recommended RetryPolicy parameters


#function to call Jev API and handle if a moment is memorable or not.
#returns keep/discard decision, confidence and reason, placeholder shape until the shared output schema (SCRUM-48) is set
def is_memorable_transcription(transcription):
    try:
        with TypeSafeClient() as client:
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
    # every TypeSafe exception inherits TypeSafeError, including the missing-key error raised when the client is created
    except TypeSafeError as exception:
        # keep is None so the segment does not continue to the KG if an exception is found
        return {
            "transcription_chunk": transcription,
            "keep": None,
            "confidence": None,
            "reason": f"An Exception was encountered during Classification: {exception}",
        }
    confidence = response.answers["is_memorable"].noul # grabs probability value
    keep = confidence >= KEEP_THRESHOLD 
    return {
        "transcription_chunk": transcription,
        "keep": keep,
        "confidence": confidence,
        "reason": response.answers["reason"].choice if keep else None,
    }

# TODO: update placeholder shape when shema is set
