# coding=utf-8
import os
import sys
import socket
import shutil
import subprocess
import logging
import traceback
from urllib.parse import urljoin
import re

__AUTHOR__ = 'Aploium <i@z.codes>'
__VERSION__ = '0.2.0'
__ZMIRROR_PROJECT_URL__ = 'https://github.com/aploium/zmirror/'
__ZMIRROR_GIT_URL__ = 'https://github.com/aploium/zmirror.git'
__ONKEY_PROJECT_URL__ = 'https://github.com/aploium/zmirror-onekey/'
__ONKEY_PROJECT_URL_CONTENT__ = 'https://raw.githubusercontent.com/aploium/zmirror-onekey/master/'

try:
    import requests
except:
    print('package requests is required for this program, installing now')
    subprocess.call('apt-get update && apt-get install python3 python3-pip -y && python3 -m pip install -U requests',
                    shell=True)
    try:
        import requests
    except:
        print('Could not install requests, program exit')
        exit(1)
    print('--------------------------')

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s %(asctime)s %(funcName)s] %(message)s',
)

if sys.platform != 'linux':
    print('This program can ONLY be used in debian-like Linux (debian, ubuntu and some others)')
    exit(1)
if os.geteuid() != 0:
    print('Root privilege is required for this program. Please use `sudo python3 deploy.py`')
    exit(2)

server_configs = {
    "apache": {
        "config_root": "/etc/apache2/",
        "htdoc": "/var/www/",

        "common_configs": ["http_generic", "apache_boilerplate"],
        "site_unique_configs": ["https"],

        "pre_delete_files": [
            "{config_root}/sites-enabled/000-default.conf",
            "{config_root}/conf-enabled/apache2-doc.conf",
            "{config_root}/conf-enabled/security.conf",
        ],

        "configs": {
            "http_generic": {
                "url": urljoin(__ONKEY_PROJECT_URL_CONTENT__, "configs/apache2-http.conf"),
                "file_path": "conf-enabled/zmirror-http-redirection.conf",
            },
            "apache_boilerplate": {
                "url": urljoin(__ONKEY_PROJECT_URL_CONTENT__, "configs/apache2-boilerplate.conf"),
                "file_path": "conf-enabled/zmirror-apache-boilerplate.conf",
            },
            "https": {
                "url": urljoin(__ONKEY_PROJECT_URL_CONTENT__, "configs/apache2-https.conf"),
                "file_path": "sites-enabled/zmirror-{mirror_name}-https.conf",
            },
        }

    }
}

mirrors_settings = {
    'google': {
        'domain': None,
        'cfg': [('more_configs/config_google_and_zhwikipedia.py', 'config.py'), ],
    },

    'youtubePC': {
        'domain': None,
        'cfg': [('more_configs/config_youtube.py', 'config.py'),
                ('more_configs/custom_func_youtube.py', 'custom_func.py')],
    },

    'twitterPC': {
        'domain': None,
        'cfg': [('more_configs/config_twitter_pc.py', 'config.py'),
                ('more_configs/custom_func_twitter.py', 'custom_func.py'), ],
    },

    'twitterMobile': {
        'domain': None,
        'cfg': [('more_configs/config_twitter_mobile.py', 'config.py'),
                ('more_configs/custom_func_twitter.py', 'custom_func.py'), ],
    },

    'instagram': {
        'domain': None,
        'cfg': [('more_configs/config_instagram.py', 'config.py'), ],
    },
}

print('OneKey deploy script for zmirror. version', __VERSION__)
print('This script will automatically deploy mirror(s) using zmirror in your ubuntu')
print('You could cancel this script in the config stage by precessing Ctrl-C')
print('This Program Only Support Ubuntu 14.04/15.10/16.10+ (for now)')
print()

# ################# 安装一些依赖包 ####################
print('[zmirror] Installing some necessarily packages')
# 设置本地时间为北京时间
subprocess.call('cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime', shell=True)
# 更新apt-get
subprocess.call('apt-get update && apt-get upgrade -y', shell=True)
# 安装必须的包
subprocess.call('apt-get install git python3 python3-pip wget -y', shell=True)
# 安装Apache2和wsgi
subprocess.call("""LC_ALL=C.UTF-8 add-apt-repository -y ppa:ondrej/apache2 &&
apt-key update &&
apt-get update &&
apt-get upgrade -y &&
apt-get install apache2 -y &&
a2enmod rewrite mime include headers filter expires deflate autoindex setenvif ssl http2 &&
apt-get install libapache2-mod-wsgi-py3 -y &&
a2enmod wsgi
""", shell=True)

# 安装和更新必须的python包
subprocess.call('python3 -m pip install -U requests flask', shell=True)
# 安装和更新非必须, 但是有好处的python包
subprocess.call('python3 -m pip install -U chardet fastcache cchardet', shell=True)

print('[zmirror] Installing letsencrypt')
subprocess.call('git clone https://github.com/certbot/certbot.git', shell=True, cwd='/etc/')
subprocess.call('chmod a+x /etc/certbot/certbot-auto', shell=True, cwd='/etc/certbot/')
subprocess.call('yes|./certbot-auto upgrade', shell=True, cwd='/etc/certbot/')

print("[zmirror] Dependencies Installation Completed")

print('\n\n\n\n[zmirror] Now we need some information:')

mirrors_to_deploy = []

_input = -1
while _input:
    _input = input(
        """Please select mirror you want to deploy?
select one mirror a time, you could select zero or more mirror(s)
1. Google (include scholar, image, zh_wikipedia) {google}
2. twitter (PC) {twitterPC}
3. twitter (Mobile) {twitterMobile}
4. youtube (pc) {youtubePC}
5. instagram {instagram}
0. Go to next steps. (OK, I have selected all mirror(s) I want to deploy)

input 0-5: """.format(
            google='[SELECTED]' if 'google' in mirrors_to_deploy else '',
            twitterPC='[SELECTED]' if 'twitterPC' in mirrors_to_deploy else '',
            twitterMobile='[SELECTED]' if 'twitterMobile' in mirrors_to_deploy else '',
            youtubePC='[SELECTED]' if 'youtubePC' in mirrors_to_deploy else '',
            instagram='[SELECTED]' if 'instagram' in mirrors_to_deploy else '',
        )

    )

    if not _input:
        break

    logging.debug("input:" + _input)

    try:
        _input = int(_input)
    except:
        print("Please input correct number")
        _input = -1

    if _input == 0:
        break
    if not (0 <= _input <= 5):
        print('[ERROR] please input correct number (0-5), only select one mirror a time\n'
              '-------------------------\n\n')
        continue

    mirror_type = {
        1: "google",
        2: "twitterPC",
        3: "twitterMobile",
        4: "youtubePC",
        5: "instagram",
    }[_input]

    # 输入镜像对应的域名, 要求已经在DNS设置中用一个A记录指向了本服务器
    while True:  # 这里面会检查输入的是否是三级域名
        domain = input("Please input your domain for this mirror: ")
        domain = domain.strip(' /.\t').replace('https://', '').replace('http://', '')  # 修剪
        if domain.count('.') != 2:
            if input(("Your domain [{domain}] is not an third-level domain, "
                      "which contains three parts and two dots. \n"
                      "eg1: lovelucia.zmirrordemo.com eg2: g.mymirror.com\n"
                      "zmirror officially only support third-level domain\n"
                      "a none third-level domain MAY work, but may cause potential errors\n"
                      "Continue anyway(y/N)?"
                      ).format(domain=domain)) in ('y', 'yes', 'Yes', 'YES'):
                break
                # 如果选择的是 N, 则重新输入
        else:  # 输入的是三级域名
            break

    # 初步检验域名是否已经被正确设置
    try:
        domain_ip = socket.gethostbyname(domain)
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception as e:  # 查询目标域名的IP失败
        print("Sorry, your domain [{domain}] is not setting correctly. {exc}".format(domain=domain, exc=str(e)))
        continue_anyway = input("Continue anyway? (y/N): ")
        if continue_anyway not in ('y', 'yes', 'Yes', 'YES'):
            continue  # 重新来
    else:
        if domain_ip != local_ip:  # 目标域名的IP不等于本地机器的IP
            print("""Sorry, your domain({domain})'s ip does not equals to this machine's ip.
domain's ip is: {domain_ip}
this machine's ip is: {local_ip}
""".format(domain=domain, domain_ip=domain_ip, local_ip=local_ip)
                  )
            continue_anyway = input("Continue anyway? (y/N): ")
            if continue_anyway not in ('y', 'yes', 'Yes', 'YES'):
                continue  # 重新来

    if mirror_type in mirrors_to_deploy:  # 在选项里, 镜像已存在, 则删去
        mirrors_to_deploy.remove(mirror_type)
        print("Mirror:{mirror_type} unchecked.")
    else:
        mirrors_to_deploy.append(mirror_type)
        mirrors_settings[mirror_type]['domain'] = domain
        print("Mirror:{mirror_type} Domain:{domain} checked".format(mirror_type=mirror_type, domain=domain))

    logging.debug(mirrors_to_deploy)

if not mirrors_to_deploy:
    print('[ERROR] you didn\'t select any mirror.\nAbort installation')
    exit(4)

email = input('Please input your email (because letsencrypt requires an email for certification)\n') or 'none@donotexist.com'

print('Your email:', email)
print('You need one domain for each mirror, please input your domain (eg: g.mydomain.com):\n'
      'And set these domain(s)\'s DNS record to this machine\n'
      'domain for every site MUST NOT BE SAME\n'
      'don\'t have an domain? Don\'t panic. Please send an email to the author (aploium email: i@z.codes), '
      'and he will be happily to give you some domains(free)\n')

# 最后确认一遍设置
print('Now, we are going to install, please check your settings here:')
print("Email: " + email)
for mirror in mirrors_to_deploy:
    print("Mirror:{mirror} Domain:{domain}".format(mirror=mirror, domain=mirrors_settings[mirror]['domain']))

if input('really continue (Y/n)? ') in ('N', 'No', 'n', 'no', 'not', 'none'):
    print('installation aborted.')
    exit(5)

# ############### Really Install ###################

# 通过 letsencrypt 获取HTTPS证书
print("Fetching HTTPS certifications")
subprocess.call("service apache2 stop", shell=True)  # 先关掉apache
for mirror in mirrors_to_deploy:
    domain = mirrors_settings[mirror]['domain']
    print("Obtaining: {domain}".format(domain=domain))
    subprocess.call(
        './certbot-auto certonly --agree-tos -t -m "{email}" --standalone -d "{domain}"'
            .format(email=email, domain=domain),
        shell=True, cwd='/etc/certbot/')

    # 检查是否成功获取证书
    if not os.path.exists('/etc/letsencrypt/live/{domain}'.format(domain=domain)):
        print('[ERROR] Could NOT obtain an ssl cert, '
              'please check your DNS record, '
              'and then run again.\n'
              'Installation abort')
        exit(3)
    print("Succeed: {domain}".format(domain=domain))
subprocess.call("service apache2 start", shell=True)  # 重新启动apache

# ####### 安装zmirror自身 #############
print('Obtain SSL cert successfully, now installing zmirror itself')

this_server = server_configs['apache']
htdoc = this_server['htdoc']
config_root = this_server['config_root']
assert isinstance(htdoc, str)
assert isinstance(config_root, str)
os.chdir(htdoc)
subprocess.call('git clone %s zmirror' % __ZMIRROR_GIT_URL__, shell=True, cwd=htdoc)
zmirror_source_folder = os.path.join(htdoc, 'zmirror')

# 预删除文件
for pre_delete_file in this_server['pre_delete_files']:
    abs_path = pre_delete_file.format(
        config_root=config_root, htdoc=htdoc
    )
    print("deleting: " + abs_path)
    try:
        os.remove(abs_path)
    except:
        logging.debug("Unable to remove file:" + abs_path + "\n" + traceback.format_exc())

# 拷贝并设置各个镜像
for mirror in mirrors_to_deploy:
    domain = mirrors_settings[mirror]['domain']
    this_mirror_folder = os.path.join(htdoc, mirror)
    # 将 zmirror 文件夹复制一份
    shutil.copytree(zmirror_source_folder, this_mirror_folder)
    # 更改文件夹所有者为 www-data (apache的用户)
    shutil.chown(this_mirror_folder, "www-data", "www-data")

    this_mirror = mirrors_settings[mirror]

    for file_from, file_to in this_mirror['cfg']:
        shutil.copy(os.path.join(this_mirror_folder, file_from),
                    os.path.join(this_mirror_folder, file_to))

    with open(os.path.join(this_mirror_folder, 'config.py'), 'r+', encoding='utf-8') as fp:
        # noinspection PyRedeclaration
        content = fp.read()

        # 将 my_host_name 修改为对应的域名
        content = re.sub(r"""my_host_name *= *(['"])[-.\w]+\1""",
                         "my_host_name = '{domain}' # Modified by zmirror-onekey".format(domain=domain),
                         content, count=1)
        # 将 my_host_scheme 修改为 https://
        content = re.sub(r"""my_host_scheme *= *(['"])https?://\1""",
                         "my_host_scheme = 'https://' # Modified by zmirror-onekey",
                         content, count=1)
        # 在文件末尾添加 verbose_level = 2
        content += '\nverbose_level = 2 # Added by zmirror-onekey\n'

        fp.seek(0)  # 指针返回文件头
        fp.write(content)  # 回写

shutil.rmtree(zmirror_source_folder)  # 删除无用的 zmirror 文件夹
print("zmirror folders deploy completed")

# ############# 配置Apache ###############
os.chdir(config_root)

# 下载通用配置文件
for conf_name in this_server['common_configs']:
    assert isinstance(config_root, str)
    url = this_server['configs'][conf_name]['url']
    file_path = this_server['configs'][conf_name]['file_path']

    with open(os.path.join(config_root, file_path), 'w', encoding='utf-8') as fp:
        print("downloading: ", conf_name)
        fp.write(requests.get(url).text)

# 下载并设置各个镜像的Apache配置文件
for mirror in mirrors_to_deploy:
    domain = mirrors_settings[mirror]['domain']
    this_mirror_folder = os.path.join(htdoc, mirror)

    for conf_name in this_server['site_unique_configs']:
        url = this_server['configs'][conf_name]['url']
        file_path = this_server['configs'][conf_name]['file_path']

        print("downloading: ", mirror, conf_name)

        conf = requests.get(url).text

        # 因为Apache conf里面有 {Ascii字符} 这种结构, 与python的string format冲突
        # 这边只能手动format
        for key, value in [
            ('domain', domain),
            ('mirror_name', mirror),
            ('path_to_wsgi_py', os.path.join(this_mirror_folder, 'wsgi.py')),
        ]:
            conf = conf.replace("{{%s}}" % key, value)

        with open(os.path.join(config_root, file_path), 'w', encoding='utf-8') as fp:
            fp.write(conf)

# 最后重启一下apache
print("Restarting apache2")
subprocess.call('service apache2 restart', shell=True)

# ####### 完成 ########
print("Completed.")
# 最后打印一遍配置
print("------------ mirrors ------------")
for mirror in mirrors_to_deploy:
    print("Mirror:{mirror} Domain:{domain}".format(mirror=mirror, domain=mirrors_settings[mirror]['domain']))

print("\nFor more information, please view zmirror's github: ", __ZMIRROR_PROJECT_URL__)
