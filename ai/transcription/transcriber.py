import os
from pathlib import Path
import numpy as np
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from typing import Union

CACHE_DIR = (Path(__file__).resolve()).parent.parent / 'models'
os.environ['HF_HOME'] = str(CACHE_DIR)

DEFAULT_BATCH_SIZE = 1


def load_model_and_processor(surpress_network:bool=False) -> tuple[WhisperProcessor, WhisperForConditionalGeneration]:
    processor = WhisperProcessor.from_pretrained("openai/whisper-base.en", cache_dir=CACHE_DIR, local_files_only=surpress_network)
    model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-base.en", cache_dir=CACHE_DIR, local_files_only=surpress_network)
    return processor, model

def process_samples(whisper_processor:WhisperProcessor, sample_arr:list, full:bool=False):
    if full:
        processed = whisper_processor(sample_arr, truncation=False, padding="longest", sampling_rate=16_000, return_tensors="pt", return_attention_mask=True)
    else:
        processed = whisper_processor(sample_arr, sampling_rate=16_000, return_tensors="pt", return_attention_mask=True)
    return processed.input_features, processed.attention_mask

def generate_from_processed_samples(model:WhisperForConditionalGeneration, proc_samples, proc_mask):
    return model.generate(
        proc_samples, 
        return_timestamps=True, # need timestamps
        # return_segments=True, # going to be set to true anyways, due to return_timestamps and return_dict_in_generate, so set to true to surpress log message - disabled, this does not infact surpress the log message
        #task='transcribe', # only accepts transcribe and translate; we're transcribing - disabled cause throws an error if is_multilingual is false
        #language='<|en|>', # base.en is an english model - disabled cause throws an error if is_multilingual is false
        is_multilingual=False, # base.en is not multilingual
        condition_on_prev_tokens=True, # According to Transformer docs for Whisper, 'this can help to improve performance' on long duration transcription
        temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0], # According to Transformer docs for Whisper, temperature fallback improves WER%
        compression_ratio_threshold=1.35, # According to Transformer docs for Whisper, 'A common value for compression_ratio_threshold is 1.35. As shown in the the Whisper paper, this can help to improve performance.'
        attention_mask=proc_mask,
        # forced_decoder_ids=None, # changing forced_decoder_ids doesn't seem to be surpressing the log message
        return_dict_in_generate=True
    )

def decode_generated_ids(whisper_processor:WhisperProcessor, generated_ids):
    # generated Ids is a torch.Tensor, but can't type hint without importing torch
    return whisper_processor.batch_decode(
        generated_ids, 
        skip_special_tokens=True, 
        clean_up_tokenization_spaces=False, # Default is true but Transformers skips this regardless because it is 'destructive for BPE'; Could enable by doing 'clean_up_tokenization_spaces_for_bpe_even_though_it_will_corrupt_output=True'
    )


def reformat_byte_arr(byte_arr):
    # Makes sure byte_arr is in list[list[np.ndarry[np.float32, np.float32, ...], int, int], ...] format
    if isinstance(byte_arr, np.ndarray):
        byte_arr = [[byte_arr, 0.0, -1]]
    elif isinstance(byte_arr, list) and len(byte_arr) == 1:
        if isinstance(byte_arr[0], np.ndarray):
            byte_arr = [[byte_arr[0], 0.0, -1]]
        elif len(byte_arr[0]) == 1:
            if isinstance(byte_arr[0], np.ndarray):
                byte_arr = [[byte_arr[0], 0.0, -1]]
            elif isinstance(byte_arr[0], list):
                if len(byte_arr[0]) == 1:
                    if isinstance(byte_arr[0][0], np.ndarray):
                        byte_arr = [[byte_arr[0][0], 0.0, -1]]
                    else:
                        raise RuntimeError('reformat_byte_arr: Foxtrot-Unplanned Encounter-Foxtrot')
                elif len(byte_arr[0]) == 2:
                    if isinstance(byte_arr[0][0], np.ndarray) and (isinstance(byte_arr[0][1], int) or isinstance(byte_arr[0][1], float)):
                        byte_arr = [[byte_arr[0][0], byte_arr[0][1], byte_arr[0][1]]]
                    else:
                        raise RuntimeError('reformat_byte_arr: Hotel-Unplanned Encounter-Hotel')
                elif len(byte_arr[0]) == 3:
                    if isinstance(byte_arr[0][0], np.ndarray) and (isinstance(byte_arr[0][1], int) or isinstance(byte_arr[0][1], float)) and (isinstance(byte_arr[0][2], int) or isinstance(byte_arr[0][2], float)):
                        pass
                    else:
                        raise RuntimeError('reformat_byte_arr: Igloo-Unplanned Encounter-Igloo')
                else:
                    raise RuntimeError('reformat_byte_arr: Juliet-Unplanned Encounter-Juliet')
            else:
                raise RuntimeError('reformat_byte_arr: Bravo-Unplanned Encounter-Bravo')
        elif len(byte_arr[0]) == 2:
            if isinstance(byte_arr[0][0], np.ndarray) and (isinstance(byte_arr[0][1], int) or isinstance(byte_arr[0][1], float)):
                byte_arr = [[byte_arr[0][0], byte_arr[0][1], byte_arr[0][1]]]
            else:
                raise RuntimeError('reformat_byte_arr: Charlie-Unplanned Encounter-Charlie')
        elif len(byte_arr[0]) == 3:
            if isinstance(byte_arr[0][0], np.ndarray) and (isinstance(byte_arr[0][1], int) or isinstance(byte_arr[0][1], float)) and (isinstance(byte_arr[0][2], int) or isinstance(byte_arr[0][2], float)):
                byte_arr = [[byte_arr[0][0], byte_arr[0][1], byte_arr[0][2]]]
            else:
                raise RuntimeError('reformat_byte_arr: Delta-Unplanned Encounter-Delta')
        else:
            raise RuntimeError('reformat_byte_arr: Echo-Unplanned Encounter-Echo')
    elif isinstance(byte_arr, list) and len(byte_arr) > 1:
        if len(byte_arr) == 2 and isinstance(byte_arr[0], np.ndarray) and (isinstance(byte_arr[1], int) or isinstance(byte_arr[1], float)):
            byte_arr = [[byte_arr[0], byte_arr[1], byte_arr[1]]]
        elif len(byte_arr) == 3 and isinstance(byte_arr[0], np.ndarray) and (isinstance(byte_arr[1], int) or isinstance(byte_arr[1], float)) and (isinstance(byte_arr[2], int) or isinstance(byte_arr[2], float)):
            byte_arr = [byte_arr]
        else:
            for index in range(len(byte_arr)):
                if isinstance(byte_arr[index], np.ndarray):
                    byte_arr[index] = [byte_arr[index], 0.0, -1]
                elif isinstance(byte_arr[index], list):
                    if len(byte_arr[index]) == 1 and isinstance(byte_arr[index][0], np.ndarray):
                        byte_arr[index] = [byte_arr[index][0], 0.0, -1]
                    elif len(byte_arr[index]) == 2:
                        byte_arr[index] = [byte_arr[index][0], byte_arr[index][1], byte_arr[index][1]]
                    elif len(byte_arr[index]) == 3:
                        pass
                    elif len(byte_arr[index]) > 3:
                        byte_arr[index] = [byte_arr[index][0], byte_arr[index][1], byte_arr[index][2]]
                else:
                    raise RuntimeError('reformat_byte_arr: Unplanned Encounter')
    else:
        raise RuntimeError('reformat_byte_arr: Alpha-Unplanned Encounter-Alpha')
    return byte_arr

def split_into_subchunks(byte_arr:Union[tuple[np.ndarray[np.float32], int, int], list[tuple[np.ndarray[np.float32], int, int]]], chunk_duration:int=30) -> tuple[list, dict]:
    # accepts:
    # list[list[np.ndarry[np.float32, np.float32, ...], int, int], list[np.ndarry[np.float32, np.float32, ...], int, int]]
    # list[list[np.ndarry[np.float32, np.float32, ...], int], list[np.ndarry[np.float32, np.float32, ...], int]]
    # list[list[np.ndarry[np.float32, np.float32, ...]], list[np.ndarry[np.float32, np.float32, ...]]
    # list[list[np.ndarry[np.float32, np.float32, ...], int, int]]
    # list[list[np.ndarry[np.float32, np.float32, ...], int]]
    # list[list[np.ndarry[np.float32, np.float32, ...]]]
    # list[np.ndarry[np.float32, np.float32, ...], np.ndarry[np.float32, np.float32, ...]]
    # list[np.ndarry[np.float32, np.float32, ...], int, int]
    # list[np.ndarry[np.float32, np.float32, ...], int]
    # np.ndarry[np.float32, np.float32, ...]
    
    byte_arr = reformat_byte_arr(byte_arr)
    
    real_byte_arr = []
    clip_id_dict = {}
    sample_bytes = 16_000 * chunk_duration # <- the number of bytes in 30 seconds sampled at 16000 bytes a second; Whisper expects 16K bytes/second sampling rate
    for index in range(len(byte_arr)):
        chunk_arr = byte_arr[index]
        # chunk_arr is: audio_bytes, capture_time, user_id
        
        bytes = chunk_arr[0]
        for index2 in range(0, len(bytes), sample_bytes):
            clip_id_dict[index] = [chunk_arr[1], chunk_arr[2], index] # Store the info related to the chunk, ie capture time, user id, and an integer correlating to the chunk so we don't store it multiple times
            real_byte_arr.append([bytes[index2:index2+sample_bytes], index2, index]) # track the actual bytes, the *order* of each subchunk, and the chunk it corresponds to
    
    return real_byte_arr, clip_id_dict

def process_subchunked_audio(real_byte_arr:list, processor:WhisperProcessor, model:WhisperForConditionalGeneration, batch_size:int=8) -> dict:
    running_pred = {}
    for index in range(0, len(real_byte_arr), batch_size):
        in_times_batchsize = index*batch_size
        batch = real_byte_arr[in_times_batchsize:in_times_batchsize+batch_size] # get only the bytes for this batch
        gathered_bytes = [arr[0] for arr in batch] # pull out anything that isn't a byte so we can hand it to the processor
        proced_samples, proced_attn_mask = process_samples(processor, gathered_bytes)
        pred = generate_from_processed_samples(model, proced_samples, proced_attn_mask)
        pred_segments = pred.get('segments') # we only care about segments, all other keys aren't needed
        
        for index2 in range(len(batch)):
            clip_id = real_byte_arr[index+index2][2] # id of initial (whole) byte array (ie, the audio chunk)
            chunk_id = real_byte_arr[index+index2][1] # id of 30s chunk of initial byte array (ie, a subchunk of the audio chunk)
            if clip_id not in running_pred:
                running_pred[clip_id] = []
            # store chunk_id first so we can sort the subchunks in ascending order so they go from start to finish instead of scrambled order
            running_pred[clip_id].append([chunk_id, pred_segments[index2], len(gathered_bytes[index2])])
    return running_pred
    
def decode_subchunked_audio(running_pred:list, clip_id_dict:dict, processor:WhisperProcessor, capture_offset:float=0.0, chunk_duration:int=30) -> list | dict:
    end_result_arr = []
    for clip_id in running_pred:
        clip_info_arr = clip_id_dict.get(clip_id)
        clip_prediction_arr = running_pred.get(clip_id)
        clip_prediction_arr.sort() # sort by the chunkids so they're in order in case they somehow got scrambled
        capture_offset = clip_info_arr[0]
        
        ac_prediction_arr = []
        min_time = float('inf')
        max_time = 0
        total_bytes = 0
        error_string = []
        
        # final_str = []
        for index in range(len(clip_prediction_arr)):
            inner_offset = index*chunk_duration # audio may have been subchunked into multiple 30s subchunks; so we need to offset the timestamp values by the subchunkid
            #true_offset = inner_offset + capture_offset
            chunk_id, segment_dict, processed_byte_number = clip_prediction_arr[index]
            if processed_byte_number == 0:
                error_string.append(f'decode_subchunked_audio was passed an empty array of bytes for the {index}th subchunk of audio for this chunk! There is no audio in this subchunk!')
            
            total_bytes += processed_byte_number
            last_pred = []
            for timestamped_segment_arr in segment_dict:
                start_time = float(timestamped_segment_arr.get('start') + inner_offset)
                end_time = float(timestamped_segment_arr.get('end') + inner_offset)
                tokens = timestamped_segment_arr.get('tokens') # these are the tokens covered by this timestamp segment
                max_time = max(max_time, end_time)
                min_time = min(min_time, start_time)
                temp = decode_generated_ids(processor, tokens)
                ac_prediction_arr.append(temp[0].strip()) # remove spaces from the edges, we'll be joining them later
                
                # old format for phrase/sentence-level timestamping
                # ac_prediction_arr.append({'timestamp': [float(start_time), float(end_time)], 'transcription': transcriber.decode_generated_ids(processor, tokens)[0].strip()})
                # final_str.append(ac_prediction_arr[-1].get('transcription'))
                
        min_time += capture_offset
        max_time += capture_offset
        
        if (max_time - min_time) * 16_000 > total_bytes:
            error_string.append('Bytes from Audio does not align with calculated Bytes from Generation; Audio has been hallucinated where there was no audio')

        
        error_string = 'Error: '' | Error: '.join(error_string) if len(error_string) > 1 else ''
        
        # old format for phrase/sentence-level timestamping
        #end_result_arr.append({'user_id': clip_info_arr[1], 'capture_time': clip_info_arr[0], 'time_stamped_transcript': ac_prediction_arr, 'transcript_string': ' '.join(final_str)})
        
        end_result_arr.append({'start_time': min_time, 'end_time': max_time, 'user_id': clip_info_arr[1], 'capture_time': clip_info_arr[0], 'transcript_string': ' '.join(ac_prediction_arr), 'error_string':error_string})
    
    # add error-flag/has_transcript flag;
    for result_arr in end_result_arr:
        result_error_string = result_arr.get('error_string')
        result_arr['error_present'] = True if len(result_error_string) > 0 else False
        result_arr['error_string'] = 'Error: ' + ' | Error: '.join(result_error_string) if len(result_error_string) > 0 else ''
        
        if len(result_arr.get('transcript_string').strip()) < 1:
            result_arr['has_transcript'] = False
        else:
            result_arr['has_transcript'] = True
    
    end_result_arr_len = len(end_result_arr)
    if end_result_arr_len != len(clip_id_dict):
        print("Bizzare mismatch that's likely going to be an issue? Number of transcripts doesn't equate to the number of clips")
    
    if end_result_arr_len > 1:
        return end_result_arr
    elif end_result_arr_len == 1:
        return end_result_arr[0]
    else:
        raise Exception(f'No resultant transcription; ClipIdDict was: {clip_id_dict} and RunningPred was: {running_pred}')
    

def transcribe(byte_arr:list, capture_time:int=0, batch_size:int=DEFAULT_BATCH_SIZE, surpress_network_access:bool=False, already_loaded_processor:WhisperProcessor=None, already_loaded_model:WhisperForConditionalGeneration=None) -> list | dict:
    # accepts any of the formats listed in the comments of split_into_subchunks() for byte_arr
    # surpress_network_access tells .from_pretrained to not check huggingface for modelW; will error out if model isn't present in CACHE_DIR with surpress_network_access set to true

    # will return one dict in format of:
    # start_time: int, end_time: int, capture_time: float, user_id: str, capture_time: float, transcript_string: str, error_string: str, error_present: bool, has_transcript: bool
    # If more than one array of bytes is provided (ie list, this will be a list of that ^ dictionary
    # you can specify a user_id/capture time (instead of doing that later) which is what those np.ndarry, int, int formats are); if none is entered, ie it's just a list of np.ndarry or a single np.ndarry, user_id is set to -1 and capture_time set to 0.0

    if already_loaded_model is not None and already_loaded_processor is not None:
        processor = already_loaded_processor
        model = already_loaded_model
    else:
        processor, model = load_model_and_processor(surpress_network_access)
    chunked_audio, clip_dict = split_into_subchunks(byte_arr, chunk_duration=30)
    generated_predictions = process_subchunked_audio(real_byte_arr=chunked_audio, processor=processor, model=model, batch_size=batch_size)
    returned_transcripts = decode_subchunked_audio(running_pred=generated_predictions, clip_id_dict=clip_dict, processor=processor, capture_offset=capture_time, chunk_duration=30)
    return returned_transcripts
    
if __name__ == '__main__':
    print('If you want to test the transcriber, go run the file at ROOT/ai/tests/test_transcriber.py')