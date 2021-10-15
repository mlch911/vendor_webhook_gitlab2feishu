script_path=`cd $(dirname $0); pwd`
cd $script_path
pip3 install -qr requirements.txt
nohup python3 -u ./vendor_bot_server_feishu.py 2>&1 |tee ./vendor_bot_server_feishu.log &
