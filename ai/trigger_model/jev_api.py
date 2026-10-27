from typesafe_sdk import Noul, NoulCriteria, TypeSafeClient #jev API imports: use Noul for 0-1 if a moment is memorable or not



#function to call Jev API and handle if a moment is memorable or not.
def is_memorable_transcription(transcription):
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
            },
        )
        return response.answers["is_memorable"].noul



def main():
    edge_prbo_true = is_memorable_transcription("yeah no the game last night was insane, I can't believe they blew that lead in the fourth. oh hey before I forget, the spare key's under the blue planter by the back door, the landlord's coming at nine tomorrow so let him in. anyway did you see that last play, I was yelling at the TV")
    edge_prob_false = is_memorable_transcription("call now, this offer ends Friday at midnight. that's one eight hundred five five five zero one nine nine. don't miss your chance, the first fifty callers get a free upgrade, remember the deadline is Friday at midnight, call one eight hundred five five five zero one nine nine")
    
    def_prob_true = is_memorable_transcription("okay everyone, quick reminder before you go, the midterm is next Thursday the fourteenth at two pm in room 210, it covers chapters three through six, and you're allowed one handwritten page of notes, front and back")
    def_prob_false = is_memorable_transcription("hey how's it going, yeah good good, just tired honestly, it's been a long day, yeah same, cool cool, alright see you later")

    print(f"Edge True Value:{edge_prbo_true}\nEdge False Value:{edge_prob_false}")
    print(f"Definite True Value:{def_prob_true}\nDefinite False Value:{def_prob_false}")

    #note about the output (jev-latest, 2026-10-27): 
    #
    # Edge True Value:0.98
    # Edge False Value:0.98
    # Definite True Value:0.98
    # Definite False Value:0.05
    #
    # edge true: key info buried in small talk, caught as intended
    # edge false: TV ad, text alone can't show its background media, passes on to the expensive classifier (intended)
    # definite true: clear exam reminder, passes the 0.35 cutoff
    # definite false: small talk only, dropped at the 0.35 cutoff
    # all yes cases saturate at 0.98, so this score works as a keep/drop gate, not as an importance ranking



if __name__ == "__main__":
    main()
