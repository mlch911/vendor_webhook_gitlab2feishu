#-*- coding: UTF-8 -*-
from bottle import Bottle, route, run, request, template, static_file
from time import localtime,strftime
from importlib import reload
import os
import sys
import requests
import json
from xml.dom.minidom import parse
import xml.dom.minidom
from dotenv import load_dotenv
from rich.console import Console

requests.packages.urllib3.disable_warnings()
reload(sys)

load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')

if API_TOKEN == None or len(API_TOKEN) == 0:
    raise RuntimeError('请先配置.env文件中的API_TOKEN')

app = Bottle()

@app.route('/')
@app.route('/<path>')
def index(path='index'):
    print (request.method)  #POST
    print(strftime("%Y-%m-%d %A %H:%M:%S",localtime()))
    print("./", path)
    return static_file("%s.html"%path, root='./html/')
    
@app.route('/css/<path>', method='GET')
def index(path):
    print (request.method)  #POST
    print(strftime("%Y-%m-%d %A %H:%M:%S",localtime()))
    print("./css", path)
    return static_file("%s"%path, root='./css/')
##########################################################

@app.route('/vendor_bot', method='POST')
def vendor_bot():
    result = False
    post_string = ''
    post_dict = {}

    try:
        for key in request.params.keys():
            post_string = post_string + key
        for value in request.params.values():
            post_string = post_string + value
        
        post_dict = json.loads(post_string)
        print(type(post_dict), post_dict)
        
        print('object_kind', post_dict.get("object_kind"))
        print('push_options', post_dict.get("push_options"))
        if post_dict.get("object_kind") == "push":
            result = True
            generate_push_notification(post_dict)
        elif post_dict.get('object_kind') == 'merge_request':
            result = True
            generate_merge_request_notification(post_dict)
        elif post_dict.get('object_kind') == 'note' and post_dict.has_key('merge_request') :
            result = True
            generate_note_notification(post_dict)

    except Exception as err:
        print('===> Exception')
        print(err)
    finally:
        print('===> Finally')
    content = """
创建失败
"""
    if result == True:
        content = """
创建成功
"""
    return content


def generate_push_notification(post_dict):
    commits = post_dict.get("commits")
    commit_post_dic = {}
    commit_lines = {}
    for commit in commits:
        commit_url = commit.get("url")
        commit_id = commit.get("id")
        commit_author_name = commit.get("author").get("name").encode('utf-8').decode('utf-8')
        commit_msg = commit.get("message")
        commit_repository_dict = post_dict.get("repository")
        commit_repository_name = "NULL"
        if commit_repository_dict:
            commit_repository_name = commit_repository_dict.get("name").encode('utf-8').decode('utf-8')
        commit_branch = post_dict.get("ref").encode('utf-8').decode('utf-8')
        if commit_branch.startswith('refs/heads/'):
            commit_branch = commit_branch[len('refs/heads/'):]
        
        if commit_branch not in commit_post_dic:
            commit_post_dic[commit_branch] = {
                'msg_type': 'interactive',
                'card': {
                    'header': {
                        'title': {
                            'content': commit_author_name + " pushed to branch " + commit_branch + " at repository " + commit_repository_name,
                            'tag': 'plain_text'
                        }
                    },
                    'elements': [],
                }
            }
        
        if commit_branch not in commit_lines:
            commit_lines[commit_branch] = []
        commit_lines[commit_branch].append("[%s](%s): %s" %(commit_id[0:8], commit_url, commit_msg))

    for (commit_branch, lines) in commit_lines.items():
        commit_post_dic[commit_branch]['card']['elements'].append({
            "tag": "markdown",
            "content": '<br>'.join(lines).encode('utf-8').decode('utf-8'),
        })

    ##################################################################
    
    for post in commit_post_dic.values():
        post_notification(post)

def generate_merge_request_notification(post_dict):
    username = post_dict['user']['name']
    action = post_dict['object_attributes'].get('action', default='update')
    source_branch = post_dict['object_attributes']['source_branch']
    target_branch = post_dict['object_attributes']['target_branch']
    state = post_dict['object_attributes']['state']
    status = post_dict['object_attributes']['merge_status']
    url = post_dict['object_attributes']['url']
    repo_name = post_dict['repository']['name']
    post_dic = {
        'msg_type': 'interactive',
        'card': {
            'header': {
                'title': {
                    'tag': 'lark_md',
                    'content': "%s %s the merge request from **%s** to **%s**" %(username, action, source_branch, target_branch),
                }
            },
            'elements': [{
                "tag": "markdown",
                "content": "[%s](%s)\nState: %s\nStatus: %s\nRepository: %s" %(source_branch, url, state, status, repo_name),
            }],
        }
    }
    post_notification(post_dic)

def generate_note_notification(post_dict):
    username = post_dict['user']['name']
    url = post_dict['object_attributes']['url']
    desc = post_dict['object_attributes']['note'].encode('utf-8').decode('utf-8')
    source_branch = post_dict['merge_request']['source_branch']
    target_branch = post_dict['merge_request']['target_branch']
    post_dic = {
        'msg_type': 'interactive',
        'card': {
            'header': {
                'title': {
                    'tag': 'lark_md',
                    'content': "%s [comment](%s) on merge request from **%s** to **%s**" %(username, url, source_branch, target_branch),
                }
            },
            'elements': [{
                "tag": "markdown",
                "content": desc,
            }],
        }
    }
    post_notification(post_dic)

def post_notification(body):
    feishu_bot_url="https://open.feishu.cn/open-apis/bot/v2/hook/" + API_TOKEN
    feishu_headers = {"Content-Type": "application/json"}
    Console().log(body, log_locals=True)
    response = requests.post(feishu_bot_url, headers=feishu_headers, data=json.dumps(body))
    print(response, response.json())

if __name__ == '__main__':
    run(app, host = '0.0.0.0', port = 6666)
