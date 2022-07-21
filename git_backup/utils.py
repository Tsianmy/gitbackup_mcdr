import mcdreforged.api.all as MCDR
import subprocess
import time
import os
import shutil
from .constants import PLUGIN_ABBR, PLUGIN_ID

def tr(translation_key: str, *args) -> MCDR.RTextMCDRTranslation:
    return MCDR.ServerInterface.get_instance().rtr('{}.{}'.format(PLUGIN_ID, translation_key), *args)

def log_info(logger, msg):
    if logger is not None:
        logger.info(msg)

def log_warning(logger, msg):
    if logger is not None:
        logger.warning(msg)

def log_except(logger, msg):
    if logger is not None:
        logger.exception(msg)

def print_message(source: MCDR.CommandSource, msg, tell=True, prefix=f'[{PLUGIN_ABBR}] '):
    msg = MCDR.RTextList(prefix, msg)
    if source.is_player and not tell:
        source.get_server().say(msg)
    else:
        source.reply(msg)

def debug_message(debug, *args, **kwargs):
    if debug:
        print('[GBU-DEBUG]', *args, **kwargs)

def get_format_time(time_=None):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time_ if time_ is not None else time.time()))

def run_sh_cmd(source: str, debug=False):
    debug_message(debug, 'Running shell command "{}"'.format(source))
    proc = subprocess.Popen(
        source, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        bufsize=-1)
    stdout0 = [b'', False]
    @MCDR.new_thread("GBU-Popen-reader")
    def reader():
        try:
            debug_message(debug, 'reading stdout...')
            while True:
                buf = proc.stdout.read()
                debug_message(debug, 'read:', buf)
                if len(buf) == 0:
                    break
                stdout0[0] += buf
            debug_message(debug, 'end read')
        finally:
            stdout0[1] = True
    reader()
    debug_message(debug, 'waiting command...')
    exitid = proc.wait()
    debug_message(debug, 'decoding stdout...')
    while not stdout0[1]:
        time.sleep(0.05)
    stdout = ''
    if len(stdout0[0]) > 0:
        try:
            stdout = stdout0[0].decode('utf-8')
        except UnicodeDecodeError:
            stdout = stdout0[0].decode('gbu')
    debug_message(debug, 'returning...', f'exitid: {type(exitid)} {exitid}')
    return 0 if exitid is None else exitid, stdout

def mkdir(path):
    if os.path.isfile(path):
        os.remove(path)
    if not os.path.isdir(path):
        os.mkdir(path)

def copy_files(src: str, dst: str, basename: str, ignores=[], logger=None):
    src_path = os.path.join(src, basename)
    dst_path = os.path.join(dst, basename)

    while os.path.islink(src_path):
        log_info(logger, 'copying {} -> {} (symbolic link)'.format(src_path, dst_path))
        dst_dir = os.path.dirname(dst_path)
        if not os.path.isdir(dst_dir):
            os.makedirs(dst_dir)
        link_path = os.readlink(src_path)
        os.symlink(link_path, dst_path)
        src_path = link_path if os.path.isabs(link_path) else os.path.normpath(os.path.join(os.path.dirname(src_path), link_path))
        dst_path = os.path.join(dst, os.path.relpath(src_path, src))

    log_info(logger, 'copying {} -> {}'.format(src_path, dst_path))
    rmtree(dst_path)
    if os.path.isdir(src_path):
        shutil.copytree(src_path, dst_path, ignore=shutil.ignore_patterns(*ignores))
    elif os.path.isfile(src_path):
        dst_dir = os.path.dirname(dst_path)
        if not os.path.isdir(dst_dir):
            os.makedirs(dst_dir)
        shutil.copy(src_path, dst_path)
    else:
        log_warning(logger, '{} does not exist while copying ({} -> {})'.format(src_path, src_path, dst_path))

def rmtree(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    
def remove_files(folder: str, basename: str, logger=None):
    target_path = os.path.join(folder, basename)

    while os.path.islink(target_path):
        link_path = os.readlink(target_path)
        os.unlink(target_path)
        target_path = link_path if os.path.isabs(link_path) else os.path.normpath(os.path.join(os.path.dirname(target_path), link_path))

    if os.path.isdir(target_path):
        shutil.rmtree(target_path)
    elif os.path.isfile(target_path):
        os.remove(target_path)
    else:
        log_warning(logger, f'[{PLUGIN_ABBR}] {target_path} does not exist while removing')

def get_dir_size(dir_: str):
    size = 0
    for root, dirs, files in os.walk(dir_):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    return size

def format_dir_size(size: int):
    if size < 2 ** 30:
        return f'{round(size / 2 ** 20, 2)} MB'
    else:
        return f'{round(size / 2 ** 30, 2)} GB'