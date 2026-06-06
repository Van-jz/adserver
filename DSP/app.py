import logging
from flask import Flask, request, Response, jsonify
from google.protobuf.json_format import Parse, MessageToJson
from SimpleDsp import SimpleDSP
from RTB_pb2 import BidRequest
import json

app = Flask(__name__)
dsp = SimpleDSP()

logging.basicConfig(handlers=[logging.FileHandler("kwai_flow.log")], format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger()

@app.errorhandler(400)
def bad_request(error):
    response = jsonify({'error': 'Bad Request', 'message': str(error)})
    response.status_code = 400
    return response

@app.route('/win')
@app.route('/imp')
@app.route('/click')
def just_log_info():
    auction_id = request.args.get("auction_id")
    if not auction_id:
        return bad_request("Missing required parameter: auction_id")
    log.info("\t".join([request.path, "auction_id="+auction_id]))
    return 'OK'

@app.route('/', methods=['POST'])
def handle_bid_request():
    try:
        if request.is_json:
            bid_request = Parse(json.dumps(request.get_json()), BidRequest())
        else:
            bid_request = BidRequest()
            bid_request.ParseFromString(request.get_data())

        one_line_bid_request = json.dumps(MessageToJson(bid_request, preserving_proto_field_name=True), separators=(',', ':'))
        log.error(one_line_bid_request)
        # Process the bid request
        bid_response = dsp.process_bid_request(bid_request)
        
        if bid_response:
            return Response(bid_response.SerializeToString(),mimetype='application/x-protobuf')
        else:
            return ('', 204)  # No bid

    except Exception as e:
        print(f"Error processing request: {e} ")
        import traceback
        print(traceback.format_exc())
        return ('Error processing request', 400)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)