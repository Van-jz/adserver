from flask import Flask, request, Response
from google.protobuf.json_format import Parse, MessageToJson
from SimpleDsp import SimpleDSP
from RTB_pb2 import BidRequest, BidResponse
import traceback
import json

app = Flask(__name__)
dsp = SimpleDSP()

@app.route('/', methods=['POST'])
def handle_bid_request():
    try:
        # Check if the request is JSON
        if request.is_json:
            # Parse JSON to protobuf
            print(request.get_json())
            bid_request = Parse(json.dumps(request.get_json()), BidRequest())
        else:
            # Parse binary protobuf
            bid_request = BidRequest()
            bid_request.ParseFromString(request.get_data())

        # TODO: bid_request to string , write to log

        # Process the bid request
        bid_response = dsp.process_bid_request(bid_request)
        
        if bid_response:
            # Return protobuf response
            return Response(
                bid_response.SerializeToString(),
                mimetype='application/x-protobuf'
            )
        else:
            return ('', 204)  # No bid

    except Exception as e:
        print(f"Error processing request: {e} ")
        print(traceback.format_exc())
        return ('Error processing request', 400)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
