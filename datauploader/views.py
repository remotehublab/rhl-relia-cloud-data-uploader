import json
import time
import logging

from flask import Blueprint, request, jsonify

from datauploader import redis_store

logger = logging.getLogger(__name__)

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/')
def index():
    return "Welcome to the data uploader"

api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/download/sessions/<session_identifier>/tasks/<task_id>/devices/<device_identifier>', methods=['GET', 'DELETE'])
def get_device_updates(session_identifier, task_id, device_identifier):

    if request.method == 'DELETE':
        blocks_key = f'relia:data-uploader:sessions:{session_identifier}:tasks:{task_id}:devices:{device_identifier}:blocks'
        block_identifiers = redis_store.smembers(blocks_key)

        pipeline = redis_store.pipeline()
        for block_identifier in block_identifiers:
            data_block_key = f'relia:data-uploader:sessions:{session_identifier}:tasks:{task_id}:devices:{device_identifier}:blocks:{block_identifier}:from-gnuradio'
            block_alive_key = f'relia:data-uploader:sessions:{session_identifier}:tasks:{task_id}:devices:{device_identifier}:blocks:{block_identifier}:alive'
            pipeline.delete(data_block_key)
            pipeline.delete(block_alive_key)
            pipeline.srem(blocks_key, block_identifier)

        devices_key = f'relia:data-uploader:sessions:{session_identifier}:tasks:{task_id}:devices'
        pipeline.srem(devices_key, device_identifier)
        pipeline.execute()
        return jsonify(success=True)

    blocking = request.args.get('blocking') in ('1', 'true', 'True')

    # 1st: check what blocks are in this device
    blocks_key = f'relia:data-uploader:sessions:{session_identifier}:tasks:{task_id}:devices:{device_identifier}:blocks'

    response = {
        'success': True,
        'data': {
            # block: [items]
        }
    }

    if session_identifier == 'my-session-id' and device_identifier == 'my-device-id':
        return jsonify(response)

    initial_time = time.time()
    maximum_time = 20

    while not response['data']: # while there is no data:
        block_identifiers = redis_store.smembers(blocks_key)

        for block_identifier in block_identifiers:
            if isinstance(block_identifier, bytes):
                block_identifier = block_identifier.decode()
            web2gnuradio_key = f'relia:data-uploader:sessions:{session_identifier}:tasks:{task_id}:devices:{device_identifier}:blocks:{block_identifier}:to-gnuradio'

            block_data = []

            while True:
                item_json = redis_store.lpop(web2gnuradio_key)
                print(web2gnuradio_key, item_json)
                if not item_json:
                    break
                
                if isinstance(item_json, bytes):
                    item_json = item_json.decode()

                try:
                    item = json.loads(item_json)
                except Exception as err:
                    logger.error(f"Error reading item of device {device_identifier} in block {block_identifier}", exc_info=True)
                    continue

                block_data.append(item)

            if block_data:
                response['data'][block_identifier] = block_data

        if response['data']:
            break

        if not blocking:
            break

        elapsed_time = time.time() - initial_time
        if elapsed_time > maximum_time:
            break

        time.sleep(0.1)

    print(response)
    return jsonify(response)

@api_blueprint.route('/upload/sessions/<session_identifier>/tasks/<task_id>/devices/<device_identifier>/blocks/<block_identifier>', methods=['GET', 'POST'])
def device_block_data(session_identifier, task_id, device_identifier, block_identifier):
    """
    This method does not know anything about the widgets themselves, but just stores the information 

    """

    if request.method == 'GET':
        return jsonify(success=False, message="Not implemented yet")

    # else: if POST


    # 
    # {
    #     'block_type': 'relia_time_sink_x',
    #     'type': 'complex64',
    #     'params': {
    #         e.g.,
    #         'nop': '1024',
    #     }
    #     'data': {
    #         e.g.,
    #         'streams': {
    #             '0': {
    #                 'real': [1,2,3],
    #                 'imag': [1,2,3],
    #             }
    #         }
    #     }
    # }
    #
    request_data = request.get_json(force=True, silent=True)
    #print(request_data)

    # Note: if you add keys here, make sure you delete them in the reliabackend/device_data.py

    data_block_key = f'relia:data-uploader:sessions:{session_identifier}:tasks:{task_id}:devices:{device_identifier}:blocks:{block_identifier}:from-gnuradio'
    block_alive_key = f'relia:data-uploader:sessions:{session_identifier}:tasks:{task_id}:devices:{device_identifier}:blocks:{block_identifier}:alive'
    blocks_key = f'relia:data-uploader:sessions:{session_identifier}:tasks:{task_id}:devices:{device_identifier}:blocks'
    devices_key = f'relia:data-uploader:sessions:{session_identifier}:tasks:{task_id}:devices'
    sessions_key = f'relia:data-uploader:sessions'

    pipeline = redis_store.pipeline()
    pipeline.rpush(data_block_key, json.dumps(request_data))

    pipeline.sadd(blocks_key, block_identifier)
    pipeline.sadd(devices_key, device_identifier)
    pipeline.set(block_alive_key, '1')

    # Probably wrong
    pipeline.sadd(sessions_key, session_identifier)
    
    # Expire in 10 minutes (unless someone adds more data here)
    for key in (data_block_key, blocks_key, devices_key, sessions_key, block_alive_key):
        pipeline.expire(key, 60)
    pipeline.execute()

    return jsonify(success=True)
