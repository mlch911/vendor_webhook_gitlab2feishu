#-*- coding: UTF-8 -*-
from bottle import Bottle, route, run, request, template, static_file
from time import localtime,strftime
import os
import requests
import json
from rich.console import Console

requests.packages.urllib3.disable_warnings()

app = Bottle()
console = Console(width=200)
API_TOKEN = ''

@app.route('/')
@app.route('/<path>')
def index(path='index'):
    print (request.method)  #POST
    print(strftime("%Y-%m-%d %A %H:%M:%S",localtime()))
    print("./", path)
    return static_file(f"{path}.html", root='./html/')
    
@app.route('/css/<path>', method='GET')
def index(path):
    print (request.method)  #POST
    print(strftime("%Y-%m-%d %A %H:%M:%S",localtime()))
    print("./css", path)
    return static_file(f"{path}.html", root='./css/')
##########################################################

@app.route('/vendor_bot', method='POST')
def vendor_bot():
    result = False
    post_string = ''
    post_dict = {}

    global API_TOKEN
    API_TOKEN = request.headers.get('X-Gitlab-Token')
    if API_TOKEN == None or len(API_TOKEN) == 0:
        raise RuntimeError('请先配置.env文件中的API_TOKEN')

    try:
        post_dict = request.json
        print('object_kind', post_dict.get("object_kind"))
        print('push_options', post_dict.get("push_options"))
        console.log(post_dict, log_locals=True)

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
    user_username = post_dict.get('user_username', '')
    username = post_dict.get('user_name', user_username)
    commits = post_dict.get("commits")
    commit_post_dic = {}
    commit_lines = {}
    for commit in commits:
        commit_url = commit.get("url")
        commit_id = commit.get("id")
        commit_msg = commit.get("message")
        
        # 去除 \n 之后的内容，一般为 commit 的描述，不需要在推送中显示
        commit_msg_desc_index = commit_msg.find('\n')
        if commit_msg_desc_index > -1:
            commit_msg = commit_msg[0 : commit_msg_desc_index+1]

        commit_repository_dict = post_dict.get("repository")
        commit_repository_name = commit_repository_dict.get("name", 'NULL')
        commit_branch = post_dict.get("ref")
        if commit_branch.startswith('refs/heads/'):
            commit_branch = commit_branch[len('refs/heads/'):]
        
        if commit_branch not in commit_post_dic:
            commit_post_dic[commit_branch] = {
                'msg_type': 'interactive',
                'card': {
                    'header': {
                        'title': {
                            'content': username + " pushed to branch " + commit_branch + " at repository " + commit_repository_name,
                            'tag': 'plain_text'
                        }
                    },
                    'elements': [],
                }
            }
        
        if commit_branch not in commit_lines:
            commit_lines[commit_branch] = []
        commit_lines[commit_branch].append(f"[{commit_id[0:8]}]({commit_url}): {commit_msg}")

    for (commit_branch, lines) in commit_lines.items():
        commit_post_dic[commit_branch]['card']['elements'].append({
            "tag": "markdown",
            "content": '<br>'.join(lines),
        })

    ##################################################################
    
    for post in commit_post_dic.values():
        post_notification(post)

def generate_merge_request_notification(post_dict):
    username = post_dict['user']['name']
    action = post_dict['object_attributes'].get('action', 'update')
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
                    'content': f"{username} {action} the merge request from **{source_branch}** to **{target_branch}**",
                }
            },
            'elements': [{
                "tag": "markdown",
                "content": f"[{source_branch}]({url})\nState: {state}\nStatus: {status}\nRepository: {repo_name}",
            }],
        }
    }
    post_notification(post_dic)

def generate_note_notification(post_dict):
    username = post_dict['user']['name']
    url = post_dict['object_attributes']['url']
    desc = post_dict['object_attributes']['note']
    source_branch = post_dict['merge_request']['source_branch']
    target_branch = post_dict['merge_request']['target_branch']
    post_dic = {
        'msg_type': 'interactive',
        'card': {
            'header': {
                'title': {
                    'tag': 'lark_md',
                    'content': f"{username} [comment]({url}) on merge request from **{source_branch}** to **{target_branch}**",
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
    console.log(body, log_locals=True)
    response = requests.post(feishu_bot_url, headers=feishu_headers, data=json.dumps(body))
    print(response, response.json())

if __name__ == '__main__':
    run(app, host = '0.0.0.0', port = 6666)
