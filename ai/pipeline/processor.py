import importlib.util
from pathlib import Path
import threading
import queue
import time
import json

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

# Set up global variables
_thread_queue = queue.Queue()
_transcription_queue = queue.Queue()
_trigger_queue = queue.Queue()
_storage_queue = queue.Queue()
_thread_runner = None
_transcript_runner = None
_trigger_runner = None
_storage_runner = None
_loaded_processor, _loaded_model = transcriber.load_model_and_processor(surpress_network=False)

_shutdown_order_given:bool = False
_trigger_model_available:bool = True

_to_process_audio:list = []
_to_process_transcripts:list = []

_temp_storage_path = Path(__file__).resolve().parent / 'temp_storage_holder.txt'
_temp_audio_storage_path = Path(__file__).resolve().parent / 'temp_audio_storage_holder.txt'
_temp_audiofile_storage_path = Path(__file__).resolve().parent / 'temp_audiofile_storage_holder.txt'
_temp_transcript_storage_path = Path(__file__).resolve().parent / 'temp_transcript_storage_holder.json'

PRINT_DEBUG_LOGS:bool = False

def preprocess_audio_data(input):
    # TODO: in the future this will be changed to convert the data provided by the hardware into the format expected by transcription. Kind of. Sort of. Really depends.
    return input

def storage_worker():
    try:
        while True:
            storage_arr = _storage_queue.get()
            if PRINT_DEBUG_LOGS: print(f'storage_worker - got {storage_arr}')
            
            # TODO: We need to forward stuff to the backend here; for now, mark as done
            # for now, PURELY as a stopgap so we don't lose things/as debugging, we'll append the data to a file.
            with open(_temp_storage_path, 'a') as a_file:
                a_file.write(json.dumps(storage_arr, ensure_ascii=False) + '\n')
            if PRINT_DEBUG_LOGS: print(f'storage_worker - finished writing')
            
            _storage_queue.task_done()
    
    # need try/except, otherwise any exceptions won't actually show up due to being in a thread
    except Exception as e:
        raise RuntimeError(f'Error triggered in pipeline/processor.py - storage_worker(): {e}')

def store_waiting_data():
    # TODO: Switch out to backend database/dedicated storage area
    
    delimiter = '\n\n' + '---'*30 + '\nNot Processed\n' + '---'*30 + '\n\n'
    encoded_delimiter = delimiter.encode('utf-8')
    
    global _to_process_audio
    byte_arr = []
    file_arr = []
    for arr in _to_process_audio:
        if arr[1] == 'byte':
            byte_arr.append(arr[0])
        else:
            file_arr.append(arr[0])
    
    if len(byte_arr) > 0:
        byte_arr = encoded_delimiter.join(_to_process_audio)
        with open(_temp_audio_storage_path, 'wb') as w_file:
            w_file.write(byte_arr)

    if len(file_arr) > 0:
        with open(_temp_audiofile_storage_path, 'w') as w_file:
            w_file.write('\n'.join(file_arr))
            
    if len(_to_process_transcripts) > 0:
        with open(_temp_transcript_storage_path, 'w') as w_file:
            json.dump(_to_process_transcripts, w_file)

def load_waiting_data():
    # load in what we couldn't process in another run;
    # TODO: pull from backend database instead of loose files
    
    delimiter = '\n\n' + '---'*30 + '\nNot Processed\n' + '---'*30 + '\n\n'
    encoded_delimiter = delimiter.encode('utf-8')
    if _temp_audio_storage_path.exists():
        loaded_bytes = []
        with open(_temp_audio_storage_path, 'rb') as r_file:
            loaded_bytes = r_file.read().split(encoded_delimiter)
        with open(_temp_audio_storage_path, 'wb') as w_file:
            w_file.write('')
        for arr in loaded_bytes:
            if len(arr) < 1:
                continue
            _transcription_queue.put([arr, 'byte'])
            
    if _temp_audiofile_storage_path.exists():
        with open(_temp_audiofile_storage_path, 'r') as r_file:
            cnt = r_file.read()
            cnt = cnt.split('\n')
            for item in cnt:
                if len(item) > 0:
                    _transcription_queue.put([item, 'file'])
        with open(_temp_audiofile_storage_path, 'w') as w_file:
            w_file.write('')

    if _temp_transcript_storage_path.exists():
        temp_arr = []
        with open(_temp_transcript_storage_path, 'r') as r_file:
            temp_arr = json.load(r_file)
        with open(_temp_transcript_storage_path, 'w') as w_file:
            w_file.write('[]')
        for item in temp_arr:
            _trigger_queue.put(item)
        

def trigger_worker():
    try:
        api_error_flag = False
        api_error_count = 0
        api_error_shutdown_threshold = 5
        global _to_process_transcripts
        global _trigger_model_available
        while True:
            transcript_dict = _trigger_queue.get()
            if PRINT_DEBUG_LOGS: print('Entered trigger_worker while loop')
            
            if _shutdown_order_given:
                # flag it as done 
                if PRINT_DEBUG_LOGS: print('Entered trigger_worker shutdown conditional')
                _trigger_queue.task_done()
                _to_process_transcripts.append(transcript_dict)
            else:
                if PRINT_DEBUG_LOGS: print('Entered trigger_worker normal-section')
                info_dict = {}
                if transcript_dict.get('error_present') or not transcript_dict.get('has_transcript'):
                    # discard empty transcriptions and ones that errored out in the process
                    _trigger_queue.task_done()
                    if PRINT_DEBUG_LOGS: print('trigger_worker says transcript is empty or has error')
                else:
                    if not _trigger_model_available:
                        if PRINT_DEBUG_LOGS: print('_trigger_model_available says trigger model is unavailable')
                        _trigger_queue.task_done()
                        _to_process_transcripts.append(transcript_dict)
                    else:
                        if PRINT_DEBUG_LOGS: print('_trigger_model_available says trigger model is available')
                        try:
                            # If our last api call had an error, lets wait a bit
                            # TODO: Revisit when handling Jev-API Exceptions
                            if api_error_flag:
                                if PRINT_DEBUG_LOGS: print('stepped into api sleep time')
                                time.sleep(10)
                                api_error_flag = False
                            if PRINT_DEBUG_LOGS: print('trigger_worker asking if transcript is memorable')
                            decision_output = trigger_model.is_memorable_transcription(transcript_dict.get('transcript_string'))
                            #decision_output =  {
                            #    "transcription_chunk": transcript_dict.get('transcript_string'),
                            #    "keep": True,
                            #    "confidence": 0.70,
                            #    "reason": 'flagged_important',
                            #}
                            
                            info_dict = {'transcript_string': transcript_dict.get('transcript_string'), 'start_time': transcript_dict.get('start_time'), 'end_time': transcript_dict.get('end_time'), 'confidence': decision_output.get('confidence')}
                            if decision_output.get('keep'):
                                if PRINT_DEBUG_LOGS: print('transcript is memorable')
                                info_dict['reason'] = decision_output.get('reason')
                            else:
                                # keep the full info incase we decide later down the road that the classifier is wrong; We can discern said not memorable transcripts by if they were marked with None as their reason as kept transcripts always have reason set to a string; Possibly turn this into a user flag where they can decide to automatically toss not-memorable transcripts or keep them around for review
                                if PRINT_DEBUG_LOGS: print('transcript is not memorable')
                                info_dict['reason'] = None
                            
                            api_error_count = 0
                            _trigger_queue.task_done()
                            _storage_queue.put(info_dict)
                        # TODO: Change exception catcher in future to each of the different Jev-Api Exceptions; For now we'll just make the next Jev-Api task sleep for a bit
                        except Exception as e:
                            if PRINT_DEBUG_LOGS: print(f'trigger_worker api section had an exception: {e}')
                            api_error_flag = True
                            api_error_count += 1
                            
                            # flag the api model as unavailable
                            if api_error_count >= api_error_shutdown_threshold:
                                _trigger_model_available = False
                                if PRINT_DEBUG_LOGS: print(f'trigger_worker api exception counter has passed threshold')
                            
                            _trigger_queue.task_done() # mark 'done' and then put it back in the queue
                            _trigger_queue.put(transcript_dict)
                            
    # need try/except, otherwise any exceptions won't actually show up due to being in a thread
    except Exception as e:
        raise RuntimeError(f'Error triggered in pipeline/processor.py - trigger_worker(): {e}')
                      
def transcription_worker():
    try:
        while True:
            packed_arr = _transcription_queue.get()
            input = packed_arr[0]
            mode = packed_arr[1]
            if PRINT_DEBUG_LOGS: print(f'transcription_worker has recieved a {mode} task')
            if _shutdown_order_given:
                # flag it as done 
                if PRINT_DEBUG_LOGS: print(f'entered transcription_worker shutdown conditional')
                _transcription_queue.task_done()
                global _to_process_audio
                _to_process_audio.append([input, mode])
            
            else:
                if PRINT_DEBUG_LOGS: print(f'transcription_worker calling transcription')
                if mode == 'byte':
                    returned_transcript_dict = transcriber.transcribe(input, already_loaded_model=_loaded_model, already_loaded_processor=_loaded_processor)
                else:
                    # mode must be file then
                    returned_transcript_dict = transcriber.transcribe_audio_files(input, already_loaded_model=_loaded_model, already_loaded_processor=_loaded_processor)
                if PRINT_DEBUG_LOGS: print(f'transcription_worker finished transcription')
                
                # bundle into list so we can handle batch and single calls easily
                if not isinstance(returned_transcript_dict, list):
                    returned_transcript_dict = [returned_transcript_dict]
                _transcription_queue.task_done()
                
                # split them up into seperate trigger-model calls
                for item in returned_transcript_dict:
                    _trigger_queue.put(item)
            
    # need try/except, otherwise any exceptions won't actually show up due to being in a thread
    except Exception as e:
        raise RuntimeError(f'Error triggered in pipeline/processor.py - transcription_worker(): {e}')

def primary_worker():
    # Idea: we create two seperate queues -> transcription and trigger model. 
    # Each transcription adds to the trigger model queue; trigger model can add back to itself if it errors
    # finished at trigger -> queue for storage
    
    try:
        while True:
            raw_bytes = _thread_queue.get()
            if PRINT_DEBUG_LOGS: print(f'primary_worker recieved raw data')
            raw_bytes = preprocess_audio_data(raw_bytes) # overwrite raw_bytes because we don't need to keep the raw_bytes around once they're preprocessed
            _transcription_queue.put(raw_bytes)
            _thread_queue.task_done()
    
    # need try/except, otherwise any exceptions won't actually show up due to being in a thread
    except Exception as e:
        raise RuntimeError(f'Error triggered in pipeline/processor.py - primary_worker(): {e}')
                
def set_up_pipeline():
    global _thread_runner, _transcript_runner, _trigger_runner, _storage_runner, _shutdown_order_given
    if _thread_runner is None or not _thread_runner.is_alive():
        _thread_runner = threading.Thread(target=primary_worker, name="primary_worker", daemon=True)
        _thread_runner.start()
    if _transcript_runner is None or not _transcript_runner.is_alive():
        _transcript_runner = threading.Thread(target=transcription_worker, name="transcription_worker", daemon=True)
        _transcript_runner.start()
    if _trigger_runner is None or not _trigger_runner.is_alive():
        _trigger_runner = threading.Thread(target=trigger_worker, name="trigger_worker", daemon=True)
        _trigger_runner.start()
    if _storage_runner is None or not _storage_runner.is_alive():
        _storage_runner = threading.Thread(target=storage_worker, name="storage_worker", daemon=True)
        _storage_runner.start()
    if PRINT_DEBUG_LOGS: print(f'All threads spun up')
    load_waiting_data()
    if PRINT_DEBUG_LOGS: print(f'All waiting data loaded')
    _shutdown_order_given = False

def await_queues():
    _thread_queue.join()
    _transcription_queue.join()
    _trigger_queue.join()
    _storage_queue.join()
    if PRINT_DEBUG_LOGS: print(f'All tasks done')
    

def close_pipeline():
    global _shutdown_order_given
    _shutdown_order_given = True
    if PRINT_DEBUG_LOGS: print(f'Shutdown order given')
    await_queues()
    
    store_waiting_data()
    if PRINT_DEBUG_LOGS: print(f'Pipeline finished closing')

def add_transcription_task(input, mode='byte'):
    # Take 'byte' or 'file'
    if mode == 'byte':
        _thread_queue.put([input, mode])
    else:
        _transcription_queue.put([input, mode])

def main():
    # side note, I've found KeyboardInterrupt hasn't really been getting caught -> could be due to earlier issues I had with the threads/queues, but if you test, you may need to manually close the terminal window to end the script if something goes wrong
    
    # this is mainly if you want to test things, stick a path to an audio file in the commented out add_transcription_task function call and uncomment it and then run this file
    global PRINT_DEBUG_LOGS
    PRINT_DEBUG_LOGS = True
    set_up_pipeline()
    
    #add_transcription_task([r"PlaceALocalFilePathHere"], mode='file')
    
    try:
        await_queues()
        
        close_pipeline()
    except KeyboardInterrupt:
        print('KeyboardInterrupt triggered, exiting')
        close_pipeline()
    PRINT_DEBUG_LOGS = False

if __name__ == '__main__':
    main()