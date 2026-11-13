import importlib.util
from pathlib import Path
import threading
import queue
import time
import json

# will be removed in future after API Exceptions are handled, for now, used to randomly throw exceptions during different stages / mimic the decision model taking a while (without actually sending a request to the decision model)
import random

# Import ../transcription/transcriber.py
transcriber_path = (Path(__file__).resolve()).parent.parent / 'transcription' / 'transcriber.py'
module_spec = importlib.util.spec_from_file_location('transcriber', transcriber_path)
transcriber = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(transcriber)

# Import ../trigger_model/jev_api.py
trigger_path = (Path(__file__).resolve()).parent.parent / 'trigger_model' / 'jev_api.py'
module_spec = importlib.util.spec_from_file_location('trigger_model', trigger_path)
trigger_model = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(trigger_model)

# Initialise Global Variables that all the threads can access
_active_threads = []
_global_variable_thread_lock = threading.Lock()
_trigger_model_available:bool = True
_api_error_flag:bool = False
_api_error_count:int = 0
_temp_storage_path = Path(__file__).resolve().parent / 'temp_storage_holder.txt'
_loaded_processor, _loaded_model = transcriber.load_model_and_processor(surpress_network=False)

# Initialise Constants; Will need tuning/tweaking based on how things are set up
CHECK_FOR_OPEN_THREAD_EVERY_X_SECONDS:int = 1
API_ERRORS_UNTIL_UNAVILABLE:int = 3
MAX_PIPELINES:int = 3
PRINT_DEBUG_LOGS:bool = False
EXCEPTION_TESTING:bool = False

def run_pipeline_thread(input, is_file_upload:bool=False, thread_id:int=-1):
    global _api_error_count
    global _trigger_model_available
    global _api_error_flag
    
    if thread_id != -1:
        identifier = f' Thread-{thread_id}:'
    else:
        identifier = ''
    
    returned_transcript_dict = {}
    try:
        if EXCEPTION_TESTING:
            excep = random.randint(0, 10)
            if excep < 5:
                raise Exception('Random Transcription Error Triggered')
        
        if not is_file_upload:
            if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Preprocessing Audio-Bytes')
            raw_bytes = preprocess_audio_data(input)
            if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Beginning Transcription of Bytes')
            returned_transcript_dict = transcriber.transcribe(raw_bytes, already_loaded_model=_loaded_model, already_loaded_processor=_loaded_processor)
        else:
            if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Beginning Transcription of Files')
            returned_transcript_dict = transcriber.transcribe_audio_files(input, already_loaded_model=_loaded_model, already_loaded_processor=_loaded_processor)
    except Exception as e:
        print(f'Transcription Exception: [{identifier} {e}]')
        if not is_file_upload:
            pass_back_audio(input)
        else:
            pass_back_audiofile(input)
        return
    
    if not isinstance(returned_transcript_dict, list):
        if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Wrapping Transcript_Dict into a List')
        returned_transcript_dict = [returned_transcript_dict]
    for transcript_dict in returned_transcript_dict:
        if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Beginning Classification process for Transcript')
        if transcript_dict.get('error_present') or not transcript_dict.get('has_transcript'):
            if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Transcript had an error or doesnt have a transcript')
            continue
        
        current_error_count = 0
        with _global_variable_thread_lock:
            current_error_count = _api_error_count
        
        info_dict = {}
        success:bool = False
        while not success and current_error_count < API_ERRORS_UNTIL_UNAVILABLE:
            told_to_sleep:bool = False
            told_model_not_available:bool = False
            with _global_variable_thread_lock:
                if not _trigger_model_available:
                    told_model_not_available = True
                if _api_error_flag:
                    if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Sleeping before trying Decision Model due to prior api-error')
                    told_to_sleep = True
            
            if told_model_not_available:
                if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Decision Model was unavailable for classification')
                break
                    
            if told_to_sleep:
                time.sleep(10)
            
            try:
                if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Passing Transcript to Decision Model for classification')
                if EXCEPTION_TESTING:
                    time.sleep(random.randint(0, 10))
                    decision_output =  {
                        "transcription_chunk": transcript_dict.get('transcript_string'),
                        "keep": True,
                        "confidence": 0.70,
                        "reason": 'flagged_important',
                    }
                else:
                    decision_output = trigger_model.is_memorable_transcription(transcript_dict.get('transcript_string'))
                
                info_dict = {'transcript_string': transcript_dict.get('transcript_string'), 'start_time': transcript_dict.get('start_time'), 'end_time': transcript_dict.get('end_time'), 'confidence': decision_output.get('confidence')}
                if decision_output.get('keep'):
                    info_dict['reason'] = decision_output.get('reason')
                    if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Keeping Transcription')
                else:
                    # keep the full info incase we decide later down the road that the classifier is wrong; We can discern said not memorable transcripts by if they were marked with None as their reason as kept transcripts always have reason set to a string; Possibly turn this into a user flag where they can decide to automatically toss not-memorable transcripts or keep them around for review
                    info_dict['reason'] = None
                    if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Tossing Transcription')
                    
                if EXCEPTION_TESTING:
                    random_excep = random.randint(0, 10)
                    if random_excep < 7:
                        raise RuntimeError(f'Random Classification Exception Triggered')
                    
                with _global_variable_thread_lock:
                    _api_error_flag = False
                    _api_error_count = 0
                    
                success = True
                break
                    
            except Exception as e:
                print(f'Classification Exception: [{identifier} {e}]')
                with _global_variable_thread_lock:
                    _api_error_flag = True
                    _api_error_count += 1
                    current_error_count = _api_error_count
                    if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} API Error Count at: {_api_error_count}')
                
                    if _api_error_count >= API_ERRORS_UNTIL_UNAVILABLE:
                        _trigger_model_available = False
                        if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Max Threshold reached for API Error Count; Flagging Trigger Model as unavailable')
                    else:
                        if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Running it back through Pipeline')

            else:
                if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Failed to classify transcript')
            
        if success:
            if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Saving Classification and Transcription')
            save_data(info_dict)
            
            #TODO: continue with embedding + extraction
            pass
        else:
            if PRINT_DEBUG_LOGS: print(f'[DEBUG]{identifier} Failed to classify transcript')
            pass_back_transcript(transcript_dict)
            
def pass_back_audio(input):
    # ...from_failed_transcription
    truncated_input = []
    if len(input) > 0 and isinstance(input[0], list):
        for item in input:
            truncated_input.append(f'[{item[:32]}...]')
        truncated_input = '[' + ', '.join(truncated_input) + ']'
    else:
        truncated_input = f'[{input[:32]}...]'
    
    if PRINT_DEBUG_LOGS: print(f'[DEBUG]: Passed back bytes {truncated_input} due to failing to classify the transcription.')
    
    # probably add input to a queue with as a dictionary with the exception + the input + the stage it failed at (transcription)
    pass
    
def pass_back_audiofile(input):
    # ...from_failed_transcription
    if PRINT_DEBUG_LOGS: print(f'[DEBUG]: Passed back file(s) {input} due to an exception during Transcription')
    
    # probably add input to a queue with as a dictionary with the exception + the input + the stage it failed at (transcription)
    pass
    
def pass_back_transcript(input):
    # ...from_failed_classification
    if PRINT_DEBUG_LOGS: print(f'[DEBUG]: Passed back transcript_dict {input} due to failing to classify the transcription.')
    
    # probably add input to a queue with as a dictionary with the exception + the input + the stage it failed at (classification)
    pass
        
def save_data(input):
    # currently storing only so you can verify classification is working/see schema of dictionaries
    with _global_variable_thread_lock:
        with open(_temp_storage_path, 'a') as a_file:
            a_file.write(json.dumps(input, ensure_ascii=False) + '\n')

def preprocess_audio_data(input):
    # TODO: in the future this will be changed to convert the data provided by the hardware into the format expected by transcription. Kind of. Sort of. Really depends.
    return input


def update_active_threads():
    global _active_threads
    
    with _global_variable_thread_lock:
        active_threads = []
        for thread in _active_threads:
            if thread.is_alive():
                active_threads.append(thread)
        _active_threads = active_threads
        
def is_thread_available(max_threads:int=MAX_PIPELINES):
    update_active_threads()
    
    with _global_variable_thread_lock:
        if len(_active_threads) < max_threads:
            return True
        return False
        
        

class ShutdownObject:
    def __init__(self):
        self.shutdown_order_given:bool = False
    
def route_to_available_thread(input, shutdown_object:ShutdownObject, is_file_upload:bool=False, thread_id:int=-1, ):
    while not is_thread_available() and not shutdown_object.shutdown_order_given:
        try:
            time.sleep(CHECK_FOR_OPEN_THREAD_EVERY_X_SECONDS)
        except KeyboardInterrupt:
            shutdown_object.shutdown_order_given = True
    if shutdown_object.shutdown_order_given: 
        if PRINT_DEBUG_LOGS: print('[DEBUG] Shutdown Order Given')
        return -1
        
    global _active_threads
    with _global_variable_thread_lock:
        thread = threading.Thread(
            target=run_pipeline_thread, 
            args=(input,), 
            kwargs={"is_file_upload": is_file_upload, "thread_id": thread_id}
        )
        _active_threads.append(thread)
        thread.start()
    
    return 0


def main():
    # this is mainly if you want to test things, stick audio files in ../ai/tests/fixtures and then run this file; Just a simple example of using the pipeline
    global PRINT_DEBUG_LOGS
    global EXCEPTION_TESTING
    PRINT_DEBUG_LOGS = True
    EXCEPTION_TESTING = True
    from tqdm.auto import tqdm
    
    files = [str(file) for file in Path('./tests/fixtures').resolve().rglob('*') if file.suffix in ['.mp3', '.mp4', '.wav', '.webm']]
    shutdown_obj:ShutdownObject = ShutdownObject()
    thread_number = 1
    for file in tqdm(files, desc='processing...'):
        temp_return = route_to_available_thread(file, shutdown_object=shutdown_obj, is_file_upload=True, thread_id=thread_number, )
        if temp_return == -1:
            # so shutdown went through (however it is you desire to handle that-- currently KeyboardInterrupt but probably a thread monitoring something on backend/frontend), this current input and anything later in the loop have not been processed
            break
        
        thread_number += 1
    unprocessed = files[thread_number-1:] # minus 1 to switch to 0-index
    if PRINT_DEBUG_LOGS: print(f'[DEBUG] Shutdown Order leaves {unprocessed} unprocessed')

if __name__ == '__main__':
    main()