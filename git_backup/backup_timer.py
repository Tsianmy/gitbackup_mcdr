import mcdreforged.api.all as MCDR
import time
from threading import Timer
from git_backup.utils import print_message, get_format_time
from git_backup.constants import MIN_INTERVAL

def new_timer(interval, call, args=None, kwargs=None, daemon=True, name='smart_backup_timer'):
    tm = Timer(interval, call, args=args, kwargs=kwargs)
    tm.name = name
    tm.daemon = daemon
    tm.start()
    return tm

def cancel_backup_timer(backup_timer):
    if backup_timer is not None:
        backup_timer.cancel()

def flush_backup_timer(backup_timer, call, source: MCDR.PluginCommandSource, config):
    cancel_backup_timer(backup_timer)
    backup_timer = None
    if config.backup_interval >= MIN_INTERVAL:
        now = time.time()
        t = max(2, config.backup_interval - (now - config.last_backup_time))
        print_message(source, 'Next backup time: ' + get_format_time(now + t), tell=False)
        backup_timer = new_timer(t, call)
    else:
        print_message(source, 'backup_timer can not be flushed, ' + 
            f'config.backup_interval {config.backup_interval} < MIN_INTERVAL {MIN_INTERVAL}', tell=False)
    return backup_timer