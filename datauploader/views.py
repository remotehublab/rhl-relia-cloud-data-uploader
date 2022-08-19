import json
from flask import Blueprint, request, jsonify

from datauploader import redis_store


main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/')
def index():
    return "Welcome to the data uploader"

api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/upload/sessions/<session_identifier>/devices/<device_identifier>/blocks/<block_identifier>', methods=['GET', 'POST'])
def device_block_data(session_identifier, device_identifier, block_identifier):
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
    print(request_data)

    block_key = f'relia:data-uploader:sessions:{session_identifier}:devices:{device_identifier}:blocks:{block_identifier}'
    blocks_key = f'relia:data-uploader:sessions:{session_identifier}:devices:{device_identifier}:blocks'
    devices_key = f'relia:data-uploader:sessions:{session_identifier}:devices'
    sessions_key = f'relia:data-uploader:sessions'

    pipeline = redis_store.pipeline()
    pipeline.rpush(block_key, json.dumps(request_data))

    pipeline.sadd(blocks_key, block_identifier)
    pipeline.sadd(devices_key, device_identifier)

    # Probably wrong
    pipeline.sadd(sessions_key, session_identifier)
    
    # Expire in 10 minutes (unless someone adds more data here)
    for key in (block_key, blocks_key, devices_key, sessions_key):
        pipeline.expire(key, 60 * 10)
    pipeline.execute()

    return jsonify(success=True)
