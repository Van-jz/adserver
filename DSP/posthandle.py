import logging
from flask import Flask, jsonify, request

posthandle = Flask(__name__)

logging.basicConfig(level=logging.DEBUG,  # 设置日志级别
                    format='%(asctime)s %(levelname)s %(message)s',  # 日志格式
                    datefmt='%Y-%m-%d %H:%M:%S',  # 日期格式
                    handlers=[logging.FileHandler("post.log")])
log = posthandle.logger

@posthandle.route('/')
def hello_world():
    return 'Hello, World!'

@posthandle.errorhandler(400)
def bad_request(error):
    response = jsonify({'error': 'Bad Request', 'message': str(error)})
    response.status_code = 400
    return response

@posthandle.route('/win')
@posthandle.route('/imp')
@posthandle.route('/click')
def win_log():
    # get url params
    auction_id = request.args.get("auction_id")
    if not auction_id:
        return bad_request("Missing required parameter: auction_id")
    log.info("\t".join([request.path, "auction_id="+auction_id]))
    return 'OK'

if __name__ == '__main__':
    posthandle.run(host='0.0.0.0', port=5000)
